import yaml, os

def read_yaml(file_path, desc=''):
    try:
        print(f"Chargement du fichier {desc} : {file_path}")
        with open(file_path, "r") as f:
            return yaml.safe_load(f.read().replace("type ", "").replace("define ", ""))
    except FileNotFoundError:
        print(f"Fichier non trouvé : {file_path}")
        exit(-1)
    except yaml.YAMLError as e:
        print(f"Erreur YAML : {e}")
        exit(-1)

def delete_sql(file_path):    
    if os.path.exists(file_path):
        os.remove(file_path)

def write_sql(file_path, data):
    with open(file_path, "a") as sql_file:
        sql_file.write(f"""{data}\n""")