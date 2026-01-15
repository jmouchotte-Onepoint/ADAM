from Resources.write_sql import *
from Resources.files import write_sql, delete_sql
from Resources.utils import get_origine_source, get_origin_user_type

def init_model(data, model_file, model_rules_file, rls_file):

    # Fin si Null
    if data is None:
        return;
    
    define_table_name_rls = []
    define_row_rsl = {}

    for object_type, config in data.items():

        define_user_type_roles = config.get('roles', {})
        define_object_relations = config.get('relations', {})
        define_relations_types = ['relations', 'roles', 'permissions']

        #Exploration des règles
        for relation_type in define_relations_types:
            for json_obj in config.get(relation_type, {}):
            
                #Exploration des relations, roles, permissions
                for new_relation, relation_object_info in json_obj.items():

                    #Activation des POLICY / Conditions
                    if new_relation != "policy":
                        list_policy = json_obj.get("policy",[])
                        for policy in list_policy :
                            # Variable pour les properties
                            policy_table_name = policy.get("resource",None)
                            policy_object_type = policy.get("object_type",object_type)
                            policy_action = policy.get("action",None)

                            policy_name = policy_action + "_" + policy_table_name.replace('.','_')
                            # Activation des Policy
                            if (policy_name not in define_table_name_rls):
                                res = init_row_level(policy_name, policy_table_name, relation_type, policy_action)
                                define_table_name_rls.append(policy_name)
                                define_row_rsl[policy_name] = [res]
                            # Ajout des Policy
                            if (policy_table_name != None and policy_action!=None):
                                res = add_new_row_level_in_list(policy, policy_table_name, policy_object_type, relation_type, new_relation)
                                define_row_rsl[policy_name].append(res)

                        #Ecriture des contions du models
                        for info in relation_object_info:
                            #Activation des RULES / models
                            list_rules = info.get("rules",[])

                            for relation_source_type, relation_value in info.items():
                                #Extraction from
                                if relation_source_type == 'rules': break
                                relation_source, condition, relation_origin = get_origine_source(relation_value)

                                #Relations parents - from // relations, roles, permissions
                                if relation_origin != None:
                                    relation = relation_source
                                    list_relation = [relation_source]
                                #Relations directs depuis un roles
                                elif relation_source_type == 'roles':
                                    list_relation = get_origin_user_type(relation_source, define_user_type_roles)
                                    list_relation += get_origin_user_type(relation_source, define_user_type_roles, 'roles')  
                                #Relations directs depuis une relation
                                else:
                                    # ajoute les relations parents pour rechercher le type d'origine
                                    list_relation = [relation_source]

                                for relation in list_relation:
                                    array_origin_user_type = get_origin_user_type(relation, define_object_relations)
                                    #Si relation avec héritage // from origine
                                    if relation_origin is None:
                                        relation, _, relation_origin = get_origine_source(relation)
                                    # Recuperation de la relation en fonction de si il y a une origine                                    
                                    if relation_origin != None: 
                                        array_origin_user_type = get_origin_user_type(relation_origin, define_object_relations)
                                    else:
                                        array_origin_user_type = get_origin_user_type(relation, define_object_relations)

                                    # Insertion direct, relations, roles, permissions sans references
                                    if len(array_origin_user_type) == 0:
                                        model_id = write_model(model_file, relation_type, relation_source, new_relation, relation_source_type, object_type, new_relation, relation_origin, condition)
                                        write_model_rules(model_rules_file, model_id, list_rules)
                                    # Insertion par la relation d'origine
                                    else:
                                        for user_type in array_origin_user_type:
                                            model_id = write_model(model_file, relation_type, user_type, relation, relation_source_type, object_type, new_relation, relation_origin, None)
                                            write_model_rules(model_rules_file, model_id, list_rules)

    # Ecriture des RLS dans le fichier final
    for key in define_row_rsl:
        write_sql(rls_file,"\tOR".join(define_row_rsl[key]) + "); \n")
    
def init_tenants(data,tenants_file):
    # Fin si Null
    if data is None:
        return;
    # Ecriture & Exploration
    for entry in data:
        tenantId = entry["id"]
        name = entry["name"]
        description = entry["description"]
        write_sql_data_tenants(tenants_file, tenantId, name, description);

def init_sql_rules(data,dynamic_rules_file):
    # Fin si Null
    if data is None:
        return;
    # Ecriture & Exploration
    for entry in data:
        id = entry["id"]
        rule = entry["sql"]
        description = entry.get("description",None)
        params = entry.get("params",None)
        write_sql_rules(dynamic_rules_file, id, rule, params, description)

def init_files(array_path_file):
    # Initilisation des fichiers
    for file in array_path_file:
        # Suppression des vieux fichiers
        delete_sql(file)   
        # Initialisation des fichiers
        write_sql(file, f"""--- Initialisation ---""");
