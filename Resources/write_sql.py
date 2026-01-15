from Resources.utils import esc, sql_value, sql_array
from Resources.files import write_sql
from uuid6 import uuid7

def init_row_level(policy_name, policy_table_name, adam_table, policy_action):  
    # Determine the policy clause based on the authorization type
    if policy_action == "insert":
        policy_clause = "WITH CHECK"
    else:
        policy_clause = "USING"

    # Construct the SQL data for the row-level security policy
    data = f"""ALTER TABLE {policy_table_name} ENABLE ROW LEVEL SECURITY;\n\n"""
    data +=  f"""CREATE POLICY adam_policy_{policy_name} ON {policy_table_name}
    FOR {policy_action.upper()}
    {policy_clause} (
        EXISTS (
            SELECT 1 FROM adam.{adam_table} AS rrp
            WHERE rrp.tenant_id = adam.get_current_tenant_id() 
            AND adam.is_allow('read')  
        )\n"""
    return data;
    
def add_new_row_level_in_list(policy, policy_table_name, policy_object_type, adam_table, relation):

    data = f"""\n\t\tEXISTS (
            SELECT 1 FROM adam.{adam_table} AS rrp
            WHERE rrp.relation = '{relation}'
            AND rrp.object_type = '{policy_object_type}'
            AND rrp.allow_deny IS TRUE
            AND rrp.user_id = adam.get_current_user_id()
            AND rrp.tenant_id = adam.get_current_tenant_id()"""
    
    # Ajoute les règles si attributes
    if policy.get("attributes",False) == True:
        data += f"""\n\t\t\tAND adam.fn_check_all_attributes_from_view(rrp.id::UUID, '{adam_table}', adam.get_current_user_attributes())"""
    # Ajoute les règles si rules active
    if policy.get("rules",False) == True:
        data += f"""\n\t\t\tAND adam.fn_check_all_rules_from_view(rrp.id::UUID, '{adam_table}', adam.get_current_user_attributes())"""
    # Ajoute de conditions sur les colonnes
    conditions_sql = format_conditions(policy.get("conditions",None), policy_table_name)
    if conditions_sql :
        data += conditions_sql

    data += """\n\t\t)\n"""
    return data

def format_conditions(array_json_conditions, app_table_name):
    conditions_sql = None

    if array_json_conditions is not None and len(array_json_conditions) > 0:
        lines = []
        for item in array_json_conditions:
            for key, value in item.items():
                if "like" in str(value):
                    lines.append(f"{app_table_name}.{key} {value}")
                elif (value in ['object_type', 'object_id', 'relation', 'user_type', 'user_id', 'tenant_id']):
                    lines.append(f"{app_table_name}.{key} = rrp.{value}")
                else:
                    lines.append(f"{app_table_name}.{key} = '{value}'")
        
        # Construire la chaîne finale avec AND et retours à la ligne
        conditions_sql = "\n\t\t\tAND " + "\n\t\t\tAND ".join(lines)

    return conditions_sql

def write_model(file_path, relation_type, user_type, relation_source, relation_source_type, object_type, relation, relation_origin=None, condition=None):   
    model_id = uuid7(); 
    data = ("INSERT INTO adam.model (id, relation_type, user_type, relation_source, object_type, relation, relation_origin, condition, relation_source_type) "
        f"VALUES ({sql_value(model_id)},{sql_value(relation_type.upper())}, {sql_value(user_type)}, {sql_value(relation_source)}, {sql_value(object_type)}, {sql_value(relation)}, {sql_value(relation_origin)}, {sql_value(condition)}, {sql_value(relation_source_type.upper())});")
    
    #Sauvegarde dans le fichier SQL
    write_sql(file_path, data)
    return model_id

def write_model_rules(file_path, model_id, list_rules): 
    data = ''
    for rule in list_rules:
        data += ("INSERT INTO adam.model_rules (model_id, rule_id, params) "
            f"VALUES ({sql_value(model_id)},{sql_value(rule.get('id'))}, {sql_value(rule.get('params'))});")
    #Sauvegarde dans le fichier SQL
    if data != '':
        write_sql(file_path, data)
    
def write_sql_data_relations(file_path, user_type, user_id, relation, object_type, object_id, tenant_id, table='relations'):
    data = (f"INSERT INTO adam.{table} (user_type,user_id, relation, object_type, object_id, tenant_id) "
            f"VALUES ('{esc(user_type)}', '{esc(user_id)}','{esc(relation)}', '{esc(object_type)}', '{esc(object_id)}', '{esc(tenant_id)}');")
    write_sql(file_path, data)

def write_sql_data_tenants(file_path, tenant_id, name, description):
    data = (f"INSERT INTO adam.tenants (id, name, description) "
            f"VALUES ({sql_value(tenant_id)}, {sql_value(name)}, {sql_value(description)});")
    write_sql(file_path, data)

def write_sql_rules(file_path, id, rule, params, description):
    data = (f"INSERT INTO adam.dynamic_rules (id, rule, params, description) "
            f"VALUES ({sql_value(id)}, {sql_value(rule)}, {sql_array(params)}, {sql_value(description)});")
    write_sql(file_path, data)