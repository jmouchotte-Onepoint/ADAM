"""Point d'entrée CLI : transforme une configuration YAML en fichiers SQL ADAM."""

import argparse

from Examples.generator import models, relations
from Examples.generator.files import read_yaml, delete_sql

# Fichiers de sortie consommés par les changelogs Liquibase
MODEL_FILE = "./ADAM/4_INSERT/INSERT-MODEL-POLICY.sql"
MODEL_RULES_FILE = "./ADAM/4_INSERT/INSERT-MODEL-POLICY-RULES.sql"
DYNAMIC_RULES_FILE = "./ADAM/4_INSERT/INSERT-DYNAMIC-RULES.sql"
TENANTS_FILE = "./ADAM/4_INSERT/INSERT-TENANTS.sql"
RLS_FILE = "./ADAM/4_INSERT/INSERT-RLS-POLICY.sql"
RELATIONS_DEV_TEST_FILE = "./ADAM/5_DEV_TEST/ADAM-0001-ADD-RELATIONS.sql"


def main():

    # Configuration des arguments du script
    parser = argparse.ArgumentParser(
        description="Génère les fichiers SQL ADAM (modèle, politiques, RLS, tenants, relations) depuis un YAML."
    )
    parser.add_argument("--models", help="Fichier yaml contenant la configuration", default=None)
    parser.add_argument("--relations", help="Fichier yaml contenant des relations pour dev/test", default=None)
    args = parser.parse_args()

    # Initialisation du models / architecture
    if args.models is not None:
        models.init_files([MODEL_FILE, MODEL_RULES_FILE, RLS_FILE, TENANTS_FILE, DYNAMIC_RULES_FILE])
        # Lire le fichier YAML
        data = read_yaml(args.models, "initialisation models")
        # Ecriture des configurations dans le fichier SQL
        models.init_model(data.get("models", None), MODEL_FILE, MODEL_RULES_FILE, RLS_FILE)
        # Ecriture des configurations dans le fichier SQL
        models.init_tenants(data.get("tenants", None), TENANTS_FILE)
        # Ecriture des configurations dans le fichier SQL
        models.init_sql_rules(data.get("rules", None), DYNAMIC_RULES_FILE)

    # Initialisation des relations pour dev/test
    if args.relations is not None:
        # Suppression des fichiers SQL existants
        delete_sql(RELATIONS_DEV_TEST_FILE)
        # Lire le fichier YAML
        data = read_yaml(args.relations, "relations")
        # Ecriture des relations dans le fichier SQL
        relations.insertRelations(data, RELATIONS_DEV_TEST_FILE)


if __name__ == "__main__":
    main()
