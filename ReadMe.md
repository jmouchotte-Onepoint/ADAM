# 🚀 Ce projet permet l'initilisation d'un model ADAM

Ce script permet de charger une configuration ainsi que des données de test (relations, tenants) afin de faciliter le développement et les tests.  

## 📦 Prérequis

### Installation Python & dépendances

- **Python 3.10+** installé sur votre machine  
- Installation des dépendances (si présentes dans un `requirements.txt`) :  

```bash
pip install -r requirements.txt
```

## Lancer un exemple

### Initialiser la DB

- **Description** : Création des schémas et tables qui correspondront à la future application
- **Type** : `.sql`
- **Valeur par défaut** : `None`  
- **Origin** : `./Example/${example_name}/Docker/docker-entrypoint-initdb.d/`
- **Source** : `./Docker/postgres/docker-entrypoint-initdb.d/`

### Initialiser Utilisateurs

- **Description** : Création d'utilisateur, attribution de rôle et insertion de données pour test local
- **Type** : `.sql`
- **Valeur par défaut** : `None`  
- **Origin** : `./Example/${example_name}/Docker/docker-entrypoint-adam.d/`
- **Source** : `./ADAM/4_DEV_TEST/*`

### Initialiser ADAM

- **Description** : Création des fichier pour créer les règles, attributs, tenants etc.
- **Type** : `.yml` et `.json`
- **Valeur par défaut** : `None` 
- **Source** : 
  - `./Example/${example_name}/init_models.yaml`
  - `./Example/${example_name}/dev-init-relations.yaml`
- **Outputs x InitModel** : 
  - `./ADAM/4_INSERT/INSERT-DYNAMIC-RULES.sql`
  - `./ADAM/4_INSERT/INSERT-MODEL-POLICY-RULES.sql`
  - `./ADAM/4_INSERT/INSERT-MODEL-POLICY.sql`
  - `./ADAM/4_INSERT/INSERT-RLS-POLICY.sql`
  - `./ADAM/4_INSERT/INSERT-TENANTS.sql`
- **Outputs x InitRelations** : 
  - `./ADAM/5_DEV_TEST/ADAM-0001-ADD-RELATIONS.sql`

### Lancement

- **Description** : Lancement local d'un environnement de test pour un des exemples à l'aide d'une commande bash & docker
- **Exemple** :  
  ```bash
  sh example.sh Spirodoc/Kanalyse/Qfq
  ```

## ⚙️ Arguments disponibles (main.py)

Le script accepte les paramètres suivants :  

### `--models`  
- **Description** : chemin vers un fichier **YAML** contenant la configuration des modèles.  
- **Type** : `str` (fichier YAML)  
- **Valeur par défaut** : `None`  
- **Exemple** :  
  ```bash
  python main.py --models ./Examples/Spirodoc/init-models.yml
  ```
- **Résultat** : Création des fichiers pour le modèles, les règles, les RLS et le tenants :
  - `./ADAM/4_INSERT/INSERT-DYNAMIC-RULES.sql`
  - `./ADAM/4_INSERT/INSERT-MODEL-POLICY-RULES.sql`
  - `./ADAM/4_INSERT/INSERT-MODEL-POLICY.sql`
  - `./ADAM/4_INSERT/INSERT-RLS-POLICY.sql`
  - `./ADAM/4_INSERT/INSERT-TENANTS.sql`

### `--relations`  
- **Description** : chemin vers un fichier **JSON** contenant les relations à créer 
- **Type** : `str` (fichier JSON)  
- **Valeur par défaut** : `None`  
- **Exemple** :  
  ```bash
  python main.py --relations ./Examples/Spirodoc/init-relations.yml
  ```
- **Résultat** : Création du fichier pour insérer les relations en sql `./ADAM/5_DEV_TEST/ADAM-0001-ADD-RELATIONS.sql`
- **Remarques**: Ajouter ce fichier dans le changelog.xml dans le docker l'exemple pour être utiliser par liquidbase au run