"""Génération des fichiers SQL ADAM à partir d'une configuration YAML.

- `models`    : modèle, politiques RBAC/RUBAC, RLS, tenants et règles dynamiques
- `relations` : jeux de relations/rôles pour le dev et les tests
- `write_sql` : écriture des instructions SQL
- `files`     : lecture YAML et gestion des fichiers de sortie
- `utils`     : échappement et conversion des valeurs SQL
"""
