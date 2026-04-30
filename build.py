#!/usr/bin/env python3
"""
Alation Business Outcomes — GitHub Actions Build Script
Reads credentials from environment variables, fetches data from Alation,
and writes index.html (Git commit/push handled by the workflow).
"""
import io, os, csv, re, datetime, requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ALATION_BASE_URL = os.environ["ALATION_BASE_URL"]
ALATION_QUERY_ID = int(os.environ["ALATION_QUERY_ID"])
REFRESH_TOKEN    = os.environ["ALATION_REFRESH_TOKEN"]
USER_ID          = int(os.environ["ALATION_USER_ID"])
TEMPLATE_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html")

# ── Auth ─────────────────────────────────────────────────────────────────────
def get_api_token():
    resp = requests.post(
        f"{ALATION_BASE_URL}/integration/v1/createAPIAccessToken/",
        json={"refresh_token": REFRESH_TOKEN, "user_id": USER_ID},
        verify=False
    )
    resp.raise_for_status()
    return resp.json()["api_access_token"]

# ── Fetch ─────────────────────────────────────────────────────────────────────
def fetch_rows(api_token):
    resp = requests.get(
        f"{ALATION_BASE_URL}/integration/v1/query/{ALATION_QUERY_ID}/result/latest/",
        headers={"Token": api_token}, verify=False
    )
    resp.raise_for_status()
    result_id = resp.json()["id"]
    resp = requests.get(
        f"{ALATION_BASE_URL}/integration/v1/result/{result_id}/csv/",
        headers={"Token": api_token}, verify=False
    )
    resp.raise_for_status()
    return list(csv.DictReader(io.StringIO(resp.text)))

# ── Build ─────────────────────────────────────────────────────────────────────
def esc(s):
    if not s:
        return ""
    return (s.replace("\\", "\\\\")
             .replace('"', '\\"')
             .replace('\r\n', ' ')
             .replace('\n', ' ')
             .replace('\r', ' ')
             .replace('\t', ' '))

def row_to_js(row):
    # Support both new clean aliases and old __C Salesforce field names
    def g(new_key, old_key=''):
        v = row.get(new_key) or (row.get(old_key) if old_key else None) or ""
        return v
    record_id    = esc(g("OUTCOME_ID",    "RECORD_ID"))
    name         = esc(g("OUTCOME_NAME",  "NAME"))
    account      = esc(g("ACCOUNT_NAME"))
    industry     = esc(g("INDUSTRY",      "INDUSTRY__C"))
    if industry == "Health Care":
        industry = "Healthcare"
    primary_prod = esc(g("PRIMARY_PRODUCT_AREA",  "PRIMARY_PRODUCT_AREA__C"))
    product      = esc(g("PRODUCT",               "PRODUCT__C"))
    type_        = esc(g("OUTCOME_TYPE",           "BUSINESS_OUTCOME_TYPE__C"))
    health       = esc(g("OUTCOME_HEALTH",         "HEALTH_STATUS__C"))
    stage        = esc(g("USE_CASE_STAGE",         "USE_CASE_STAGE__C"))
    created      = (g("OUTCOME_CREATED_DATE",      "CREATEDDATE"))[:10]
    ds           = esc(g("DEPLOYMENT_STRATEGIST",  "DEPLOYMENT_STRATEGIST__C"))
    sales_lead   = esc(g("SALES_LEAD",             "SALES_LEAD__C"))
    fde          = esc(g("FORWARD_DEPLOYED_ENGINEER", "FORWARD_DEPLOYED_ENGINEER__C"))
    statement    = esc(g("BUSINESS_OUTCOME_STATEMENT", "BUSINESS_OUTCOME_STATEMENT__C"))
    if name and name.startswith("aLdVt"):
        name = ""
    return (
        f' {{ recordId: "{record_id}", name: "{name}", account: "{account}", '
        f'industry: "{industry}", primaryProduct: "{primary_prod}", product: "{product}", '
        f'type: "{type_}", health: "{health}", stage: "{stage}", created: "{created}", '
        f'ds: "{ds}", salesLead: "{sales_lead}", fde: "{fde}", '
        f'statement: "{statement}" }}'
    )
def build_html(rows):
    with open(TEMPLATE_PATH) as f:
        html = f.read()
    today      = datetime.date.today().strftime("%B %-d, %Y")
    data_array = "[\n" + ",\n".join(row_to_js(r) for r in rows) + "\n]"
    html       = html.replace("DATA_PLACEHOLDER", data_array)
    html       = re.sub(r"Last refreshed:.*?</div>", f"Last refreshed: {today}</div>", html)
    total      = len(rows)
    html       = re.sub(
        r'<div class="stat-value orange" id="stat-total">\d+</div>',
        f'<div class="stat-value orange" id="stat-total">{total}</div>',
        html
    )
    return html

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Authenticating with Alation...")
    token = get_api_token()
    print(f"Fetching query {ALATION_QUERY_ID}...")
    rows = fetch_rows(token)
    if rows:
        print(f"  COLUMNS: {list(rows[0].keys())}")
        print(f"  ROW0: {dict(list(rows[0].items())[:5])}")
    print(f"  {len(rows)} outcomes retrieved.")
    print("Building HTML...")
    html = build_html(rows)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"  Written: {out} ({len(html):,} chars)")
    print("Done.")
