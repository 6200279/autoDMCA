-- Database Constraints and Business Rules
-- Ensures data integrity and enforces subscription limits
-- Created: 2025-08-07

-- Function to check protected profile limits based on subscription tier
CREATE OR REPLACE FUNCTION check_profile_limit()
RETURNS TRIGGER AS $$
DECLARE
    current_count INTEGER;
    max_profiles INTEGER;
    user_tier subscription_tier;
BEGIN
    -- Get user's subscription tier
    SELECT subscription_tier INTO user_tier
    FROM users 
    WHERE id = NEW.user_id;
    
    -- Set max profiles based on tier
    IF user_tier = 'basic' THEN
        max_profiles := 1;
    ELSIF user_tier = 'professional' THEN
        max_profiles := 5;
    ELSE
        RAISE EXCEPTION 'Unknown subscription tier: %', user_tier;
    END IF;
    
    -- Count current active profiles
    SELECT COUNT(*) INTO current_count
    FROM protected_profiles 
    WHERE user_id = NEW.user_id AND status = 'active';
    
    -- Check if adding this profile would exceed the limit
    IF current_count >= max_profiles THEN
        RAISE EXCEPTION 'Profile limit exceeded. % tier allows maximum % profiles, but user already has %', 
            user_tier, max_profiles, current_count;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to enforce profile limits
CREATE TRIGGER trigger_check_profile_limit
    BEFORE INSERT ON protected_profiles
    FOR EACH ROW
    EXECUTE FUNCTION check_profile_limit();

-- Function to validate subscription pricing
CREATE OR REPLACE FUNCTION validate_subscription_pricing()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate pricing based on tier
    IF NEW.subscription_tier = 'basic' AND NEW.subscription_price != 49.00 THEN
        RAISE EXCEPTION 'Basic tier must be priced at $49.00, got $%', NEW.subscription_price;
    ELSIF NEW.subscription_tier = 'professional' AND (NEW.subscription_price < 89.00 OR NEW.subscription_price > 99.00) THEN
        RAISE EXCEPTION 'Professional tier must be priced between $89.00-$99.00, got $%', NEW.subscription_price;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to validate subscription pricing
CREATE TRIGGER trigger_validate_subscription_pricing
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW
    WHEN (NEW.subscription_price IS NOT NULL)
    EXECUTE FUNCTION validate_subscription_pricing();

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at columns
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_profiles_updated_at
    BEFORE UPDATE ON protected_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_infringements_updated_at
    BEFORE UPDATE ON infringements
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_dmca_requests_updated_at
    BEFORE UPDATE ON dmca_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_face_encodings_updated_at
    BEFORE UPDATE ON face_encodings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Function to prevent duplicate DMCA requests for same infringement
CREATE OR REPLACE FUNCTION check_duplicate_dmca()
RETURNS TRIGGER AS $$
DECLARE
    existing_count INTEGER;
BEGIN
    -- Count existing pending or active DMCA requests for this infringement
    SELECT COUNT(*) INTO existing_count
    FROM dmca_requests 
    WHERE infringement_id = NEW.infringement_id 
    AND status IN ('pending', 'sent', 'acknowledged');
    
    IF existing_count > 0 THEN
        RAISE EXCEPTION 'DMCA request already exists for infringement %', NEW.infringement_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to prevent duplicate DMCA requests
CREATE TRIGGER trigger_check_duplicate_dmca
    BEFORE INSERT ON dmca_requests
    FOR EACH ROW
    EXECUTE FUNCTION check_duplicate_dmca();

-- Function to validate face encoding dimensions
CREATE OR REPLACE FUNCTION validate_face_encoding()
RETURNS TRIGGER AS $$
BEGIN
    IF array_length(NEW.encoding_vector, 1) != 128 THEN
        RAISE EXCEPTION 'Face encoding must be exactly 128 dimensions, got %', array_length(NEW.encoding_vector, 1);
    END IF;
    
    -- Ensure only one primary encoding per profile
    IF NEW.is_primary THEN
        UPDATE face_encodings 
        SET is_primary = false 
        WHERE profile_id = NEW.profile_id AND id != COALESCE(NEW.id, uuid_generate_v4());
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to validate face encodings
CREATE TRIGGER trigger_validate_face_encoding
    BEFORE INSERT OR UPDATE ON face_encodings
    FOR EACH ROW
    EXECUTE FUNCTION validate_face_encoding();

-- Function to log user activities
CREATE OR REPLACE FUNCTION log_user_activity()
RETURNS TRIGGER AS $$
DECLARE
    action_type TEXT;
    resource_type TEXT;
    user_id_val UUID;
BEGIN
    -- Determine action type
    IF TG_OP = 'INSERT' THEN
        action_type := 'CREATE';
    ELSIF TG_OP = 'UPDATE' THEN
        action_type := 'UPDATE';
    ELSIF TG_OP = 'DELETE' THEN
        action_type := 'DELETE';
    END IF;
    
    -- Determine resource type and user_id
    resource_type := TG_TABLE_NAME;
    
    IF TG_TABLE_NAME = 'users' THEN
        user_id_val := COALESCE(NEW.id, OLD.id);
    ELSIF TG_TABLE_NAME = 'protected_profiles' THEN
        user_id_val := COALESCE(NEW.user_id, OLD.user_id);
    ELSIF TG_TABLE_NAME = 'infringements' THEN
        user_id_val := COALESCE(NEW.user_id, OLD.user_id);
    ELSIF TG_TABLE_NAME = 'dmca_requests' THEN
        user_id_val := COALESCE(NEW.user_id, OLD.user_id);
    END IF;
    
    -- Insert activity log
    INSERT INTO user_activity_logs (
        user_id, 
        action, 
        resource_type, 
        resource_id, 
        details
    ) VALUES (
        user_id_val,
        action_type,
        resource_type,
        COALESCE(NEW.id, OLD.id),
        jsonb_build_object(
            'table', TG_TABLE_NAME,
            'operation', TG_OP,
            'timestamp', CURRENT_TIMESTAMP
        )
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create activity logging triggers (selective to avoid performance impact)
CREATE TRIGGER trigger_log_profile_activity
    AFTER INSERT OR UPDATE OR DELETE ON protected_profiles
    FOR EACH ROW
    EXECUTE FUNCTION log_user_activity();

CREATE TRIGGER trigger_log_dmca_activity
    AFTER INSERT OR UPDATE ON dmca_requests
    FOR EACH ROW
    EXECUTE FUNCTION log_user_activity();

-- Add row-level security policies (optional - can be enabled later)
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE protected_profiles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE infringements ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE dmca_requests ENABLE ROW LEVEL SECURITY;

-- Example RLS policies (commented out - enable when needed)
/*
CREATE POLICY users_own_data ON users
    FOR ALL TO authenticated_users
    USING (id = current_user_id());

CREATE POLICY profiles_own_data ON protected_profiles
    FOR ALL TO authenticated_users
    USING (user_id = current_user_id());

CREATE POLICY infringements_own_data ON infringements
    FOR ALL TO authenticated_users
    USING (user_id = current_user_id());

CREATE POLICY dmca_own_data ON dmca_requests
    FOR ALL TO authenticated_users
    USING (user_id = current_user_id());
*/