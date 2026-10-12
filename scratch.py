import requests
import json, os, glob

RAW_DIR = "data/raw/permits"
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
    SELECT cartodb_id, permitnumber, permittype, permitdescription, typeofwork,
       commercialorresidential, approvedscopeofwork, status, applicanttype,
       permitissuedate, permitcompleteddate, certificateofoccupancydate,
       certificateofoccupancyrequired, numberofunits, numberofstories,
       areaofdisturbance, usecategories, occupancytype,
       address, unit_type, unit_num, zip, censustract, council_district,
       opa_account_num, opa_owner, parcel_id_num, addressobjectid,
       parentjobid, zoningpermitjobid, posse_jobid, systemofrecord,
       geocode_x, geocode_y, mostrecentinsp
    FROM permits
    WHERE cartodb_id > {after}
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
