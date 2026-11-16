# Émissions de CO₂ des voitures neuves en France

Analyse exploratoire des émissions homologuées (g/km) en 2022–2024, des écarts départementaux et de leur association avec les motorisations. Les fichiers bruts SDES et le fond de carte Etalab sont conservés dans `data/raw/` avec leurs liens dans [data/raw/README.md](data/raw/README.md).

## Utilisation

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python prepare_data.py
.venv/bin/jupyter lab main.ipynb
```

Le script vérifie la structure, la couverture, les clés, les parts et les dénominateurs avant de créer `data/processed/tableau_departement_2022_2024.csv` (303 lignes : 101 départements × 3 années). Le notebook contient l'analyse et sept graphiques, dont deux cartes. Il peut être exécuté depuis la racine du projet.

La moyenne nationale est pondérée par les immatriculations. La catégorie « électrique et hydrogène » est celle publiée par le SDES ; elle ne permet pas d'isoler les seules voitures électriques. Les émissions sont homologuées à l'échappement, et les corrélations départementales ne prouvent pas une causalité.
