def esc(val):
    return str(val).replace("'", "\"") if val else ""

def sql_value(val):
    return "NULL" if val is None or val == "" else f"'{esc(val)}'"

def sql_array(val):
    # Convert params list to PostgreSQL array format
    if val is not None and isinstance(val, list):
        # Convert Python list to PostgreSQL array syntax: {"item1", "item2"}
        sql_array = "{" + ",".join(f'"{p}"' for p in val) + "}"
    else:
        sql_array = val
    return f"'{sql_array}'"

def split_user_type_condition(value: str):
    if "#" in value:
        return value.split("#", 1)
    return value, None

def get_origine_source(exp: str, default=None):
    if " from " in exp:
        relation_user_condition, relation_source = exp.split(" from ", 1)
    else:
        relation_user_condition, relation_source = exp, default

    relation_or_user_type, condition = split_user_type_condition(relation_user_condition)
    return relation_or_user_type, condition, relation_source

def get_origin_user_type(relation_source_name, array_relation, relation_type='relations'):
    if array_relation == {} : return []

    result = []
    for json_relation in array_relation:
        #Exploration des relations
        for relation, json_user_type in json_relation.items():
            # Récuperation si relation match
            if relation == relation_source_name:
                for user_type in json_user_type:
                    # Récuperation relation, relation_type
                    if relation_type in user_type:
                        clean_user_type, condition = split_user_type_condition(user_type.get(relation_type))
                        result.append(clean_user_type)
    return result