from Resources.write_sql import write_sql_data_relations, write_sql_data_roles
def insertRelations(data,rebac_dev_test_file):

    for tenant_id in data :
        for entry in data[tenant_id]:
            user = entry["user"]
            obj = entry["object"]
            relation = entry["relation"]

            object_type, object_id = obj.split(":", 1)
            user_type, user_id = user.split(":", 1)

            entry_type = entry.get('type', 'relations')
            if entry_type == 'roles':
                write_sql_data_roles(rebac_dev_test_file, user_type, user_id, relation, object_type, object_id, tenant_id)
            else:
                write_sql_data_relations(rebac_dev_test_file, user_type, user_id, relation, object_type, object_id, tenant_id, entry_type);

