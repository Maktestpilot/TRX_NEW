# txn_local_analysis_app.py
# Streamlit застосунок для локального аналізу транзакцій з CSV:
# - Гео з трьох джерел: BIN (bin_country), Billing (із body/JSON), IP (із колонки або додаткового мапінгу)
# - Топ причин відмов: gateway_code + gateway_message
# - Щоденні/тижневі/місячні метрики, WoW/МoM дельти, DQ-перевірки
#
# Запуск:
#   pip install streamlit pandas numpy matplotlib
#   streamlit run txn_local_analysis_app.py

import json
import io
import re
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Txn Local Analytics (BIN/Billing/IP)", layout="wide")
st.title("Локальний аналітичний застосунок: BIN/Billing/IP та причини відмов")

st.caption("""
Завантажте основний CSV-експорт (`pt × ci × t × ap`), а також **опціонально** — файл зіставлення IP→Country,
якщо у ваших даних немає готової колонки `ip_country`. Застосунок працює локально, без звернень у зовнішній інтернет.
""")

# ---------- Helpers ----------

JSON_CANDIDATES = ["body", "request_payload", "response_payload"]
UA_CANDIDATES = ["user_agent", "ua", "client_user_agent"]
LANG_CANDIDATES = ["accept_language", "language", "browser_language"]
IP_CANDIDATES = ["ip_country", "ip_country_iso", "client_ip_country", "ip"]
BIN_COUNTRY_CANDIDATES = ["bin_country", "bin_country_iso", "issuer_country", "ci.bin_country_iso"]

SUCCESS_STATUSES_DEFAULT = ['approved','authorized','captured','success','paid','completed','ok']

def pick_first_col(df: pd.DataFrame, names: List[str]) -> Optional[str]:
    lower_cols = {c.lower(): c for c in df.columns}
    for name in names:
        if name in lower_cols:
            return lower_cols[name]
    # try endswith
    for c in df.columns:
        lc = c.lower()
        if any(lc.endswith("." + n) for n in names):
            return c
    return None

def try_parse_json(val: Any) -> Optional[Dict[str, Any]]:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = str(val).strip()
    if not s:
        return None
    # must look like JSON object/array
    if not (s.startswith("{") or s.startswith("[")):
        return None
    try:
        return json.loads(s)
    except Exception:
        return None

def deep_get(d: Any, path_variants: List[List[str]]) -> Optional[Any]:
    """Try multiple path variants in nested dicts: e.g. [['billing','country'], ['billing_address','country']]"""
    for path in path_variants:
        cur = d
        ok = True
        for p in path:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                ok = False
                break
        if ok:
            return cur
    return None

def normalize_iso2(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    return s.upper()[:2]

def month_floor(dt: pd.Series) -> pd.Series:
    return pd.to_datetime(dt.dt.year.astype(str) + "-" + dt.dt.month.astype(str) + "-01")

# ---------- Inputs ----------

main_csv = st.file_uploader("Основний CSV (JOIN pt × ci × t × ap)", type=["csv"])
ip_map_csv = st.file_uploader("Опціонально: CSV мапінгу IP→Country (колонки: ip,country)", type=["csv"])

success_labels = st.multiselect(
    "Статуси, які вважаємо успішними (payment_status_code):",
    options=SUCCESS_STATUSES_DEFAULT,
    default=['approved','authorized','captured','success']
)

country_scope = st.multiselect("Аналізуємо країни (ISO2):", options=['AU','DE','IT','HU'], default=['AU','DE','IT','HU'])

if main_csv is None:
    st.info("Очікую на основний CSV...")
    st.stop()

df = pd.read_csv(main_csv)

# Pick columns
col_created = pick_first_col(df, ["created_at"])
col_status  = pick_first_col(df, ["payment_status_code","status"])
col_gate_cd = pick_first_col(df, ["gateway_code"])
col_gate_msg= pick_first_col(df, ["gateway_message","message","gateway_text","decline_reason"])

col_bin_country = pick_first_col(df, BIN_COUNTRY_CANDIDATES)
col_ip_country  = pick_first_col(df, IP_CANDIDATES)
col_ua          = pick_first_col(df, UA_CANDIDATES)
col_lang        = pick_first_col(df, LANG_CANDIDATES)

json_cols_detected = [c for c in JSON_CANDIDATES if pick_first_col(df, [c])]
json_cols_detected = [pick_first_col(df, [c]) for c in JSON_CANDIDATES if pick_first_col(df, [c])]

missing = [("created_at", col_created), ("payment_status_code/status", col_status), ("gateway_code", col_gate_cd)]
missing = [name for name, col in missing if col is None]
if missing:
    st.error(f"Відсутні ключові колонки в CSV: {missing}. Додайте їх у експорт і завантажте знову.")
    st.stop()

# Parse datetimes
df[col_created] = pd.to_datetime(df[col_created], errors='coerce', utc=True)
df = df.dropna(subset=[col_created])

# Build BIN geo
df['geo_bin'] = df[col_bin_country].astype(str).str.upper().str.slice(0,2) if col_bin_country else np.nan

# Parse JSON bodies to extract billing address and language if present
def extract_from_json_rows(df: pd.DataFrame) -> pd.DataFrame:
    billing_country, billing_zip, billing_city, billing_addr, browser_lang = [], [], [], [], []
    for _, row in df.iterrows():
        parsed = None
        for jc in json_cols_detected:
            parsed = try_parse_json(row.get(jc))
            if parsed: break
        if not parsed:
            billing_country.append(None); billing_zip.append(None); billing_city.append(None); billing_addr.append(None); browser_lang.append(None); continue

        bc = deep_get(parsed, [['billing','country'], ['billing_address','country'], ['address','country']])
        bz = deep_get(parsed, [['billing','zip'], ['billing','postal_code'], ['billing_address','zip'], ['address','zip']])
        bcity = deep_get(parsed, [['billing','city'], ['billing_address','city'], ['address','city']])
        baddr = deep_get(parsed, [['billing','address'], ['billing_address','line1'], ['billing_address','address1'], ['address','line1']])
        lang = deep_get(parsed, [['browser','language'], ['device','language'], ['headers','accept-language']])

        billing_country.append(normalize_iso2(bc))
        billing_zip.append(bz if (bz is None or str(bz).strip()!='') else None)
        billing_city.append(bcity if (bcity is None or str(bcity).strip()!='') else None)
        billing_addr.append(baddr if (baddr is None or str(baddr).strip()!='') else None)
        browser_lang.append(lang if (lang is None or str(lang).strip()!='') else None)
    out = pd.DataFrame({
        'billing_country': billing_country,
        'billing_zip': billing_zip,
        'billing_city': billing_city,
        'billing_address': billing_addr,
        'browser_language_from_body': browser_lang
    })
    return out

json_extracted = extract_from_json_rows(df)
df = pd.concat([df.reset_index(drop=True), json_extracted.reset_index(drop=True)], axis=1)

# User agent & Accept-Language outside JSON
df['user_agent'] = df[col_ua] if col_ua else None
df['accept_language_hdr'] = df[col_lang] if col_lang else None

# IP country resolution
if col_ip_country and col_ip_country.lower().startswith("ip_") and "country" in col_ip_country.lower():
    # already country code
    df['geo_ip'] = df[col_ip_country].astype(str).str.upper().str.slice(0,2)
else:
    # Try use optional mapping file if provided & we have an 'ip' column
    ip_col_name = None
    if col_ip_country and col_ip_country.lower() == "ip":
        ip_col_name = col_ip_country
    else:
        # try find 'ip' column
        ip_col_name = pick_first_col(df, ["ip","client_ip","t.ip"])

    if ip_col_name and ip_map_csv is not None:
        ip_map = pd.read_csv(ip_map_csv)
        if set(['ip','country']).issubset({c.lower() for c in ip_map.columns}):
            # normalize column names to lower for merge
            ip_map.columns = [c.lower() for c in ip_map.columns]
            df = df.merge(ip_map[['ip','country']], left_on=ip_col_name, right_on='ip', how='left')
            df['geo_ip'] = df['country'].astype(str).str.upper().str.slice(0,2)
            df.drop(columns=['ip','country'], inplace=True)
        else:
            st.warning("IP-мепінг: очікую колонки 'ip' та 'country'. Мепінг проігноровано.")
            df['geo_ip'] = np.nan
    else:
        df['geo_ip'] = np.nan

# Build outcome
status_series = df[col_status].astype(str).str.lower()
df['is_approved'] = status_series.isin([s.lower() for s in success_labels])

# Gateway fields
df['gateway_code'] = df[col_gate_cd]
df['gateway_message'] = df[col_gate_msg] if col_gate_msg else None

# Filter by scope
df = df[(df['geo_bin'].isin(country_scope)) | (df['billing_country'].isin(country_scope)) | (df['geo_ip'].isin(country_scope))]

# Time grains
df['day'] = df[col_created].dt.floor('D')
df['week'] = df[col_created].dt.to_period('W').apply(lambda r: r.start_time)
df['month'] = df[col_created].dt.to_period('M').apply(lambda r: r.start_time)

min_dt, max_dt = df[col_created].min(), df[col_created].max()
st.info(f"Діапазон дат у файлі (UTC): **{min_dt} → {max_dt}** | Рядків після фільтру: **{len(df)}**")

# ---------- METRICS BY GEO SOURCE ----------

def agg_metrics(df: pd.DataFrame, geo_col: str, grain: str) -> pd.DataFrame:
    out = (df.groupby([grain, geo_col], as_index=False)
             .agg(attempts=(col_status, 'size'),
                  approved=('is_approved', 'sum')))
    out['ar_pct'] = (100.0 * out['approved'] / out['attempts']).round(2)
    out = out.rename(columns={geo_col: 'geo'})
    out['geo_source'] = geo_col
    return out

tabs = st.tabs(["Daily","Weekly","Monthly"])

with tabs[0]:
    st.subheader("Щоденні метрики за джерелом GEO")
    daily = pd.concat([
        agg_metrics(df, 'geo_bin','day'),
        agg_metrics(df, 'billing_country','day'),
        agg_metrics(df, 'geo_ip','day'),
    ], ignore_index=True)
    st.dataframe(daily.sort_values(['day','geo_source','geo']), use_container_width=True)

    # charts
    st.markdown("**Графіки AR% (по кожному джерелу GEO)**")
    for source in ['geo_bin','billing_country','geo_ip']:
        tmp = daily[daily['geo_source']==source]
        if tmp.empty: continue
        for g in sorted(tmp['geo'].dropna().unique()):
            fig = plt.figure()
            plt.plot(tmp[tmp['geo']==g]['day'], tmp[tmp['geo']==g]['ar_pct'])
            plt.title(f"AR% — {g} ({source})")
            plt.xlabel("Day"); plt.ylabel("AR%")
            st.pyplot(fig)

with tabs[1]:
    st.subheader("Тижневі метрики за джерелом GEO (та WoW-дельти)")
    weekly = pd.concat([
        agg_metrics(df, 'geo_bin','week'),
        agg_metrics(df, 'billing_country','week'),
        agg_metrics(df, 'geo_ip','week'),
    ], ignore_index=True)

    # WoW delta
    weekly_sorted = weekly.sort_values(['geo_source','geo','week'])
    weekly_sorted['ar_prev'] = weekly_sorted.groupby(['geo_source','geo'])['ar_pct'].shift(1)
    weekly_sorted['delta_ar'] = (weekly_sorted['ar_pct'] - weekly_sorted['ar_prev']).round(2)

    st.dataframe(weekly_sorted.sort_values(['week','geo_source','geo'], ascending=[False,True,True]), use_container_width=True)

    # Highlight largest changes
    top_changes = (weekly_sorted.dropna(subset=['delta_ar'])
                   .sort_values('delta_ar', ascending=True)
                   .groupby(['geo_source'])
                   .head(10))
    st.markdown("**Найбільші негативні зміни WoW (топ-10 на джерело GEO):**")
    st.dataframe(top_changes, use_container_width=True)

with tabs[2]:
    st.subheader("Місячні метрики за джерелом GEO (та MoM-дельти)")
    monthly = pd.concat([
        agg_metrics(df, 'geo_bin','month'),
        agg_metrics(df, 'billing_country','month'),
        agg_metrics(df, 'geo_ip','month'),
    ], ignore_index=True)

    monthly_sorted = monthly.sort_values(['geo_source','geo','month'])
    monthly_sorted['ar_prev'] = monthly_sorted.groupby(['geo_source','geo'])['ar_pct'].shift(1)
    monthly_sorted['delta_ar'] = (monthly_sorted['ar_pct'] - monthly_sorted['ar_prev']).round(2)

    st.dataframe(monthly_sorted.sort_values(['month','geo_source','geo'], ascending=[False,True,True]), use_container_width=True)

# ---------- TOP DECLINES (gateway_code + gateway_message) ----------
st.header("Топ причин відмов")
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
], ignore_index=True)

st.dataframe(top_tbl.sort_values([grain,'geo_source','geo','declines'], ascending=[False,True,True,False]).head(300), use_container_width=True)

# ---------- DATA QUALITY ----------
st.header("Перевірки якості даних (DQ)")

dq_rows = []
dq_rows.append(("Missing BIN country", float((df['geo_bin'].isna() | (df['geo_bin']=="")).mean()*100)))
dq_rows.append(("Missing Billing country", float((df['billing_country'].isna() | (df['billing_country']=="")).mean()*100)))
dq_rows.append(("Missing IP country", float((df['geo_ip'].isna() | (df['geo_ip']=="")).mean()*100)))

# Presence of UA & language & billing details
dq_rows.append(("Missing User-Agent", float((df['user_agent'].isna() | (df['user_agent']=="")).mean()*100)))
dq_rows.append(("Missing Accept-Language header", float((df['accept_language_hdr'].isna() | (df['accept_language_hdr']=="")).mean()*100)))
dq_rows.append(("Missing Billing ZIP", float((df['billing_zip'].isna() | (df['billing_zip']=="")).mean()*100)))
dq_rows.append(("Missing Billing City", float((df['billing_city'].isna() | (df['billing_city']=="")).mean()*100)))
dq_rows.append(("Missing Billing Address", float((df['billing_address'].isna() | (df['billing_address']=="")).mean()*100)))

# Mismatch rates
def mismatch_rate(a: pd.Series, b: pd.Series) -> float:
    both = (~a.isna()) & (~b.isna())
    if both.sum() == 0: return float('nan')
    return float((a[both] != b[both]).mean()*100)

dq_rows.append(("Mismatch BIN vs Billing country", mismatch_rate(df['geo_bin'], df['billing_country'])))
dq_rows.append(("Mismatch BIN vs IP country", mismatch_rate(df['geo_bin'], df['geo_ip'])))
dq_rows.append(("Mismatch Billing vs IP country", mismatch_rate(df['billing_country'], df['geo_ip'])))

dq = pd.DataFrame(dq_rows, columns=['check','percent'])
st.dataframe(dq, use_container_width=True)

# Gateway code consistency: one code -> many messages?
cons = (declines.groupby(['gateway_code','gateway_message'], as_index=False)
               .size().rename(columns={'size':'cnt'}))
code_variety = (cons.groupby('gateway_code', as_index=False)['gateway_message'].nunique()
                     .rename(columns={'gateway_message':'distinct_messages'})
               ).sort_values('distinct_messages', ascending=False)
st.subheader("Варіативність повідомлень для одного gateway_code")
st.dataframe(code_variety.head(50), use_container_width=True)

# Export buttons
st.header("Експорти")
@st.cache_data
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

st.download_button("Завантажити (daily metrics)", data=to_csv_bytes(daily), file_name="daily_metrics.csv")
st.download_button("Завантажити (weekly metrics)", data=to_csv_bytes(weekly_sorted), file_name="weekly_metrics.csv")
st.download_button("Завантажити (monthly metrics)", data=to_csv_bytes(monthly_sorted), file_name="monthly_metrics.csv")
st.download_button("Завантажити (top declines)", data=to_csv_bytes(top_tbl), file_name="top_declines.csv")
st.download_button("Завантажити (DQ)", data=to_csv_bytes(dq), file_name="dq_checks.csv")
