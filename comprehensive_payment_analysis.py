# Comprehensive Payment Analysis Dashboard
# Advanced fraud detection and payment processing analysis

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
    page_title="Comprehensive Payment Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Configuration ----------

RISK_THRESHOLDS = {
    'velocity_high': 5,
    'velocity_critical': 10,
    'amount_suspicious': [470, 496, 1878, 1978, 2000, 2313, 2420, 5000],
    'geo_mismatch_score': 3,
    'velocity_score': 2,
    'amount_score': 2,
    'time_score': 1,
    'failed_transaction_score': 2,
    'multiple_failures_score': 1,
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
            ip = str(ip).strip()
            if not ip or ip.lower() in ['nan', 'none', '']:
                return {}
            
            result = self.reader.get(ip)
            if not result:
                return {}
            
            location_data = {}
            
            if 'country' in result:
                location_data['country_name'] = result['country']
            if 'country_code' in result:
                location_data['country'] = result['country_code']
            if 'continent' in result:
                location_data['continent_name'] = result['continent']
            if 'continent_code' in result:
                location_data['continent'] = result['continent_code']
            if 'asn' in result:
                location_data['asn'] = result['asn']
            if 'as_name' in result:
                location_data['org'] = result['as_name']
            if 'as_domain' in result:
                location_data['as_domain'] = result['as_domain']
            
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

def extract_body_data(df: pd.DataFrame) -> pd.DataFrame:
    """Extract comprehensive data from body JSON field"""
    
    if 'body' not in df.columns:
        st.warning("No 'body' column found in the data")
        return df
    
    new_columns = [
        'payer_email', 'payer_first_name', 'payer_last_name',
        'billing_address_line1', 'billing_country_code', 'billing_country_iso3',
        'browser_language', 'browser_timezone', 'browser_user_agent',
        'browser_screen_width', 'browser_screen_height',
        'initiator_ip_address', 'order_amount', 'order_currency',
        'card_type', 'card_brand', 'card_last4'
    ]
    
    for col in new_columns:
        df[col] = None
    
    st.info("🔍 Parsing body JSON field for user and transaction data...")
    
    if len(df) == 0:
        st.warning("No data to process")
        return df
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, row in df.iterrows():
        try:
            body_data = try_parse_json(row['body'])
            if body_data and isinstance(body_data, dict):
                
                if 'payer' in body_data:
                    payer = body_data['payer']
                    if isinstance(payer, dict):
                        df.at[idx, 'payer_email'] = payer.get('email')
                        df.at[idx, 'payer_first_name'] = payer.get('first_name')
                        df.at[idx, 'payer_last_name'] = payer.get('last_name')
                        
                        if 'billing_address' in payer:
                            billing = payer['billing_address']
                            if isinstance(billing, dict):
                                df.at[idx, 'billing_address_line1'] = billing.get('address_line_1')
                                df.at[idx, 'billing_country_code'] = billing.get('country_code')
                                df.at[idx, 'billing_country_iso3'] = billing.get('country_code_iso3')
                
                if 'initiator' in body_data:
                    initiator = body_data['initiator']
                    if isinstance(initiator, dict):
                        df.at[idx, 'initiator_ip_address'] = initiator.get('ip_address')
                        
                        if 'browser' in initiator:
                            browser = initiator['browser']
                            if isinstance(browser, dict):
                                df.at[idx, 'browser_language'] = browser.get('language')
                                df.at[idx, 'browser_timezone'] = browser.get('time_zone')
                                df.at[idx, 'browser_user_agent'] = browser.get('user_agent')
                                df.at[idx, 'browser_screen_width'] = browser.get('screen_width')
                                df.at[idx, 'browser_screen_height'] = browser.get('screen_height')
                
                if 'order' in body_data:
                    order = body_data['order']
                    if isinstance(order, dict):
                        df.at[idx, 'order_amount'] = order.get('amount_total')
                        df.at[idx, 'order_currency'] = order.get('currency')
                
                if 'card' in body_data:
                    card = body_data['card']
                    if isinstance(card, dict):
                        df.at[idx, 'card_type'] = card.get('type')
                        df.at[idx, 'card_brand'] = card.get('brand')
                        card_number = card.get('number', '')
                        if card_number and len(str(card_number)) >= 4:
                            df.at[idx, 'card_last4'] = str(card_number)[-4:]
        
        except Exception as e:
            st.warning(f"Error parsing body for row {idx}: {e}")
        
        if idx % 100 == 0:
            progress_value = min(1.0, (idx + 1) / len(df))
            progress_bar.progress(progress_value)
            status_text.text(f"Processing row {idx + 1}/{len(df)}")
    
    progress_bar.progress(1.0)
    status_text.text("✅ Body JSON parsing complete!")
    
    return df

def prepare_data_for_analysis(df: pd.DataFrame, ipinfo: IPinfoBundleGeolocator) -> pd.DataFrame:
    """Prepare data with all necessary columns for comprehensive analysis"""
    
    df = df.copy()
    
    # Basic status flags
    if 'status_title' in df.columns:
        df['is_failed'] = df['status_title'] == 'Failed'
        df['is_successful'] = df['status_title'] != 'Failed'
        df['transaction_status'] = df['status_title']
    
    # User identification
    if 'payer_email' in df.columns:
        df['user_email'] = df['payer_email']
    elif 'user_email' in df.columns:
        pass
    else:
        df['user_email'] = 'unknown'
    
    # Billing country
    if 'billing_country_code' in df.columns:
        df['billing_country'] = df['billing_country_code']
    elif 'billing_country_iso3' in df.columns:
        df['billing_country'] = df['billing_country_iso3']
    
    # IP geolocation
    if ipinfo and ipinfo.reader:
        ip_fields = ['initiator_ip_address', 'ip_address', 'payer_ip_address', 'ip']
        
        for idx, row in df.iterrows():
            ip = None
            for field in ip_fields:
                if field in df.columns and pd.notna(row[field]):
                    ip = row[field]
                    break
            
            if ip:
                location = ipinfo.get_location(ip)
                if location:
                    df.at[idx, 'ip_country'] = location.get('country')
                    df.at[idx, 'ip_country_name'] = location.get('country_name')
                    df.at[idx, 'ip_continent'] = location.get('continent')
                    df.at[idx, 'ip_asn'] = location.get('asn')
                    df.at[idx, 'ip_org'] = location.get('org')
    
    # Time processing
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        df['hour'] = df['created_at'].dt.hour
        df['day_of_week'] = df['created_at'].dt.dayofweek
        df['day_name'] = df['created_at'].dt.day_name()
    
    if 'processed_at' in df.columns:
        df['processed_at'] = pd.to_datetime(df['processed_at'], errors='coerce')
        df['processing_time'] = (df['processed_at'] - df['created_at']).dt.total_seconds()
    
    # Device and browser info
    if 'browser_device_os_family' in df.columns:
        df['device_os'] = df['browser_device_os_family']
    elif 'payer_device_os_family' in df.columns:
        df['device_os'] = df['payer_device_os_family']
    
    if 'browser_user_agent' in df.columns:
        df['user_agent'] = df['browser_user_agent']
    elif 'payer_browser' in df.columns:
        df['user_agent'] = df['payer_browser']
    
    return df

# ---------- Analysis Functions ----------

def analyze_payment_success_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze payment success patterns and dependencies"""
    
    analysis = {}
    
    # 1. Overall Success Rate
    if 'is_successful' in df.columns:
        analysis['overall_success_rate'] = df['is_successful'].mean()
        analysis['total_transactions'] = len(df)
        analysis['successful_transactions'] = df['is_successful'].sum()
        analysis['failed_transactions'] = (~df['is_successful']).sum()
    
    # 2. Success Rate by Gateway
    if 'gateway_name' in df.columns and 'is_successful' in df.columns:
        gateway_success = df.groupby('gateway_name').agg({
            'is_successful': ['count', 'sum', 'mean'],
            'processing_time': ['mean', 'std'] if 'processing_time' in df.columns else ['count']
        }).round(3)
        analysis['gateway_success'] = gateway_success
    
    # 3. Success Rate by Amount Ranges
    if 'amount' in df.columns and 'is_successful' in df.columns:
        amount_ranges = pd.cut(df['amount'], 
                             bins=[0, 1000, 5000, 10000, 50000, float('inf')], 
                             labels=['0-10€', '10-50€', '50-100€', '100-500€', '500€+'])
        amount_success = df.groupby(amount_ranges).agg({
            'is_successful': ['mean', 'count']
        }).round(3)
        analysis['amount_success'] = amount_success
    
    # 4. Success Rate by Time
    if 'hour' in df.columns and 'is_successful' in df.columns:
        hourly_success = df.groupby('hour').agg({
            'is_successful': ['mean', 'count']
        }).round(3)
        analysis['hourly_success'] = hourly_success
    
    if 'day_of_week' in df.columns and 'is_successful' in df.columns:
        dow_success = df.groupby('day_of_week').agg({
            'is_successful': ['mean', 'count']
        }).round(3)
        analysis['day_of_week_success'] = dow_success
    
    return analysis

def analyze_failure_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze failure patterns and reasons"""
    
    analysis = {}
    
    failed_df = df[df.get('is_failed', False) == True]
    
    if len(failed_df) == 0:
        analysis['no_failures'] = "No failed transactions found"
        return analysis
    
    # 1. Failure Reasons
    if 'gateway_message' in failed_df.columns:
        failure_reasons = failed_df.groupby('gateway_message').size().sort_values(ascending=False)
        analysis['failure_reasons'] = failure_reasons
    
    # 2. Failure by User
    if 'user_email' in failed_df.columns:
        user_failures = failed_df.groupby('user_email').size().sort_values(ascending=False)
        analysis['user_failures'] = user_failures.head(20)
    
    # 3. Failure by Device/Browser
    if 'device_os' in failed_df.columns:
        device_failures = failed_df.groupby('device_os').size().sort_values(ascending=False)
        analysis['device_failures'] = device_failures
    
    if 'user_agent' in failed_df.columns:
        browser_failures = failed_df.groupby('user_agent').size().sort_values(ascending=False)
        analysis['browser_failures'] = browser_failures.head(10)
    
    # 4. Failure by Amount
    if 'amount' in failed_df.columns:
        amount_failures = failed_df.groupby(pd.cut(failed_df['amount'], bins=10))['id'].count()
        analysis['amount_failures'] = amount_failures
    
    return analysis

def analyze_geographic_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze geographic patterns and dependencies"""
    
    analysis = {}
    
    # 1. Geographic Success Rates
    if 'billing_country' in df.columns and 'is_successful' in df.columns:
        geo_success = df.groupby('billing_country').agg({
            'is_successful': ['mean', 'count']
        }).round(3)
        analysis['geo_success'] = geo_success
    
    # 2. IP vs Billing Mismatches
    if 'ip_country' in df.columns and 'billing_country' in df.columns:
        df['geo_mismatch'] = df['ip_country'] != df['billing_country']
        mismatch_success = df.groupby('geo_mismatch').agg({
            'is_successful': ['mean', 'count']
        }).round(3)
        analysis['mismatch_success'] = mismatch_success
        
        # Detailed mismatch analysis
        detailed_mismatch = df[df['geo_mismatch'] == True].groupby(['billing_country', 'ip_country']).agg({
            'is_successful': ['mean', 'count']
        }).round(3)
        analysis['detailed_mismatch'] = detailed_mismatch
    
    # 3. ASN Analysis
    if 'ip_asn' in df.columns and 'is_successful' in df.columns:
        asn_success = df.groupby('ip_asn').agg({
            'is_successful': ['mean', 'count']
        }).round(3)
        analysis['asn_success'] = asn_success.head(20)
    
    return analysis

def analyze_user_behavior_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze user behavior and retry patterns"""
    
    analysis = {}
    
    if 'user_email' not in df.columns:
        return analysis
    
    # 1. User Transaction Patterns
    user_patterns = df.groupby('user_email').agg({
        'id': 'count',
        'is_successful': 'sum',
        'is_failed': 'sum',
        'amount': ['sum', 'mean', 'std'],
        'created_at': ['min', 'max'] if 'created_at' in df.columns else 'count'
    }).round(3)
    
    user_patterns.columns = ['total_transactions', 'successful_count', 'failed_count', 
                            'total_amount', 'avg_amount', 'amount_std', 'first_transaction', 'last_transaction']
    
    user_patterns['success_rate'] = user_patterns['successful_count'] / user_patterns['total_transactions']
    user_patterns['failure_rate'] = user_patterns['failed_count'] / user_patterns['total_transactions']
    
    analysis['user_patterns'] = user_patterns
    
    # 2. Retry Patterns
    if 'created_at' in df.columns:
        retry_users = []
        for user in df['user_email'].unique():
            user_df = df[df['user_email'] == user].sort_values('created_at')
            if len(user_df) > 1:
                retry_sequences = []
                for i in range(len(user_df) - 1):
                    if user_df.iloc[i]['is_failed'] and user_df.iloc[i+1]['is_successful']:
                        time_diff = (user_df.iloc[i+1]['created_at'] - user_df.iloc[i]['created_at']).total_seconds() / 60
                        amount_diff = user_df.iloc[i+1]['amount'] - user_df.iloc[i]['amount']
                        retry_sequences.append({
                            'retry_time_minutes': time_diff,
                            'amount_change': amount_diff
                        })
                
                if retry_sequences:
                    retry_users.append({
                        'user_email': user,
                        'retry_count': len(retry_sequences),
                        'avg_retry_time': np.mean([r['retry_time_minutes'] for r in retry_sequences]),
                        'retry_sequences': retry_sequences
                    })
        
        if retry_users:
            retry_df = pd.DataFrame(retry_users)
            analysis['retry_patterns'] = retry_df
    
    return analysis

def analyze_technical_infrastructure(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze technical infrastructure and performance"""
    
    analysis = {}
    
    # 1. Processing Time Analysis
    if 'processing_time' in df.columns:
        processing_analysis = df.groupby('gateway_name').agg({
            'processing_time': ['mean', 'std', 'min', 'max', 'count']
        }).round(3)
        analysis['processing_times'] = processing_analysis
        
        # Overall processing time distribution
        overall_processing = df['processing_time'].describe()
        analysis['overall_processing'] = overall_processing
    
    # 2. Error Code Analysis
    if 'gateway_code' in df.columns:
        error_codes = df.groupby('gateway_code').size().sort_values(ascending=False)
        analysis['error_codes'] = error_codes
    
    # 3. Device and Browser Performance
    if 'device_os' in df.columns and 'is_successful' in df.columns:
        device_performance = df.groupby('device_os').agg({
            'is_successful': ['mean', 'count']
        }).round(3)
        analysis['device_performance'] = device_performance
    
    # 4. Screen Resolution Impact
    if 'browser_screen_width' in df.columns and 'browser_screen_height' in df.columns and 'is_successful' in df.columns:
        df['screen_resolution'] = df['browser_screen_width'].astype(str) + 'x' + df['browser_screen_height'].astype(str)
        resolution_performance = df.groupby('screen_resolution').agg({
            'is_successful': ['mean', 'count']
        }).round(3)
        analysis['resolution_performance'] = resolution_performance.head(20)
    
    return analysis

def analyze_fraud_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze fraud patterns and suspicious activities"""
    
    analysis = {}
    
    # 1. Suspicious Amounts
    if 'amount' in df.columns:
        suspicious_amounts = df[df['amount'].isin(RISK_THRESHOLDS['amount_suspicious'])]
        if len(suspicious_amounts) > 0:
            suspicious_analysis = suspicious_amounts.groupby('amount').agg({
                'is_successful': ['mean', 'count'],
                'user_email': 'nunique'
            }).round(3)
            analysis['suspicious_amounts'] = suspicious_analysis
    
    # 2. Velocity Analysis
    if 'user_email' in df.columns and 'created_at' in df.columns:
        user_velocity = df.groupby('user_email').agg({
            'id': 'count',
            'created_at': lambda x: (x.max() - x.min()).total_seconds() / 3600  # hours
        })
        user_velocity['transactions_per_hour'] = user_velocity['id'] / user_velocity['created_at']
        
        high_velocity_users = user_velocity[user_velocity['transactions_per_hour'] > 1]
        analysis['high_velocity_users'] = high_velocity_users.sort_values('transactions_per_hour', ascending=False)
    
    # 3. Geographic Anomalies
    if 'geo_mismatch' in df.columns:
        geo_anomalies = df[df['geo_mismatch'] == True].groupby(['billing_country', 'ip_country']).agg({
            'is_successful': ['mean', 'count'],
            'user_email': 'nunique'
        }).round(3)
        analysis['geographic_anomalies'] = geo_anomalies
    
    return analysis

# ---------- Visualization Functions ----------

def create_success_rate_charts(analysis: Dict[str, Any]) -> List[go.Figure]:
    """Create charts for success rate analysis"""
    
    figures = []
    
    # 1. Overall Success Rate
    if 'overall_success_rate' in analysis:
        fig = go.Figure(data=[
            go.Pie(labels=['Successful', 'Failed'], 
                   values=[analysis['successful_transactions'], analysis['failed_transactions']],
                   hole=0.3)
        ])
        fig.update_layout(title="Overall Transaction Success Rate", height=400)
        figures.append(fig)
    
    # 2. Gateway Success Rates
    if 'gateway_success' in analysis:
        gateway_df = analysis['gateway_success']
        fig = px.bar(gateway_df, 
                     x=gateway_df.index, 
                     y=('is_successful', 'mean'),
                     title="Success Rate by Gateway",
                     labels={'value': 'Success Rate', 'index': 'Gateway'})
        fig.update_layout(height=400)
        figures.append(fig)
    
    # 3. Hourly Success Pattern
    if 'hourly_success' in analysis:
        hourly_df = analysis['hourly_success']
        fig = px.line(hourly_df, 
                      x=hourly_df.index, 
                      y=('is_successful', 'mean'),
                      title="Success Rate by Hour of Day",
                      labels={'value': 'Success Rate', 'index': 'Hour'})
        fig.update_layout(height=400)
        figures.append(fig)
    
    return figures

def create_failure_analysis_charts(analysis: Dict[str, Any]) -> List[go.Figure]:
    """Create charts for failure analysis"""
    
    figures = []
    
    # 1. Failure Reasons
    if 'failure_reasons' in analysis:
        fig = px.bar(x=analysis['failure_reasons'].index, 
                     y=analysis['failure_reasons'].values,
                     title="Top Failure Reasons",
                     labels={'x': 'Error Message', 'y': 'Count'})
        fig.update_layout(height=400)
        figures.append(fig)
    
    # 2. Device Failure Rates
    if 'device_failures' in analysis:
        fig = px.bar(x=analysis['device_failures'].index, 
                     y=analysis['device_failures'].values,
                     title="Failures by Device OS",
                     labels={'x': 'Device OS', 'y': 'Failure Count'})
        fig.update_layout(height=400)
        figures.append(fig)
    
    return figures

def create_geographic_charts(analysis: Dict[str, Any]) -> List[go.Figure]:
    """Create charts for geographic analysis"""
    
    figures = []
    
    # 1. Geographic Success Rates
    if 'geo_success' in analysis:
        geo_df = analysis['geo_success']
        fig = px.bar(geo_df, 
                     x=geo_df.index, 
                     y=('is_successful', 'mean'),
                     title="Success Rate by Billing Country",
                     labels={'value': 'Success Rate', 'index': 'Country'})
        fig.update_layout(height=400)
        figures.append(fig)
    
    # 2. Geographic Mismatch Impact
    if 'mismatch_success' in analysis:
        mismatch_df = analysis['mismatch_success']
        fig = px.bar(mismatch_df, 
                     x=mismatch_df.index, 
                     y=('is_successful', 'mean'),
                     title="Success Rate: Geographic Match vs Mismatch",
                     labels={'value': 'Success Rate', 'index': 'Geographic Match'})
        fig.update_layout(height=400)
        figures.append(fig)
    
    return figures

# ---------- Main Dashboard ----------

def main():
    st.title("📊 Comprehensive Payment Analysis Dashboard")
    st.markdown("**Advanced analysis of payment processing issues, fraud patterns, and system dependencies**")
    
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
        help="Upload your transaction CSV file for comprehensive analysis"
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
            with st.spinner("Preparing data for comprehensive analysis..."):
                df = extract_body_data(df)
                df = prepare_data_for_analysis(df, ipinfo)
            
            # Run all analyses
            with st.spinner("Running comprehensive payment analysis..."):
                
                # 1. Payment Success Patterns
                st.subheader("🎯 Payment Success Pattern Analysis")
                success_analysis = analyze_payment_success_patterns(df)
                
                col1, col2 = st.columns(2)
                with col1:
                    if 'overall_success_rate' in success_analysis:
                        st.metric("Overall Success Rate", f"{success_analysis['overall_success_rate']:.2%}")
                        st.metric("Total Transactions", success_analysis['total_transactions'])
                
                with col2:
                    if 'successful_transactions' in success_analysis:
                        st.metric("Successful", success_analysis['successful_transactions'])
                        st.metric("Failed", success_analysis['failed_transactions'])
                
                # Success rate charts
                success_charts = create_success_rate_charts(success_analysis)
                for i, fig in enumerate(success_charts):
                    st.plotly_chart(fig, use_container_width=True)
                
                # 2. Failure Pattern Analysis
                st.subheader("🚨 Failure Pattern Analysis")
                failure_analysis = analyze_failure_patterns(df)
                
                if 'failure_reasons' in failure_analysis:
                    st.subheader("Top Failure Reasons")
                    st.dataframe(failure_analysis['failure_reasons'].head(10), use_container_width=True)
                
                failure_charts = create_failure_analysis_charts(failure_analysis)
                for i, fig in enumerate(failure_charts):
                    st.plotly_chart(fig, use_container_width=True)
                
                # 3. Geographic Analysis
                st.subheader("🌍 Geographic Pattern Analysis")
                geo_analysis = analyze_geographic_patterns(df)
                
                if 'geo_success' in geo_analysis:
                    st.subheader("Success Rate by Country")
                    st.dataframe(geo_analysis['geo_success'].head(20), use_container_width=True)
                
                geo_charts = create_geographic_charts(geo_analysis)
                for i, fig in enumerate(geo_charts):
                    st.plotly_chart(fig, use_container_width=True)
                
                # 4. User Behavior Analysis
                st.subheader("👤 User Behavior Analysis")
                behavior_analysis = analyze_user_behavior_patterns(df)
                
                if 'user_patterns' in behavior_analysis:
                    st.subheader("User Transaction Patterns")
                    st.dataframe(behavior_analysis['user_patterns'].head(20), use_container_width=True)
                
                # 5. Technical Infrastructure Analysis
                st.subheader("🔧 Technical Infrastructure Analysis")
                tech_analysis = analyze_technical_infrastructure(df)
                
                if 'processing_times' in tech_analysis:
                    st.subheader("Processing Times by Gateway")
                    st.dataframe(tech_analysis['processing_times'], use_container_width=True)
                
                # 6. Fraud Pattern Analysis
                st.subheader("🕵️ Fraud Pattern Analysis")
                fraud_analysis = analyze_fraud_patterns(df)
                
                if 'suspicious_amounts' in fraud_analysis:
                    st.subheader("Suspicious Amount Analysis")
                    st.dataframe(fraud_analysis['suspicious_amounts'], use_container_width=True)
                
                # Export functionality
                st.subheader("📤 Export Analysis Results")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("Export Success Analysis"):
                        success_csv = pd.DataFrame(success_analysis).to_csv()
                        st.download_button(
                            label="Download Success Analysis CSV",
                            data=success_csv,
                            file_name=f"success_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                
                with col2:
                    if st.button("Export Failure Analysis"):
                        failure_csv = pd.DataFrame(failure_analysis).to_csv()
                        st.download_button(
                            label="Download Failure Analysis CSV",
                            data=failure_csv,
                            file_name=f"failure_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                
                with col3:
                    if st.button("Export Full Analysis"):
                        full_csv = df.to_csv(index=False)
                        st.download_button(
                            label="Download Full Analysis CSV",
                            data=full_csv,
                            file_name=f"comprehensive_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
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
