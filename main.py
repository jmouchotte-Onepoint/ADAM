from Resources.files import read_yaml, delete_sql
import argparse, init_archi_rls_sql, init_data_dev_test

def main():

    # Configuration des arguments du script
    parser = argparse.ArgumentParser(description="Un exemple de script avec des paramètres.")
    parser.add_argument("--models", help="Fichier yaml contenant la configuration", default=None)
    parser.add_argument("--relations", help="Fichier json contenant des relations pour dev/test", default=None)
    args = parser.parse_args()

    # Configuration des fichiers de sorties
    model_file = "./ADAM/4_INSERT/INSERT-MODEL-POLICY.sql"
    model_rules_file = "./ADAM/4_INSERT/INSERT-MODEL-POLICY-RULES.sql"
    dynamic_rules_file = "./ADAM/4_INSERT/INSERT-DYNAMIC-RULES.sql"
    tenants_file = "./ADAM/4_INSERT/INSERT-TENANTS.sql"
    rls_file = "./ADAM/4_INSERT/INSERT-RLS-POLICY.sql"
    rebac_relation_dev_test_file = "./ADAM/5_DEV_TEST/ADAM-0001-ADD-RELATIONS.sql"

    # Initialisation du models / architecture
    if args.models is not None:
        init_archi_rls_sql.init_files([model_file,model_rules_file,rls_file,tenants_file,dynamic_rules_file])
        # Lire le fichier YAML
        data = read_yaml(args.models,"initialisation models")
        # Ecriture des configurations dans le fichier SQL
        init_archi_rls_sql.init_model(data.get("models",None), model_file, model_rules_file, rls_file)
        # Ecriture des configurations dans le fichier SQL
        init_archi_rls_sql.init_tenants(data.get("tenants",None), tenants_file)
        # Ecriture des configurations dans le fichier SQL
        init_archi_rls_sql.init_sql_rules(data.get("rules",None), dynamic_rules_file)

    # Initialisation des relations pour dev/test  
    if args.relations is not None:
        # Suppression des fichiers SQL existants
        delete_sql(rebac_relation_dev_test_file)
        # Lire le fichier YAML
        data = read_yaml(args.relations,"relations")
        # Ecriture des relations dans le fichier SQL
        init_data_dev_test.insertRelations(data, rebac_relation_dev_test_file)

if __name__ == "__main__":
    main()