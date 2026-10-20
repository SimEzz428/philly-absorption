import requests
import json, os, glob

RAW_DIR = "data/raw/rtt"
os.makedirs(RAW_DIR, exist_ok=True)

PAGE_SIZE = 1000
after = 0
pages = 0

existing = sorted(glob.glob(f"{RAW_DIR}/page_*.ndjson"))
if existing:
    pages = len(existing)
    last_line = open(existing[-1]).readlines()[-1]
    after = json.loads(last_line)["cartodb_id"]
    print(f"resuming: {pages} pages on disk, after={after}")

while True:
    SQL = f"""
    SELECT cartodb_id, document_id, document_type, display_date, recording_date,
       document_date, receipt_date, street_address, address_low, address_low_suffix,
       address_low_frac, address_high, street_predir, street_name, street_suffix,
       street_postdir, unit_num, zip_code, ward, opa_account_num, condo_name,
       grantors, grantees, total_consideration, cash_consideration,
       other_consideration, assessed_value, fair_market_value,
       property_count, matched_regmap, reg_map_id, record_id, legal_remarks
    FROM RTT_SUMMARY
    WHERE cartodb_id > {after}
      AND document_type = 'DEED'
      AND total_consideration > 0
      AND display_date >= '2010-01-01'
    ORDER BY cartodb_id
    LIMIT {PAGE_SIZE}
    """
    rows = requests.get("https://phl.carto.com/api/v2/sql", params={"q": SQL}).json()["rows"]

    if not rows:
        break

    path = f"{RAW_DIR}/page_{pages:05d}.ndjson"
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    print(f"page {pages}: {len(rows)} rows, ids {rows[0]['cartodb_id']}-{rows[-1]['cartodb_id']}")
    after = rows[-1]["cartodb_id"]
    pages += 1

    if len(rows) < PAGE_SIZE:
        break

    if pages >= 2000:          
        print("hit the cap")
        break

