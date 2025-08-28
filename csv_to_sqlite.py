# csv_to_sqlite.py
# Створює локальну SQLite-базу (transactions.db) з нормалізованою таблицею "facts"
# із вашого CSV, витягаючи billing-дані з JSON body/payloads.
#
# Використання:
#   pip install pandas numpy
#   python csv_to_sqlite.py input.csv transactions.db
#
import sys
import json
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

JSON_CANDIDATES = ["body", "request_payload", "response_payload"]

def try_parse_json(val):
    if pd.isna(val): return None
    s = str(val).strip()
    if not s or not (s.startswith("{") or s.startswith("[")): return None
    try:
        return json.loads(s)
    except Exception:
        return None

def deep_get(d, paths):
    for path in paths:
        cur = d
        ok = True
        for p in path:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                ok = False; break
        if ok: return cur
    return None

def normalize_iso2(val):
    if val is None: return None
    s = str(val).strip()
    return s.upper()[:2] if s else None

def main(csv_path, db_path):
    df = pd.read_csv(csv_path)
    # detect columns
    col_created = next((c for c in df.columns if c.lower().endswith("created_at") or c.lower()=="created_at"), None)
    col_status  = next((c for c in df.columns if c.lower() in ("payment_status_code","status")), None)
    col_gate_cd = next((c for c in df.columns if c.lower()=="gateway_code"), None)
    col_gate_msg= next((c for c in df.columns if c.lower() in ("gateway_message","message","gateway_text","decline_reason")), None)
    col_bin_cty = next((c for c in df.columns if c.lower() in ("bin_country","bin_country_iso","issuer_country")), None)
    col_ip_cty  = next((c for c in df.columns if "ip_country" in c.lower()), None)
    col_ip      = next((c for c in df.columns if c.lower() in ("ip","client_ip","t.ip")), None)
    if not all([col_created, col_status, col_gate_cd]):
        raise SystemExit("CSV must contain created_at, payment_status_code/status, gateway_code")

    # parse json
    json_cols = [c for c in JSON_CANDIDATES if c in df.columns]
    billing_country = []
    billing_zip, billing_city, billing_addr = [], [], []
    browser_lang = []
    for _, row in df.iterrows():
        parsed = None
        for jc in json_cols:
            parsed = try_parse_json(row[jc])
            if parsed: break
        if not parsed:
            billing_country.append(None); billing_zip.append(None); billing_city.append(None); billing_addr.append(None); browser_lang.append(None); continue
        bc = deep_get(parsed, [['billing','country'], ['billing_address','country'], ['address','country']])
        bz = deep_get(parsed, [['billing','zip'], ['billing','postal_code'], ['billing_address','zip'], ['address','zip']])
        bcity = deep_get(parsed, [['billing','city'], ['billing_address','city'], ['address','city']])
        baddr = deep_get(parsed, [['billing','address'], ['billing_address','line1'], ['billing_address','address1'], ['address','line1']])
        lang = deep_get(parsed, [['browser','language'], ['device','language'], ['headers','accept-language']])
        billing_country.append(normalize_iso2(bc)); billing_zip.append(bz); billing_city.append(bcity); billing_addr.append(baddr); browser_lang.append(lang)

    out = pd.DataFrame({
        'created_at': pd.to_datetime(df[col_created], errors='coerce', utc=True),
        'status': df[col_status].astype(str),
        'gateway_code': df[col_gate_cd],
        'gateway_message': df[col_gate_msg] if col_gate_msg else None,
        'bin_country': df[col_bin_cty].astype(str).str.upper().str.slice(0,2) if col_bin_cty else None,
        'ip_country': df[col_ip_cty].astype(str).str.upper().str.slice(0,2) if col_ip_cty else None,
        'ip': df[col_ip] if col_ip else None,
        'billing_country': billing_country,
        'billing_zip': billing_zip,
        'billing_city': billing_city,
        'billing_address': billing_addr,
        'browser_language': browser_lang
    })

    out = out.dropna(subset=['created_at'])
    # write to sqlite
    con = sqlite3.connect(db_path)
    out.to_sql("facts", con=con, if_exists="replace", index=False)
    # basic indexes
    try:
        con.execute("CREATE INDEX idx_facts_created ON facts(created_at)")
        con.execute("CREATE INDEX idx_facts_bin ON facts(bin_country)")
        con.execute("CREATE INDEX idx_facts_bill ON facts(billing_country)")
        con.execute("CREATE INDEX idx_facts_ip ON facts(ip_country)")
        con.execute("CREATE INDEX idx_facts_code ON facts(gateway_code)")
    except Exception:
        pass
    con.commit(); con.close()
    print(f"SQLite DB created: {db_path} with table 'facts' ({len(out)} rows)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python csv_to_sqlite.py input.csv transactions.db")
        raise SystemExit(1)
    main(sys.argv[1], sys.argv[2])
