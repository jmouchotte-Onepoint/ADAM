#!/bin/sh
set -e
clear

# Arrêt et suppression des conteneurs, réseaux et volumes
docker compose down -v

# --- Vérification de l'argument ---
if [ -z "$1" ]; then
    echo "===== Commands ====="
    echo "Usage: $0 <nom_du_parcours> [schema_cible]"
    echo "Exemple: $0 Woodgrove adam_demo"
    exit 1
fi

EXAMPLE_NAME="$1"
TARGET_SCHEMA="${2:-adam}"
export TARGET_SCHEMA

echo "Schema cible Liquibase: ${TARGET_SCHEMA}"

case "$TARGET_SCHEMA" in
    ''|*[!a-zA-Z0-9_]*)
        echo "Erreur: schema_cible invalide. Utilisez uniquement [a-zA-Z0-9_]."
        exit 1
        ;;
esac

# Nettoyer les folder sans supprimer .gitkeep
find ./docker/postgres/docker-entrypoint-initdb.d/ -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +
find ./ADAM/4_INSERT/ -mindepth 1 ! -name 'changelog.xml' -exec rm -rf {} +
find ./ADAM/5_DEV_TEST/ -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +

# Copier tous les fichiers nécessaires (remplace selon tes besoins)
cp -r ./Examples/${EXAMPLE_NAME}/Database/docker-entrypoint-initdb.d/* ./docker/postgres/docker-entrypoint-initdb.d/
cp -r ./Examples/${EXAMPLE_NAME}/Database/adam-entrypoint-dev-test.d/* ./ADAM/5_DEV_TEST/

# Génère un script d'init PostgreSQL pour créer le schéma cible et l'utiliser par défaut
cat > ./docker/postgres/docker-entrypoint-initdb.d/0000-init-target-schema.sql <<EOF
CREATE SCHEMA IF NOT EXISTS ${TARGET_SCHEMA};
ALTER ROLE postgres IN DATABASE adamdb SET search_path TO ${TARGET_SCHEMA}, public;
EOF

# Exécution des scripts Python via uv si disponible (fallback vers python3)
PYTHON_CMD="python3"
if command -v uv >/dev/null 2>&1; then
    PYTHON_CMD="uv run"
fi

${PYTHON_CMD} ./main.py --models ./Examples/${EXAMPLE_NAME}/init-models.yml
${PYTHON_CMD} ./main.py --relations ./Examples/${EXAMPLE_NAME}/dev-init-relations.yml

## Démarrage des conteneurs en arrière-plan
docker compose up -d