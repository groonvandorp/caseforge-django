-- EXECUTE THE ACTUAL COPY OPERATION
-- This will copy process details from Cross Industry to Life Science

-- First, verify we have a user for ownership
SELECT 'Checking for available users...' as status;
SELECT id, email FROM core_user LIMIT 5;

-- Execute the copy
INSERT INTO node_document (
    node_id,
    document_type,
    title,
    content,
    meta_json,
    created_at,
    updated_at,
    user_id
)
SELECT 
    ls_pn.id as node_id,
    'process_details' as document_type,
    nd.title,
    nd.content,
    nd.meta_json,
    datetime('now') as created_at,
    datetime('now') as updated_at,
    (SELECT id FROM core_user LIMIT 1) as user_id
FROM process_node ci_pn
JOIN process_model_version ci_pmv ON ci_pn.model_version_id = ci_pmv.id
JOIN process_model ci_pm ON ci_pmv.model_id = ci_pm.id
JOIN node_document nd ON nd.node_id = ci_pn.id
JOIN (
    SELECT ls_pn.id, ls_pn.code, ls_pn.name, COALESCE(ls_pn.description,'') as description
    FROM process_node ls_pn
    JOIN process_model_version ls_pmv ON ls_pn.model_version_id = ls_pmv.id
    JOIN process_model ls_pm ON ls_pmv.model_id = ls_pm.id
    WHERE ls_pm.model_key = 'apqc_pcf_lifescience'
    AND ls_pn.id NOT IN (
        SELECT DISTINCT parent_id FROM process_node WHERE parent_id IS NOT NULL
    )
    AND ls_pn.id NOT IN (
        SELECT node_id FROM node_document WHERE document_type = 'process_details'
    )
) ls_pn ON ci_pn.code = ls_pn.code 
          AND ci_pn.name = ls_pn.name 
          AND COALESCE(ci_pn.description,'') = ls_pn.description
WHERE ci_pm.model_key = 'apqc_pcf'
AND ci_pn.id NOT IN (
    SELECT DISTINCT parent_id FROM process_node WHERE parent_id IS NOT NULL
)
AND nd.document_type = 'process_details';

-- POST-COPY VERIFICATION
SELECT '=== POST-COPY VERIFICATION ===' as status;

SELECT 
    'Cross Industry process details (MUST REMAIN SAME):' as category,
    COUNT(*) as count
FROM node_document nd
JOIN process_node pn ON nd.node_id = pn.id
JOIN process_model_version pmv ON pn.model_version_id = pmv.id
JOIN process_model pm ON pmv.model_id = pm.id
WHERE pm.model_key = 'apqc_pcf' AND nd.document_type = 'process_details';

SELECT 
    'Life Science process details (AFTER COPY):' as category,
    COUNT(*) as count
FROM node_document nd
JOIN process_node pn ON nd.node_id = pn.id
JOIN process_model_version pmv ON pn.model_version_id = pmv.id
JOIN process_model pm ON pmv.model_id = pm.id
WHERE pm.model_key = 'apqc_pcf_lifescience' AND nd.document_type = 'process_details';

SELECT 'COPY OPERATION COMPLETED!' as status;