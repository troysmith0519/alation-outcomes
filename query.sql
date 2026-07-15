-- Business Outcomes Library — Snowflake source query
-- Replaces the Alation Compose query previously used by build.py.
--
-- ⚠ VERIFY BEFORE RELYING ON THIS: I could not connect to Snowflake directly
-- to test this query — I don't have Snowflake network/credential access from
-- this session. The table name and column aliases below are reverse-engineered
-- from:
--   1. template.html's footer ("Data sourced from Valhalla.Salesforce.BUSINESS_OUTCOME__C")
--   2. build.py's existing fallback field names (INDUSTRY__C, PRIMARY_PRODUCT_AREA__C,
--      BUSINESS_OUTCOME_TYPE__C, HEALTH_STATUS__C, USE_CASE_STAGE__C, CREATEDDATE,
--      DEPLOYMENT_STRATEGIST__C, SALES_LEAD__C, FORWARD_DEPLOYED_ENGINEER__C,
--      BUSINESS_OUTCOME_STATEMENT__C) — these look like raw Salesforce-replica
--      column names, i.e. exactly what you'd query directly in Snowflake.
--   3. The "Outcome Intelligence Layer" data product schema in Alation, which
--      confirmed ACCOUNTID exists on the outcome object and that VALHALLA.SALESFORCE.ACCOUNT
--      is the joined table for account name.
--
-- Before the first real run, have whoever provisions the Snowflake service
-- account run:
--   DESCRIBE TABLE VALHALLA.SALESFORCE.BUSINESS_OUTCOME__C;
--   DESCRIBE TABLE VALHALLA.SALESFORCE.ACCOUNT;
-- and fix any column names below that don't match. Don't rename the AS aliases
-- (OUTCOME_ID, OUTCOME_NAME, etc.) without also updating build.py's row_to_js().

SELECT
    bo.ID                              AS OUTCOME_ID,
    bo.NAME                            AS OUTCOME_NAME,
    acc.NAME                           AS ACCOUNT_NAME,
    bo.INDUSTRY__C                     AS INDUSTRY,
    bo.PRIMARY_PRODUCT_AREA__C         AS PRIMARY_PRODUCT_AREA,
    bo.PRODUCT__C                      AS PRODUCT,
    bo.BUSINESS_OUTCOME_TYPE__C        AS OUTCOME_TYPE,
    bo.HEALTH_STATUS__C                AS OUTCOME_HEALTH,
    bo.USE_CASE_STAGE__C               AS USE_CASE_STAGE,
    bo.CREATEDDATE                      AS OUTCOME_CREATED_DATE,
    bo.DEPLOYMENT_STRATEGIST__C        AS DEPLOYMENT_STRATEGIST,
    bo.SALES_LEAD__C                   AS SALES_LEAD,
    bo.FORWARD_DEPLOYED_ENGINEER__C    AS FORWARD_DEPLOYED_ENGINEER,
    bo.BUSINESS_OUTCOME_STATEMENT__C   AS BUSINESS_OUTCOME_STATEMENT
FROM VALHALLA.SALESFORCE.BUSINESS_OUTCOME__C bo
LEFT JOIN VALHALLA.SALESFORCE.ACCOUNT acc
    ON bo.ACCOUNTID = acc.ID
-- WHERE bo.ISDELETED = FALSE   -- uncomment once confirmed this column exists
ORDER BY bo.CREATEDDATE DESC;
