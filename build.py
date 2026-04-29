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
    return s.replace("\\", "\\\\").replace('"', '\\"')


def row_to_js(row):
    record_id    = esc(row.get("RECORD_ID", "") or "")
    name         = esc(row.get("NAME", "") or "")
    account      = esc(row.get("ACCOUNT_NAME", "") or "")
    industry     = esc(row.get("INDUSTRY__C", "") or "")
    if industry == "Health Care":
        industry = "Healthcare"
    primary_prod = esc(row.get("PRIMARY_PRODUCT_AREA__C", "") or "")
    product      = esc(row.get("PRODUCT__C", "") or "")
    type_        = esc(row.get("BUSINESS_OUTCOME_TYPE__C", "") or "")
    health       = esc(row.get("HEALTH_STATUS__C", "") or "")
    stage        = esc(row.get("USE_CASE_STAGE__C", "") or "")
    created      = (row.get("CREATEDDATE", "") or "")[:10]
    ds           = esc(row.get("DEPLOYMENT_STRATEGIST__C", "") or "")
    sales_lead   = esc(row.get("SALES_LEAD__C", "") or "")
    fde          = esc(row.get("FORWARD_DEPLOYED_ENGINEER__C", "") or "")
    if name and name.startswith("aLdVt"):
        name = ""
    return (
        f'  {{ recordId: "{record_id}", name: "{name}", account: "{account}", '
        f'industry: "{industry}", primaryProduct: "{primary_prod}", product: "{product}", '
        f'type: "{type_}", health: "{health}", stage: "{stage}", created: "{created}", '
        f'ds: "{ds}", salesLead: "{sales_lead}", fde: "{fde}" }}'
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
    print(f"  {len(rows)} outcomes retrieved.")

    print("Building HTML...")
    html = build_html(rows)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"  Written: {out} ({len(html):,} chars)")
    print("Done.")
