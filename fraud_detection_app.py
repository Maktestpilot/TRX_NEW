# Fraud Detection Application with IPinfo Bundle Database Integration
# Enhanced fraud detection using local IPinfo bundle MMDB database for geographic analysis

import json
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# IPinfo bundle database integration
try:
    import maxminddb
    IPINFO_AVAILABLE = True
except ImportError:
    IPINFO_AVAILABLE = False
    st.warning("IPinfo packages not available. Install with: pip install maxminddb")

st.set_page_config(
    page_title="Fraud Detection with IPinfo Bundle",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Configuration ----------

RISK_THRESHOLDS = {
    'velocity_high': 5,      # High velocity threshold
    'velocity_critical': 10, # Critical velocity threshold
    'amount_suspicious': [470, 1978, 1979, 2000, 5000],  # Suspicious amounts in cents
    'geo_mismatch_score': 3, # Score for geographic mismatch
    'velocity_score': 2,     # Score per velocity violation
    'amount_score': 2,       # Score for suspicious amounts
    'time_score': 1,         # Score for time anomalies
}

# ---------- IPinfo Bundle Database Integration ----------

class IPinfoBundleGeolocator:
    """IP geolocation using local IPinfo bundle MMDB database"""
    
    def __init__(self, db_path: str = "ipinfo_lite.mmdb"):
        self.db_path = db_path
        self.reader = None
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize the MMDB database reader"""
        try:
            if IPINFO_AVAILABLE:
                self.reader = maxminddb.open_database(self.db_path)
                st.success(f"✅ IPinfo bundle database loaded: {self.db_path}")
            else:
                st.error("❌ maxminddb package not available")
        except Exception as e:
            st.error(f"❌ Failed to load IPinfo bundle database: {e}")
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
            result = self.reader.get(ip)
            
            if not result:
                return {}
            
            # Extract information from ipinfo bundle format
            location_data = {}
            
            # Country information
            if 'country' in result:
                location_data['country_name'] = result['country']
            if 'country_code' in result:
                location_data['country'] = result['country_code']
            
            # Continent information
            if 'continent' in result:
                location_data['continent_name'] = result['continent']
            if 'continent_code' in result:
                location_data['continent'] = result['continent_code']
            
            # ASN information
            if 'asn' in result:
                location_data['asn'] = result['asn']
            if 'as_name' in result:
                location_data['org'] = result['as_name']
            if 'as_domain' in result:
                location_data['as_domain'] = result['as_domain']
            
            # Additional fields that might be available
            for key in ['city', 'region', 'postal_code', 'latitude', 'longitude', 'timezone']:
                if key in result:
                    location_data[key] = result[key]
            
            return location_data
            
        except Exception as e:
            st.warning(f"IP lookup error for {ip}: {e}")
            return {}
    
    def close(self):
        """Close the database reader"""
        if self.reader:
            self.reader.close()

# ---------- Data Processing Functions ----------

def extract_json_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Extract fields from JSON columns in the dataframe"""
    
    json_candidates = ["body", "request_payload", "response_payload"]
    
    for col in json_candidates:
        if col in df.columns:
            df[f"{col}_parsed"] = df[col].apply(lambda x: try_parse_json(x))
    
    return df

def try_parse_json(val: Any) -> Optional[Any]:
    """Safely parse JSON values"""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    
    s = str(val).strip()
    if not s or (not s.startswith("{") and not s.startswith("[")):
        return None
    
    try:
        return json.loads(s)
    except Exception:
        return None

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

def calculate_risk_scores(df: pd.DataFrame, ipinfo: IPinfoBundleGeolocator) -> pd.DataFrame:
    """Calculate comprehensive risk scores for transactions"""
    
    df = df.copy()
    df['risk_score'] = 0
    df['risk_factors'] = ''
    risk_factors = []
    
    # 1. Velocity Risk (multiple transactions per user)
    user_counts = df.groupby('user_email')['id'].transform('count')
    df['velocity_risk'] = user_counts
    
    # Apply velocity scoring
    df.loc[user_counts > RISK_THRESHOLDS['velocity_high'], 'risk_score'] += RISK_THRESHOLDS['velocity_score']
    df.loc[user_counts > RISK_THRESHOLDS['velocity_critical'], 'risk_score'] += RISK_THRESHOLDS['velocity_score']
    
    # Add risk factors
    df.loc[user_counts > RISK_THRESHOLDS['velocity_high'], 'risk_factors'] += 'High Velocity; '
    df.loc[user_counts > RISK_THRESHOLDS['velocity_critical'], 'risk_factors'] += 'Critical Velocity; '
    
    # 2. Amount Risk (suspicious amounts)
    for amount in RISK_THRESHOLDS['amount_suspicious']:
        mask = df['amount'] == amount
        df.loc[mask, 'risk_score'] += RISK_THRESHOLDS['amount_score']
        df.loc[mask, 'risk_factors'] += f'Suspicious Amount ({amount}); '
    
    # 3. Geographic Risk (IP vs Billing mismatch)
    if ipinfo and ipinfo.reader:
        for idx, row in df.iterrows():
            ip = row.get('ip', row.get('client_ip', None))
            if ip:
                location = ipinfo.get_location(ip)
                if location:
                    df.at[idx, 'ip_country'] = location.get('country')
                    df.at[idx, 'ip_country_name'] = location.get('country_name')
                    df.at[idx, 'ip_continent'] = location.get('continent')
                    df.at[idx, 'ip_asn'] = location.get('asn')
                    df.at[idx, 'ip_org'] = location.get('org')
                    
                    # Check for geographic mismatch
                    billing_country = row.get('billing_country')
                    if billing_country and location.get('country'):
                        if str(billing_country).upper() != str(location.get('country')).upper():
                            df.at[idx, 'risk_score'] += RISK_THRESHOLDS['geo_mismatch_score']
                            df.at[idx, 'risk_factors'] += 'Geographic Mismatch; '
                            df.at[idx, 'geo_mismatch'] = True
                        else:
                            df.at[idx, 'geo_mismatch'] = False
    
    # 4. Time-based Risk (rapid succession)
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

def generate_fraud_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate comprehensive fraud analysis report"""
    
    report = {
        'total_transactions': len(df),
        'high_risk_transactions': len(df[df['risk_score'] >= 5]),
        'critical_risk_transactions': len(df[df['risk_score'] >= 8]),
        'total_risk_score': df['risk_score'].sum(),
        'average_risk_score': df['risk_score'].mean(),
        'risk_distribution': df['risk_score'].value_counts().sort_index().to_dict(),
        'top_risk_factors': df['risk_factors'].str.split('; ').explode().value_counts().head(10).to_dict(),
        'high_risk_users': df[df['risk_score'] >= 5].groupby('user_email')['risk_score'].sum().sort_values(ascending=False).head(10).to_dict(),
        'geographic_mismatches': len(df[df.get('geo_mismatch', False) == True]),
        'velocity_violations': len(df[df['velocity_risk'] > RISK_THRESHOLDS['velocity_high']]),
    }
    
    return report

# ---------- Streamlit UI ----------

def main():
    st.title("🕵️ Fraud Detection Application with IPinfo Bundle Integration")
    st.markdown("Enhanced fraud detection using local IPinfo bundle MMDB database for geographic analysis")
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    
    # Initialize IPinfo bundle
    ipinfo = IPinfoBundleGeolocator()
    
    if not ipinfo.reader:
        st.error("IPinfo bundle database not available. Please ensure ipinfo_lite.mmdb is in the project directory.")
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
            with st.spinner("Processing data and calculating risk scores..."):
                df = extract_json_fields(df)
                df = extract_user_info(df)
                df = calculate_risk_scores(df, ipinfo)
            
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
                if 'ip_country' in high_risk_df.columns:
                    display_cols.append('ip_country')
                if 'billing_country' in high_risk_df.columns:
                    display_cols.append('billing_country')
                
                st.dataframe(
                    high_risk_df[display_cols].head(20),
                    use_container_width=True
                )
            else:
                st.info("No high-risk transactions found.")
            
            # Geographic analysis
            if 'ip_country' in df.columns and 'billing_country' in df.columns:
                st.subheader("🌍 Geographic Analysis")
                
                # Geographic mismatch chart
                geo_mismatch_df = df[df.get('geo_mismatch', False) == True]
                if len(geo_mismatch_df) > 0:
                    # Create a summary of geographic mismatches
                    geo_summary = geo_mismatch_df.groupby(['billing_country', 'ip_country']).size().reset_index(name='count')
                    geo_summary = geo_summary.sort_values('count', ascending=False)
                    
                    fig_geo = px.bar(
                        geo_summary.head(20),
                        x='count',
                        y='billing_country',
                        color='ip_country',
                        title="Top Geographic Mismatches (Billing vs IP Country)",
                        orientation='h'
                    )
                    st.plotly_chart(fig_geo, use_container_width=True)
                    
                    # Show detailed mismatch summary
                    st.subheader("Geographic Mismatch Summary")
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
                        file_name=f"high_risk_transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col2:
                if st.button("Export Full Analysis"):
                    full_csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download Full Analysis CSV",
                        data=full_csv,
                        file_name=f"fraud_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            # Detailed analysis
            st.subheader("🔍 Detailed Analysis")
            
            # User velocity analysis
            user_velocity = df.groupby('user_email').agg({
                'id': 'count',
                'amount': 'sum',
                'risk_score': 'sum'
            }).rename(columns={'id': 'transaction_count', 'amount': 'total_amount'})
            
            user_velocity = user_velocity.sort_values('transaction_count', ascending=False)
            
            fig_velocity = px.bar(
                user_velocity.head(20),
                x='transaction_count',
                y=user_velocity.head(20).index,
                title="Top 20 Users by Transaction Count",
                orientation='h'
            )
            st.plotly_chart(fig_velocity, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.exception(e)
    
    # Close IPinfo database
    if ipinfo:
        ipinfo.close()

if __name__ == "__main__":
    main()
