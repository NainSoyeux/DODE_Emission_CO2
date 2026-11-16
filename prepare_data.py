"""Contrôles et consolidation des deux fichiers départementaux du SDES.

Exécution : python prepare_data.py
Les codes départementaux restent des chaînes (01, 2A, 971, etc.).
"""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "tableau_departement_2022_2024.csv"

ENERGIES = {
    "Diesel - hybride NR": "diesel_hybride_nr",
    "Diesel - thermique": "diesel_thermique",
    "Electrique et hydrogène": "electrique_hydrogene",
    "Essence - hybride NR": "essence_hybride_nr",
    "Essence - thermique": "essence_thermique",
    "Gaz et ND": "gaz_nd",
    "Hybride rechargeable": "hybride_rechargeable",
}


def load_and_validate():
    motor = pd.read_csv(RAW / "motorisations_departement.csv", dtype={"geocode_departement": "string"})
    co2 = pd.read_csv(RAW / "emissions_departement.csv", dtype={"geocode_departement": "string"})

    assert len(motor) == 4_949 and len(co2) == 303, "Nombre de lignes inattendu : vérifier les sources."
    assert set(motor["type_energie"]) == set(ENERGIES), "Catégories de motorisation modifiées."
    assert not motor.isna().any().any() and not co2.isna().any().any(), "Valeurs manquantes dans les CSV."
    assert motor["geocode_departement"].str.fullmatch(r"(?:\d{2,3}|2[AB])").all()
    assert co2["geocode_departement"].str.fullmatch(r"(?:\d{2,3}|2[AB])").all()

    motor["annee"] = pd.to_numeric(motor["annee"], errors="raise").astype(int)
    co2["annee"] = pd.to_datetime(co2["date_mesure"], errors="raise").dt.year
    assert (pd.to_datetime(motor["date_mesure"]).dt.year == motor["annee"]).all()
    assert set(motor["annee"]) == set(range(2019, 2026))
    assert set(co2["annee"]) == {2022, 2023, 2024}

    for frame in (motor, co2):
        for col in ("numerateur", "denominateur", "valeur"):
            frame[col] = pd.to_numeric(frame[col], errors="raise")
        assert (frame["denominateur"] > 0).all()
        assert (frame["numerateur"] >= 0).all()

    key = ["annee", "geocode_departement"]
    assert not motor.duplicated(key + ["type_energie"]).any()
    assert not co2.duplicated(key).any()
    assert motor.groupby(key).size().eq(7).all()
    assert motor.groupby("annee")["geocode_departement"].nunique().eq(101).all()
    assert co2.groupby("annee")["geocode_departement"].nunique().eq(101).all()
    assert motor.groupby(key)["denominateur"].nunique().eq(1).all()

    counts = motor.groupby(key, as_index=False).agg(
        n_voitures=("numerateur", "sum"),
        denominateur_mot=("denominateur", "first"),
    )
    assert (counts["n_voitures"] == counts["denominateur_mot"]).all()
    assert ((motor["valeur"] - 100 * motor["numerateur"] / motor["denominateur"]).abs() <= 0.0051).all()
    assert ((co2["valeur"] - co2["numerateur"] / co2["denominateur"]).abs() <= 0.0501).all()

    motor["energie"] = motor["type_energie"].map(ENERGIES)
    wide = motor.pivot(index=key, columns="energie", values="numerateur")
    wide.columns = [f"n_{c}" for c in wide.columns]
    wide = wide.reset_index()
    wide = wide.merge(counts, on=key, validate="one_to_one")
    wide["n_essence"] = wide["n_essence_hybride_nr"] + wide["n_essence_thermique"]
    wide["n_diesel"] = wide["n_diesel_hybride_nr"] + wide["n_diesel_thermique"]
    for name in ("essence", "diesel", "hybride_rechargeable", "electrique_hydrogene", "gaz_nd"):
        wide[f"part_{name}_pct"] = 100 * wide[f"n_{name}"] / wide["n_voitures"]
    assert (wide[[f"part_{n}_pct" for n in ("essence", "diesel", "hybride_rechargeable", "electrique_hydrogene", "gaz_nd")]].sum(axis=1) - 100).abs().max() < 1e-9

    co2 = co2.rename(columns={
        "libelle_departement": "departement",
        "numerateur": "somme_co2_g_km",
        "denominateur": "n_voitures_co2",
        "valeur": "co2_publie_g_km",
    })
    cols = key + ["departement", "somme_co2_g_km", "n_voitures_co2", "co2_publie_g_km"]
    wide_overlap = wide[wide["annee"].isin({2022, 2023, 2024})]
    merged = co2[cols].merge(wide_overlap, on=key, how="outer", validate="one_to_one", indicator=True)
    assert merged["_merge"].eq("both").all(), "Clés non appariées."
    assert merged["n_voitures"].eq(merged["n_voitures_co2"]).all(), "Dénominateurs différents."
    merged["co2_g_km"] = merged["somme_co2_g_km"] / merged["n_voitures_co2"]
    merged = merged.drop(columns=["_merge", "denominateur_mot", "n_voitures_co2"])
    merged = merged.sort_values(key).reset_index(drop=True)
    assert len(merged) == 303
    return motor, co2, merged


def national(merged):
    count_cols = [c for c in merged if c.startswith("n_") and c != "n_voitures"]
    totals = merged.groupby("annee", as_index=False)[["somme_co2_g_km", "n_voitures"] + count_cols].sum()
    totals["co2_g_km"] = totals["somme_co2_g_km"] / totals["n_voitures"]
    for name in ("essence", "diesel", "hybride_rechargeable", "electrique_hydrogene", "gaz_nd"):
        totals[f"part_{name}_pct"] = 100 * totals[f"n_{name}"] / totals["n_voitures"]
    return totals


if __name__ == "__main__":
    motor, co2, merged = load_and_validate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT, index=False, float_format="%.10f")
    print(f"{len(motor)} lignes motorisations ; {len(co2)} lignes CO₂ ; {len(merged)} lignes consolidées")
    print(f"Tableau enregistré : {OUT.relative_to(ROOT)}")
    print(national(merged)[["annee", "n_voitures", "co2_g_km", "part_electrique_hydrogene_pct"]].round(2).to_string(index=False))
