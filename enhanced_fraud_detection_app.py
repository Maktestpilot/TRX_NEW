# enhanced_fraud_detection_app.py
# Final app: Local analytics for transaction pass-through (AR%) with drivers
# Focus: AU / DE / IT / HU by default (dynamic otherwise)
# Success rule: status_title != 'Failed' AND is_final == TRUE
# IP->Country: optional local IPinfo MMDB (ipinfo-db) OR optional ip_map.csv
#
# Run:
#   pip install streamlit pandas numpy matplotlib ipinfo-db
#   streamlit run enhanced_fraud_detection_app.py

import json, re, os, tempfile
from typing import Any, Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Optional dependency for local IPinfo MMDB
try:
    from ipinfo_db.reader import Reader as IPinfoMMDBReader
except Exception:
    IPinfoMMDBReader = None

# st.set_page_config(page_title="Fraud & Pass-through Analytics (AU/DE/IT/HU)", layout="wide")  # Commented out to avoid conflicts
st.title("Проходимость и причины отказов — локальная аналитика")

st.caption("""
**Правила:** Успех = `status_title` ≠ `'Failed'` **и** `is_final == TRUE`. Анализ строится только по финальным записям.
**GEO источники:** BIN / Billing / Shipping / IP. IP-страна — из локальной базы **IPinfo MMDB** (если загружена) или из `ip_map.csv`.
**Фокус:** Австралия (AU), Германия (DE), Италия (IT), Венгрия (HU) — по умолчанию; можно переключить страны.
""")

# -------------------- Helpers --------------------

JSON_CANDIDATES = ["body", "request_payload", "response_payload"]
UA_CANDIDATES = ["user_agent", "ua", "client_user_agent", "headers.user-agent"]
LANG_CANDIDATES = ["accept_language", "accept-language", "language", "browser_language", "headers.accept-language"]
IP_COUNTRY_CANDIDATES = ["ip_country", "ip_country_iso", "client_ip_country"]
IP_RAW_CANDIDATES = ["ip", "client_ip", "t.ip", "headers.x-forwarded-for", "ip_from_body"]
BIN_COUNTRY_CANDIDATES = ["bin_country", "bin_country_iso", "issuer_country", "ci.bin_country_iso"]

FOCUS_COUNTRIES = ["AU","DE","IT","HU"]

def pick_first_col(df: pd.DataFrame, names: List[str]) -> Optional[str]:
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n in lower: return lower[n]
    for c in df.columns:
        lc = c.lower()
        if any(lc.endswith("." + n) for n in names):
            return c
    return None

def try_parse_json(val: Any) -> Optional[Any]:
    if val is None or (isinstance(val, float) and np.isnan(val)): return None
    s = str(val).strip()
    if not s or (not s.startswith("{") and not s.startswith("[")): return None
    try:
        return json.loads(s)
    except Exception:
        return None

def flatten_json(obj: Any, prefix: str = "") -> List[Tuple[str, Any]]:
    out: List[Tuple[str, Any]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            out.extend(flatten_json(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}[{i}]"
            out.extend(flatten_json(v, p))
    else:
        out.append((prefix, obj))
    return out

def lookup_first(flat: List[Tuple[str, Any]], key_regexes: List[re.Pattern]) -> Optional[Any]:
    for path, val in flat:
        last = path.split(".")[-1].lower()
        for rx in key_regexes:
            if rx.search(last):
                return val
    return None

def normalize_iso2(val: Any) -> Optional[str]:
    if val is None: return None
    s = str(val).strip()
    if not s: return None
    return s.upper()[:2]

def norm_phone(val: Any) -> Optional[str]:
    if val is None: return None
    digits = re.sub(r"\D+", "", str(val))
    return digits or None

def first_in_csv_list(s: str) -> str:
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts[0] if parts else s

def to_bool_series(s: pd.Series) -> pd.Series:
    sl = s.astype(str).str.strip().str.lower()
    return sl.isin(["true","t","1","yes","y"])

def safe_progress_update(bar, current:int, total:int, every:int=500):
    if bar is None or total <= 0: 
        return
    if (current % every != 0) and (current != total):
        return
    pct = min(1.0, max(0.0, current / total))
    bar.progress(pct)

# -------------------- Inputs --------------------

csv_file = st.file_uploader("Основной CSV (JOIN pt × ci × t × ap)", type=["csv"])
ip_map_csv = st.file_uploader("Опционально: готовый мэппинг IP→Country (`ip,country`)", type=["csv"])
mmdb_file = st.file_uploader("Опционально: база IPinfo MMDB (например, ipinfo_lite.mmdb)", type=["mmdb"])

if csv_file is None:
    st.info("Загрузите CSV для начала анализа.")
    st.stop()

df = pd.read_csv(csv_file)

# -------------------- Detect key columns --------------------
col_created      = pick_first_col(df, ["created_at"])
col_status_title = pick_first_col(df, ["status_title"])
col_is_final     = pick_first_col(df, ["is_final","final"])
col_gate_cd      = pick_first_col(df, ["gateway_code"])
col_gate_msg     = pick_first_col(df, ["gateway_message","message","gateway_text","decline_reason"])

col_bin_country  = pick_first_col(df, BIN_COUNTRY_CANDIDATES)
col_ip_country   = pick_first_col(df, IP_COUNTRY_CANDIDATES)
col_ip_raw       = pick_first_col(df, IP_RAW_CANDIDATES)

col_ua           = pick_first_col(df, UA_CANDIDATES)
col_lang         = pick_first_col(df, LANG_CANDIDATES)

json_cols = [pick_first_col(df, [c]) for c in JSON_CANDIDATES if pick_first_col(df, [c])]

missing = []
for label, col in [("created_at", col_created), ("status_title", col_status_title), ("is_final", col_is_final), ("gateway_code", col_gate_cd)]:
    if col is None: missing.append(label)
if missing:
    st.error(f"Отсутствуют ключевые колонки: {missing}. Добавьте их в экспорт и перезагрузите файл.")
    st.stop()

# -------------------- Normalize / basic fields --------------------
df[col_created] = pd.to_datetime(df[col_created], errors='coerce', utc=True)
df = df.dropna(subset=[col_created])

df['is_final_bool'] = to_bool_series(df[col_is_final])
status_title_l = df[col_status_title].astype(str).str.strip().str.lower()
df['is_failed'] = status_title_l.eq('failed')
df['is_approved'] = (~df['is_failed']) & (df['is_final_bool'])

# consider only final rows for metrics
df = df[df['is_final_bool']]

# BIN geo
df['geo_bin'] = df[col_bin_country].astype(str).str.upper().str.slice(0,2) if col_bin_country else np.nan

# -------------------- Deep JSON parsing (with progress fix) --------------------
def extract_body_data(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    if total == 0:
        return pd.DataFrame({
            'billing_country': [], 'billing_zip': [], 'billing_city': [], 'billing_address1': [], 'billing_address2': [],
            'shipping_country': [], 'shipping_zip': [], 'shipping_city': [], 'shipping_address1': [], 'shipping_address2': [], 'shipping_name': [],
            'email': [], 'phone': [], 'first_name': [], 'last_name': [], 'full_name': [],
            'user_id': [], 'customer_id': [], 'account_id': [], 'session_id': [],
            'device_id': [], 'fingerprint': [], 'browser_name': [], 'browser_version': [],
            'browser_language_from_body': [], 'os_name': [], 'os_version': [], 'timezone': [],
            'ip_from_body': []
        })

    progress_bar = st.progress(0.0, text="Парсим JSON body…")

    billing_country, billing_zip, billing_city, billing_addr1, billing_addr2 = [], [], [], [], []
    shipping_country, shipping_zip, shipping_city, shipping_addr1, shipping_addr2, shipping_name = [], [], [], [], [], []
    emails, phones, fnames, lnames, fullnames = [], [], [], [], []
    user_ids, customer_ids, account_ids, session_ids = [], [], [], []
    device_ids, fps, br_names, br_versions, br_langs, os_names, os_versions, timezones, ip_body_list = [], [], [], [], [], [], [], [], []

    rx = lambda *alts: [re.compile(a, re.I) for a in alts]

    for i, row in enumerate(df.itertuples(index=False), start=1):
        parsed = None
        for jc in json_cols:
            parsed = try_parse_json(getattr(row, jc)) if hasattr(row, jc) else try_parse_json(df.loc[i-1, jc])
            if parsed is not None:
                break

        if parsed is None:
            billing_country.append(None); billing_zip.append(None); billing_city.append(None); billing_addr1.append(None); billing_addr2.append(None)
            shipping_country.append(None); shipping_zip.append(None); shipping_city.append(None); shipping_addr1.append(None); shipping_addr2.append(None); shipping_name.append(None)
            emails.append(None); phones.append(None); fnames.append(None); lnames.append(None); fullnames.append(None)
            user_ids.append(None); customer_ids.append(None); account_ids.append(None); session_ids.append(None)
            device_ids.append(None); fps.append(None); br_names.append(None); br_versions.append(None); br_langs.append(None)
            os_names.append(None); os_versions.append(None); timezones.append(None); ip_body_list.append(None)
            safe_progress_update(progress_bar, i, total, every=500)
            continue

        flat = flatten_json(parsed)

        # Billing
        bc = lookup_first(flat, rx(r'billing_?country$', r'address\.country$', r'\.country$'))
        bzip = lookup_first(flat, rx(r'billing_?(zip|postal_code)$', r'address\.(zip|postal_code)$'))
        bcity = lookup_first(flat, rx(r'billing_?city$', r'address\.city$'))
        baddr1 = lookup_first(flat, rx(r'billing_?(address(_?line)?1?)$', r'address\.(address1|line1)$'))
        baddr2 = lookup_first(flat, rx(r'billing_?(address(_?line)?2)$', r'address\.(address2|line2)$'))

        # Shipping
        sc = lookup_first(flat, rx(r'shipping_?country$', r'ship_address\.country$'))
        szip = lookup_first(flat, rx(r'shipping_?(zip|postal_code)$'))
        scity = lookup_first(flat, rx(r'shipping_?city$'))
        saddr1 = lookup_first(flat, rx(r'shipping_?(address(_?line)?1?)$'))
        saddr2 = lookup_first(flat, rx(r'shipping_?(address(_?line)?2)$'))
        sname = lookup_first(flat, rx(r'shipping_?name$', r'ship_to_name$', r'recipient_name$'))

        # User identifiers
        email = lookup_first(flat, rx(r'email(_address)?$', r'user\.email$', r'customer\.email$', r'buyer\.email$', r'contact\.email$'))
        phone = lookup_first(flat, rx(r'phone(_number)?$', r'mobile$', r'msisdn$', r'contact\.phone$'))
        fname = lookup_first(flat, rx(r'first_?name$', r'given_?name$', r'fname$'))
        lname = lookup_first(flat, rx(r'last_?name$', r'family_?name$', r'lname$', r'surname$'))
        fullname = lookup_first(flat, rx(r'full_?name$', r'^name$', r'user\.name$', r'customer\.name$', r'cardholder\.name$', r'billing_?name$'))
        if not fullname:
            parts = [p for p in [fname, lname] if p and str(p).strip()]
            fullname = " ".join(map(str, parts)) if parts else None

        user_id = lookup_first(flat, rx(r'user_?id$', r'^user\.id$', r'uid$', r'guid$'))
        customer_id = lookup_first(flat, rx(r'customer_?id$', r'customer\.id$'))
        account_id = lookup_first(flat, rx(r'account_?id$', r'account\.id$'))
        session_id = lookup_first(flat, rx(r'session_?id$', r'session\.id$'))

        # Device/browser
        device_id = lookup_first(flat, rx(r'device_?id$', r'device\.id$', r'fingerprint$', r'device\.fingerprint$'))
        fp = lookup_first(flat, rx(r'fingerprint$', r'device\.fingerprint$'))
        br_name = lookup_first(flat, rx(r'browser\.name$', r'^browser$'))
        br_ver = lookup_first(flat, rx(r'browser\.version$', r'br(?:owser)?_?version$'))
        br_lang = lookup_first(flat, rx(r'browser\.language$', r'headers\.accept-language$', r'accept-?language$'))
        os_name = lookup_first(flat, rx(r'device\.os$', r'\bos\b', r'operating_?system$'))
        os_ver = lookup_first(flat, rx(r'device\.os_?version$', r'os_?version$'))
        tz = lookup_first(flat, rx(r'timezone$', r'device\.timezone$', r'browser\.timezone$'))
        ip_body = lookup_first(flat, rx(r'ip$', r'client_?ip$', r'remote_?ip$', r'headers\.x-forwarded-for$'))
        if isinstance(ip_body, str) and "," in ip_body:
            ip_body = first_in_csv_list(ip_body)

        billing_country.append(normalize_iso2(bc)); billing_zip.append(bzip); billing_city.append(bcity); billing_addr1.append(baddr1); billing_addr2.append(baddr2)
        shipping_country.append(normalize_iso2(sc)); shipping_zip.append(szip); shipping_city.append(scity); shipping_addr1.append(saddr1); shipping_addr2.append(saddr2); shipping_name.append(sname)
        emails.append((str(email).strip().lower() if email not in [None, ""] else None)); phones.append(norm_phone(phone))
        fnames.append(fname); lnames.append(lname); fullnames.append(fullname)
        user_ids.append(user_id); customer_ids.append(customer_id); account_ids.append(account_id); session_ids.append(session_id)
        device_ids.append(device_id); fps.append(fp); br_names.append(br_name); br_versions.append(br_ver); br_langs.append(br_lang)
        os_names.append(os_name); os_versions.append(os_ver); timezones.append(tz); ip_body_list.append(ip_body)

        safe_progress_update(progress_bar, i, total, every=500)

    # finalize progress
    safe_progress_update(progress_bar, total, total, every=1)

    return pd.DataFrame({
        'billing_country': billing_country, 'billing_zip': billing_zip, 'billing_city': billing_city, 'billing_address1': billing_addr1, 'billing_address2': billing_addr2,
        'shipping_country': shipping_country, 'shipping_zip': shipping_zip, 'shipping_city': shipping_city, 'shipping_address1': shipping_addr1, 'shipping_address2': shipping_addr2, 'shipping_name': shipping_name,
        'email': emails, 'phone': phones, 'first_name': fnames, 'last_name': lnames, 'full_name': fullnames,
        'user_id': user_ids, 'customer_id': customer_ids, 'account_id': account_ids, 'session_id': session_ids,
        'device_id': device_ids, 'fingerprint': fps, 'browser_name': br_names, 'browser_version': br_versions,
        'browser_language_from_body': br_langs, 'os_name': os_names, 'os_version': os_versions, 'timezone': timezones,
        'ip_from_body': ip_body_list
    })

body_df = extract_body_data(df)
df = pd.concat([df.reset_index(drop=True), body_df.reset_index(drop=True)], axis=1)

# UA & Accept-Language (headers from columns)
df['user_agent'] = df[col_ua] if col_ua else None
df['accept_language_hdr'] = df[col_lang] if col_lang else None

# -------------------- IP -> Country via IPinfo MMDB or ip_map.csv --------------------
if not col_ip_raw:
    col_ip_raw = pick_first_col(df, ["ip","client_ip","t.ip","ip_from_body","headers.x-forwarded-for"])

if col_ip_raw:
    df['_ip_norm'] = df[col_ip_raw].astype(str).apply(lambda s: s.split(",")[0].strip())
else:
    df['_ip_norm'] = np.nan

df['geo_ip'] = np.nan

# 1) MMDB
if mmdb_file is not None and IPinfoMMDBReader is not None and col_ip_raw:
    progress = st.progress(0.0, text="MMDB: резолв IP→Country…")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mmdb") as tmp:
        tmp.write(mmdb_file.read())
        mmdb_path = tmp.name
    reader = IPinfoMMDBReader(mmdb_path)
    uniq_ips = df['_ip_norm'].dropna().astype(str).unique().tolist()
    total = len(uniq_ips)
    rows = []
    for i, ip in enumerate(uniq_ips, start=1):
        try:
            rec = reader.get(ip)
            cc = rec.get('country') if isinstance(rec, dict) else None
        except Exception:
            cc = None
        rows.append({"ip": ip, "country": cc})
        safe_progress_update(progress, i, total, every=max(1, total//100))
    reader.close()
    mmdb_map = pd.DataFrame(rows).drop_duplicates("ip")
    df = df.merge(mmdb_map, left_on="_ip_norm", right_on="ip", how="left")
    df['geo_ip'] = df['country'].astype(str).str.upper().str.slice(0,2)
    df.drop(columns=['ip','country'], inplace=True, errors='ignore')
    safe_progress_update(progress, total, total, every=1)
    st.download_button("Скачать ip_map_from_ipinfo_mmdb.csv", mmdb_map.to_csv(index=False).encode("utf-8"), file_name="ip_map_from_ipinfo_mmdb.csv")

# 2) ip_map.csv fallback
if ip_map_csv is not None and col_ip_raw:
    ip_map = pd.read_csv(ip_map_csv)
    cols_lower = {c.lower(): c for c in ip_map.columns}
    if 'ip' in cols_lower and 'country' in cols_lower:
        ip_map.rename(columns=cols_lower, inplace=True)
        df = df.merge(ip_map[['ip','country']], left_on='_ip_norm', right_on='ip', how='left')
        df['geo_ip'] = df['geo_ip'].fillna(ip_map['country'].astype(str).str.upper().str.slice(0,2))
        df.drop(columns=['ip','country'], inplace=True)
    else:
        st.warning("ip_map.csv должен содержать колонки 'ip' и 'country'.")

# -------------------- Time grains --------------------
df['day'] = df[col_created].dt.floor('D')
df['week'] = df[col_created].dt.to_period('W').apply(lambda r: r.start_time)
df['month'] = df[col_created].dt.to_period('M').apply(lambda r: r.start_time)

st.info(f"Диапазон дат (UTC): **{df[col_created].min()} → {df[col_created].max()}** | Финальных строк: **{len(df)}**")

# -------------------- Countries selection --------------------
# Build all countries set
all_countries = pd.unique(pd.concat([
    df['geo_bin'].dropna().astype(str),
    df['billing_country'].dropna().astype(str),
    df['geo_ip'].dropna().astype(str),
    df['shipping_country'].dropna().astype(str),
], ignore_index=True))
all_countries = sorted([c for c in all_countries if c and c != 'NA'])

default_selection = [c for c in FOCUS_COUNTRIES if c in all_countries] or all_countries
country_filter = st.multiselect("Страны для анализа (ISO2):", options=all_countries, default=default_selection)

df = df[
    (df['geo_bin'].isin(country_filter)) |
    (df['billing_country'].isin(country_filter)) |
    (df['geo_ip'].isin(country_filter)) |
    (df['shipping_country'].isin(country_filter))
]

# Gateway fields
df['gateway_code'] = df[col_gate_cd]
df['gateway_message'] = df[col_gate_msg] if col_gate_msg else None
df['code_msg'] = df['gateway_code'].astype(str) + " | " + df['gateway_message'].astype(str)

# -------------------- Metrics helpers --------------------
def agg_metrics(_df: pd.DataFrame, geo_col: str, grain: str) -> pd.DataFrame:
    out = (_df.groupby([grain, geo_col], as_index=False)
             .agg(attempts=('is_approved', 'size'),
                  approved=('is_approved', 'sum')))
    out['ar_pct'] = (100.0 * out['approved'] / out['attempts']).round(2)
    out = out.rename(columns={geo_col: 'geo'})
    out['geo_source'] = geo_col
    return out

def declines_by_reason(_df: pd.DataFrame, geo_col: str, grain: str) -> pd.DataFrame:
    data = _df[~_df['is_approved']].copy()
    grp = (data.groupby([grain, geo_col, 'code_msg'], as_index=False)
               .size()
               .rename(columns={'size':'declines'}))
    at = (_df.groupby([grain, geo_col], as_index=False)
              .size().rename(columns={'size':'attempts'}))
    out = grp.merge(at, on=[grain, geo_col], how='left')
    out['declines_per_100'] = (100.0 * out['declines'] / out['attempts']).round(4)
    out = out.rename(columns={geo_col: 'geo', grain: 'period'})
    out['geo_source'] = geo_col
    return out

def drivers_for_last_period(_df: pd.DataFrame, geo_col: str, grain: str) -> pd.DataFrame:
    d = declines_by_reason(_df, geo_col, grain)
    d = d.sort_values(['geo_source','geo','code_msg','period'])
    d['prev_dp100'] = d.groupby(['geo_source','geo','code_msg'])['declines_per_100'].shift(1)
    d['delta_dp100'] = (d['declines_per_100'] - d['prev_dp100']).round(4)
    # AR metrics deltas
    m = agg_metrics(_df, geo_col, grain).rename(columns={grain:'period'})
    m = m.sort_values(['geo_source','geo','period'])
    m['ar_prev'] = m.groupby(['geo_source','geo'])['ar_pct'].shift(1)
    m['delta_ar'] = (m['ar_pct'] - m['ar_prev']).round(2)
    # pick last period per (geo_source, geo)
    last_periods = m.groupby(['geo_source','geo'], as_index=False)['period'].max().rename(columns={'period':'last_period'})
    d_last = d.merge(last_periods, left_on=['geo_source','geo','period'], right_on=['geo_source','geo','last_period'], how='inner')
    d_last = d_last.merge(m[['geo_source','geo','period','ar_pct','ar_prev','delta_ar']], left_on=['geo_source','geo','period'], right_on=['geo_source','geo','period'], how='left')
    return d_last.sort_values(['geo_source','geo','delta_dp100'], ascending=[True,True,False])

tabs = st.tabs(["Daily","Weekly","Monthly","Drivers (explainer)","Decline catalog","Data Quality"])

# -------------------- Daily / Weekly / Monthly --------------------
with tabs[0]:
    st.subheader("Ежедневные метрики (attempts / approved / AR%)")
    daily = pd.concat([
        agg_metrics(df, 'geo_bin','day'),
        agg_metrics(df, 'billing_country','day'),
        agg_metrics(df, 'geo_ip','day'),
        agg_metrics(df, 'shipping_country','day'),
    ], ignore_index=True)
    st.dataframe(daily.sort_values(['day','geo_source','geo']), use_container_width=True)
    st.markdown("**AR% графики**")
    for source in ['geo_bin','billing_country','geo_ip','shipping_country']:
        tmp = daily[daily['geo_source']==source]
        if tmp.empty: continue
        for g in sorted(tmp['geo'].dropna().unique()):
            fig = plt.figure()
            plt.plot(tmp[tmp['geo']==g]['day'], tmp[tmp['geo']==g]['ar_pct'])
            plt.title(f"AR% — {g} ({source})")
            plt.xlabel("Day"); plt.ylabel("AR%")
            st.pyplot(fig)

with tabs[1]:
    st.subheader("Недельные метрики + WoW дельта")
    weekly = pd.concat([
        agg_metrics(df, 'geo_bin','week'),
        agg_metrics(df, 'billing_country','week'),
        agg_metrics(df, 'geo_ip','week'),
        agg_metrics(df, 'shipping_country','week'),
    ], ignore_index=True)
    weekly = weekly.sort_values(['geo_source','geo','week'])
    weekly['ar_prev'] = weekly.groupby(['geo_source','geo'])['ar_pct'].shift(1)
    weekly['delta_ar'] = (weekly['ar_pct'] - weekly['ar_prev']).round(2)
    st.dataframe(weekly.sort_values(['week','geo_source','geo'], ascending=[False,True,True]), use_container_width=True)

with tabs[2]:
    st.subheader("Месячные метрики + MoM дельта")
    monthly = pd.concat([
        agg_metrics(df, 'geo_bin','month'),
        agg_metrics(df, 'billing_country','month'),
        agg_metrics(df, 'geo_ip','month'),
        agg_metrics(df, 'shipping_country','month'),
    ], ignore_index=True)
    monthly = monthly.sort_values(['geo_source','geo','month'])
    monthly['ar_prev'] = monthly.groupby(['geo_source','geo'])['ar_pct'].shift(1)
    monthly['delta_ar'] = (monthly['ar_pct'] - monthly['ar_prev']).round(2)
    st.dataframe(monthly.sort_values(['month','geo_source','geo'], ascending=[False,True,True]), use_container_width=True)

# -------------------- Drivers --------------------
with tabs[3]:
    st.subheader("Пояснение изменения AR% — вклад деклайнов (Δ declines per 100 attempts)")
    grain = st.selectbox("Гранулярность:", ["week","month","day"], index=1)
    driver_tbl = pd.concat([
        drivers_for_last_period(df, 'geo_bin', grain),
        drivers_for_last_period(df, 'billing_country', grain),
        drivers_for_last_period(df, 'geo_ip', grain),
        drivers_for_last_period(df, 'shipping_country', grain),
    ], ignore_index=True)
    # показываем ТОП-увеличений и ТОП-снижений по каждой паре geo_source+geo
    top_k = st.slider("Сколько причин показать на пару GEO", min_value=3, max_value=20, value=10, step=1)
    out = []
    for (src, geo), sub in driver_tbl.groupby(['geo_source','geo']):
        # топ рост
        up = sub.sort_values('delta_dp100', ascending=False).head(top_k)
        up['direction'] = 'UP (ухудшение)'
        # топ падение
        down = sub.sort_values('delta_dp100', ascending=True).head(top_k)
        down['direction'] = 'DOWN (улучшение)'
        out.append(pd.concat([up, down], ignore_index=True))
    if out:
        explain = pd.concat(out, ignore_index=True)
        cols = ['period','geo_source','geo','ar_prev','ar_pct','delta_ar','code_msg','declines','attempts','declines_per_100','prev_dp100','delta_dp100','direction']
        cols = [c for c in cols if c in explain.columns]
        st.dataframe(explain[cols].sort_values(['period','geo_source','geo','direction','delta_dp100'], ascending=[False,True,True,True,False]), use_container_width=True)
    else:
        st.info("Недостаточно данных для вычисления драйверов.")

# -------------------- Decline catalog --------------------
with tabs[4]:
    st.subheader("Каталог причин отказов (по выбранным странам)")
    declines = df[~df['is_approved']].copy()
    cat = (declines.groupby(['gateway_code','gateway_message'], as_index=False)
                   .size().rename(columns={'size':'cnt'}))
    code_var = (cat.groupby('gateway_code', as_index=False)
                  .agg(declines=('cnt','sum'),
                       distinct_messages=('gateway_message','nunique')))
    # примеры сообщений
    examples = (cat.sort_values('cnt', ascending=False)
                  .groupby('gateway_code')
                  .head(3)
                  .groupby('gateway_code')['gateway_message']
                  .apply(lambda s: "; ".join(s.head(3).astype(str))[:300])
                  .reset_index(name='top_messages'))
    cat_tbl = code_var.merge(examples, on='gateway_code', how='left').sort_values(['declines'], ascending=False)
    st.dataframe(cat_tbl, use_container_width=True)

# -------------------- Data Quality --------------------
with tabs[5]:
    st.subheader("Проверки качества данных (DQ) и консистентность GEO")
    def pct_missing(s: pd.Series) -> float:
        return float((s.isna() | (s=="")).mean()*100)

    checks = []
    checks.append(("Missing BIN country", pct_missing(df['geo_bin'])))
    checks.append(("Missing Billing country", pct_missing(df['billing_country'])))
    checks.append(("Missing Shipping country", pct_missing(df['shipping_country'])))
    checks.append(("Missing IP country", pct_missing(df['geo_ip'])))
    checks.append(("Missing User-Agent", pct_missing(df['user_agent'])))
    checks.append(("Missing Accept-Language", pct_missing(df['accept_language_hdr'])))
    checks.append(("Missing Billing ZIP", pct_missing(df['billing_zip'])))
    checks.append(("Missing Billing City", pct_missing(df['billing_city'])))
    checks.append(("Missing Billing Address1", pct_missing(df['billing_address1'])))

    def mismatch_rate(a: pd.Series, b: pd.Series) -> float:
        both = (~a.isna()) & (~b.isna())
        if both.sum() == 0: return float('nan')
        return float((a[both] != b[both]).mean()*100)

    checks.append(("Mismatch BIN vs Billing", mismatch_rate(df['geo_bin'], df['billing_country'])))
    checks.append(("Mismatch BIN vs IP", mismatch_rate(df['geo_bin'], df['geo_ip'])))
    checks.append(("Mismatch Billing vs IP", mismatch_rate(df['billing_country'], df['geo_ip'])))

    dq = pd.DataFrame(checks, columns=['check','percent']).round(2)
    st.dataframe(dq, use_container_width=True)

    st.markdown("""
**Интерпретация:**
- Высокая доля `Missing` по Billing/IP/UA/Accept-Language может указывать на ошибки заполнения `body`/заголовков или сбои интеграции.
- Высокая `Mismatch` BIN vs Billing/IP — сигнал о прокси/тревел/подарочных картах или подмене данных.
- Используйте вкладку **Drivers**, чтобы связать провалы AR% с конкретными `gateway_code|message` и оценить, что можно исправить на вашей стороне (валидация адреса/языка/браузера) vs. что остаётся на стороне эмитента/юзера.
""")

# -------------------- Exports --------------------
@st.cache_data
def to_csv_bytes(_df: pd.DataFrame) -> bytes:
    return _df.to_csv(index=False).encode("utf-8")

st.header("Экспорты")
try:
    st.download_button("daily_metrics.csv", data=to_csv_bytes(daily), file_name="daily_metrics.csv")
    st.download_button("weekly_metrics.csv", data=to_csv_bytes(weekly), file_name="weekly_metrics.csv")
    st.download_button("monthly_metrics.csv", data=to_csv_bytes(monthly), file_name="monthly_metrics.csv")
    # drivers table may be large; recompute with default week for stability
    drv_def = pd.concat([
        drivers_for_last_period(df, 'geo_bin', "week"),
        drivers_for_last_period(df, 'billing_country', "week"),
        drivers_for_last_period(df, 'geo_ip', "week"),
        drivers_for_last_period(df, 'shipping_country', "week"),
    ], ignore_index=True)
    st.download_button("drivers_explainer_week.csv", data=to_csv_bytes(drv_def), file_name="drivers_explainer_week.csv")
    st.download_button("decline_catalog.csv", data=to_csv_bytes(cat_tbl), file_name="decline_catalog.csv")
    st.download_button("dq_checks.csv", data=to_csv_bytes(dq), file_name="dq_checks.csv")
except Exception:
    st.warning("Экспорты недоступны до построения соответствующих таблиц.")
