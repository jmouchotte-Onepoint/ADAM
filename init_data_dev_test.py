from Resources.write_sql import write_sql_data_relations
def insertRelations(data,rebac_dev_test_file):

    for tenant_id in data :
        for entry in data[tenant_id]:
            user = entry["user"]
            obj = entry["object"]
            relation = entry["relation"]

            object_type, object_id = obj.split(":", 1)
            user_type, user_id = user.split(":", 1)

            write_sql_data_relations(rebac_dev_test_file, user_type, user_id, relation, object_type, object_id, tenant_id, entry.get('type','relations'));

