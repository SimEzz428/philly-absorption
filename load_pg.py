import json, glob, time
import psycopg2
from psycopg2.extras import execute_values

conn = psycopg2.connect(dbname="philly")
cur  = conn.cursor()

def load(table, raw_dir, key, batch=5000):
    paths = sorted(glob.glob(f"{raw_dir}/*.ndjson"))
    if not paths:
        print(f"{table}: no files")
        return

    with open(paths[0]) as f:
        columns = list(json.loads(f.readline()).keys())

    sql = (f"INSERT INTO {table} ({','.join(columns)}) VALUES %s "
           f"ON CONFLICT ({key}) DO NOTHING")

    buf, n, t0 = [], 0, time.time()
    for path in paths:
        for line in open(path):
            d = json.loads(line)
            buf.append(tuple(d.get(c) for c in columns))
            if len(buf) >= batch:
                execute_values(cur, sql, buf)
                conn.commit()
                n += len(buf)
                buf = []
    if buf:
        execute_values(cur, sql, buf)
        conn.commit()
        n += len(buf)

    cur.execute(f"SELECT COUNT(*) FROM {table}")
    print(f"{table:<12}{n:>9,} offered   {cur.fetchone()[0]:>9,} in table"
          f"   {time.time()-t0:>6.1f}s")

load("permits",    "data/raw/permits", "cartodb_id")
load("deeds",      "data/raw/rtt",     "cartodb_id")
load("properties", "data/raw/opa",     "parcel_number")

cur.close()
conn.close()