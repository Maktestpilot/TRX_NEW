# txn_local_analysis_app.py
# Локальний аналітичний застосунок із глибоким парсингом JSON body для user-полів
#
# Правила:
# - Успіх транзакції: (status_title != 'Failed') AND (is_final == TRUE)
# - Метрики рахуються лише по фінальних записах
# - GEO: BIN (bin_country), Billing (із JSON), IP (із колонки або CSV-мапи ip→country)
# - JSON-поля: body / request_payload / response_payload (будь-яке з них, якщо валідне)
#
# Запуск:
#   pip install streamlit pandas numpy matplotlib
#   streamlit run txn_local_analysis_app.py

import json
import re
from typing import Any, Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Txn Local Analytics (User + GEO + Declines)", layout="wide")
st.title("Локальний аналітичний застосунок: користувач (з JSON body), GEO та причини відмов")

st.caption("""
Завантажте основний CSV (`pt × ci × t × ap`). Успішність: `status_title != 'Failed'` **та** `is_final == TRUE`.
Застосунок витягує з JSON **додаткові user-поля** (email/phone/name/id, shipping/billing, device/browser, IP, language).
""")

# ---------- Helpers ----------

JSON_CANDIDATES = ["body", "request_payload", "response_payload"]
UA_CANDIDATES = ["user_agent", "ua", "client_user_agent", "headers.user-agent"]
LANG_CANDIDATES = ["accept_language", "accept-language", "language", "browser_language", "headers.accept-language"]
IP_COUNTRY_CANDIDATES = ["ip_country", "ip_country_iso", "client_ip_country"]
IP_RAW_CANDIDATES = ["ip", "client_ip", "t.ip", "headers.x-forwarded-for"]
BIN_COUNTRY_CANDIDATES = ["bin_country", "bin_country_iso", "issuer_country", "ci.bin_country_iso"]

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
    """DFS-флеттенер JSON у (path, value). Масиви повертаємо із числовим індексом."""
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

# ---------- Inputs ----------

main_csv = st.file_uploader("Основний CSV (JOIN pt × ci × t × ap)", type=["csv"])
ip_map_csv = st.file_uploader("Опціонально: CSV мапінгу IP→Country (колонки: ip,country)", type=["csv"])

if main_csv is None:
    st.info("Очікую на основний CSV...")
    st.stop()

df = pd.read_csv(main_csv)

# --- Detect key columns ---
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

json_cols = [c for c in JSON_CANDIDATES if pick_first_col(df, [c])]
json_cols = [pick_first_col(df, [c]) for c in JSON_CANDIDATES if pick_first_col(df, [c])]

missing = []
for label, col in [("created_at", col_created), ("status_title", col_status_title), ("is_final", col_is_final), ("gateway_code", col_gate_cd)]:
    if col is None: missing.append(label)

if missing:
    st.error(f"Відсутні ключові колонки: {missing}. Додайте їх у експорт і завантажте знову.")
    st.stop()

# --- Normalize/parse basics ---
df[col_created] = pd.to_datetime(df[col_created], errors='coerce', utc=True)
df = df.dropna(subset=[col_created])

df['is_final_bool'] = to_bool_series(df[col_is_final])
status_title_l = df[col_status_title].astype(str).str.strip().str.lower()
df['is_failed'] = status_title_l.eq('failed')
df['is_approved'] = (~df['is_failed']) & (df['is_final_bool'])

# Only final for metrics
df = df[df['is_final_bool']]

# BIN geo
df['geo_bin'] = df[col_bin_country].astype(str).str.upper().str.slice(0,2) if col_bin_country else np.nan

# --- Deep JSON extraction per row ---
def extract_user_fields_from_row(row: pd.Series) -> Dict[str, Any]:
    parsed = None
    for jc in json_cols:
        parsed = try_parse_json(row.get(jc))
        if parsed is not None:
            break
    if parsed is None:
        return {
            'billing_country': None, 'billing_zip': None, 'billing_city': None, 'billing_address1': None, 'billing_address2': None,
            'shipping_country': None, 'shipping_zip': None, 'shipping_city': None, 'shipping_address1': None, 'shipping_address2': None, 'shipping_name': None,
            'email': None, 'phone': None, 'first_name': None, 'last_name': None, 'full_name': None,
            'user_id': None, 'customer_id': None, 'account_id': None, 'session_id': None,
            'device_id': None, 'fingerprint': None, 'browser_name': None, 'browser_version': None,
            'browser_language_from_body': None, 'os_name': None, 'os_version': None, 'timezone': None,
            'ip_from_body': None
        }

    flat = flatten_json(parsed)
    # regexes for lookup
    rx = lambda *alts: [re.compile(a, re.I) for a in alts]

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
    full_name = lookup_first(flat, rx(r'full_?name$', r'^name$', r'user\.name$', r'customer\.name$', r'cardholder\.name$', r'billing_?name$'))

    user_id = lookup_first(flat, rx(r'user_?id$', r'^user\.id$', r'uid$', r'guid$'))
    customer_id = lookup_first(flat, rx(r'customer_?id$', r'customer\.id$'))
    account_id = lookup_first(flat, rx(r'account_?id$', r'account\.id$'))
    session_id = lookup_first(flat, rx(r'session_?id$', r'session\.id$'))

    # Device/browser
    device_id = lookup_first(flat, rx(r'device_?id$', r'device\.id$', r'fingerprint$', r'device\.fingerprint$'))
    fingerprint = lookup_first(flat, rx(r'fingerprint$', r'device\.fingerprint$'))
    browser_name = lookup_first(flat, rx(r'browser\.name$', r'^browser$'))
    browser_version = lookup_first(flat, rx(r'browser\.version$', r'br(?:owser)?_?version$'))
    browser_lang = lookup_first(flat, rx(r'browser\.language$', r'headers\.accept-language$', r'accept-?language$'))
    os_name = lookup_first(flat, rx(r'device\.os$', r'\bos\b', r'operating_?system$'))
    os_version = lookup_first(flat, rx(r'device\.os_?version$', r'os_?version$'))
    timezone = lookup_first(flat, rx(r'timezone$', r'device\.timezone$', r'browser\.timezone$'))
    ip_body = lookup_first(flat, rx(r'ip$', r'client_?ip$', r'remote_?ip$', r'headers\.x-forwarded-for$'))

    # Normalize
    bc = normalize_iso2(bc); sc = normalize_iso2(sc)
    email = (str(email).strip().lower() if email not in [None, ""] else None)
    phone = norm_phone(phone)
    if not full_name:
        parts = [p for p in [fname, lname] if p and str(p).strip()]
        full_name = " ".join(map(str, parts)) if parts else None
    if isinstance(ip_body, str) and "," in ip_body:
        ip_body = first_in_csv_list(ip_body)

    return {
        'billing_country': bc, 'billing_zip': bzip, 'billing_city': bcity, 'billing_address1': baddr1, 'billing_address2': baddr2,
        'shipping_country': sc, 'shipping_zip': szip, 'shipping_city': scity, 'shipping_address1': saddr1, 'shipping_address2': saddr2, 'shipping_name': sname,
        'email': email, 'phone': phone, 'first_name': fname, 'last_name': lname, 'full_name': full_name,
        'user_id': user_id, 'customer_id': customer_id, 'account_id': account_id, 'session_id': session_id,
        'device_id': device_id, 'fingerprint': fingerprint, 'browser_name': browser_name, 'browser_version': browser_version,
        'browser_language_from_body': browser_lang, 'os_name': os_name, 'os_version': os_version, 'timezone': timezone,
        'ip_from_body': ip_body
    }

# Apply extraction
enriched = df.apply(extract_user_fields_from_row, axis=1, result_type='expand')
df = pd.concat([df.reset_index(drop=True), enriched.reset_index(drop=True)], axis=1)

# UA & Accept-Language (headers from columns)
df['user_agent'] = df[pick_first_col(df, UA_CANDIDATES)] if pick_first_col(df, UA_CANDIDATES) else None
df['accept_language_hdr'] = df[pick_first_col(df, LANG_CANDIDATES)] if pick_first_col(df, LANG_CANDIDATES) else None

# IP country resolution
if col_ip_country:
    df['geo_ip'] = df[col_ip_country].astype(str).str.upper().str.slice(0,2)
else:
    if ip_map_csv is not None and col_ip_raw:
        ip_map = pd.read_csv(ip_map_csv)
        cols_lower = {c.lower(): c for c in ip_map.columns}
        if 'ip' in cols_lower and 'country' in cols_lower:
            ip_map.rename(columns=cols_lower, inplace=True)
            df = df.merge(ip_map[['ip','country']], left_on=col_ip_raw, right_on='ip', how='left')
            df['geo_ip'] = df['country'].astype(str).str.upper().str.slice(0,2)
            df.drop(columns=['ip','country'], inplace=True)
        else:
            st.warning("IP-мепінг: очікую колонки 'ip' та 'country'. Мепінг проігноровано.")
            df['geo_ip'] = np.nan
    else:
        df['geo_ip'] = np.nan

# Time grains
df['day'] = df[col_created].dt.floor('D')
df['week'] = df[col_created].dt.to_period('W').apply(lambda r: r.start_time)
df['month'] = df[col_created].dt.to_period('M').apply(lambda r: r.start_time)

min_dt, max_dt = df[col_created].min(), df[col_created].max()
st.info(f"Діапазон (UTC): **{min_dt} → {max_dt}** | Фінальних рядків: **{len(df)}**")

# ---------- Dynamic countries from all sources ----------
all_countries = pd.unique(pd.concat([
    df['geo_bin'].dropna().astype(str),
    df['billing_country'].dropna().astype(str),
    df['geo_ip'].dropna().astype(str),
    df['shipping_country'].dropna().astype(str),
], ignore_index=True))
all_countries = sorted([c for c in all_countries if c and c != 'NA'])

country_filter = st.multiselect("Країни для аналізу (ISO2, з даних):", options=all_countries, default=all_countries)

df = df[
    (df['geo_bin'].isin(country_filter)) |
    (df['billing_country'].isin(country_filter)) |
    (df['geo_ip'].isin(country_filter)) |
    (df['shipping_country'].isin(country_filter))
]

# Gateway fields for declines
df['gateway_code'] = df[col_gate_cd]
df['gateway_message'] = df[col_gate_msg] if col_gate_msg else None

# ---------- METRICS ----------
def agg_metrics(_df: pd.DataFrame, geo_col: str, grain: str) -> pd.DataFrame:
    out = (_df.groupby([grain, geo_col], as_index=False)
             .agg(attempts=('is_approved', 'size'),
                  approved=('is_approved', 'sum')))
    out['ar_pct'] = (100.0 * out['approved'] / out['attempts']).round(2)
    out = out.rename(columns={geo_col: 'geo'})
    out['geo_source'] = geo_col
    return out

tabs = st.tabs(["Daily","Weekly","Monthly","User snapshot"])

with tabs[0]:
    st.subheader("Щоденні метрики за джерелом GEO (final=TRUE)")
    daily = pd.concat([
        agg_metrics(df, 'geo_bin','day'),
        agg_metrics(df, 'billing_country','day'),
        agg_metrics(df, 'geo_ip','day'),
        agg_metrics(df, 'shipping_country','day'),
    ], ignore_index=True)
    st.dataframe(daily.sort_values(['day','geo_source','geo']), use_container_width=True)

    st.markdown("**AR% графіки**")
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
    st.subheader("Тижневі метрики + WoW")
    weekly = pd.concat([
        agg_metrics(df, 'geo_bin','week'),
        agg_metrics(df, 'billing_country','week'),
        agg_metrics(df, 'geo_ip','week'),
        agg_metrics(df, 'shipping_country','week'),
    ], ignore_index=True)
    weekly_sorted = weekly.sort_values(['geo_source','geo','week'])
    weekly_sorted['ar_prev'] = weekly_sorted.groupby(['geo_source','geo'])['ar_pct'].shift(1)
    weekly_sorted['delta_ar'] = (weekly_sorted['ar_pct'] - weekly_sorted['ar_prev']).round(2)
    st.dataframe(weekly_sorted.sort_values(['week','geo_source','geo'], ascending=[False,True,True]), use_container_width=True)

with tabs[2]:
    st.subheader("Місячні метрики + MoM")
    monthly = pd.concat([
        agg_metrics(df, 'geo_bin','month'),
        agg_metrics(df, 'billing_country','month'),
        agg_metrics(df, 'geo_ip','month'),
        agg_metrics(df, 'shipping_country','month'),
    ], ignore_index=True)
    monthly_sorted = monthly.sort_values(['geo_source','geo','month'])
    monthly_sorted['ar_prev'] = monthly_sorted.groupby(['geo_source','geo'])['ar_pct'].shift(1)
    monthly_sorted['delta_ar'] = (monthly_sorted['ar_pct'] - monthly_sorted['ar_prev']).round(2)
    st.dataframe(monthly_sorted.sort_values(['month','geo_source','geo'], ascending=[False,True,True]), use_container_width=True)

# ---------- USER SNAPSHOT ----------
with tabs[3]:
    st.subheader("User snapshot (на рівні транзакції)")
    cols_user = [
        col_created, 'is_approved', 'geo_bin','billing_country','geo_ip','shipping_country',
        'email','phone','full_name','first_name','last_name',
        'user_id','customer_id','account_id','session_id',
        'device_id','fingerprint','browser_name','browser_version','browser_language_from_body','accept_language_hdr','user_agent',
        'ip_from_body'
    ]
    present = [c for c in cols_user if c in df.columns]
    st.dataframe(df[present].sort_values(col_created, ascending=False).head(300), use_container_width=True)

    st.markdown("**Агрегація по користувачу** (anchor = email → phone → customer_id → user_id):")
    anchor = df[['email','phone','customer_id','user_id']].fillna('')
    anchor = anchor.apply(lambda r: r['email'] or r['phone'] or r['customer_id'] or r['user_id'], axis=1)
    df['_user_anchor'] = anchor.replace('', np.nan)

    agg_user = (df.dropna(subset=['_user_anchor'])
                  .groupby('_user_anchor', as_index=False)
                  .agg(
                      txns=('is_approved','size'),
                      approved=('is_approved','sum'),
                      first_txn=(col_created,'min'),
                      last_txn=(col_created,'max')
                  ))
    agg_user['ar_pct'] = (100.0 * agg_user['approved']/agg_user['txns']).round(2)
    st.dataframe(agg_user.sort_values(['txns','ar_pct'], ascending=[False,False]).head(300), use_container_width=True)

# ---------- TOP DECLINES (gateway_code + gateway_message) ----------
st.header("Топ причин відмов (final=TRUE)")
grain = st.selectbox("Групування:", ["week","month","day"], index=1)

declines = df[~df['is_approved']].copy()
declines['code_msg'] = declines['gateway_code'].astype(str) + " | " + declines['gateway_message'].astype(str)

def top_declines(data: pd.DataFrame, geo_col: str) -> pd.DataFrame:
    grp = (data.groupby([grain, geo_col, 'code_msg'], as_index=False)
               .size().rename(columns={'size':'declines'}))
    tot = grp.groupby([grain, geo_col], as_index=False)['declines'].sum().rename(columns={'declines':'total_declines'})
    out = grp.merge(tot, on=[grain, geo_col], how='left')
    out['share_pct'] = (100.0 * out['declines'] / out['total_declines']).round(2)
    out = out.rename(columns={geo_col:'geo'})
    out['geo_source'] = geo_col
    return out

top_tbl = pd.concat([
    top_declines(declines, 'geo_bin'),
    top_declines(declines, 'billing_country'),
    top_declines(declines, 'geo_ip'),
    top_declines(declines, 'shipping_country'),
], ignore_index=True)

st.dataframe(top_tbl.sort_values([grain,'geo_source','geo','declines'], ascending=[False,True,True,False]).head(800), use_container_width=True)

# ---------- DATA QUALITY ----------
st.header("Перевірки якості даних (DQ)")

dq_rows = []
def pct_missing(s: pd.Series) -> float:
    return float((s.isna() | (s=="")).mean()*100)

dq_rows.append(("Missing BIN country", pct_missing(df['geo_bin'])))
dq_rows.append(("Missing Billing country", pct_missing(df['billing_country'])))
dq_rows.append(("Missing Shipping country", pct_missing(df['shipping_country'])))
dq_rows.append(("Missing IP country", pct_missing(df['geo_ip'])))

dq_rows.append(("Missing Email", pct_missing(df['email'])))
dq_rows.append(("Missing Phone", pct_missing(df['phone'])))
dq_rows.append(("Missing Full Name", pct_missing(df['full_name'])))
dq_rows.append(("Missing Device ID", pct_missing(df['device_id'])))
dq_rows.append(("Missing Browser Name", pct_missing(df['browser_name'])))
dq_rows.append(("Missing Accept-Language (header)", pct_missing(df['accept_language_hdr'])))
dq_rows.append(("Missing Billing ZIP", pct_missing(df['billing_zip'])))
dq_rows.append(("Missing Billing City", pct_missing(df['billing_city'])))
dq_rows.append(("Missing Billing Address1", pct_missing(df['billing_address1'])))

# Mismatch rates
def mismatch_rate(a: pd.Series, b: pd.Series) -> float:
    both = (~a.isna()) & (~b.isna())
    if both.sum() == 0: return float('nan')
    return float((a[both] != b[both]).mean()*100)

dq_rows.append(("Mismatch BIN vs Billing", mismatch_rate(df['geo_bin'], df['billing_country'])))
dq_rows.append(("Mismatch BIN vs IP", mismatch_rate(df['geo_bin'], df['geo_ip'])))
dq_rows.append(("Mismatch Billing vs IP", mismatch_rate(df['billing_country'], df['geo_ip'])))

dq = pd.DataFrame(dq_rows, columns=['check','percent'])
st.dataframe(dq, use_container_width=True)

# Gateway code consistency: one code -> many messages?
cons = (declines.groupby(['gateway_code','gateway_message'], as_index=False)
               .size().rename(columns={'size':'cnt'}))
code_variety = (cons.groupby('gateway_code', as_index=False)['gateway_message'].nunique()
                     .rename(columns={'gateway_message':'distinct_messages'})
               ).sort_values('distinct_messages', ascending=False)
st.subheader("Варіативність повідомлень для одного gateway_code")
st.dataframe(code_variety.head(100), use_container_width=True)

# ---------- EXPORTS ----------
@st.cache_data
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

st.header("Експорти")
try:
    st.download_button("daily_metrics.csv", data=to_csv_bytes(daily), file_name="daily_metrics.csv")
    st.download_button("weekly_metrics.csv", data=to_csv_bytes(weekly_sorted), file_name="weekly_metrics.csv")
    st.download_button("monthly_metrics.csv", data=to_csv_bytes(monthly_sorted), file_name="monthly_metrics.csv")
    st.download_button("top_declines.csv", data=to_csv_bytes(top_tbl), file_name="top_declines.csv")
    st.download_button("user_snapshot.csv", data=to_csv_bytes(df), file_name="user_snapshot_enriched.csv")
    st.download_button("dq_checks.csv", data=to_csv_bytes(dq), file_name="dq_checks.csv")
except Exception:
    st.warning("Експорти недоступні до формування відповідних таблиць.")
