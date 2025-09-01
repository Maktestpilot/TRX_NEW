"""
Enhanced Payment Analysis Dashboard
Modular architecture with improved performance and maintainability
"""

import streamlit as st
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Any
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.integration_manager import IntegrationManager
from src.core.data_processor import EnhancedDataProcessor
from src.services.geolocation_service import GeolocationService, IPinfoGeolocationProvider, CSVGeolocationProvider
from src.services.conversion_optimizer import AdvancedConversionOptimizer
from src.utils.validators import DataValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Enhanced TRX Analysis Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'integration_manager' not in st.session_state:
    st.session_state.integration_manager = None
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None


@st.cache_resource
def initialize_integration_manager(mmdb_path: str = None, csv_path: str = None) -> IntegrationManager:
    """Initialize the integration manager with configuration"""
    config = {}
    
    if mmdb_path and os.path.exists(mmdb_path):
        config['ipinfo_mmdb_path'] = mmdb_path
    
    if csv_path and os.path.exists(csv_path):
        config['ip_csv_path'] = csv_path
    
    return IntegrationManager(config)


def display_system_status(integration_manager: IntegrationManager):
    """Display system status and health"""
    status = integration_manager.get_system_status()
    
    st.sidebar.subheader("🔧 System Status")
    
    # Overall status
    if status['overall_status'] == 'healthy':
        st.sidebar.success("✅ System Healthy")
    else:
        st.sidebar.warning("⚠️ System Degraded")
    
    # Service status
    for service_name, is_available in status['services'].items():
        if is_available:
            st.sidebar.success(f"✅ {service_name.title()}")
        else:
            st.sidebar.error(f"❌ {service_name.title()}")
    
    # Geolocation cache stats
    if 'geolocation' in status['services'] and status['services']['geolocation']:
        cache_stats = integration_manager._get_geolocation_stats()
        if cache_stats:
            st.sidebar.metric("Cache Hit Rate", f"{cache_stats['hit_rate']:.1%}")
            st.sidebar.metric("Cache Size", cache_stats['cache_size'])


@st.cache_data
def display_critical_metrics(df: pd.DataFrame):
    """Display critical conversion metrics"""
    st.subheader("🚨 Critical Conversion Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Overall conversion rate
        if 'is_successful' in df.columns:
            conversion_rate = df['is_successful'].mean()
            st.metric("Conversion Rate", f"{conversion_rate:.1%}")
            
            if conversion_rate < 0.8:
                st.error("⚠️ Below target (80%)")
            else:
                st.success("✅ Above target")
    
    with col2:
        # IP-BIN match rate
        if 'ip_bin_country_match' in df.columns:
            match_rate = df['ip_bin_country_match'].mean()
            st.metric("IP-BIN Match Rate", f"{match_rate:.1%}")
            
            if match_rate < 0.7:
                st.error("⚠️ Low match rate")
            else:
                st.success("✅ Good match rate")
    
    with col3:
        # Data quality score
        if 'data_quality_score' in df.columns:
            avg_quality = df['data_quality_score'].mean()
            st.metric("Data Quality", f"{avg_quality:.1f}/20")
            
            if avg_quality < 15:
                st.error("⚠️ Low quality")
            else:
                st.success("✅ Good quality")
    
    with col4:
        # Geographic risk
        if 'geo_risk_score' in df.columns:
            avg_risk = df['geo_risk_score'].mean()
            st.metric("Geo Risk Score", f"{avg_risk:.1f}/10")
            
            if avg_risk > 5:
                st.error("⚠️ High risk")
            else:
                st.success("✅ Low risk")


@st.cache_data
def display_conversion_analysis(analysis_results: Dict[str, Any]):
    """Display detailed conversion analysis"""
    if not analysis_results or 'conversion_analysis' not in analysis_results:
        return
    
    conversion_analysis = analysis_results['conversion_analysis']
    
    st.subheader("📊 Conversion Impact Analysis")
    
    # IP-BIN country impact
    if 'ip_bin_match' in conversion_analysis.get('factors', {}):
        factor = conversion_analysis['factors']['ip_bin_match']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**IP-BIN Country Match Impact:**")
            st.metric("Match Rate", f"{factor['match_rate']:.1%}")
            st.metric("Conversion When Matched", f"{factor['conversion_when_matched']:.1%}")
            st.metric("Conversion When Mismatched", f"{factor['conversion_when_mismatched']:.1%}")
        
        with col2:
            st.write("**Impact Analysis:**")
            impact = factor['impact']
            st.metric("Conversion Impact", f"{impact:+.1%}")
            
            if impact > 0.1:
                st.success(f"🎯 High impact factor: {impact:.1%}")
            elif impact > 0.05:
                st.info(f"📈 Medium impact factor: {impact:.1%}")
            else:
                st.warning(f"📊 Low impact factor: {impact:.1%}")


def display_optimization_recommendations(integration_manager: IntegrationManager, df: pd.DataFrame):
    """Display optimization recommendations"""
    st.subheader("🎯 Optimization Recommendations")
    
    recommendations = integration_manager.get_optimization_recommendations(df)
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            st.write(f"{i}. {rec}")
    else:
        st.info("No specific recommendations available")
    
    # Conversion impact prediction
    impact_prediction = integration_manager.get_conversion_impact_prediction(df)
    
    if impact_prediction:
        st.subheader("📈 Conversion Impact Prediction")
        
        current_rate = impact_prediction.get('current_conversion_rate', 0)
        predicted_rate = impact_prediction.get('predicted_conversion_rate', 0)
        total_improvement = impact_prediction.get('total_potential_improvement', 0)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Current Rate", f"{current_rate:.1%}")
        
        with col2:
            st.metric("Predicted Rate", f"{predicted_rate:.1%}")
        
        with col3:
            st.metric("Potential Improvement", f"{total_improvement:+.1%}")


def display_data_quality_analysis(analysis_results: Dict[str, Any]):
    """Display data quality analysis"""
    if not analysis_results or 'processing_stats' not in analysis_results:
        return
    
    processing_stats = analysis_results['processing_stats']
    quality_metrics = processing_stats.get('data_quality_metrics', {})
    
    st.subheader("🔍 Data Quality Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        quality_score = quality_metrics.get('data_quality_score', 0)
        st.metric("Overall Quality Score", f"{quality_score}/100")
        
        if quality_score >= 80:
            st.success("✅ Excellent quality")
        elif quality_score >= 60:
            st.warning("⚠️ Good quality")
        else:
            st.error("❌ Poor quality")
    
    with col2:
        total_errors = len(quality_metrics.get('validation_errors', []))
        st.metric("Validation Errors", total_errors)
        
        if total_errors == 0:
            st.success("✅ No errors")
        elif total_errors < 10:
            st.warning("⚠️ Few errors")
        else:
            st.error("❌ Many errors")
    
    with col3:
        total_rows = quality_metrics.get('total_rows', 0)
        st.metric("Total Rows", total_rows)
    
    # Show validation errors if any
    validation_errors = quality_metrics.get('validation_errors', [])
    if validation_errors:
        with st.expander("🚨 Validation Errors", expanded=False):
            for error in validation_errors[:20]:  # Show first 20 errors
                st.write(f"• {error}")
            
            if len(validation_errors) > 20:
                st.write(f"... and {len(validation_errors) - 20} more errors")


def main():
    """Main application function"""
    st.title("🚀 Enhanced TRX Analysis Dashboard")
    st.markdown("**Modular Architecture | Advanced Analytics | Conversion Optimization**")
    
    # Sidebar configuration
    st.sidebar.header("⚙️ Configuration")
    
    # File upload
    uploaded_file = st.sidebar.file_uploader(
        "📁 Upload Transaction Data (CSV)",
        type=['csv'],
        help="Upload your transaction data CSV file"
    )
    
    # MMDB file configuration
    mmdb_file = st.sidebar.file_uploader(
        "🌍 IPinfo MMDB Database",
        type=['mmdb'],
        help="Upload IPinfo MMDB database for geolocation"
    )
    
    # CSV mapping file
    csv_file = st.sidebar.file_uploader(
        "📋 IP Country Mapping (CSV)",
        type=['csv'],
        help="Upload CSV file with IP to country mapping"
    )
    
    # Initialize integration manager
    if st.sidebar.button("🔄 Initialize System") or st.session_state.integration_manager is None:
        with st.spinner("Initializing system..."):
            try:
                # Save uploaded files temporarily
                mmdb_path = None
                csv_path = None
                
                if mmdb_file:
                    mmdb_path = f"temp_{mmdb_file.name}"
                    with open(mmdb_path, "wb") as f:
                        f.write(mmdb_file.getbuffer())
                
                if csv_file:
                    csv_path = f"temp_{csv_file.name}"
                    with open(csv_path, "wb") as f:
                        f.write(csv_file.getbuffer())
                
                st.session_state.integration_manager = initialize_integration_manager(mmdb_path, csv_path)
                st.success("✅ System initialized successfully!")
                
            except Exception as e:
                st.error(f"❌ System initialization failed: {e}")
                return
    
    # Display system status
    if st.session_state.integration_manager:
        display_system_status(st.session_state.integration_manager)
    
    # Main content
    if uploaded_file is not None and st.session_state.integration_manager:
        # Load and process data
        if st.button("🔄 Process Data") or st.session_state.processed_data is None:
            with st.spinner("Processing data..."):
                try:
                    # Load CSV data
                    df = pd.read_csv(uploaded_file)
                    st.success(f"✅ Data loaded: {len(df)} transactions")
                    
                    # Process data through integration manager
                    analysis_results = st.session_state.integration_manager.process_transaction_data(df)
                    
                    # Store results
                    st.session_state.processed_data = analysis_results['processed_data']
                    st.session_state.analysis_results = analysis_results
                    
                    st.success("✅ Data processing completed!")
                    
                except Exception as e:
                    st.error(f"❌ Data processing failed: {e}")
                    logger.error(f"Data processing error: {e}", exc_info=True)
                    return
        
        # Display results
        if st.session_state.processed_data is not None and st.session_state.analysis_results is not None:
            df = st.session_state.processed_data
            analysis_results = st.session_state.analysis_results
            
            # Critical metrics
            display_critical_metrics(df)
            
            # Conversion analysis
            display_conversion_analysis(analysis_results)
            
            # Optimization recommendations
            display_optimization_recommendations(st.session_state.integration_manager, df)
            
            # Data quality analysis
            display_data_quality_analysis(analysis_results)
            
            # Data preview
            with st.expander("📋 Processed Data Preview", expanded=False):
                st.dataframe(df.head(20), use_container_width=True)
            
            # Insights
            if 'insights' in analysis_results:
                st.subheader("💡 Key Insights")
                for insight in analysis_results['insights']:
                    st.write(insight)
    
    else:
        st.info("💡 Please upload transaction data and initialize the system to begin analysis.")
        
        st.markdown("""
        ### 🚀 Enhanced Features:
        - **Modular Architecture**: Clean, maintainable code structure
        - **Advanced IP Analysis**: IP vs BIN country comparison
        - **Data Quality Scoring**: Comprehensive data validation
        - **Conversion Optimization**: ML-based recommendations
        - **Geographic Risk Analysis**: Advanced fraud detection
        - **Caching**: Improved performance with intelligent caching
        - **Error Handling**: Robust error handling and logging
        """)


if __name__ == "__main__":
    main()
