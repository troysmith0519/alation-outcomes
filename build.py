#!/usr/bin/env python3
"""
Alation Business Outcomes — GitHub Actions Build Script (Snowflake edition)

Queries Snowflake (Valhalla) directly using key-pair authentication and writes
index.html from template.html. Git commit/push is handled by the workflow.

This replaces the old Alation Compose API integration, which depended on
ALATION_REFRESH_TOKEN — a token that expires and needs manual renewal, which
is what broke the site. Key-pair auth against Snowflake doesn't expire on the
same cycle and is the standard pattern for unattended/service jobs like this.
"""
import os
import re
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "template.html")
QUERY_PATH = os.path.join(BASE_DIR, "query.sql")


# ── Auth ─────────────────────────────────────────────────────────────────────
# Snowflake env vars and imports are read lazily (inside these functions,
# not at module load time) so this file can still be imported/unit-tested
# without the snowflake-connector-python package or any secrets present.
def load_private_key():
    from cryptography.hazmat.primitives import serialization

    private_key = os.environ["SNOWFLAKE_PRIVATE_KEY"]
    passphrase_raw = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    key_bytes = private_key.encode()
    passphrase = passphrase_raw.encode() if passphrase_raw else None
    p_key = serialization.load_pem_private_key(key_bytes, password=passphrase)
    return p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def connect():
    import snowflake.connector

    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=load_private_key(),
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        role=os.environ.get("SNOWFLAKE_ROLE"),
    )


# ── Fetch ─────────────────────────────────────────────────────────────────────
def fetch_rows():
    import snowflake.connector

    with open(QUERY_PATH) as f:
        query = f.read()
    conn = connect()
    try:
        cur = conn.cursor(snowflake.connector.DictCursor)
        cur.execute(query)
        return cur.fetchall()
    finally:
        conn.close()


# ── Build (same rendering logic as the Alation version) ─────────────────────
def esc(s):
    if not s:
        return ""
    return (str(s).replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace('\r\n', ' ')
            .replace('\n', ' ')
            .replace('\r', ' ')
            .replace('\t', ' '))


def row_to_js(row):
    # Snowflake's DictCursor returns the column/alias names from query.sql as
    # keys (uppercase by default). These are the raw Salesforce-replica names
    # Troy verified directly in Snowsight — see query.sql.
    def g(key):
        return row.get(key) or ""

    record_id = esc(g("RECORD_ID"))
    name = esc(g("NAME"))
    if name and name.startswith("aLdVt"):
        name = ""
    account = esc(g("ACCOUNT_NAME"))
    industry = esc(g("INDUSTRY__C"))
    if industry == "Health Care":
        industry = "Healthcare"
    primary_prod = esc(g("PRIMARY_PRODUCT_AREA__C"))
    product = esc(g("PRODUCT__C"))
    type_ = esc(g("BUSINESS_OUTCOME_TYPE__C"))
    health = esc(g("HEALTH_STATUS__C"))
    stage = esc(g("USE_CASE_STAGE__C"))
    created_raw = g("CREATEDDATE")
    created = str(created_raw)[:10] if created_raw else ""
    ds = esc(g("DEPLOYMENT_STRATEGIST__C"))
    sales_lead = esc(g("SALES_LEAD__C"))
    fde = esc(g("FORWARD_DEPLOYED_ENGINEER__C"))
    statement = esc(g("BUSINESS_OUTCOME_STATEMENT__C"))

    return (
        f'  {{ recordId: "{record_id}", name: "{name}", account: "{account}", '
        f'industry: "{industry}", primaryProduct: "{primary_prod}", product: "{product}", '
        f'type: "{type_}", health: "{health}", stage: "{stage}", created: "{created}", '
        f'ds: "{ds}", salesLead: "{sales_lead}", fde: "{fde}", '
        f'statement: "{statement}" }}'
    )


def build_html(rows):
    with open(TEMPLATE_PATH) as f:
        html = f.read()
    today = datetime.date.today().strftime("%B %-d, %Y")
    data_array = "[\n" + ",\n".join(row_to_js(r) for r in rows) + "\n]"
    html = html.replace("DATA_PLACEHOLDER", data_array)
    # template.html has two DATA_LAST_REFRESHED placeholders: one in the
    # header, one in the footer. Plain string replace catches both.
    html = html.replace("DATA_LAST_REFRESHED", today)
    total = len(rows)
    html = re.sub(
        r'<div class="stat-value orange" id="stat-total">\d+</div>',
        f'<div class="stat-value orange" id="stat-total">{total}</div>',
        html,
    )
    return html


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Connecting to Snowflake...")
    rows = fetch_rows()
    if rows:
        print(f"  COLUMNS: {list(rows[0].keys())}")
        print(f"  ROW0: {dict(list(rows[0].items())[:5])}")
    print(f"  {len(rows)} outcomes retrieved.")
    print("Building HTML...")
    html = build_html(rows)
    out = os.path.join(BASE_DIR, "index.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"  Written: {out} ({len(html):,} chars)")
    print("Done.")
