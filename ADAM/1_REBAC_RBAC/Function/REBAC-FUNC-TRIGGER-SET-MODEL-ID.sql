-- 1. Fonction trigger pour auto-peupler model_id
CREATE OR REPLACE FUNCTION adam.fn_trigger_set_model_id()
RETURNS TRIGGER AS $$
BEGIN
    -- Si model_id n'est pas déjà défini, on le récupère depuis la table model
    IF NEW.model_id IS NULL THEN
        SELECT id INTO NEW.model_id
        FROM adam.model
        WHERE user_type = NEW.user_type
          AND object_type = NEW.object_type
          AND relation = NEW.relation
        LIMIT 1;
        
        -- Lever une erreur si aucun model correspondant n'est trouvé
        IF NEW.model_id IS NULL THEN
            RAISE WARNING 'Le modèle ne connais pas user_type=%, relation=%, object_type=%', 
                NEW.user_type, NEW.relation, NEW.object_type;
            RETURN NULL;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;