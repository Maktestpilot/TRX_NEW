# txn_analytics_app.py
# Streamlit-додаток для швидкого аналізу CSV-експорту транзакцій
# Фокус: AU/DE/IT/HU, щоденні метрики та топ причин відмов (gateway_code)
#
# Запуск локально:
#   pip install streamlit pandas numpy
#   streamlit run txn_analytics_app.py

import io
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="Txn Analytics (AU/DE/IT/HU)", layout="wide")

st.title("Аналіз прохідності та відмов (AU/DE/IT/HU)")
st.caption("Завантажте CSV з результатом JOIN (pt × ci × t). Мінімально потрібні колонки: created_at, bin_country_iso, payment_status_code, gateway_code.")

uploaded = st.file_uploader("Завантажте CSV", type=["csv"])

default_success_labels = ['approved','authorized','captured','success']
success_labels = st.multiselect(
    "Які значення payment_status_code рахувати як успішні?",
    options=default_success_labels + ['paid','completed','ok'],
    default=default_success_labels
)

country_filter = st.multiselect(
    "Країни (ISO2, емітент за BIN)",
    options=['AU','DE','IT','HU'],
    default=['AU','DE','IT','HU']
)

if uploaded is not None:
    df = pd.read_csv(uploaded)

    # Мінімальна валідація
    required_cols = ['created_at','bin_country_iso','payment_status_code','gateway_code']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Відсутні обов'язкові колонки: {missing}")
        st.stop()

    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce', utc=True)
    df['geo'] = df['bin_country_iso'].astype(str).str.upper().replace({'': np.nan})
    df = df.dropna(subset=['created_at'])

    # Фільтр країн
    df = df[df['geo'].isin(country_filter)]

    # Контрольний діапазон дат
    min_dt, max_dt = df['created_at'].min(), df['created_at'].max()
    st.info(f"Діапазон дат у файлі (UTC): **{min_dt} → {max_dt}**")

    # === 1) Daily metrics ===
    daily = (
        df.assign(day=lambda x: x['created_at'].dt.floor('D'))
          .groupby(['day','geo'], as_index=False)
          .agg(
              attempts=('payment_status_code','size'),
              approved=('payment_status_code', lambda s: s.isin(success_labels).sum())
          )
    )
    daily['ar_pct'] = (100.0 * daily['approved'] / daily['attempts']).round(2)

    st.subheader("Щоденні метрики (attempts / approved / AR%)")
    st.dataframe(daily.sort_values(['day','geo'], ascending=[False, True]), use_container_width=True)

    # Графіки
    st.subheader("Графік: Attempts за день")
    import matplotlib.pyplot as plt

    for geo in country_filter:
        tmp = daily[daily['geo']==geo]
        fig = plt.figure()
        plt.plot(tmp['day'], tmp['attempts'])
        plt.title(f"Attempts — {geo}")
        plt.xlabel("Day")
        plt.ylabel("Attempts")
        st.pyplot(fig)

    st.subheader("Графік: Approval rate (AR%) за день")
    for geo in country_filter:
        tmp = daily[daily['geo']==geo]
        fig = plt.figure()
        plt.plot(tmp['day'], tmp['ar_pct'])
        plt.title(f"AR% — {geo}")
        plt.xlabel("Day")
        plt.ylabel("AR%")
        st.pyplot(fig)

    # === 2) Top decline reasons (weekly) ===
    df['week'] = df['created_at'].dt.to_period('W').apply(lambda r: r.start_time)
    declines = df[~df['payment_status_code'].isin(success_labels)]
    wk = (
        declines.groupby(['week','geo','gateway_code'], as_index=False)
                .size()
                .rename(columns={'size':'declines'})
    )
    wk_tot = wk.groupby(['week','geo'], as_index=False)['declines'].sum().rename(columns={'declines':'total_declines'})
    wk = wk.merge(wk_tot, on=['week','geo'], how='left')
    wk['share_pct'] = (100.0 * wk['declines'] / wk['total_declines']).round(2)

    st.subheader("Топ причин відмов (gateway_code) за тиждень")
    st.dataframe(
        wk.sort_values(['week','geo','declines'], ascending=[False, True, False]).head(200),
        use_container_width=True
    )

    # === 3) Data quality: наявність GEO ===
    dq_null_geo = (df['geo'].isna() | (df['geo']=='')).mean() * 100.0
    st.subheader("Якість даних — наявність GEO (bin_country_iso)")
    st.write(f"Відсоток порожніх GEO: **{dq_null_geo:.2f}%**")

else:
    st.info("Очікую на CSV...")
