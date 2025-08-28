-- SAFE COPY of Process Details from Cross Industry to Life Science Model
-- This script creates NEW records in node_document table for Life Science nodes
-- WITHOUT modifying any Cross Industry data
-- Author: Claude Code Assistant
-- Date: August 28, 2025

-- First, let's analyze what we'll be copying
SELECT '=== COPY ANALYSIS ===' as status;

SELECT 
    'Cross Industry leaf nodes with process details:' as category,
    COUNT(DISTINCT ci_pn.id) as node_count,
    COUNT(nd.id) as document_count
FROM process_node ci_pn
JOIN process_model_version ci_pmv ON ci_pn.model_version_id = ci_pmv.id
JOIN process_model ci_pm ON ci_pmv.model_id = ci_pm.id
JOIN node_document nd ON nd.node_id = ci_pn.id
WHERE ci_pm.model_key = 'apqc_pcf'
AND ci_pn.id NOT IN (
    SELECT DISTINCT parent_id FROM process_node WHERE parent_id IS NOT NULL
)
AND nd.document_type = 'process_details';

-- Count Life Science nodes that would receive copies
SELECT 
    'Life Science nodes that will receive copies:' as category,
    COUNT(*) as count
FROM (
    -- CI leaf nodes with process details
    SELECT ci_pn.code, ci_pn.name, COALESCE(ci_pn.description,'') as description
    FROM process_node ci_pn
    JOIN process_model_version ci_pmv ON ci_pn.model_version_id = ci_pmv.id
    JOIN process_model ci_pm ON ci_pmv.model_id = ci_pm.id
    JOIN node_document nd ON nd.node_id = ci_pn.id
    WHERE ci_pm.model_key = 'apqc_pcf'
    AND ci_pn.id NOT IN (
        SELECT DISTINCT parent_id FROM process_node WHERE parent_id IS NOT NULL
    )
    AND nd.document_type = 'process_details'
) ci
INNER JOIN (
    -- LS leaf nodes (potential targets)
    SELECT ls_pn.id, ls_pn.code, ls_pn.name, COALESCE(ls_pn.description,'') as description
    FROM process_node ls_pn
    JOIN process_model_version ls_pmv ON ls_pn.model_version_id = ls_pmv.id
    JOIN process_model ls_pm ON ls_pmv.model_id = ls_pm.id
    WHERE ls_pm.model_key = 'apqc_pcf_lifescience'
    AND ls_pn.id NOT IN (
        SELECT DISTINCT parent_id FROM process_node WHERE parent_id IS NOT NULL
    )
    -- Only copy to nodes that don't already have process details
    AND ls_pn.id NOT IN (
        SELECT node_id FROM node_document WHERE document_type = 'process_details'
    )
) ls ON ci.code = ls.code AND ci.name = ls.name AND ci.description = ls.description;

-- Show sample of what will be copied (first 5 matches)
SELECT '=== SAMPLE COPY OPERATIONS ===' as status;

SELECT 
    ci_pn.id as ci_node_id,
    ci_pn.code,
    ci_pn.name,
    ls_pn.id as ls_node_id,
    nd.title,
    LENGTH(nd.content) as content_length
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
AND nd.document_type = 'process_details'
ORDER BY ci_pn.code
LIMIT 5;

-- SAFETY CHECK: Count existing data before copy
SELECT '=== PRE-COPY INTEGRITY CHECK ===' as status;

SELECT 
    'Cross Industry process details (MUST NOT CHANGE):' as category,
    COUNT(*) as count
FROM node_document nd
JOIN process_node pn ON nd.node_id = pn.id
JOIN process_model_version pmv ON pn.model_version_id = pmv.id
JOIN process_model pm ON pmv.model_id = pm.id
WHERE pm.model_key = 'apqc_pcf' AND nd.document_type = 'process_details';

SELECT 
    'Life Science process details (BEFORE COPY):' as category,
    COUNT(*) as count
FROM node_document nd
JOIN process_node pn ON nd.node_id = pn.id
JOIN process_model_version pmv ON pn.model_version_id = pmv.id
JOIN process_model pm ON pmv.model_id = pm.id
WHERE pm.model_key = 'apqc_pcf_lifescience' AND nd.document_type = 'process_details';

/*
-- UNCOMMENT THE FOLLOWING TO EXECUTE THE ACTUAL COPY
-- WARNING: Only run this after reviewing the analysis above!

-- Get the first user ID for ownership
-- Note: In production, you might want to use a specific user
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
*/

-- POST-COPY VERIFICATION (run this after uncommenting and executing the INSERT above)
-- SELECT '=== POST-COPY VERIFICATION ===' as status;
-- 
-- SELECT 
--     'Cross Industry process details (MUST REMAIN SAME):' as category,
--     COUNT(*) as count
-- FROM node_document nd
-- JOIN process_node pn ON nd.node_id = pn.id
-- JOIN process_model_version pmv ON pn.model_version_id = pmv.id
-- JOIN process_model pm ON pmv.model_id = pm.id
-- WHERE pm.model_key = 'apqc_pcf' AND nd.document_type = 'process_details';
-- 
-- SELECT 
--     'Life Science process details (AFTER COPY):' as category,
--     COUNT(*) as count
-- FROM node_document nd
-- JOIN process_node pn ON nd.node_id = pn.id
-- JOIN process_model_version pmv ON pn.model_version_id = pmv.id
-- JOIN process_model pm ON pmv.model_id = pm.id
-- WHERE pm.model_key = 'apqc_pcf_lifescience' AND nd.document_type = 'process_details';
-- 
-- SELECT 'COPY OPERATION COMPLETED SUCCESSFULLY!' as status;