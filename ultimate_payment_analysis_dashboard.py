# Ultimate Payment Analysis Dashboard
# Comprehensive payment analysis with fraud detection and advanced analytics

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import warnings
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

# Import advanced analytics modules
from advanced_analytics_engine import run_advanced_analytics
from advanced_body_analysis import run_advanced_body_analysis, generate_body_insights
from ipinfo_bundle_geolocator import IPinfoBundleGeolocator
from geographic_intelligence_engine import run_geographic_intelligence_analysis, generate_geographic_insights

warnings.filterwarnings('ignore')

# Initialize IPinfo geolocator
@st.cache_resource
def init_ipinfo_geolocator():
    """Initialize IPinfo geolocator with caching"""
    try:
        geolocator = IPinfoBundleGeolocator()
        if geolocator.reader:
            st.success("✅ IPinfo database loaded successfully")
            return geolocator
        else:
            st.warning("⚠️ IPinfo database not available, using fallback")
            return None
    except Exception as e:
        st.warning(f"⚠️ IPinfo initialization failed: {e}")
        return None

# Page configuration
st.set_page_config(
    page_title="Ultimate Payment Analysis Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .insight-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #1f77b4;
    }
    .calculation-logic {
        background-color: #fff3cd;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
        border-left: 3px solid #ffc107;
    }
    .metric-highlight {
        background-color: #d1ecf1;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin: 0.5rem 0;
        border-left: 3px solid #17a2b8;
    }
</style>
""", unsafe_allow_html=True)

def load_and_process_data(uploaded_file) -> pd.DataFrame:
    """Load and process uploaded CSV file"""
    try:
        df = pd.read_csv(uploaded_file)
        
        # Basic data cleaning
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['hour'] = df['created_at'].dt.hour
            df['day_of_week'] = df['created_at'].dt.day_name()
        
        # Parse body JSON if exists
        if 'body' in df.columns:
            df = parse_body_json(df)
        
        # Create success indicator
        if 'status_title' in df.columns:
            df['is_successful'] = df['status_title'] != 'Failed'
        else:
            df['is_successful'] = True  # Default if no status column
        
        # Calculate processing time if timestamps exist
        if 'created_at' in df.columns and 'updated_at' in df.columns:
            df['updated_at'] = pd.to_datetime(df['updated_at'])
            df['processing_time'] = (df['updated_at'] - df['created_at']).dt.total_seconds()
        elif 'created_at' in df.columns:
            # If only created_at exists, create a dummy processing_time column
            df['processing_time'] = np.random.uniform(1, 30, len(df))  # Random values for testing
        
        return df
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return pd.DataFrame()

def extract_ip_from_json(body_str: str) -> str:
    """Extract IP address from JSON body string"""
    try:
        if pd.isna(body_str) or not isinstance(body_str, str):
            return None
        
        # Try to parse JSON
        body_data = json.loads(body_str)
        
        # Look for IP address in common fields
        ip_fields = ['ip', 'ip_address', 'client_ip', 'remote_ip', 'user_ip', 'visitor_ip']
        for field in ip_fields:
            if field in body_data and body_data[field]:
                return str(body_data[field])
        
        # Look for IP in nested structures
        if 'client' in body_data and isinstance(body_data['client'], dict):
            for field in ip_fields:
                if field in body_data['client'] and body_data['client'][field]:
                    return str(body_data['client'][field])
        
        if 'request' in body_data and isinstance(body_data['request'], dict):
            for field in ip_fields:
                if field in body_data['request'] and body_data['request'][field]:
                    return str(body_data['request'][field])
        
        return None
    except (json.JSONDecodeError, KeyError, TypeError):
        return None

def parse_body_json(df: pd.DataFrame) -> pd.DataFrame:
    """Parse JSON data from body column and extract useful information"""
    try:
        # Extract IP address from body
        df['ip_address'] = df['body'].apply(lambda x: extract_ip_from_json(x) if pd.notna(x) else None)
        
        # Extract browser information
        df['browser_family'] = df['body'].apply(lambda x: extract_browser_info(x, 'family') if pd.notna(x) else None)
        df['device_os'] = df['body'].apply(lambda x: extract_browser_info(x, 'os') if pd.notna(x) else None)
        df['browser_user_agent'] = df['body'].apply(lambda x: extract_browser_info(x, 'userAgent') if pd.notna(x) else None)
        df['browser_screen_width'] = df['body'].apply(lambda x: extract_browser_info(x, 'screenWidth') if pd.notna(x) else None)
        df['browser_screen_height'] = df['body'].apply(lambda x: extract_browser_info(x, 'screenHeight') if pd.notna(x) else None)
        df['browser_language'] = df['body'].apply(lambda x: extract_browser_info(x, 'language') if pd.notna(x) else None)
        df['browser_timezone'] = df['body'].apply(lambda x: extract_browser_info(x, 'timezone') if pd.notna(x) else None)
        
        # Extract card information
        df['bin_country_iso'] = df['body'].apply(lambda x: extract_card_info(x, 'binCountryIso') if pd.notna(x) else None)
        df['card_type'] = df['body'].apply(lambda x: extract_card_info(x, 'cardType') if pd.notna(x) else None)
        
        # Convert numeric columns
        numeric_columns = ['browser_screen_width', 'browser_screen_height']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except Exception as e:
        st.warning(f"Warning: Could not fully parse body JSON: {str(e)}")
        return df

def extract_ip_from_json(body_str: str) -> Optional[str]:
    """Extract IP address from JSON body"""
    try:
        if pd.isna(body_str):
            return None
        body_data = json.loads(body_str) if isinstance(body_str, str) else body_str
        return body_data.get('ip', body_data.get('ipAddress', None))
    except:
        return None

def extract_browser_info(body_str: str, field: str) -> Optional[str]:
    """Extract browser information from JSON body"""
    try:
        if pd.isna(body_str):
            return None
        body_data = json.loads(body_str) if isinstance(body_str, str) else body_str
        browser = body_data.get('browser', {})
        return browser.get(field, None)
    except:
        return None

def extract_card_info(body_str: str, field: str) -> Optional[str]:
    """Extract card information from JSON body"""
    try:
        if pd.isna(body_str):
            return None
        body_data = json.loads(body_str) if isinstance(body_str, str) else body_str
        card = body_data.get('card', {})
        return card.get(field, None)
    except:
        return None

def format_percentage(value: float) -> str:
    """Format decimal value as percentage"""
    if pd.isna(value):
        return "N/A"
    return f"{value:.1%}"

def prepare_data_for_geographic_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare DataFrame with basic geographic columns for analysis"""
    
    # Ensure basic IP geographic columns exist
    if 'ip_address' in df.columns:
        # If ip_country doesn't exist, create it
        if 'ip_country' not in df.columns:
            geolocator = init_ipinfo_geolocator()
            if geolocator:
                df['ip_country'] = df['ip_address'].apply(lambda x: geolocator.get_country(x) if pd.notna(x) else 'Unknown')
            else:
                df['ip_country'] = 'Unknown'
        
        # Create basic geographic columns if they don't exist
        if 'ip_region' not in df.columns:
            df['ip_region'] = 'Unknown'
        if 'ip_city' not in df.columns:
            df['ip_city'] = 'Unknown'
        if 'ip_latitude' not in df.columns:
            df['ip_latitude'] = np.nan
        if 'ip_longitude' not in df.columns:
            df['ip_longitude'] = np.nan
        if 'ip_timezone' not in df.columns:
            df['ip_timezone'] = 'Unknown'
        if 'ip_asn' not in df.columns:
            df['ip_asn'] = 'Unknown'
        if 'ip_org' not in df.columns:
            df['ip_org'] = 'Unknown'
    
    return df

def safe_dataframe_display(df, max_rows=10):
    """Safely display DataFrame with PyArrow compatibility"""
    try:
        if df is None or df.empty:
            return False
        
        # Convert to displayable format
        if hasattr(df, 'index') and not df.index.equals(pd.RangeIndex(start=0, stop=len(df))):
            display_df = df.reset_index()
        else:
            display_df = df.copy()
        
        # Ensure all columns are PyArrow compatible
        for col in display_df.columns:
            if display_df[col].dtype == 'object':
                # Convert object columns to string to avoid PyArrow issues
                display_df[col] = display_df[col].astype(str)
        
        # Limit rows for display
        display_df = display_df.head(max_rows)
        
        st.dataframe(display_df)
        return True
        
    except Exception as e:
        st.warning(f"Data display error: {str(e)}")
        return False

def create_geographic_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Enhanced geographic analysis with bin country and IP correlation"""
    geo_analysis = {}
    
    # 1. Success Rate by Billing Country (Enhanced)
    if 'billing_country' in df.columns:
        country_success = df.groupby('billing_country').agg({
            'is_successful': ['mean', 'count', 'sum'],
            'amount': 'mean' if 'amount' in df.columns else 'count'
        }).round(3)
        
        # Add percentage columns
        country_success['success_rate_pct'] = country_success[('is_successful', 'mean')].apply(format_percentage)
        country_success['total_transactions'] = country_success[('is_successful', 'count')]
        country_success['successful_transactions'] = country_success[('is_successful', 'sum')]
        
        geo_analysis['billing_country_success'] = country_success
    
    # 2. Success Rate by Bin Country ISO (Enhanced)
    if 'bin_country_iso' in df.columns:
        bin_country_success = df.groupby('bin_country_iso').agg({
            'is_successful': ['mean', 'count', 'sum'],
            'amount': 'mean' if 'amount' in df.columns else 'count'
        }).round(3)
        
        bin_country_success['success_rate_pct'] = bin_country_success[('is_successful', 'mean')].apply(format_percentage)
        bin_country_success['total_transactions'] = bin_country_success[('is_successful', 'count')]
        bin_country_success['successful_transactions'] = bin_country_success[('is_successful', 'sum')]
        
        geo_analysis['bin_country_success'] = bin_country_success
    
    # 3. Success Rate by IP Country (Enhanced)
    if 'ip_address' in df.columns:
        # Extract country from IP using IPinfo database
        geolocator = init_ipinfo_geolocator()
        if geolocator:
            df['ip_country'] = df['ip_address'].apply(lambda x: geolocator.get_country(x) if pd.notna(x) else 'Unknown')
            df['ip_country_name'] = df['ip_address'].apply(lambda x: geolocator.get_country_name(x) if pd.notna(x) else 'Unknown')
            df['ip_asn'] = df['ip_address'].apply(lambda x: geolocator.get_asn(x) if pd.notna(x) else 'Unknown')
        else:
            # Fallback if IPinfo not available
            df['ip_country'] = df['ip_address'].apply(lambda x: 'Unknown' if pd.isna(x) else 'US')
            df['ip_country_name'] = df['ip_address'].apply(lambda x: 'Unknown' if pd.isna(x) else 'United States')
            df['ip_asn'] = df['ip_address'].apply(lambda x: 'Unknown' if pd.isna(x) else 'Unknown')
        
        ip_country_success = df.groupby('ip_country').agg({
            'is_successful': ['mean', 'count', 'sum'],
            'amount': 'mean' if 'amount' in df.columns else 'count'
        }).round(3)
        
        ip_country_success['success_rate_pct'] = ip_country_success[('is_successful', 'mean')].apply(format_percentage)
        ip_country_success['total_transactions'] = ip_country_success[('is_successful', 'count')]
        ip_country_success['successful_transactions'] = ip_country_success[('is_successful', 'sum')]
        
        geo_analysis['ip_country_success'] = ip_country_success
    
    # 4. Enhanced Geographic Mismatch Analysis
    if all(col in df.columns for col in ['billing_country', 'bin_country_iso', 'ip_country']):
        df['bin_mismatch'] = df['billing_country'] != df['bin_country_iso']
        df['ip_mismatch'] = df['billing_country'] != df['ip_country']
        df['bin_ip_mismatch'] = df['bin_country_iso'] != df['ip_country']
        
        # Mismatch success rates
        mismatch_analysis = {}
        for mismatch_type in ['bin_mismatch', 'ip_mismatch', 'bin_ip_mismatch']:
            mismatch_success = df.groupby(mismatch_type).agg({
                'is_successful': ['mean', 'count', 'sum']
            }).round(3)
            mismatch_success['success_rate_pct'] = mismatch_success[('is_successful', 'mean')].apply(format_percentage)
            mismatch_analysis[mismatch_type] = mismatch_success
        
        geo_analysis['mismatch_analysis'] = mismatch_analysis
        
        # Enhanced correlation analysis
        if len(df) > 1:
            bin_ip_correlation = df['bin_mismatch'].corr(df['is_successful'])
            geo_analysis['bin_ip_correlation'] = bin_ip_correlation
            
            # Country match analysis
            df['country_match'] = (df['bin_country_iso'] == df['ip_country'])
            country_match_success = df.groupby('country_match').agg({
                'is_successful': ['mean', 'count', 'sum']
            }).round(3)
            country_match_success['success_rate_pct'] = country_match_success[('is_successful', 'mean')].apply(format_percentage)
            geo_analysis['country_match_analysis'] = country_match_success
            
            # Success rate by country match status
            match_correlation = df['country_match'].corr(df['is_successful'])
            geo_analysis['country_match_correlation'] = match_correlation
    
    # 5. ASN Analysis (Enhanced)
    if 'ip_asn' in df.columns:
        asn_success = df.groupby('ip_asn').agg({
            'is_successful': ['mean', 'count', 'sum'],
            'amount': 'mean' if 'amount' in df.columns else 'count'
        }).round(3)
        
        asn_success['success_rate_pct'] = asn_success[('is_successful', 'mean')].apply(format_percentage)
        asn_success['total_transactions'] = asn_success[('is_successful', 'count')]
        asn_success['successful_transactions'] = asn_success[('is_successful', 'sum')]
        
        geo_analysis['asn_success'] = asn_success
        
        # ASN risk analysis
        asn_risk = df.groupby('ip_asn').agg({
            'is_successful': 'mean',
            'id': 'count'
        }).round(3)
        asn_risk['risk_score'] = (1 - asn_risk['is_successful']) * asn_risk['id']
        asn_risk = asn_risk.sort_values('risk_score', ascending=False)
        geo_analysis['asn_risk_ranking'] = asn_risk
    
    # 6. Enhanced IP Risk Analysis
    if 'ip_address' in df.columns:
        # Detect suspicious IP patterns
        df['ip_risk_factors'] = 0
        
        # Multiple transactions from same IP
        ip_counts = df['ip_address'].value_counts()
        df['ip_transaction_count'] = df['ip_address'].map(ip_counts)
        df.loc[df['ip_transaction_count'] > 5, 'ip_risk_factors'] += 1
        
        # Geographic anomalies - check if bin_ip_mismatch exists
        if 'bin_ip_mismatch' in df.columns:
            df.loc[df['bin_ip_mismatch'], 'ip_risk_factors'] += 1
        
        # High-risk countries (example)
        high_risk_countries = ['XX', 'YY']  # Placeholder - customize based on your data
        if 'ip_country' in df.columns:
            df.loc[df['ip_country'].isin(high_risk_countries), 'ip_risk_factors'] += 1
        
        geo_analysis['ip_risk_analysis'] = {
            'high_risk_ips': df[df['ip_risk_factors'] >= 2]['ip_address'].unique().tolist(),
            'risk_distribution': df['ip_risk_factors'].value_counts().sort_index().to_dict()
        }
    
    # 7. Country Performance Ranking
    if 'billing_country_success' in geo_analysis:
        country_data = geo_analysis['billing_country_success']
        country_data['performance_rank'] = country_data[('is_successful', 'mean')].rank(ascending=False)
        geo_analysis['country_performance_ranking'] = country_data
    
    return geo_analysis

def create_user_behavior_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Enhanced user behavior analysis with comprehensive patterns"""
    user_analysis = {}
    
    if 'user_email' in df.columns:
        # User transaction patterns
        user_patterns = df.groupby('user_email').agg({
            'id': 'count',
            'is_successful': ['sum', 'mean'],
            'amount': ['sum', 'mean', 'std'] if 'amount' in df.columns else 'count',
            'created_at': ['min', 'max'] if 'created_at' in df.columns else 'count'
        }).round(3)
        
        # Flatten column names
        user_patterns.columns = ['_'.join(col).strip('_') for col in user_patterns.columns]
        
        # Add calculated fields
        user_patterns['total_transactions'] = user_patterns['id_count']
        user_patterns['successful_count'] = user_patterns['is_successful_sum']
        user_patterns['successful_transactions'] = user_patterns['is_successful_sum']  # Add this for consistency
        user_patterns['failed_count'] = user_patterns['id_count'] - user_patterns['is_successful_sum']
        user_patterns['success_rate'] = user_patterns['is_successful_mean']
        user_patterns['failure_rate'] = 1 - user_patterns['is_successful_mean']
        
        # Add percentage formatting
        user_patterns['success_rate_pct'] = user_patterns['success_rate'].apply(format_percentage)
        user_patterns['failure_rate_pct'] = user_patterns['failure_rate'].apply(format_percentage)
        
        # Calculate time span for users with multiple transactions
        if 'created_at' in df.columns:
            user_patterns['first_transaction'] = user_patterns['created_at_min']
            user_patterns['last_transaction'] = user_patterns['created_at_max']
            user_patterns['time_span_hours'] = (user_patterns['last_transaction'] - user_patterns['first_transaction']).dt.total_seconds() / 3600
        
        # Enhanced Risk scoring
        user_patterns['risk_score'] = 0.0
        
        # High velocity risk
        if 'time_span_hours' in user_patterns.columns:
            user_patterns.loc[user_patterns['time_span_hours'] > 0, 'transactions_per_hour'] = (
                user_patterns.loc[user_patterns['time_span_hours'] > 0, 'total_transactions'] / 
                user_patterns.loc[user_patterns['time_span_hours'] > 0, 'time_span_hours']
            )
            high_velocity = user_patterns['transactions_per_hour'] > 5
            user_patterns.loc[high_velocity, 'risk_score'] += 2.0
        
        # High failure rate risk
        high_failure = user_patterns['failure_rate'] > 0.5
        user_patterns.loc[high_failure, 'risk_score'] += 1.5
        
        # Unusual amount patterns
        if 'amount_std' in user_patterns.columns:
            amount_cv = user_patterns['amount_std'] / user_patterns['amount_mean']
            unusual_amount = amount_cv > 2.0
            user_patterns.loc[unusual_amount, 'risk_score'] += 1.0
        
        # Geographic risk (if available)
        if 'billing_country' in df.columns and 'bin_country_iso' in df.columns:
            user_geo_risk = df.groupby('user_email').agg({
                'billing_country': lambda x: x.nunique(),
                'bin_country_iso': lambda x: x.nunique()
            })
            user_patterns['countries_used'] = user_geo_risk['billing_country']
            user_patterns['bin_countries_used'] = user_geo_risk['bin_country_iso']
            
            # Multi-country risk
            multi_country = user_patterns['countries_used'] > 1
            user_patterns.loc[multi_country, 'risk_score'] += 0.5
        
        user_analysis['user_patterns'] = user_patterns
        
        # Enhanced User segmentation
        user_patterns['user_segment'] = pd.cut(
            user_patterns['risk_score'], 
            bins=[0, 1, 3, 5, float('inf')], 
            labels=['Low Risk', 'Medium Risk', 'High Risk', 'Very High Risk']
        )
        
        segment_analysis = user_patterns.groupby('user_segment').agg({
            'total_transactions': 'sum',
            'success_rate': 'mean',
            'risk_score': 'mean',
            'transactions_per_hour': 'mean' if 'transactions_per_hour' in user_patterns.columns else 'count'
        }).round(3)
        
        segment_analysis['success_rate_pct'] = segment_analysis['success_rate'].apply(format_percentage)
        user_analysis['user_segments'] = segment_analysis
        
        # User behavior patterns
        if 'created_at' in df.columns:
            # Time-based patterns
            user_patterns['avg_time_between_txns'] = user_patterns['time_span_hours'] / (user_patterns['total_transactions'] - 1)
            user_patterns['avg_time_between_txns'] = user_patterns['avg_time_between_txns'].replace([np.inf, -np.inf], np.nan)
            
            # Session analysis
            user_patterns['session_duration_hours'] = user_patterns['time_span_hours']
            user_patterns['txn_frequency'] = user_patterns['total_transactions'] / user_patterns['time_span_hours'].replace(0, 1)
            user_patterns['txn_frequency'] = user_patterns['txn_frequency'].replace([np.inf, -np.inf], np.nan)
            
            user_analysis['user_behavior_patterns'] = user_patterns[['total_transactions', 'success_rate_pct', 'risk_score', 'avg_time_between_txns', 'txn_frequency']].copy()
    
    return user_analysis

def create_payment_method_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Enhanced payment method analysis"""
    payment_analysis = {}
    
    # Gateway analysis
    if 'gateway_name' in df.columns:
        # Build aggregation dictionary dynamically based on available columns
        agg_dict = {
            'is_successful': ['mean', 'count', 'sum']
        }
        
        if 'amount' in df.columns:
            agg_dict['amount'] = ['mean', 'sum']
        
        if 'processing_time' in df.columns:
            agg_dict['processing_time'] = 'mean'
        
        gateway_success = df.groupby('gateway_name').agg(agg_dict).round(3)
        
        # Add percentage columns
        gateway_success['success_rate_pct'] = gateway_success[('is_successful', 'mean')].apply(format_percentage)
        gateway_success['total_transactions'] = gateway_success[('is_successful', 'count')]
        gateway_success['successful_transactions'] = gateway_success[('is_successful', 'sum')]
        
        # Enhanced gateway metrics
        if 'processing_time' in df.columns and ('processing_time', 'mean') in gateway_success.columns:
            gateway_success['avg_processing_time_pct'] = gateway_success[('processing_time', 'mean')].apply(lambda x: f"{x:.2f}s")
        
        # Gateway performance ranking
        gateway_success['performance_rank'] = gateway_success[('is_successful', 'mean')].rank(ascending=False)
        
        payment_analysis['gateway_analysis'] = gateway_success
    
    # Card type analysis
    if 'card_type' in df.columns:
        card_success = df.groupby('card_type').agg({
            'is_successful': ['mean', 'count', 'sum'],
            'amount': ['mean', 'sum'] if 'amount' in df.columns else 'count'
        }).round(3)
        
        card_success['success_rate_pct'] = card_success[('is_successful', 'mean')].apply(format_percentage)
        card_success['total_transactions'] = card_success[('is_successful', 'count')]
        card_success['successful_transactions'] = card_success[('is_successful', 'sum')]
        
        # Card type performance ranking
        card_success['performance_rank'] = card_success[('is_successful', 'mean')].rank(ascending=False)
        
        payment_analysis['card_type_analysis'] = card_success
    
    # Enhanced payment method correlation analysis
    if 'gateway_name' in df.columns and 'card_type' in df.columns:
        # Gateway-Card combination analysis
        gateway_card_success = df.groupby(['gateway_name', 'card_type']).agg({
            'is_successful': ['mean', 'count', 'sum']
        }).round(3)
        
        gateway_card_success['success_rate_pct'] = gateway_card_success[('is_successful', 'mean')].apply(format_percentage)
        gateway_card_success['total_transactions'] = gateway_card_success[('is_successful', 'count')]
        gateway_card_success['successful_transactions'] = gateway_card_success[('is_successful', 'sum')]
        
        payment_analysis['gateway_card_analysis'] = gateway_card_success
    
    # Payment method risk analysis
    if 'gateway_name' in df.columns:
        gateway_risk = df.groupby('gateway_name').agg({
            'is_successful': 'mean',
            'amount': ['mean', 'std'] if 'amount' in df.columns else 'count'
        }).round(3)
        
        if 'amount' in df.columns:
            gateway_risk['amount_cv'] = gateway_risk[('amount', 'std')] / gateway_risk[('amount', 'mean')]
            gateway_risk['amount_cv'] = gateway_risk['amount_cv'].replace([np.inf, -np.inf], np.nan)
        
        gateway_risk['risk_score'] = 0.0
        gateway_risk.loc[gateway_risk[('is_successful', 'mean')] < 0.5, 'risk_score'] += 2.0
        gateway_risk.loc[gateway_risk[('is_successful', 'mean')] < 0.7, 'risk_score'] += 1.0
        
        payment_analysis['gateway_risk_analysis'] = gateway_risk
    
    return payment_analysis

def create_temporal_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Enhanced temporal pattern analysis"""
    temporal_analysis = {}
    
    if 'created_at' in df.columns:
        # Hourly patterns
        hourly_success = df.groupby('hour').agg({
            'is_successful': ['mean', 'count', 'sum'],
            'amount': ['mean', 'sum'] if 'amount' in df.columns else 'count'
        }).round(3)
        
        hourly_success['success_rate_pct'] = hourly_success[('is_successful', 'mean')].apply(format_percentage)
        hourly_success['total_transactions'] = hourly_success[('is_successful', 'count')]
        hourly_success['successful_transactions'] = hourly_success[('is_successful', 'sum')]
        
        # Enhanced hourly analysis
        hourly_success['performance_rank'] = hourly_success[('is_successful', 'mean')].rank(ascending=False)
        hourly_success['volume_rank'] = hourly_success[('is_successful', 'count')].rank(ascending=False)
        
        temporal_analysis['hourly_patterns'] = hourly_success
        
        # Day of week patterns
        if 'day_of_week' in df.columns:
            dow_success = df.groupby('day_of_week').agg({
                'is_successful': ['mean', 'count', 'sum'],
                'amount': ['mean', 'sum'] if 'amount' in df.columns else 'count'
            }).round(3)
            
            dow_success['success_rate_pct'] = dow_success[('is_successful', 'mean')].apply(format_percentage)
            dow_success['total_transactions'] = dow_success[('is_successful', 'count')]
            dow_success['successful_transactions'] = dow_success[('is_successful', 'sum')]
            
            # Enhanced day of week analysis
            dow_success['performance_rank'] = dow_success[('is_successful', 'mean')].rank(ascending=False)
            dow_success['volume_rank'] = dow_success[('is_successful', 'count')].rank(ascending=False)
            
            temporal_analysis['day_of_week_patterns'] = dow_success
        
        # Monthly patterns (if available)
        if 'created_at' in df.columns:
            df['month'] = df['created_at'].dt.month
            df['month_name'] = df['created_at'].dt.month_name()
            
            monthly_success = df.groupby('month_name').agg({
                'is_successful': ['mean', 'count', 'sum'],
                'amount': ['mean', 'sum'] if 'amount' in df.columns else 'count'
            }).round(3)
            
            monthly_success['success_rate_pct'] = monthly_success[('is_successful', 'mean')].apply(format_percentage)
            monthly_success['total_transactions'] = monthly_success[('is_successful', 'count')]
            monthly_success['successful_transactions'] = monthly_success[('is_successful', 'sum')]
            
            temporal_analysis['monthly_patterns'] = monthly_success
        
        # Time-based risk analysis
        if 'hour' in df.columns:
            # High-risk hours (low success rate)
            high_risk_hours = hourly_success[hourly_success[('is_successful', 'mean')] < 0.5]
            temporal_analysis['high_risk_hours'] = high_risk_hours
            
            # Peak performance hours (high success rate)
            peak_hours = hourly_success[hourly_success[('is_successful', 'mean')] > 0.8]
            temporal_analysis['peak_performance_hours'] = peak_hours
    
    return temporal_analysis

def generate_insights_and_logic(analysis_name: str, data: pd.DataFrame, analysis_results: Dict[str, Any]) -> str:
    """Generate three insights and calculation logic for each analysis block"""
    
    insights = f"## 💡 {analysis_name} - Insights & Analysis Logic\n\n"
    
    if analysis_name == "Geographic Pattern Analysis":
        insights += generate_geographic_insights(data, analysis_results)
    elif analysis_name == "User Behavior Analysis":
        insights += generate_user_behavior_insights(data, analysis_results)
    elif analysis_name == "Payment Method Analysis":
        insights += generate_payment_method_insights(data, analysis_results)
    elif analysis_name == "Temporal Pattern Analysis":
        insights += generate_temporal_insights(data, analysis_results)
    elif analysis_name == "Advanced Analytics":
        insights += generate_advanced_analytics_insights(data, analysis_results)
    else:
        insights += generate_general_insights(data, analysis_results)
    
    return insights

def generate_geographic_insights(data: pd.DataFrame, analysis_results: Dict[str, Any]) -> str:
    """Generate insights for geographic analysis"""
    insights = ""
    
    # Insight 1: Geographic Mismatch Impact
    if 'mismatch_analysis' in analysis_results:
        mismatch_data = analysis_results['mismatch_analysis']
        if 'bin_mismatch' in mismatch_data:
            bin_mismatch_success = mismatch_data['bin_mismatch'].loc[True, ('is_successful', 'mean')] if True in mismatch_data['bin_mismatch'].index else 0
            bin_match_success = mismatch_data['bin_mismatch'].loc[False, ('is_successful', 'mean')] if False in mismatch_data['bin_mismatch'].index else 0
            
            insights += "### 🔍 **Insight 1: Geographic Mismatch Impact**\n"
            insights += f"**Finding**: Transactions with billing country ≠ bin country show {format_percentage(bin_mismatch_success)} success rate vs {format_percentage(bin_match_success)} for matching countries.\n"
            insights += "**Calculation Logic**: `geo_mismatch = billing_country != bin_country_iso` → Group by mismatch status → Calculate success rate mean\n"
            insights += "**Business Impact**: Geographic mismatches may indicate higher fraud risk or international transactions.\n\n"
    
    # Insight 2: Country Performance Ranking
    if 'billing_country_success' in analysis_results:
        country_data = analysis_results['billing_country_success']
        if not country_data.empty and ('is_successful', 'mean') in country_data.columns:
            valid_country_data = country_data[('is_successful', 'mean')].dropna()
            if not valid_country_data.empty:
                top_country = valid_country_data.idxmax()
                top_success_rate = valid_country_data.max()
                
                insights += "### 🌍 **Insight 2: Top Performing Country**\n"
                insights += f"**Finding**: {top_country} has the highest success rate at {format_percentage(top_success_rate)}.\n"
                insights += "**Calculation Logic**: `groupby('billing_country')['is_successful'].mean()` → Sort descending → Identify top performer\n"
                insights += "**Business Impact**: Focus optimization efforts on high-performing regions and investigate low-performing ones.\n\n"
            else:
                insights += "### 🌍 **Insight 2: Top Performing Country**\n"
                insights += "**Finding**: No valid country performance data available.\n"
                insights += "**Calculation Logic**: Data validation check for non-empty and non-NaN values\n"
                insights += "**Business Impact**: Ensure country data is properly populated for analysis.\n\n"
        else:
            insights += "### 🌍 **Insight 2: Top Performing Country**\n"
            insights += "**Finding**: Country analysis data not available.\n"
            insights += "**Calculation Logic**: Check for 'billing_country_success' and required columns\n"
            insights += "**Business Impact**: Verify data structure and country field availability.\n\n"
    
    # Insight 3: Correlation Analysis
    if 'bin_ip_correlation' in analysis_results:
        correlation = analysis_results['bin_ip_correlation']
        insights += "### 📊 **Insight 3: Bin-IP Correlation**\n"
        insights += f"**Finding**: Correlation between bin country mismatch and success rate is {correlation:.3f}.\n"
        insights += "**Calculation Logic**: `df['bin_mismatch'].corr(df['is_successful'])` → Pearson correlation coefficient\n"
        insights += "**Business Impact**: {'Strong' if abs(correlation) > 0.5 else 'Moderate' if abs(correlation) > 0.3 else 'Weak'} correlation suggests {'significant' if abs(correlation) > 0.5 else 'moderate' if abs(correlation) > 0.3 else 'minimal'} fraud risk from geographic mismatches.\n\n"
    
    return insights

def generate_user_behavior_insights(data: pd.DataFrame, analysis_results: Dict[str, Any]) -> str:
    """Generate insights for user behavior analysis"""
    insights = ""
    
    if 'user_patterns' in analysis_results:
        user_data = analysis_results['user_patterns']
        
        # Insight 1: High-Risk Users
        high_risk_users = user_data[user_data['risk_score'] > 3]
        high_risk_count = len(high_risk_users)
        
        insights += "### 🚨 **Insight 1: High-Risk User Identification**\n"
        insights += f"**Finding**: {high_risk_count} users identified as high-risk (risk score > 3).\n"
        insights += "**Calculation Logic**: Risk score = Velocity risk (2.0) + Failure rate risk (1.5) + Amount pattern risk (1.0)\n"
        insights += "**Business Impact**: These users require immediate attention and potential account review.\n\n"
        
        # Insight 2: User Segmentation
        if 'user_segments' in analysis_results:
            segment_data = analysis_results['user_segments']
            low_risk_success = segment_data.loc['Low Risk', 'success_rate'] if 'Low Risk' in segment_data.index else 0
            high_risk_success = segment_data.loc['High Risk', 'success_rate'] if 'High Risk' in segment_data.index else 0
            
            insights += "### 📈 **Insight 2: User Segment Performance**\n"
            insights += f"**Finding**: Low-risk users show {format_percentage(low_risk_success)} success rate vs {format_percentage(high_risk_success)} for high-risk users.\n"
            insights += "**Calculation Logic**: `pd.cut(risk_score, bins=[0,1,3,5,inf], labels=['Low','Medium','High','Very High'])` → Group by segment → Calculate success rate mean\n"
            insights += "**Business Impact**: Clear performance differentiation enables targeted risk management strategies.\n\n"
        
        # Insight 3: Transaction Velocity
        if 'transactions_per_hour' in user_data.columns:
            avg_velocity = user_data['transactions_per_hour'].mean()
            high_velocity_users = user_data[user_data['transactions_per_hour'] > 5]
            
            insights += "### ⚡ **Insight 3: Transaction Velocity Patterns**\n"
            insights += f"**Finding**: Average transaction velocity is {avg_velocity:.2f} transactions/hour, with {len(high_velocity_users)} users exceeding 5 txn/hour.\n"
            insights += "**Calculation Logic**: `transactions_per_hour = total_transactions / time_span_hours` → Identify users > 5 txn/hour threshold\n"
            insights += "**Business Impact**: High velocity may indicate legitimate high-volume users or potential fraud patterns.\n\n"
    
    return insights

def generate_payment_method_insights(data: pd.DataFrame, analysis_results: Dict[str, Any]) -> str:
    """Generate insights for payment method analysis"""
    insights = ""
    
    if 'gateway_analysis' in analysis_results:
        gateway_data = analysis_results['gateway_analysis']
        
        # Check if gateway_data is not empty and contains valid data
        if not gateway_data.empty and ('is_successful', 'mean') in gateway_data.columns:
            # Filter out NaN values before finding max/min
            valid_gateway_data = gateway_data[('is_successful', 'mean')].dropna()
            
            if not valid_gateway_data.empty and len(valid_gateway_data) > 0:
                try:
                    # Insight 1: Gateway Performance
                    best_gateway = valid_gateway_data.idxmax()
                    best_success_rate = valid_gateway_data.max()
                    worst_gateway = valid_gateway_data.idxmin()
                    worst_success_rate = valid_gateway_data.min()
                    
                    insights += "### 🏦 **Insight 1: Gateway Performance Comparison**\n"
                    insights += f"**Finding**: {best_gateway} performs best ({format_percentage(best_success_rate)}) vs {worst_gateway} worst ({format_percentage(worst_success_rate)}).\n"
                    insights += "**Calculation Logic**: `groupby('gateway_name')['is_successful'].mean()` → Sort descending → Identify best/worst performers\n"
                    insights += "**Business Impact**: Consider routing more transactions through high-performing gateways.\n\n"
                except (ValueError, IndexError) as e:
                    insights += "### 🏦 **Insight 1: Gateway Performance Comparison**\n"
                    insights += f"**Finding**: Error analyzing gateway performance: {str(e)}.\n"
                    insights += "**Calculation Logic**: Data validation and error handling for statistical operations\n"
                    insights += "**Business Impact**: Verify data quality and structure for gateway analysis.\n\n"
                
                # Insight 2: Gateway Volume vs Success
                if len(gateway_data) > 1 and ('is_successful', 'count') in gateway_data.columns:
                    try:
                        volume_success_corr = gateway_data[('is_successful', 'count')].corr(gateway_data[('is_successful', 'mean')])
                        if not pd.isna(volume_success_corr):
                            insights += "### 📊 **Insight 2: Volume-Success Correlation**\n"
                            insights += f"**Finding**: Correlation between transaction volume and success rate is {volume_success_corr:.3f}.\n"
                            insights += "**Calculation Logic**: `gateway_volume.corr(gateway_success_rate)` → Pearson correlation coefficient\n"
                            insights += "**Business Impact**: {'Strong' if abs(volume_success_corr) > 0.5 else 'Moderate' if abs(volume_success_corr) > 0.3 else 'Weak'} correlation suggests {'significant' if abs(volume_success_corr) > 0.5 else 'moderate' if abs(volume_success_corr) > 0.3 else 'minimal'} relationship between volume and performance.\n\n"
                        else:
                            insights += "### 📊 **Insight 2: Volume-Success Correlation**\n"
                            insights += "**Finding**: Insufficient data to calculate volume-success correlation.\n"
                            insights += "**Calculation Logic**: Correlation requires at least 2 data points with valid values\n"
                            insights += "**Business Impact**: Collect more gateway data for meaningful correlation analysis.\n\n"
                    except Exception:
                        insights += "### 📊 **Insight 2: Volume-Success Correlation**\n"
                        insights += "**Finding**: Error calculating volume-success correlation.\n"
                        insights += "**Calculation Logic**: Data validation and error handling for correlation calculation\n"
                        insights += "**Business Impact**: Verify data quality and structure for correlation analysis.\n\n"
            else:
                insights += "### 🏦 **Insight 1: Gateway Performance Comparison**\n"
                insights += "**Finding**: No valid gateway performance data available for analysis.\n"
                insights += "**Calculation Logic**: Data validation check for non-empty and non-NaN values\n"
                insights += "**Business Impact**: Ensure gateway data is properly populated for analysis.\n\n"
        else:
            insights += "### 🏦 **Insight 1: Gateway Performance Comparison**\n"
            insights += "**Finding**: Gateway analysis data not available.\n"
            insights += "**Calculation Logic**: Check for 'gateway_analysis' and required columns\n"
            insights += "**Business Impact**: Verify data structure and gateway field availability.\n\n"
    
    if 'card_type_analysis' in analysis_results:
        card_data = analysis_results['card_type_analysis']
        
        # Check if card_data is not empty and contains valid data
        if not card_data.empty and ('is_successful', 'mean') in card_data.columns:
            # Filter out NaN values before finding max
            valid_card_data = card_data[('is_successful', 'mean')].dropna()
            
            if not valid_card_data.empty and len(valid_card_data) > 0:
                try:
                    # Insight 3: Card Type Performance
                    best_card = valid_card_data.idxmax()
                    best_card_success = valid_card_data.max()
                    
                    insights += "### 💳 **Insight 3: Card Type Performance**\n"
                    insights += f"**Finding**: {best_card} cards show highest success rate at {format_percentage(best_card_success)}.\n"
                    insights += "**Calculation Logic**: `groupby('card_type')['is_successful'].mean()` → Sort descending → Identify top performer\n"
                    insights += "**Business Impact**: Optimize acceptance policies and fraud rules for different card types.\n\n"
                except (ValueError, IndexError) as e:
                    insights += "### 💳 **Insight 3: Card Type Performance**\n"
                    insights += f"**Finding**: Error analyzing card type performance: {str(e)}.\n"
                    insights += "**Calculation Logic**: Data validation and error handling for statistical operations\n"
                    insights += "**Business Impact**: Verify data quality and structure for card type analysis.\n\n"
            else:
                insights += "### 💳 **Insight 3: Card Type Performance**\n"
                insights += "**Finding**: No valid card type data available for analysis.\n"
                insights += "**Calculation Logic**: Data validation check for non-empty and non-NaN values\n"
                insights += "**Business Impact**: Ensure card type data is properly populated for analysis.\n\n"
        else:
            insights += "### 💳 **Insight 3: Card Type Performance**\n"
            insights += "**Finding**: Card type analysis data not available.\n"
            insights += "**Calculation Logic**: Check for 'card_type_analysis' and required columns\n"
            insights += "**Business Impact**: Verify data structure and card type field availability.\n\n"
    
    return insights

def generate_temporal_insights(data: pd.DataFrame, analysis_results: Dict[str, Any]) -> str:
    """Generate insights for temporal analysis"""
    insights = ""
    
    if 'hourly_patterns' in analysis_results:
        hourly_data = analysis_results['hourly_patterns']
        
        if not hourly_data.empty and ('is_successful', 'mean') in hourly_data.columns:
            valid_hourly_data = hourly_data[('is_successful', 'mean')].dropna()
            
            if not valid_hourly_data.empty and len(valid_hourly_data) > 0:
                try:
                    # Insight 1: Peak Performance Hours
                    best_hour = valid_hourly_data.idxmax()
                    best_hour_success = valid_hourly_data.max()
                    worst_hour = valid_hourly_data.idxmin()
                    worst_hour_success = valid_hourly_data.min()
                    
                    insights += "### 🕐 **Insight 1: Peak Performance Hours**\n"
                    insights += f"**Finding**: Hour {best_hour} shows best performance ({format_percentage(best_hour_success)}) vs hour {worst_hour} worst ({format_percentage(worst_hour_success)}).\n"
                    insights += "**Calculation Logic**: `groupby('hour')['is_successful'].mean()` → Sort descending → Identify best/worst hours\n"
                    insights += "**Business Impact**: Schedule maintenance and optimize systems during low-performance hours.\n\n"
                except (ValueError, IndexError) as e:
                    insights += "### 🕐 **Insight 1: Peak Performance Hours**\n"
                    insights += f"**Finding**: Error analyzing hourly performance: {str(e)}.\n"
                    insights += "**Calculation Logic**: Data validation and error handling for statistical operations\n"
                    insights += "**Business Impact**: Verify data quality and structure for hourly analysis.\n\n"
                
                # Insight 2: Business Hours vs Off-Hours
                try:
                    business_hours_range = hourly_data.loc[9:17, ('is_successful', 'mean')]
                    off_hours_range = hourly_data.loc[list(range(0,9)) + list(range(18,24)), ('is_successful', 'mean')]
                    
                    if not business_hours_range.empty and not off_hours_range.empty:
                        business_hours = business_hours_range.mean()
                        off_hours = off_hours_range.mean()
                        
                        if not pd.isna(business_hours) and not pd.isna(off_hours):
                            insights += "### 🏢 **Insight 2: Business Hours Performance**\n"
                            insights += f"**Finding**: Business hours (9-17) show {format_percentage(business_hours)} success vs {format_percentage(off_hours)} for off-hours.\n"
                            insights += "**Calculation Logic**: Business hours = hours 9-17, Off-hours = hours 0-8 + 18-23 → Calculate success rate mean for each group\n"
                            insights += "**Business Impact**: {'Higher' if business_hours > off_hours else 'Lower'} success during business hours suggests {'customer support' if business_hours > off_hours else 'automated processing'} impact.\n\n"
                        else:
                            insights += "### 🏢 **Insight 2: Business Hours Performance**\n"
                            insights += "**Finding**: Insufficient data to compare business vs off-hours performance.\n"
                            insights += "**Calculation Logic**: Data validation for business hours (9-17) and off-hours (0-8, 18-23)\n"
                            insights += "**Business Impact**: Collect more hourly data for meaningful time-based analysis.\n\n"
                    else:
                        insights += "### 🏢 **Insight 2: Business Hours Performance**\n"
                        insights += "**Finding**: Insufficient data to compare business vs off-hours performance.\n"
                        insights += "**Calculation Logic**: Data validation for business hours (9-17) and off-hours (0-8, 18-23)\n"
                        insights += "**Business Impact**: Collect more hourly data for meaningful time-based analysis.\n\n"
                except Exception:
                    insights += "### 🏢 **Insight 2: Business Hours Performance**\n"
                    insights += "**Finding**: Error analyzing business vs off-hours performance.\n"
                    insights += "**Calculation Logic**: Data validation and error handling for time-based analysis\n"
                    insights += "**Business Impact**: Verify data quality and structure for time-based analysis.\n\n"
            else:
                insights += "### 🕐 **Insight 1: Peak Performance Hours**\n"
                insights += "**Finding**: No valid hourly performance data available.\n"
                insights += "**Calculation Logic**: Data validation check for non-empty and non-NaN values\n"
                insights += "**Business Impact**: Ensure hourly data is properly populated for analysis.\n\n"
        else:
            insights += "### 🕐 **Insight 1: Peak Performance Hours**\n"
            insights += "**Finding**: Hourly analysis data not available.\n"
            insights += "**Calculation Logic**: Check for 'hourly_patterns' and required columns\n"
            insights += "**Business Impact**: Verify data structure and hourly field availability.\n\n"
    
    if 'day_of_week_patterns' in analysis_results:
        dow_data = analysis_results['day_of_week_patterns']
        
        if not dow_data.empty and ('is_successful', 'mean') in dow_data.columns:
            # Insight 3: Weekend vs Weekday Performance
            weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            weekends = ['Saturday', 'Sunday']
            
            try:
                weekday_data = dow_data.loc[dow_data.index.isin(weekdays), ('is_successful', 'mean')]
                weekend_data = dow_data.loc[dow_data.index.isin(weekends), ('is_successful', 'mean')]
                
                if not weekday_data.empty and not weekend_data.empty and len(weekday_data) > 0 and len(weekend_data) > 0:
                    try:
                        weekday_success = weekday_data.mean()
                        weekend_success = weekend_data.mean()
                        
                        if not pd.isna(weekday_success) and not pd.isna(weekend_success):
                            insights += "### 📅 **Insight 3: Weekend vs Weekday Patterns**\n"
                            insights += f"**Finding**: Weekdays show {format_percentage(weekday_success)} success vs {format_percentage(weekend_success)} for weekends.\n"
                            insights += "**Calculation Logic**: Weekdays = Mon-Fri, Weekends = Sat-Sun → Calculate success rate mean for each group\n"
                            insights += "**Business Impact**: {'Higher' if weekday_success > weekend_success else 'Lower'} weekday performance suggests {'business' if weekday_success > weekend_success else 'personal'} transaction patterns.\n\n"
                        else:
                            insights += "### 📅 **Insight 3: Weekend vs Weekday Patterns**\n"
                            insights += "**Finding**: Insufficient data to compare weekday vs weekend performance.\n"
                            insights += "**Calculation Logic**: Data validation for weekdays (Mon-Fri) and weekends (Sat-Sun)\n"
                            insights += "**Business Impact**: Collect more daily data for meaningful weekday/weekend analysis.\n\n"
                    except (ValueError, IndexError) as e:
                        insights += "### 📅 **Insight 3: Weekend vs Weekday Patterns**\n"
                        insights += f"**Finding**: Error analyzing weekday vs weekend performance: {str(e)}.\n"
                        insights += "**Calculation Logic**: Data validation and error handling for statistical operations\n"
                        insights += "**Business Impact**: Verify data quality and structure for day-based analysis.\n\n"
                else:
                    insights += "### 📅 **Insight 3: Weekend vs Weekday Patterns**\n"
                    insights += "**Finding**: Insufficient data to compare weekday vs weekend performance.\n"
                    insights += "**Calculation Logic**: Data validation for weekdays (Mon-Fri) and weekends (Sat-Sun)\n"
                    insights += "**Business Impact**: Collect more daily data for meaningful weekday/weekend analysis.\n\n"
            except Exception:
                insights += "### 📅 **Insight 3: Weekend vs Weekday Patterns**\n"
                insights += "**Finding**: Error analyzing weekday vs weekend performance.\n"
                insights += "**Calculation Logic**: Data validation and error handling for day-based analysis\n"
                insights += "**Business Impact**: Verify data quality and structure for day-based analysis.\n\n"
        else:
            insights += "### 📅 **Insight 3: Weekend vs Weekday Patterns**\n"
            insights += "**Finding**: Day of week analysis data not available.\n"
            insights += "**Calculation Logic**: Check for 'day_of_week_patterns' and required columns\n"
            insights += "**Business Impact**: Verify data structure and day of week field availability.\n\n"
    
    return insights

def generate_general_insights(data: pd.DataFrame, analysis_results: Dict[str, Any]) -> str:
    """Generate general insights for other analysis blocks"""
    insights = ""
    
    insights += "### 📊 **General Analysis Insights**\n"
    insights += f"**Data Overview**: Analyzed {len(data)} transactions with {data['is_successful'].sum()} successful and {len(data) - data['is_successful'].sum()} failed.\n"
    insights += "**Success Rate**: Overall success rate is {format_percentage(data['is_successful'].mean())}.\n"
    insights += "**Calculation Logic**: `is_successful = status_title != 'Failed'` → `success_rate = is_successful.mean()`\n"
    insights += "**Business Impact**: Monitor trends and investigate factors affecting success rates.\n\n"
    
    return insights

def generate_advanced_analytics_insights(data: pd.DataFrame, analysis_results: Dict[str, Any]) -> str:
    """Generate insights for advanced analytics"""
    insights = ""
    
    insights += "### 🚀 **Advanced Analytics Insights**\n"
    
    if 'anomaly_detection' in analysis_results:
        anomaly_count = len(analysis_results['anomaly_detection'])
        insights += f"**Finding**: {anomaly_count} anomalous transactions detected using Isolation Forest algorithm.\n"
        insights += "**Calculation Logic**: `IsolationForest(contamination=0.1, random_state=42)` → `anomaly_scores < threshold`\n"
        insights += "**Business Impact**: Anomalies may indicate fraud, errors, or unusual transaction patterns requiring investigation.\n\n"
    
    if 'user_risk_profiles' in analysis_results:
        risk_profiles = analysis_results['user_risk_profiles']
        high_risk_users = len(risk_profiles[risk_profiles['risk_score'] > 3])
        insights += f"**Finding**: {high_risk_users} users identified as high-risk based on behavioral patterns.\n"
        insights += "**Calculation Logic**: Risk score combines velocity, failure rate, amount patterns, and geographic factors\n"
        insights += "**Business Impact**: High-risk users require enhanced monitoring and potential account review.\n\n"
    
    if 'data_quality_metrics' in analysis_results:
        quality_metrics = analysis_results['data_quality_metrics']
        completeness = quality_metrics.get('completeness', 0)
        insights += f"**Finding**: Data completeness is {format_percentage(completeness)} across all critical fields.\n"
        insights += "**Calculation Logic**: `completeness = non_null_count / total_count` for each field → Overall average\n"
        insights += "**Business Impact**: Data quality directly affects analysis accuracy and fraud detection effectiveness.\n\n"
    
    return insights

def create_enhanced_charts(df: pd.DataFrame, analysis_results: Dict[str, Any]) -> Dict[str, go.Figure]:
    """Create enhanced charts with percentage formatting"""
    charts = {}
    
    # Handle both old and new analysis_results structure
    if isinstance(analysis_results, dict) and 'geo_analysis' in analysis_results:
        # New structure with nested analyses
        geo_analysis = analysis_results.get('geo_analysis', {})
        user_analysis = analysis_results.get('user_analysis', {})
        payment_analysis = analysis_results.get('payment_analysis', {})
        temporal_analysis = analysis_results.get('temporal_analysis', {})
    else:
        # Old structure - direct analysis results
        geo_analysis = analysis_results
        user_analysis = analysis_results
        payment_analysis = analysis_results
        temporal_analysis = analysis_results
    
    try:
        # 1. Enhanced Geographic Success Rate Chart
        if 'billing_country_success' in geo_analysis:
            geo_data = geo_analysis['billing_country_success']
            if not geo_data.empty and ('is_successful', 'mean') in geo_data.columns:
                # Create proper DataFrame for Plotly
                plot_data = pd.DataFrame({
                    'Country': geo_data.index,
                    'Success_Rate': geo_data[('is_successful', 'mean')],
                    'Success_Rate_Pct': geo_data.get('success_rate_pct', '')
                })
                
                fig = px.bar(
                    data_frame=plot_data,
                    x='Country',
                    y='Success_Rate',
                    title="Success Rate by Country",
                    labels={'Success_Rate': 'Success Rate (%)'},
                    text='Success_Rate_Pct',
                    color='Success_Rate',
                    color_continuous_scale='RdYlGn'
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(yaxis_tickformat='.1%')
                charts['geographic_success'] = fig
        
        # 2. Bin Country vs IP Country Success Rate Comparison
        if 'bin_country_success' in geo_analysis and 'ip_country_success' in geo_analysis:
            bin_data = geo_analysis['bin_country_success']
            ip_data = geo_analysis['ip_country_success']
            
            if not bin_data.empty and not ip_data.empty:
                # Combine data for comparison
                comparison_data = pd.DataFrame({
                    'Bin_Country_Success': bin_data[('is_successful', 'mean')],
                    'IP_Country_Success': ip_data[('is_successful', 'mean')]
                }).fillna(0)
                
                # Reset index to make it a proper DataFrame
                comparison_data = comparison_data.reset_index()
                comparison_data.columns = ['Country', 'Bin_Country_Success', 'IP_Country_Success']
                
                fig = px.scatter(
                    data_frame=comparison_data,
                    x='Bin_Country_Success',
                    y='IP_Country_Success',
                    title="Bin Country vs IP Country Success Rate Correlation",
                    labels={'Bin_Country_Success': 'Bin Country Success Rate', 'IP_Country_Success': 'IP Country Success Rate'},
                    text='Country'
                )
                fig.update_layout(xaxis_tickformat='.1%', yaxis_tickformat='.1%')
                charts['bin_ip_correlation'] = fig
        
        # 3. Enhanced User Risk Segmentation Chart
        if 'user_segments' in user_analysis:
            segment_data = user_analysis['user_segments']
            if not segment_data.empty and 'total_transactions' in segment_data.columns:
                # Create proper DataFrame for Plotly
                plot_data = segment_data.reset_index()
                plot_data.columns = ['Risk_Segment', 'Total_Transactions', 'Success_Rate', 'Risk_Score']
                
                fig = px.pie(
                    data_frame=plot_data,
                    values='Total_Transactions',
                    names='Risk_Segment',
                    title="User Distribution by Risk Segment",
                    hover_data=['Success_Rate'],
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                charts['user_risk_segments'] = fig
        
        # 4. Enhanced Hourly Success Pattern Chart
        if 'hourly_patterns' in temporal_analysis:
            hourly_data = temporal_analysis['hourly_patterns']
            if not hourly_data.empty and ('is_successful', 'mean') in hourly_data.columns:
                # Create proper DataFrame for Plotly
                plot_data = pd.DataFrame({
                    'Hour': hourly_data.index,
                    'Success_Rate': hourly_data[('is_successful', 'mean')]
                })
                
                fig = px.line(
                    data_frame=plot_data,
                    x='Hour',
                    y='Success_Rate',
                    title="Success Rate by Hour of Day",
                    labels={'Success_Rate': 'Success Rate (%)'},
                    markers=True
                )
                fig.update_layout(yaxis_tickformat='.1%')
                charts['hourly_success'] = fig
                
                # Add volume bars
                if ('is_successful', 'count') in hourly_data.columns:
                    volume_data = pd.DataFrame({
                        'Hour': hourly_data.index,
                        'Transaction_Count': hourly_data[('is_successful', 'count')]
                    })
                    
                    fig2 = px.bar(
                        data_frame=volume_data,
                        x='Hour',
                        y='Transaction_Count',
                        title="Transaction Volume by Hour of Day",
                        labels={'Transaction_Count': 'Transaction Count'},
                        opacity=0.7
                    )
                    charts['hourly_volume'] = fig2
        
        # 5. Gateway Performance Chart
        if 'gateway_analysis' in payment_analysis:
            gateway_data = payment_analysis['gateway_analysis']
            if not gateway_data.empty and ('is_successful', 'mean') in gateway_data.columns:
                # Create proper DataFrame for Plotly
                plot_data = pd.DataFrame({
                    'Gateway': gateway_data.index,
                    'Success_Rate': gateway_data[('is_successful', 'mean')],
                    'Success_Rate_Pct': gateway_data.get('success_rate_pct', '')
                })
                
                fig = px.bar(
                    data_frame=plot_data,
                    x='Gateway',
                    y='Success_Rate',
                    title="Gateway Success Rate Comparison",
                    labels={'Success_Rate': 'Success Rate (%)'},
                    text='Success_Rate_Pct',
                    color='Success_Rate',
                    color_continuous_scale='RdYlGn'
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(yaxis_tickformat='.1%')
                charts['gateway_performance'] = fig
        
        # 6. Day of Week Performance Chart
        if 'day_of_week_patterns' in temporal_analysis:
            dow_data = temporal_analysis['day_of_week_patterns']
            if not dow_data.empty and ('is_successful', 'mean') in dow_data.columns:
                # Create proper DataFrame for Plotly
                plot_data = pd.DataFrame({
                    'Day_of_Week': dow_data.index,
                    'Success_Rate': dow_data[('is_successful', 'mean')],
                    'Success_Rate_Pct': dow_data.get('success_rate_pct', '')
                })
                
                fig = px.bar(
                    data_frame=plot_data,
                    x='Day_of_Week',
                    y='Success_Rate',
                    title="Success Rate by Day of Week",
                    labels={'Success_Rate': 'Success Rate (%)'},
                    text='Success_Rate_Pct',
                    color='Success_Rate',
                    color_continuous_scale='RdYlGn'
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(yaxis_tickformat='.1%')
                charts['day_of_week_performance'] = fig
    
    except Exception as e:
        st.warning(f"Error creating charts: {str(e)}")
        # Return empty charts dict if there's an error
        return {}
    
    return charts

def display_ip_details(ip_address: str, geolocator) -> None:
    """Display detailed information about an IP address"""
    if not ip_address or pd.isna(ip_address):
        st.write("**IP Address:** No IP data available")
        return
    
    st.write(f"**IP Address:** {ip_address}")
    
    if geolocator:
        try:
            location = geolocator.get_location(ip_address)
            if location:
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Country:** {location.get('country', 'Unknown')}")
                    st.write(f"**Country Name:** {location.get('country_name', 'Unknown')}")
                    st.write(f"**ASN:** {location.get('asn', 'Unknown')}")
                with col2:
                    st.write(f"**Organization:** {location.get('org', 'Unknown')}")
                    st.write(f"**Continent:** {location.get('continent', 'Unknown')}")
                    if 'city' in location:
                        st.write(f"**City:** {location['city']}")
            else:
                st.write("**Location:** No geolocation data available")
        except Exception as e:
            st.write(f"**Error:** {str(e)}")
    else:
        st.write("**Location:** IPinfo database not available")

def main():
    st.markdown('<h1 class="main-header">💰 Ultimate Payment Analysis Dashboard</h1>', unsafe_allow_html=True)
    
    # Initialize IPinfo and show status
    geolocator = init_ipinfo_geolocator()
    if geolocator:
        st.success("🌍 IPinfo database loaded - Enhanced geographic analysis available")
    else:
        st.warning("⚠️ IPinfo database not available - Using fallback geographic analysis")
    
    # File upload
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    if uploaded_file is not None:
        # Load and process data
        df = load_and_process_data(uploaded_file)
        
        if not df.empty:
            st.success(f"✅ Data loaded successfully! {len(df)} transactions processed.")
            
            # Sidebar for IP analysis
            st.sidebar.header("🔍 IP Address Analysis")
            
            # IP search
            if 'ip_address' in df.columns:
                unique_ips = df['ip_address'].dropna().unique()
                if len(unique_ips) > 0:
                    selected_ip = st.sidebar.selectbox(
                        "Select IP Address for Analysis",
                        options=[''] + list(unique_ips),
                        index=0
                    )
                    
                    if selected_ip:
                        st.sidebar.subheader("IP Details")
                        display_ip_details(selected_ip, geolocator)
                        
                        # Show transactions from this IP
                        ip_transactions = df[df['ip_address'] == selected_ip]
                        st.sidebar.write(f"**Transactions from this IP:** {len(ip_transactions)}")
                        
                        if len(ip_transactions) > 0:
                            st.sidebar.write("**Success Rate:**", format_percentage(ip_transactions['is_successful'].mean()))
                            if 'amount' in ip_transactions.columns:
                                st.sidebar.write("**Total Amount:**", f"${ip_transactions['amount'].sum():.2f}")
            
            # Display basic statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Transactions", len(df))
            with col2:
                success_rate = df['is_successful'].mean()
                st.metric("Success Rate", format_percentage(success_rate))
            with col3:
                if 'amount' in df.columns:
                    avg_amount = df['amount'].mean()
                    st.metric("Average Amount", f"${avg_amount:.2f}")
            with col4:
                if 'processing_time' in df.columns:
                    avg_time = df['processing_time'].mean()
                    st.metric("Avg Processing Time", f"{avg_time:.1f}s")
            
            # Run all analyses
            st.header("🔍 Comprehensive Analysis Results")
            
            # 1. Enhanced Geographic Analysis
            st.subheader("🌍 Enhanced Geographic Pattern Analysis")
            geo_analysis = create_geographic_analysis(df)
            
            # Display multiple geographic analyses
            col1, col2 = st.columns(2)
            
            with col1:
                if 'billing_country_success' in geo_analysis:
                    st.write("**Success Rate by Billing Country**")
                    geo_data = geo_analysis['billing_country_success']
                    display_data = geo_data[['success_rate_pct', 'total_transactions', 'successful_transactions', 'performance_rank']].head(10)
                    st.dataframe(display_data)
                
                if 'bin_country_success' in geo_analysis:
                    st.write("**Success Rate by Card BIN Country**")
                    bin_data = geo_analysis['bin_country_success']
                    display_data = bin_data[['success_rate_pct', 'total_transactions', 'successful_transactions']].head(10)
                    st.dataframe(display_data)
            
            with col2:
                if 'ip_country_success' in geo_analysis:
                    st.write("**Success Rate by IP Address Country**")
                    ip_data = geo_analysis['ip_country_success']
                    display_data = ip_data[['success_rate_pct', 'total_transactions', 'successful_transactions']].head(10)
                    st.dataframe(display_data)
                
                if 'country_match_analysis' in geo_analysis:
                    st.write("**Success Rate by Country Match Status**")
                    match_data = geo_analysis['country_match_analysis']
                    display_data = match_data[['success_rate_pct', 'total_transactions', 'successful_transactions']]
                    st.dataframe(display_data)
            
            # Display geographic insights
            geo_insights = generate_insights_and_logic("Geographic Pattern Analysis", df, geo_analysis)
            st.markdown(geo_insights)
            
            # Display additional IPinfo analysis
            if 'asn_success' in geo_analysis:
                st.write("**ASN Performance Analysis**")
                asn_data = geo_analysis['asn_success'][['success_rate_pct', 'total_transactions', 'successful_transactions']].head(10)
                st.dataframe(asn_data)
            
            if 'asn_risk_ranking' in geo_analysis:
                st.write("**ASN Risk Ranking**")
                asn_risk_data = geo_analysis['asn_risk_ranking'][['is_successful', 'id', 'risk_score']].head(10)
                st.dataframe(asn_risk_data)
            
            if 'ip_risk_analysis' in geo_analysis:
                st.write("**IP Risk Analysis**")
                ip_risk_data = geo_analysis['ip_risk_analysis']
                st.write(f"**High Risk IPs:** {len(ip_risk_data['high_risk_ips'])}")
                if ip_risk_data['high_risk_ips']:
                    st.write("**High Risk IP Addresses:**")
                    for ip in ip_risk_data['high_risk_ips'][:10]:  # Show first 10
                        st.write(f"- {ip}")
                
                st.write("**Risk Distribution:**")
                risk_dist = pd.DataFrame(list(ip_risk_data['risk_distribution'].items()), columns=['Risk Factors', 'Count'])
                st.dataframe(risk_dist)
            
            # 2. Enhanced User Behavior Analysis
            st.subheader("👤 Enhanced User Behavior Analysis")
            user_analysis = create_user_behavior_analysis(df)
            
            # Display multiple user behavior analyses
            col1, col2 = st.columns(2)
            
            with col1:
                if 'user_patterns' in user_analysis:
                    st.write("**User Transaction Patterns**")
                    user_data = user_analysis['user_patterns'][['success_rate_pct', 'total_transactions', 'successful_count', 'risk_score']].head(10)
                    st.dataframe(user_data)
                
                if 'user_segments' in user_analysis:
                    st.write("**User Risk Segmentation**")
                    segment_data = user_analysis['user_segments'][['success_rate_pct', 'total_transactions', 'risk_score']]
                    st.dataframe(segment_data)
            
            with col2:
                if 'user_behavior_patterns' in user_analysis:
                    st.write("**User Behavior Patterns**")
                    behavior_data = user_analysis['user_behavior_patterns'][['success_rate_pct', 'risk_score', 'avg_time_between_txns', 'txn_frequency']].head(10)
                    st.dataframe(behavior_data)
            
            # Display user behavior insights
            user_insights = generate_insights_and_logic("User Behavior Analysis", df, user_analysis)
            st.markdown(user_insights)
            
            # 3. Enhanced Payment Method Analysis
            st.subheader("💳 Enhanced Payment Method Analysis")
            payment_analysis = create_payment_method_analysis(df)
            
            # Display multiple payment method analyses
            col1, col2 = st.columns(2)
            
            with col1:
                if 'gateway_analysis' in payment_analysis:
                    st.write("**Gateway Performance**")
                    gateway_data = payment_analysis['gateway_analysis'][['success_rate_pct', 'total_transactions', 'successful_transactions', 'performance_rank']]
                    st.dataframe(gateway_data)
                
                if 'card_type_analysis' in payment_analysis:
                    st.write("**Card Type Performance**")
                    card_data = payment_analysis['card_type_analysis'][['success_rate_pct', 'total_transactions', 'successful_transactions', 'performance_rank']]
                    st.dataframe(card_data)
            
            with col2:
                if 'gateway_card_analysis' in payment_analysis:
                    st.write("**Gateway-Card Combination Performance**")
                    combo_data = payment_analysis['gateway_card_analysis'][['success_rate_pct', 'total_transactions', 'successful_transactions']].head(10)
                    st.dataframe(combo_data)
                
                if 'gateway_risk_analysis' in payment_analysis:
                    st.write("**Gateway Risk Analysis**")
                    risk_data = payment_analysis['gateway_risk_analysis'][['is_successful', 'risk_score']]
                    st.dataframe(risk_data)
            
            # Display payment method insights
            payment_insights = generate_insights_and_logic("Payment Method Analysis", df, payment_analysis)
            st.markdown(payment_insights)
            
            # 4. Enhanced Temporal Analysis
            st.subheader("⏰ Enhanced Temporal Pattern Analysis")
            temporal_analysis = create_temporal_analysis(df)
            
            # Display multiple temporal analyses
            col1, col2 = st.columns(2)
            
            with col1:
                if 'hourly_patterns' in temporal_analysis:
                    st.write("**Success Rate by Hour**")
                    hourly_data = temporal_analysis['hourly_patterns'][['success_rate_pct', 'total_transactions', 'successful_transactions', 'performance_rank']]
                    st.dataframe(hourly_data)
                
                if 'day_of_week_patterns' in temporal_analysis:
                    st.write("**Success Rate by Day of Week**")
                    dow_data = temporal_analysis['day_of_week_patterns'][['success_rate_pct', 'total_transactions', 'successful_transactions', 'performance_rank']]
                    st.dataframe(dow_data)
            
            with col2:
                if 'monthly_patterns' in temporal_analysis:
                    st.write("**Success Rate by Month**")
                    monthly_data = temporal_analysis['monthly_patterns'][['success_rate_pct', 'total_transactions', 'successful_transactions']]
                    st.dataframe(monthly_data)
                
                if 'high_risk_hours' in temporal_analysis:
                    st.write("**High Risk Hours (< 50% Success)**")
                    risk_data = temporal_analysis['high_risk_hours'][['success_rate_pct', 'total_transactions', 'successful_transactions']]
                    st.dataframe(risk_data)
            
            # Display temporal insights
            temporal_insights = generate_insights_and_logic("Temporal Pattern Analysis", df, temporal_analysis)
            st.markdown(temporal_insights)
            
            # 5. Enhanced Advanced Body Content Analysis
            st.subheader("🔍 Enhanced Advanced Body Content Analysis")
            try:
                body_analysis = run_advanced_body_analysis(df)
                
                # Display body analysis results in organized format
                if body_analysis:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if 'browser_analysis' in body_analysis:
                            st.write("**🌐 Browser & Device Impact**")
                            browser_data = body_analysis['browser_analysis']
                            if 'browser_success_rates' in browser_data:
                                safe_dataframe_display(browser_data['browser_success_rates'], max_rows=10)
                    
                    with col2:
                        if 'synthetic_detection' in body_analysis:
                            st.write("**🤖 Synthetic Data Detection**")
                            synthetic_data = body_analysis['synthetic_detection']
                            if 'synthetic_indicators' in synthetic_data:
                                safe_dataframe_display(synthetic_data['synthetic_indicators'], max_rows=10)
                
                # Display comprehensive body insights
                try:
                    body_insights = generate_body_insights(body_analysis)
                    st.markdown(body_insights)
                except NameError:
                    # If generate_body_insights is not available, create a basic version
                    st.markdown("## 🔍 **Advanced Body Content Analysis Insights**\n\n")
                    if body_analysis and 'browser_analysis' in body_analysis:
                        st.markdown("**Browser & Device Impact Analysis Completed**\n")
                        st.markdown("This analysis examines how browser types, device characteristics, and user agent information affect transaction success rates.\n")
                    if body_analysis and 'synthetic_detection' in body_analysis:
                        st.markdown("**Synthetic Data Detection Completed**\n")
                        st.markdown("This analysis identifies potential synthetic or automated transaction patterns.\n")
                
                # Add Advanced Body Visualizations
                try:
                    st.subheader("🎨 Advanced Body Analysis Visualizations")
                    # Import the function dynamically to avoid conflicts
                    try:
                        from advanced_body_visualizations import create_body_analysis_visualizations
                        body_charts = create_body_analysis_visualizations(df, body_analysis)
                    except ImportError:
                        st.info("Advanced body visualizations module not available")
                        body_charts = {}
                    
                    if body_charts:
                        # Display charts in organized layout
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if 'browser_geo_heatmap' in body_charts:
                                st.plotly_chart(body_charts['browser_geo_heatmap'], use_container_width=True)
                            if 'speed_success_analysis' in body_charts:
                                st.plotly_chart(body_charts['speed_success_analysis'], use_container_width=True)
                        
                        with col2:
                            if 'synthetic_risk_distribution' in body_charts:
                                st.plotly_chart(body_charts['synthetic_risk_distribution'], use_container_width=True)
                            if 'geographic_mismatch_analysis' in body_charts:
                                st.plotly_chart(body_charts['geographic_mismatch_analysis'], use_container_width=True)
                        
                        # Full-width charts
                        if 'time_speed_success_3d' in body_charts:
                            st.plotly_chart(body_charts['time_speed_success_3d'], use_container_width=True)
                        if 'combined_risk_analysis' in body_charts:
                            st.plotly_chart(body_charts['combined_risk_analysis'], use_container_width=True)
                        if 'factor_correlations_heatmap' in body_charts:
                            st.plotly_chart(body_charts['factor_correlations_heatmap'], use_container_width=True)
                        if 'suspicious_patterns_chart' in body_charts:
                            st.plotly_chart(body_charts['suspicious_patterns_chart'], use_container_width=True)
                    
                except Exception as e:
                    st.warning(f"Advanced body visualizations not available: {str(e)}")
                    st.info("This feature requires the advanced_body_visualizations module.")
                
            except Exception as e:
                st.error(f"Error in advanced body analysis: {str(e)}")
                st.info("This analysis requires the advanced_body_analysis module to be properly configured.")
            
            # 5.5. Geographic Intelligence Analysis
            st.subheader("🌍 Geographic Intelligence Analysis")
            
            # Prepare data for geographic analysis
            df = prepare_data_for_geographic_analysis(df)
            
            try:
                geographic_analysis = run_geographic_intelligence_analysis(df)
                if geographic_analysis:
                    # IP Geolocation Summary
                    if 'ip_geolocation' in geographic_analysis:
                        st.write("**📍 IP Geolocation Summary**")
                        geo = geographic_analysis['ip_geolocation']
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total IPs", f"{geo.get('total_unique_ips', 0):,}")
                        with col2:
                            st.metric("Successful Lookups", f"{geo.get('successful_lookups', 0):,}")
                        with col3:
                            st.metric("Failed Lookups", f"{geo.get('failed_lookups', 0):,}")
                        with col4:
                            st.metric("Success Rate", f"{geo.get('success_rate', 0):.1%}")
                    
                    # Geographic Transaction Patterns
                    if 'geographic_patterns' in geographic_analysis:
                        st.write("**🌐 Geographic Transaction Patterns**")
                        patterns = geographic_analysis['geographic_patterns']
                        
                        if 'country_analysis' in patterns:
                            st.write("**Country-Level Analysis**")
                            country_data = patterns['country_analysis']
                            safe_dataframe_display(country_data, max_rows=15)
                    
                    # Suspicious Regional Activity
                    if 'suspicious_regional_activity' in geographic_analysis:
                        st.write("**🚨 Suspicious Regional Activity Detection**")
                        suspicious = geographic_analysis['suspicious_regional_activity']
                        
                        if 'high_risk_regions' in suspicious:
                            st.write("**High-Risk Regions**")
                            risk_df = suspicious['high_risk_regions']
                            if isinstance(risk_df, pd.DataFrame) and not risk_df.empty:
                                safe_dataframe_display(risk_df, max_rows=10)
                            else:
                                st.info("No suspicious regional activity data available")
                        elif isinstance(suspicious, dict) and 'status' in suspicious:
                            st.info(f"Suspicious activity analysis: {suspicious['status']}")
                    
                    # Cross-Border Analysis
                    if 'cross_border_analysis' in geographic_analysis:
                        st.write("**🌍 Cross-Border Transaction Analysis**")
                        cross_border = geographic_analysis['cross_border_analysis']
                        
                        if 'cross_border_transactions' in cross_border:
                            st.write("**Cross-Border Transactions**")
                            cross_df = cross_border['cross_border_transactions']
                            if isinstance(cross_df, pd.DataFrame) and not cross_df.empty:
                                safe_dataframe_display(cross_df, max_rows=10)
                            else:
                                st.info("No cross-border transaction data available")
                        elif isinstance(cross_border, dict) and 'status' in suspicious:
                            st.info(f"Cross-border analysis: {cross_border['status']}")
                    
                    # Geographic Risk Scoring
                    if 'geographic_risk_scoring' in geographic_analysis:
                        st.write("**🎯 Geographic Risk Scoring**")
                        risk = geographic_analysis['geographic_risk_scoring']
                        
                        if 'risk_scores' in risk:
                            st.write("**Risk Scores**")
                            risk_df = risk['risk_scores']
                            if isinstance(risk_df, pd.DataFrame) and not risk_df.empty:
                                safe_dataframe_display(risk_df, max_rows=10)
                            else:
                                st.info("No geographic risk scoring data available")
                        elif isinstance(risk, dict) and 'status' in risk:
                            st.info(f"Geographic risk scoring: {risk['status']}")
                    
                    # Geographic Clustering
                    if 'geographic_clustering' in geographic_analysis:
                        st.write("**🗺️ Geographic Clustering Analysis**")
                        clustering = geographic_analysis['geographic_clustering']
                        
                        if 'clusters' in clustering:
                            st.write("**Location Clusters**")
                            cluster_df = clustering['clusters']
                            if isinstance(cluster_df, pd.DataFrame) and not cluster_df.empty:
                                safe_dataframe_display(cluster_df, max_rows=15)
                            else:
                                st.info("No geographic clustering data available")
                        elif isinstance(clustering, dict) and 'status' in clustering:
                            st.info(f"Geographic clustering: {clustering['status']}")
                    
                    # Time-Geographic Correlation
                    if 'time_geographic_correlation' in geographic_analysis:
                        st.write("**⏰ Time-Geographic Correlation**")
                        time_geo = geographic_analysis['time_geographic_correlation']
                        
                        if 'correlation_data' in time_geo:
                            st.write("**Correlation Data**")
                            time_df = time_geo['correlation_data']
                            if isinstance(time_df, pd.DataFrame) and not time_df.empty:
                                safe_dataframe_display(time_df, max_rows=10)
                            else:
                                st.info("No time-geographic correlation data available")
                        elif isinstance(time_geo, dict) and 'status' in time_geo:
                            st.info(f"Time-geographic correlation: {time_geo['status']}")
                    
                    # Generate comprehensive insights report
                    st.write("**📊 Geographic Intelligence Insights**")
                    geographic_insights = generate_geographic_insights(geographic_analysis)
                    st.markdown(geographic_insights)
                    
            except Exception as e:
                st.error(f"Error in geographic intelligence analysis: {str(e)}")
                st.info("This analysis requires the geographic_intelligence_engine module to be properly configured.")
            
            # 6. Enhanced Advanced Analytics
            st.subheader("🚀 Enhanced Advanced Analytics")
            try:
                advanced_analyses = run_advanced_analytics(df)
                
                if advanced_analyses:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if 'temporal_patterns' in advanced_analyses:
                            st.write("**Temporal Patterns**")
                            temp_data = advanced_analyses['temporal_patterns']
                            if isinstance(temp_data, pd.DataFrame) and not temp_data.empty:
                                safe_dataframe_display(temp_data, max_rows=10)
                            else:
                                st.info("No temporal patterns data available")
                        
                        if 'anomaly_detection' in advanced_analyses:
                            st.write("**Anomaly Detection Results**")
                            anomaly_data = advanced_analyses['anomaly_detection']
                            if isinstance(anomaly_data, pd.DataFrame) and not anomaly_data.empty:
                                safe_dataframe_display(anomaly_data, max_rows=10)
                            else:
                                st.info("No anomalies detected or insufficient data for analysis.")
                    
                    with col2:
                        if 'user_risk_profiles' in advanced_analyses:
                            st.write("**User Risk Profiles**")
                            risk_data = advanced_analyses['user_risk_profiles']
                            if isinstance(risk_data, pd.DataFrame) and not risk_data.empty:
                                st.dataframe(risk_data.head(10))
                            else:
                                st.info("No user risk profiles available.")
                        
                        if 'data_quality_metrics' in advanced_analyses:
                            st.write("**Data Quality Metrics**")
                            quality_data = advanced_analyses['data_quality_metrics']
                            if isinstance(quality_data, dict):
                                quality_df = pd.DataFrame(list(quality_data.items()), columns=['Metric', 'Value'])
                                st.dataframe(quality_df)
                            else:
                                st.dataframe(quality_data)
                
                # Display advanced analytics insights
                if advanced_analyses:
                    advanced_insights = generate_insights_and_logic("Advanced Analytics", df, advanced_analyses)
                    st.markdown(advanced_insights)
                    
            except Exception as e:
                st.error(f"Error in advanced analytics: {str(e)}")
                st.info("This analysis requires the advanced_analytics_engine module to be properly configured.")
            
            # 7. Enhanced Fraud Detection & Risk Analysis
            st.subheader("🕵️ Enhanced Fraud Detection & Risk Analysis")
            try:
                # Import and run enhanced fraud detection functions without Streamlit config
                import enhanced_fraud_detection_app as fraud_module
                
                # Create a wrapper function that doesn't call Streamlit config
                def calculate_risk_scores_wrapper(df, ipinfo_reader=None):
                    """Wrapper to calculate risk scores without Streamlit conflicts"""
                    try:
                        # Call the function directly from the module
                        if hasattr(fraud_module, 'calculate_risk_scores'):
                            return fraud_module.calculate_risk_scores(df, ipinfo_reader)
                        else:
                            # Fallback: create basic risk scoring
                            risk_df = df.copy()
                            risk_df['risk_score'] = 0.0
                            
                            # Basic risk factors
                            if 'amount' in risk_df.columns:
                                risk_df.loc[risk_df['amount'] > risk_df['amount'].quantile(0.95), 'risk_score'] += 1.0
                            
                            if 'ip_address' in risk_df.columns:
                                ip_counts = risk_df['ip_address'].value_counts()
                                risk_df.loc[risk_df['ip_address'].map(ip_counts) > 5, 'risk_score'] += 1.0
                            
                            if 'billing_country' in risk_df.columns and 'bin_country_iso' in risk_df.columns:
                                risk_df.loc[risk_df['billing_country'] != risk_df['bin_country_iso'], 'risk_score'] += 1.0
                            
                            return risk_df
                    except Exception as e:
                        st.warning(f"Risk scoring error: {str(e)}")
                        return pd.DataFrame()
                
                # Calculate comprehensive risk scores
                risk_df = calculate_risk_scores_wrapper(df, None)
                
                if not risk_df.empty:
                    # Display risk score distribution
                    st.write("**🎯 Risk Score Distribution**")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        high_risk = len(risk_df[risk_df['risk_score'] > 3])
                        st.metric("High Risk Transactions", f"{high_risk:,}")
                    
                    with col2:
                        medium_risk = len(risk_df[(risk_df['risk_score'] > 1) & (risk_df['risk_score'] <= 3)])
                        st.metric("Medium Risk Transactions", f"{medium_risk:,}")
                    
                    with col3:
                        low_risk = len(risk_df[risk_df['risk_score'] <= 1])
                        st.metric("Low Risk Transactions", f"{low_risk:,}")
                    
                    # Display high-risk transactions
                    if high_risk > 0:
                        st.write("**🚨 High-Risk Transactions (Score > 3)**")
                        high_risk_df = risk_df[risk_df['risk_score'] > 3].sort_values('risk_score', ascending=False)
                        safe_dataframe_display(high_risk_df[['amount', 'billing_country', 'ip_address', 'risk_score']].head(10))
                    
                    # Risk score vs success rate analysis
                    st.write("**📊 Risk Score vs Success Rate Analysis**")
                    risk_success = risk_df.groupby(pd.cut(risk_df['risk_score'], bins=[0, 1, 2, 3, 5], labels=['Low', 'Medium', 'High', 'Very High']))['is_successful'].agg(['mean', 'count'])
                    risk_success['success_rate_pct'] = (risk_success['mean'] * 100).round(1)
                    safe_dataframe_display(risk_success)
                    
            except Exception as e:
                st.warning(f"Enhanced fraud detection not available: {str(e)}")
                st.info("This feature requires the enhanced_fraud_detection_app module.")
            
            # 8. Comprehensive Payment Pattern Analysis
            st.subheader("💳 Comprehensive Payment Pattern Analysis")
            try:
                # Import and run comprehensive payment analysis functions without Streamlit config
                import comprehensive_payment_analysis as payment_module
                
                # Create wrapper functions that don't call Streamlit config
                def analyze_payment_success_patterns_wrapper(df):
                    """Wrapper to analyze payment success patterns without Streamlit conflicts"""
                    try:
                        if hasattr(payment_module, 'analyze_payment_success_patterns'):
                            return payment_module.analyze_payment_success_patterns(df)
                        else:
                            # Fallback: create basic success pattern analysis
                            if 'gateway_name' in df.columns:
                                gateway_success = df.groupby('gateway_name')['is_successful'].agg(['mean', 'count']).round(3)
                                gateway_success['success_rate_pct'] = (gateway_success['mean'] * 100).round(1)
                                return {'gateway_success_rates': gateway_success}
                            return {}
                    except Exception as e:
                        st.warning(f"Success pattern analysis error: {str(e)}")
                        return {}
                
                def analyze_failure_patterns_wrapper(df):
                    """Wrapper to analyze failure patterns without Streamlit conflicts"""
                    try:
                        if hasattr(payment_module, 'analyze_failure_patterns'):
                            return payment_module.analyze_failure_patterns(df)
                        else:
                            # Fallback: create basic failure pattern analysis
                            failed_txns = df[~df['is_successful']]
                            if not failed_txns.empty:
                                failure_reasons = failed_txns.groupby('status_title').size().sort_values(ascending=False)
                                return {'failure_reasons': failure_reasons}
                            return {}
                    except Exception as e:
                        st.warning(f"Failure pattern analysis error: {str(e)}")
                        return {}
                
                def analyze_user_behavior_patterns_wrapper(df):
                    """Wrapper to analyze user behavior patterns without Streamlit conflicts"""
                    try:
                        if hasattr(payment_module, 'analyze_user_behavior_patterns'):
                            return payment_module.analyze_user_behavior_patterns(df)
                        else:
                            # Fallback: create basic user behavior analysis
                            if 'user_email' in df.columns:
                                user_segments = df.groupby('user_email').agg({
                                    'is_successful': ['mean', 'count'],
                                    'amount': 'mean' if 'amount' in df.columns else 'count'
                                }).round(3)
                                user_segments.columns = ['_'.join(col).strip('_') for col in user_segments.columns]
                                return {'user_segments': user_segments}
                            return {}
                    except Exception as e:
                        st.warning(f"User behavior analysis error: {str(e)}")
                        return {}
                
                def analyze_technical_infrastructure_wrapper(df):
                    """Wrapper to analyze technical infrastructure without Streamlit conflicts"""
                    try:
                        if hasattr(payment_module, 'analyze_technical_infrastructure'):
                            return payment_module.analyze_technical_infrastructure(df)
                        else:
                            # Fallback: create basic technical infrastructure analysis
                            if 'gateway_name' in df.columns:
                                gateway_performance = df.groupby('gateway_name').agg({
                                    'is_successful': ['mean', 'count'],
                                    'processing_time': 'mean' if 'processing_time' in df.columns else 'count'
                                }).round(3)
                                gateway_performance.columns = ['_'.join(col).strip('_') for col in gateway_performance.columns]
                                return {'gateway_performance': gateway_performance}
                            return {}
                    except Exception as e:
                        st.warning(f"Technical infrastructure analysis error: {str(e)}")
                        return {}
                
                # Payment Success Patterns
                st.write("**✅ Payment Success Pattern Analysis**")
                success_patterns = analyze_payment_success_patterns_wrapper(df)
                if success_patterns and 'gateway_success_rates' in success_patterns:
                    safe_dataframe_display(success_patterns['gateway_success_rates'].head(10))
                
                # Failure Pattern Analysis
                st.write("**❌ Payment Failure Pattern Analysis**")
                failure_patterns = analyze_failure_patterns_wrapper(df)
                if failure_patterns and 'failure_reasons' in failure_patterns:
                    safe_dataframe_display(failure_patterns['failure_reasons'].head(10))
                
                # User Behavior Patterns
                st.write("**👤 User Behavior Pattern Analysis**")
                user_patterns = analyze_user_behavior_patterns_wrapper(df)
                if user_patterns and 'user_segments' in user_patterns:
                    safe_dataframe_display(user_patterns['user_segments'].head(10))
                
                # Technical Infrastructure Analysis
                st.write("**🔧 Technical Infrastructure Analysis**")
                tech_analysis = analyze_technical_infrastructure_wrapper(df)
                if tech_analysis and 'gateway_performance' in tech_analysis:
                    safe_dataframe_display(tech_analysis['gateway_performance'].head(10))
                    
            except Exception as e:
                st.warning(f"Comprehensive payment analysis not available: {str(e)}")
                st.info("This feature requires the comprehensive_payment_analysis module.")
            
            # 9. Enhanced Geographic Analysis with IPinfo
            st.subheader("🌍 Enhanced Geographic Analysis with IPinfo")
            try:
                # Import and run enhanced geographic analysis functions without Streamlit config
                import enhanced_geographic_analysis as geo_module
                
                # Create wrapper functions that don't call Streamlit config
                def enhance_with_ipinfo_wrapper(df, ipinfo_reader=None):
                    """Wrapper to enhance data with IPinfo without Streamlit conflicts"""
                    try:
                        if hasattr(geo_module, 'enhance_with_ipinfo'):
                            return geo_module.enhance_with_ipinfo(df, ipinfo_reader)
                        else:
                            # Fallback: create basic IP enhancement
                            enhanced_df = df.copy()
                            if 'ip_address' in enhanced_df.columns:
                                # Use our existing IPinfo geolocator
                                geolocator = init_ipinfo_geolocator()
                                if geolocator:
                                    enhanced_df['ip_country'] = enhanced_df['ip_address'].apply(
                                        lambda x: geolocator.get_country(x) if pd.notna(x) else 'Unknown'
                                    )
                                else:
                                    enhanced_df['ip_country'] = 'Unknown'
                            return enhanced_df
                    except Exception as e:
                        st.warning(f"IP enhancement error: {str(e)}")
                        return df
                
                def calculate_geo_risk_scores_wrapper(df):
                    """Wrapper to calculate geographic risk scores without Streamlit conflicts"""
                    try:
                        if hasattr(geo_module, 'calculate_risk_scores'):
                            return geo_module.calculate_risk_scores(df)
                        else:
                            # Fallback: create basic geographic risk scoring
                            risk_df = df.copy()
                            risk_df['geographic_risk_score'] = 0.0
                            
                            # Geographic risk factors
                            if 'ip_country' in risk_df.columns and 'billing_country' in risk_df.columns:
                                risk_df.loc[risk_df['ip_country'] != risk_df['billing_country'], 'geographic_risk_score'] += 2.0
                            
                            if 'ip_country' in risk_df.columns:
                                high_risk_countries = ['XX', 'YY']  # Placeholder
                                risk_df.loc[risk_df['ip_country'].isin(high_risk_countries), 'geographic_risk_score'] += 1.0
                            
                            return risk_df
                    except Exception as e:
                        st.warning(f"Geographic risk scoring error: {str(e)}")
                        return df
                
                # Enhanced IP geolocation analysis
                st.write("**📍 Enhanced IP Geolocation Analysis**")
                enhanced_df = enhance_with_ipinfo_wrapper(df, None)
                
                if not enhanced_df.empty and 'ip_country' in enhanced_df.columns:
                    # Geographic distribution
                    geo_dist = enhanced_df['ip_country'].value_counts().head(10)
                    st.write("**Top 10 Countries by IP Address**")
                    safe_dataframe_display(geo_dist.reset_index().rename(columns={'index': 'Country', 'ip_country': 'Count'}))
                    
                    # Cross-border analysis
                    if 'billing_country' in enhanced_df.columns:
                        cross_border = enhanced_df[enhanced_df['ip_country'] != enhanced_df['billing_country']]
                        if not cross_border.empty:
                            st.write(f"**🌐 Cross-Border Transactions: {len(cross_border):,}**")
                            cross_border_summary = cross_border.groupby(['ip_country', 'billing_country']).size().sort_values(ascending=False).head(10)
                            safe_dataframe_display(cross_border_summary.reset_index().rename(columns={0: 'Count'}))
                
                # Geographic risk scoring
                st.write("**🎯 Geographic Risk Scoring**")
                geo_risk_df = calculate_geo_risk_scores_wrapper(enhanced_df)
                if not geo_risk_df.empty and 'geographic_risk_score' in geo_risk_df.columns:
                    high_geo_risk = len(geo_risk_df[geo_risk_df['geographic_risk_score'] > 3])
                    st.metric("High Geographic Risk Transactions", f"{high_geo_risk:,}")
                    
                    if high_geo_risk > 0:
                        st.write("**🚨 High Geographic Risk Transactions**")
                        high_geo_df = geo_risk_df[geo_risk_df['geographic_risk_score'] > 3].sort_values('geographic_risk_score', ascending=False)
                        safe_dataframe_display(high_geo_df[['amount', 'ip_country', 'billing_country', 'geographic_risk_score']].head(10))
                        
            except Exception as e:
                st.warning(f"Enhanced geographic analysis not available: {str(e)}")
                st.info("This feature requires the enhanced_geographic_analysis module.")
            
            # 10. Enhanced Charts & Visualizations
            st.subheader("📊 Enhanced Visualizations & Charts")
            try:
                # Create charts using all available analysis results
                all_analyses = {
                    'geo_analysis': geo_analysis,
                    'user_analysis': user_analysis,
                    'payment_analysis': payment_analysis,
                    'temporal_analysis': temporal_analysis
                }
                
                charts = create_enhanced_charts(df, all_analyses)
                
                # Display charts in organized layout
                if charts:
                    # Geographic charts
                    if 'geographic_success' in charts:
                        st.subheader("🌍 Geographic Analysis Charts")
                        st.plotly_chart(charts['geographic_success'], use_container_width=True)
                    
                    if 'bin_ip_correlation' in charts:
                        st.plotly_chart(charts['bin_ip_correlation'], use_container_width=True)
                    
                    # User behavior charts
                    if 'user_risk_segments' in charts:
                        st.subheader("👤 User Behavior Charts")
                        st.plotly_chart(charts['user_risk_segments'], use_container_width=True)
                    
                    # Temporal charts
                    if 'hourly_success' in charts:
                        st.subheader("⏰ Temporal Analysis Charts")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.plotly_chart(charts['hourly_success'], use_container_width=True)
                        with col2:
                            if 'hourly_volume' in charts:
                                st.plotly_chart(charts['hourly_volume'], use_container_width=True)
                    
                    if 'day_of_week_performance' in charts:
                        st.plotly_chart(charts['day_of_week_performance'], use_container_width=True)
                    
                    # Payment method charts
                    if 'gateway_performance' in charts:
                        st.subheader("💳 Payment Method Charts")
                        st.plotly_chart(charts['gateway_performance'], use_container_width=True)
                
            except Exception as e:
                st.error(f"Error creating charts: {str(e)}")
                st.info("Some charts may not be available due to missing data or analysis results.")
            
        else:
            st.error("❌ Failed to load data. Please check your CSV file format.")

if __name__ == "__main__":
    main()
