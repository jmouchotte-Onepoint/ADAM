#!/bin/sh
set -e
clear

# Arrêt et suppression des conteneurs, réseaux et volumes
docker compose down -v

# --- Vérification de l'argument ---
if [ -z "$1" ]; then
    echo "===== Commands ====="
    echo "Usage: $0 <nom_du_parcours>"
    echo "Exemple: $0 Spirodoc"
    exit 1
fi

EXAMPLE_NAME="$1"

# Nettoyer les folder sans supprimer .gitkeep
find ./docker/postgres/docker-entrypoint-initdb.d/ -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +
find ./ADAM/4_INSERT/ -mindepth 1 ! -name 'changelog.xml' -exec rm -rf {} +
find ./ADAM/5_DEV_TEST/ -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +

# Copier tous les fichiers nécessaires (remplace selon tes besoins)
cp -r ./Examples/${EXAMPLE_NAME}/Database/docker-entrypoint-initdb.d/* ./docker/postgres/docker-entrypoint-initdb.d/
cp -r ./Examples/${EXAMPLE_NAME}/Database/adam-entrypoint-dev-test.d/* ./ADAM/5_DEV_TEST/

# Exécution des scripts Python
python ./main.py --models ./Examples/${EXAMPLE_NAME}/init_models.yml
python ./main.py --relations ./Examples/${EXAMPLE_NAME}/dev-init-relations.yml

## Démarrage des conteneurs en arrière-plan
docker compose up -d