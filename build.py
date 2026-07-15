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
import snowflake.connector
from cryptography.hazmat.primitives import serialization

SNOWFLAKE_ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
SNOWFLAKE_USER = os.environ["SNOWFLAKE_USER"]
SNOWFLAKE_WAREHOUSE = os.environ["SNOWFLAKE_WAREHOUSE"]
SNOWFLAKE_ROLE = os.environ.get("SNOWFLAKE_ROLE")  # optional
SNOWFLAKE_PRIVATE_KEY = os.environ["SNOWFLAKE_PRIVATE_KEY"]  # PEM contents
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")  # only if key is encrypted

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "template.html")
QUERY_PATH = os.path.join(BASE_DIR, "query.sql")


# ── Auth ─────────────────────────────────────────────────────────────────────
def load_private_key():
    key_bytes = SNOWFLAKE_PRIVATE_KEY.encode()
    passphrase = SNOWFLAKE_PRIVATE_KEY_PASSPHRASE.encode() if SNOWFLAKE_PRIVATE_KEY_PASSPHRASE else None
    p_key = serialization.load_pem_private_key(key_bytes, password=passphrase)
    return p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def connect():
    return snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        private_key=load_private_key(),
        warehouse=SNOWFLAKE_WAREHOUSE,
        role=SNOWFLAKE_ROLE,
    )


# ── Fetch ─────────────────────────────────────────────────────────────────────
def fetch_rows():
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
    # Snowflake's DictCursor returns the AS aliases from query.sql as keys
    # (uppercase by default), so no old/new fallback juggling is needed here
    # the way the Alation CSV version required.
    def g(key):
        return row.get(key) or ""

    record_id = esc(g("OUTCOME_ID"))
    name = esc(g("OUTCOME_NAME"))
    if name and name.startswith("aLdVt"):
        name = ""
    account = esc(g("ACCOUNT_NAME"))
    industry = esc(g("INDUSTRY"))
    if industry == "Health Care":
        industry = "Healthcare"
    primary_prod = esc(g("PRIMARY_PRODUCT_AREA"))
    product = esc(g("PRODUCT"))
    type_ = esc(g("OUTCOME_TYPE"))
    health = esc(g("OUTCOME_HEALTH"))
    stage = esc(g("USE_CASE_STAGE"))
    created_raw = g("OUTCOME_CREATED_DATE")
    created = str(created_raw)[:10] if created_raw else ""
    ds = esc(g("DEPLOYMENT_STRATEGIST"))
    sales_lead = esc(g("SALES_LEAD"))
    fde = esc(g("FORWARD_DEPLOYED_ENGINEER"))
    statement = esc(g("BUSINESS_OUTCOME_STATEMENT"))

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
    html = re.sub(r"Last refreshed:.*?</div>", f"Last refreshed: {today}</div>", html)
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
