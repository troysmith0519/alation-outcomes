-- Business Outcomes Library — Snowflake source query
-- Verified directly in Snowsight by Troy on 2026-07-02 (39 rows returned).
-- This is the exact query he ran — do not rename these columns without also
-- updating build.py's row_to_js(), which reads these raw names directly.

SELECT
    o.ID AS RECORD_ID,
    o.NAME,
    a.NAME AS ACCOUNT_NAME,
    o.INDUSTRY__C,
    o.PRIMARY_PRODUCT_AREA__C,
    o.PRODUCT__C,
    o.BUSINESS_OUTCOME_TYPE__C,
    o.HEALTH_STATUS__C,
    o.USE_CASE_STAGE__C,
    o.CREATEDDATE,
    o.BUSINESS_OUTCOME_STATEMENT__C,
    ds_user.NAME AS DEPLOYMENT_STRATEGIST__C,
    ae_user.NAME AS SALES_LEAD__C,
    fde_user.NAME AS FORWARD_DEPLOYED_ENGINEER__C
FROM VALHALLA.SALESFORCE.BUSINESS_OUTCOME__C o
LEFT JOIN VALHALLA.SALESFORCE.ACCOUNT a
    ON o.ACCOUNT__C = a.ID
LEFT JOIN VALHALLA.SALESFORCE.USER ds_user
    ON o.DEPLOYMENT_STRATEGIST__C = ds_user.ID
LEFT JOIN VALHALLA.SALESFORCE.USER ae_user
    ON o.SALES_LEAD__C = ae_user.ID
LEFT JOIN VALHALLA.SALESFORCE.USER fde_user
    ON o.FORWARD_DEPLOYED_ENGINEER__C = fde_user.ID
WHERE o.ISDELETED = FALSE
ORDER BY o.INDUSTRY__C, a.NAME;
