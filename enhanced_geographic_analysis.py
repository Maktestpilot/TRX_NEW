# Enhanced Geographic Analysis Application with IPinfo Integration
# Локальний аналітичний застосунок із глибоким парсингом JSON body для user-полів та IPinfo базою

import json
import re
from typing import Any, Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# IPinfo database integration
try:
    import geoip2.database
    import geoip2.errors
    IPINFO_AVAILABLE = True
except ImportError:
    IPINFO_AVAILABLE = False
    st.warning("IPinfo packages not available. Install with: pip install geoip2 maxminddb")

# st.set_page_config(  # Commented out to avoid conflicts
#     page_title="Enhanced Geographic Analysis with IPinfo",
#     page_icon="🌍",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

st.title("🌍 Enhanced Geographic Analysis with IPinfo Database")
st.caption("""
Завантажте основний CSV (`pt × ci × t × ap`). Успішність: `status_title != 'Failed'` **та** `is_final == TRUE`.
Застосунок витягує з JSON **додаткові user-поля** (email/phone/name/id, shipping/billing, device/browser, IP, language).
**НОВО: Інтеграція з IPinfo базою для точного геолокації IP адрес.**
""")

# ---------- Configuration ----------

RISK_THRESHOLDS = {
    'velocity_high': 5,
    'velocity_critical': 10,
    'geo_mismatch_score': 3,
    'velocity_score': 2,
    'amount_score': 2,
    'time_score': 1,
}

# ---------- IPinfo Database Integration ----------

class IPinfoGeolocator:
    """IP geolocation using local IPinfo MMDB database"""
    
    def __init__(self, db_path: str = "ipinfo_lite.mmdb"):
        self.db_path = db_path
        self.reader = None
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize the MMDB database reader"""
        try:
            if IPINFO_AVAILABLE:
                self.reader = geoip2.database.Reader(self.db_path)
                st.sidebar.success(f"✅ IPinfo database loaded")
            else:
                st.sidebar.error("❌ IPinfo packages not available")
        except Exception as e:
            st.sidebar.error(f"❌ Failed to load IPinfo database: {e}")
            self.reader = None
    
    def get_location(self, ip: str) -> Dict[str, Any]:
        """Get location information for an IP address"""
        if not self.reader or not ip:
            return {}
        
        try:
            # Clean IP address
            ip = str(ip).strip()
            if not ip or ip.lower() in ['nan', 'none', '']:
                return {}
            
            # Query the database
            response = self.reader.city(ip)
            
            return {
                'country': response.country.iso_code,
                'country_name': response.country.name,
                'city': response.city.name,
                'region': response.subdivisions.most_specific.name if response.subdivisions.most_specific else None,
                'latitude': response.location.latitude,
                'longitude': response.location.longitude,
                'timezone': response.location.time_zone,
                'postal_code': response.postal.code,
                'asn': response.traits.autonomous_system_number,
                'org': response.traits.autonomous_system_organization,
                'connection_type': response.traits.connection_type,
                'user_type': response.traits.user_type,
                'proxy': response.traits.is_anonymous_proxy or response.traits.is_satellite_provider,
            }
        except (geoip2.errors.AddressNotFoundError, ValueError, AttributeError):
            return {}
        except Exception as e:
            st.warning(f"IP lookup error for {ip}: {e}")
            return {}
    
    def close(self):
        """Close the database reader"""
        if self.reader:
            self.reader.close()

# ---------- Helpers ----------

JSON_CANDIDATES = ["body", "request_payload", "response_payload"]
UA_CANDIDATES = ["user_agent", "ua", "client_user_agent", "headers.user-agent"]
LANG_CANDIDATES = ["accept_language", "accept-language", "language", "browser_language", "headers.accept-language"]
IP_COUNTRY_CANDIDATES = ["ip_country", "ip_country_iso", "client_ip_country"]
IP_RAW_CANDIDATES = ["ip", "client_ip", "t.ip", "headers.x-forwarded-for"]
BIN_COUNTRY_CANDIDATES = ["bin_country", "bin_country_iso", "issuer_country", "ci.bin_country_iso"]

def pick_first_col(df: pd.DataFrame, names: List[str]) -> Optional[str]:
    """Find the first available column from a list of possible names"""
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n in lower: return lower[n]
    for c in df.columns:
        lc = c.lower()
        if any(lc.endswith("." + n) for n in names):
            return c
    return None

def try_parse_json(val: Any) -> Optional[Any]:
    """Safely parse JSON values"""
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
    """Find first matching value from flattened JSON"""
    for path, val in flat:
        last = path.split(".")[-1].lower()
        for rx in key_regexes:
            if rx.search(last):
                return val
    return None

def normalize_iso2(val: Any) -> Optional[str]:
    """Normalize country codes to ISO2 format"""
    if val is None: return None
    s = str(val).strip()
    if not s: return None
    return s.upper()[:2]

def norm_phone(val: Any) -> Optional[str]:
    """Normalize phone numbers"""
    if val is None: return None
    digits = re.sub(r"\D+", "", str(val))
    return digits or None

def first_in_csv_list(s: str) -> str:
    """Get first value from comma-separated list"""
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts[0] if parts else s

def to_bool_series(s: pd.Series) -> pd.Series:
    """Convert series to boolean"""
    sl = s.astype(str).str.strip().str.lower()
    return sl.isin(["true","t","1","yes","y"])

# ---------- Data Processing Functions ----------

def extract_json_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Extract and parse JSON fields from the dataframe"""
    
    for col in JSON_CANDIDATES:
        if col in df.columns:
            df[f"{col}_parsed"] = df[col].apply(lambda x: try_parse_json(x))
    
    return df

def extract_user_info(df: pd.DataFrame) -> pd.DataFrame:
    """Extract user information from JSON fields"""
    
    # Extract email, name, billing info from JSON
    for idx, row in df.iterrows():
        for col in ["body_parsed", "request_payload_parsed", "response_payload_parsed"]:
            if col in df.columns and row[col]:
                json_data = row[col]
                
                # Extract email
                if isinstance(json_data, dict):
                    if 'email' in json_data and pd.isna(df.at[idx, 'user_email']):
                        df.at[idx, 'user_email'] = json_data['email']
                    
                    # Extract billing information
                    if 'billing' in json_data:
                        billing = json_data['billing']
                        if isinstance(billing, dict):
                            if 'country' in billing and pd.isna(df.at[idx, 'billing_country']):
                                df.at[idx, 'billing_country'] = billing['country']
                            if 'city' in billing and pd.isna(df.at[idx, 'billing_city']):
                                df.at[idx, 'billing_city'] = billing['city']
    
    return df

def enhance_with_ipinfo(df: pd.DataFrame, ipinfo: IPinfoGeolocator) -> pd.DataFrame:
    """Enhance dataframe with IPinfo geolocation data"""
    
    if not ipinfo or not ipinfo.reader:
        return df
    
    # Find IP column
    ip_col = pick_first_col(df, IP_RAW_CANDIDATES)
    if not ip_col:
        st.warning("No IP column found for geolocation")
        return df
    
    st.info(f"Using IP column: {ip_col}")
    
    # Add new columns for IPinfo data
    df['ip_country_ipinfo'] = None
    df['ip_city_ipinfo'] = None
    df['ip_latitude'] = None
    df['ip_longitude'] = None
    df['ip_proxy'] = False
    df['ip_asn'] = None
    df['ip_org'] = None
    
    # Process each IP address
    processed = 0
    total = len(df)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, row in df.iterrows():
        ip = row.get(ip_col)
        if ip:
            location = ipinfo.get_location(ip)
            if location:
                df.at[idx, 'ip_country_ipinfo'] = location.get('country')
                df.at[idx, 'ip_city_ipinfo'] = location.get('city')
                df.at[idx, 'ip_latitude'] = location.get('latitude')
                df.at[idx, 'ip_longitude'] = location.get('longitude')
                df.at[idx, 'ip_proxy'] = location.get('proxy', False)
                df.at[idx, 'ip_asn'] = location.get('asn')
                df.at[idx, 'ip_org'] = location.get('org')
                processed += 1
        
        # Update progress
        if idx % 100 == 0:
            progress_bar.progress((idx + 1) / total)
            status_text.text(f"Processing IP addresses: {idx + 1}/{total}")
    
    progress_bar.progress(1.0)
    status_text.text(f"✅ IP geolocation complete: {processed}/{total} IPs processed")
    
    return df

def calculate_risk_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate comprehensive risk scores for transactions"""
    
    df = df.copy()
    df['risk_score'] = 0
    df['risk_factors'] = ''
    
    # 1. Velocity Risk (multiple transactions per user)
    user_counts = df.groupby('user_email')['id'].transform('count')
    df['velocity_risk'] = user_counts
    
    # Apply velocity scoring
    df.loc[user_counts > RISK_THRESHOLDS['velocity_high'], 'risk_score'] += RISK_THRESHOLDS['velocity_score']
    df.loc[user_counts > RISK_THRESHOLDS['velocity_critical'], 'risk_score'] += RISK_THRESHOLDS['velocity_score']
    
    # Add risk factors
    df.loc[user_counts > RISK_THRESHOLDS['velocity_high'], 'risk_factors'] += 'High Velocity; '
    df.loc[user_counts > RISK_THRESHOLDS['velocity_critical'], 'risk_factors'] += 'Critical Velocity; '
    
    # 2. Geographic Risk (IP vs Billing mismatch)
    if 'ip_country_ipinfo' in df.columns and 'billing_country' in df.columns:
        for idx, row in df.iterrows():
            ip_country = row.get('ip_country_ipinfo')
            billing_country = row.get('billing_country')
            
            if ip_country and billing_country:
                if str(ip_country).upper() != str(billing_country).upper():
                    df.at[idx, 'risk_score'] += RISK_THRESHOLDS['geo_mismatch_score']
                    df.at[idx, 'risk_factors'] += 'Geographic Mismatch; '
                    df.at[idx, 'geo_mismatch'] = True
                else:
                    df.at[idx, 'geo_mismatch'] = False
    
    # 3. Time-based Risk (rapid succession)
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        df = df.sort_values(['user_email', 'created_at'])
        
        for user in df['user_email'].unique():
            user_df = df[df['user_email'] == user].copy()
            if len(user_df) > 1:
                user_df = user_df.sort_values('created_at')
                time_diffs = user_df['created_at'].diff().dt.total_seconds() / 60  # minutes
                
                # Flag rapid transactions (less than 5 minutes apart)
                rapid_mask = time_diffs < 5
                user_df.loc[rapid_mask, 'risk_score'] += RISK_THRESHOLDS['time_score']
                user_df.loc[rapid_mask, 'risk_factors'] += 'Rapid Succession; '
                
                # Update main dataframe
                df.loc[user_df.index, 'risk_score'] = user_df['risk_score']
                df.loc[user_df.index, 'risk_factors'] = user_df['risk_factors']
    
    # Clean up risk factors
    df['risk_factors'] = df['risk_factors'].str.strip('; ')
    
    return df

# ---------- Main Application ----------

def main():
    # Initialize IPinfo
    ipinfo = IPinfoGeolocator()
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    
    if not ipinfo.reader:
        st.error("IPinfo database not available. Please ensure ipinfo_lite.mmdb is in the project directory.")
        return
    
    # File upload
    st.header("📁 Data Upload")
    uploaded_file = st.file_uploader(
        "Upload CSV file with transaction data",
        type=['csv'],
        help="Upload your transaction CSV file for analysis"
    )
    
    if uploaded_file is not None:
        try:
            # Load data
            with st.spinner("Loading and processing data..."):
                df = pd.read_csv(uploaded_file)
                st.success(f"✅ Data loaded: {len(df)} transactions")
            
            # Show data preview
            st.subheader("📊 Data Preview")
            st.dataframe(df.head(), use_container_width=True)
            
            # Process data
            with st.spinner("Processing data..."):
                df = extract_json_fields(df)
                df = extract_user_info(df)
                df = enhance_with_ipinfo(df, ipinfo)
                df = calculate_risk_scores(df)
            
            # Display results
            st.subheader("🎯 Risk Analysis Results")
            
            # Risk score distribution
            col1, col2 = st.columns(2)
            
            with col1:
                fig_risk_dist = px.histogram(
                    df, x='risk_score', 
                    title="Risk Score Distribution",
                    nbins=20
                )
                st.plotly_chart(fig_risk_dist, use_container_width=True)
            
            with col2:
                # Risk summary
                risk_summary = {
                    'Total Transactions': len(df),
                    'High Risk (≥5)': len(df[df['risk_score'] >= 5]),
                    'Critical Risk (≥8)': len(df[df['risk_score'] >= 8]),
                    'Average Risk Score': f"{df['risk_score'].mean():.2f}",
                    'Geographic Mismatches': len(df[df.get('geo_mismatch', False) == True]),
                    'Velocity Violations': len(df[df['velocity_risk'] > RISK_THRESHOLDS['velocity_high']])
                }
                
                for key, value in risk_summary.items():
                    st.metric(key, value)
            
            # High-risk transactions
            st.subheader("🚨 High-Risk Transactions")
            high_risk_df = df[df['risk_score'] >= 5].sort_values('risk_score', ascending=False)
            
            if len(high_risk_df) > 0:
                display_cols = ['user_email', 'amount', 'risk_score', 'risk_factors']
                if 'ip_country_ipinfo' in high_risk_df.columns:
                    display_cols.append('ip_country_ipinfo')
                if 'billing_country' in high_risk_df.columns:
                    display_cols.append('billing_country')
                
                st.dataframe(
                    high_risk_df[display_cols].head(20),
                    use_container_width=True
                )
            else:
                st.info("No high-risk transactions found.")
            
            # Geographic analysis
            if 'ip_country_ipinfo' in df.columns and 'billing_country' in df.columns:
                st.subheader("🌍 Geographic Analysis")
                
                # Geographic mismatch chart
                geo_mismatch_df = df[df.get('geo_mismatch', False) == True]
                if len(geo_mismatch_df) > 0:
                    fig_geo = px.scatter(
                        geo_mismatch_df,
                        x='ip_longitude', y='ip_latitude',
                        color='risk_score',
                        hover_data=['user_email', 'billing_country', 'ip_country_ipinfo'],
                        title="Geographic Mismatches (IP vs Billing)"
                    )
                    st.plotly_chart(fig_geo, use_container_width=True)
                    
                    # Geographic mismatch summary
                    st.subheader("Geographic Mismatch Summary")
                    geo_summary = geo_mismatch_df.groupby(['billing_country', 'ip_country_ipinfo']).size().reset_index(name='count')
                    geo_summary = geo_summary.sort_values('count', ascending=False)
                    st.dataframe(geo_summary, use_container_width=True)
                else:
                    st.info("No geographic mismatches found.")
            
            # Export functionality
            st.subheader("📤 Export Results")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Export High-Risk Transactions"):
                    high_risk_csv = high_risk_df.to_csv(index=False)
                    st.download_button(
                        label="Download High-Risk CSV",
                        data=high_risk_csv,
                        file_name=f"high_risk_transactions_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col2:
                if st.button("Export Full Analysis"):
                    full_csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download Full Analysis CSV",
                        data=full_csv,
                        file_name=f"enhanced_geographic_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.exception(e)
    
    # Close IPinfo database
    if ipinfo:
        ipinfo.close()

if __name__ == "__main__":
    main()
