# Advanced Analytics Engine for Payment Analysis
# Sophisticated fraud detection and pattern analysis

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ---------- Advanced Statistical Analysis ----------

def calculate_anomaly_scores(df: pd.DataFrame, columns: List[str], method: str = 'zscore') -> pd.DataFrame:
    """Calculate anomaly scores for numerical columns using various methods"""
    
    df = df.copy()
    
    for col in columns:
        if col in df.columns and df[col].dtype in ['int64', 'float64']:
            if method == 'zscore':
                # Z-score method
                mean_val = df[col].mean()
                std_val = df[col].std()
                if std_val > 0:
                    df[f'{col}_anomaly_score'] = abs((df[col] - mean_val) / std_val)
                else:
                    df[f'{col}_anomaly_score'] = 0
            
            elif method == 'iqr':
                # IQR method
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                if IQR > 0:
                    df[f'{col}_anomaly_score'] = abs((df[col] - Q1) / IQR)
                else:
                    df[f'{col}_anomaly_score'] = 0
            
            elif method == 'mad':
                # Median Absolute Deviation method
                median_val = df[col].median()
                mad = np.median(np.abs(df[col] - median_val))
                if mad > 0:
                    df[f'{col}_anomaly_score'] = abs((df[col] - median_val) / mad)
                else:
                    df[f'{col}_anomaly_score'] = 0
    
    return df

def detect_temporal_patterns(df: pd.DataFrame, time_column: str = 'created_at', 
                           target_column: str = 'is_successful') -> pd.DataFrame:
    """Detect temporal patterns and seasonality in transaction data"""
    
    if time_column not in df.columns or target_column not in df.columns:
        return pd.DataFrame()
    
    try:
        # Convert to datetime if needed
        df[time_column] = pd.to_datetime(df[time_column], errors='coerce')
        
        # Create a comprehensive temporal analysis DataFrame
        temporal_data = []
        
        # 1. Hourly patterns
        df['hour'] = df[time_column].dt.hour
        hourly_pattern = df.groupby('hour')[target_column].agg(['mean', 'count', 'std']).round(3)
        hourly_pattern['pattern_type'] = 'hourly'
        hourly_pattern['time_unit'] = hourly_pattern.index
        temporal_data.append(hourly_pattern.reset_index())
        
        # 2. Day of week patterns
        df['day_of_week'] = df[time_column].dt.dayofweek
        df['day_name'] = df[time_column].dt.day_name()
        dow_pattern = df.groupby('day_of_week')[target_column].agg(['mean', 'count', 'std']).round(3)
        dow_pattern['pattern_type'] = 'day_of_week'
        dow_pattern['time_unit'] = dow_pattern.index
        temporal_data.append(dow_pattern.reset_index())
        
        # 3. Monthly patterns
        df['month'] = df[time_column].dt.month
        monthly_pattern = df.groupby('month')[target_column].agg(['mean', 'count', 'std']).round(3)
        monthly_pattern['pattern_type'] = 'monthly'
        monthly_pattern['time_unit'] = monthly_pattern.index
        temporal_data.append(monthly_pattern.reset_index())
        
        # Combine all patterns into one DataFrame
        if temporal_data:
            combined_df = pd.concat(temporal_data, ignore_index=True)
            return combined_df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Error in temporal pattern detection: {e}")
        return pd.DataFrame()

def analyze_transaction_sequences(df: pd.DataFrame, user_column: str = 'user_email', 
                                time_column: str = 'created_at') -> Dict[str, Any]:
    """Analyze transaction sequences and patterns for individual users"""
    
    analysis = {}
    
    if user_column not in df.columns or time_column not in df.columns:
        return analysis
    
    # Sort by user and time
    df_sorted = df.sort_values([user_column, time_column])
    
    sequence_patterns = []
    retry_analysis = []
    velocity_analysis = []
    
    for user in df[user_column].unique():
        user_df = df_sorted[df_sorted[user_column] == user]
        
        if len(user_df) > 1:
            # 1. Transaction sequence analysis
            status_sequence = list(user_df['status_title']) if 'status_title' in user_df.columns else []
            amount_sequence = list(user_df['amount']) if 'amount' in user_df.columns else []
            
            # 2. Retry pattern detection
            retry_count = 0
            retry_times = []
            retry_amounts = []
            
            for i in range(len(user_df) - 1):
                current_status = user_df.iloc[i].get('status_title', '')
                next_status = user_df.iloc[i+1].get('status_title', '')
                
                if current_status == 'Failed' and next_status != 'Failed':
                    retry_count += 1
                    
                    # Time between retry
                    time_diff = (user_df.iloc[i+1][time_column] - user_df.iloc[i][time_column]).total_seconds() / 60
                    retry_times.append(time_diff)
                    
                    # Amount change
                    if 'amount' in user_df.columns:
                        amount_diff = user_df.iloc[i+1]['amount'] - user_df.iloc[i]['amount']
                        retry_amounts.append(amount_diff)
            
            # 3. Velocity analysis
            time_span = (user_df[time_column].max() - user_df[time_column].min()).total_seconds() / 3600  # hours
            transactions_per_hour = len(user_df) / max(time_span, 1)
            
            # 4. Amount pattern analysis
            amount_stats = {}
            if 'amount' in user_df.columns:
                amount_stats = {
                    'min_amount': user_df['amount'].min(),
                    'max_amount': user_df['amount'].max(),
                    'avg_amount': user_df['amount'].mean(),
                    'amount_variance': user_df['amount'].var(),
                    'amount_trend': 'increasing' if len(amount_sequence) > 1 and amount_sequence[-1] > amount_sequence[0] else 'decreasing'
                }
            
            # Compile user analysis
            user_analysis = {
                'user_email': user,
                'total_transactions': len(user_df),
                'status_sequence': status_sequence,
                'retry_count': retry_count,
                'avg_retry_time_minutes': np.mean(retry_times) if retry_times else 0,
                'transactions_per_hour': transactions_per_hour,
                'time_span_hours': time_span,
                **amount_stats
            }
            
            sequence_patterns.append(user_analysis)
            
            if retry_count > 0:
                retry_analysis.append({
                    'user_email': user,
                    'retry_count': retry_count,
                    'retry_times': retry_times,
                    'retry_amounts': retry_amounts
                })
            
            if transactions_per_hour > 1:  # High velocity users
                velocity_analysis.append({
                    'user_email': user,
                    'transactions_per_hour': transactions_per_hour,
                    'total_transactions': len(user_df),
                    'time_span_hours': time_span
                })
    
    analysis['sequence_patterns'] = pd.DataFrame(sequence_patterns)
    analysis['retry_analysis'] = pd.DataFrame(retry_analysis) if retry_analysis else None
    analysis['velocity_analysis'] = pd.DataFrame(velocity_analysis) if velocity_analysis else None
    
    return analysis

def analyze_geographic_anomalies(df: pd.DataFrame) -> Dict[str, Any]:
    """Advanced geographic anomaly detection and analysis"""
    
    analysis = {}
    
    # Required columns check
    required_cols = ['ip_country', 'billing_country', 'is_successful']
    if not all(col in df.columns for col in required_cols):
        return analysis
    
    # 1. Geographic mismatch analysis
    df['geo_mismatch'] = df['ip_country'] != df['billing_country']
    
    # 2. Success rate by geographic match/mismatch
    geo_success_analysis = df.groupby('geo_mismatch').agg({
        'is_successful': ['mean', 'count', 'sum'],
        'amount': ['mean', 'sum'] if 'amount' in df.columns else ['count']
    }).round(3)
    analysis['geo_success_analysis'] = geo_success_analysis
    
    # 3. Detailed mismatch patterns
    if df['geo_mismatch'].any():
        mismatch_details = df[df['geo_mismatch'] == True].groupby(['billing_country', 'ip_country']).agg({
            'is_successful': ['mean', 'count'],
            'amount': ['mean', 'sum'] if 'amount' in df.columns else ['count'],
            'user_email': 'nunique' if 'user_email' in df.columns else 'count'
        }).round(3)
        analysis['mismatch_details'] = mismatch_details
        
        # 4. Risk assessment for mismatches
        mismatch_risk = mismatch_details.copy()
        mismatch_risk['risk_score'] = (
            (1 - mismatch_risk[('is_successful', 'mean')]) * 3 +  # Low success rate
            (mismatch_risk[('is_successful', 'count')] / mismatch_risk[('is_successful', 'count')].max()) * 2  # High volume
        )
        mismatch_risk = mismatch_risk.sort_values('risk_score', ascending=False)
        analysis['mismatch_risk'] = mismatch_risk
    
    # 5. ASN analysis for geographic mismatches
    if 'ip_asn' in df.columns:
        asn_analysis = df[df['geo_mismatch'] == True].groupby('ip_asn').agg({
            'is_successful': ['mean', 'count'],
            'billing_country': 'nunique',
            'ip_country': 'nunique'
        }).round(3)
        asn_analysis.columns = ['success_rate', 'transaction_count', 'billing_countries', 'ip_countries']
        analysis['asn_analysis'] = asn_analysis
    
    return analysis

def analyze_payment_method_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze payment method patterns and dependencies"""
    
    analysis = {}
    
    # 1. Card brand analysis
    if 'bin_brand' in df.columns and 'is_successful' in df.columns:
        card_brand_analysis = df.groupby('bin_brand').agg({
            'is_successful': ['mean', 'count', 'sum'],
            'amount': ['mean', 'sum', 'std'] if 'amount' in df.columns else ['count'],
            'processing_time': ['mean', 'std'] if 'processing_time' in df.columns else ['count']
        }).round(3)
        analysis['card_brand_analysis'] = card_brand_analysis
    
    # 2. Card type analysis
    if 'bin_card_type' in df.columns and 'is_successful' in df.columns:
        card_type_analysis = df.groupby('bin_card_type').agg({
            'is_successful': ['mean', 'count'],
            'amount': ['mean', 'sum'] if 'amount' in df.columns else ['count']
        }).round(3)
        analysis['card_type_analysis'] = card_type_analysis
    
    # 3. Card number pattern analysis
    if 'card_last4' in df.columns:
        # Analyze last 4 digits patterns
        df['last4_pattern'] = df['card_last4'].astype(str).str[-4:].str.isdigit()
        pattern_analysis = df.groupby('last4_pattern').agg({
            'is_successful': ['mean', 'count'] if 'is_successful' in df.columns else ['count']
        }).round(3)
        analysis['card_pattern_analysis'] = pattern_analysis
    
    # 4. Payment method by country
    if 'billing_country' in df.columns and 'bin_brand' in df.columns:
        country_card_analysis = df.groupby(['billing_country', 'bin_brand']).agg({
            'is_successful': ['mean', 'count'],
            'amount': ['mean', 'sum'] if 'amount' in df.columns else ['count']
        }).round(3)
        analysis['country_card_analysis'] = country_card_analysis
    
    return analysis

def analyze_user_risk_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """Create comprehensive user risk profiles based on multiple factors"""
    
    if 'user_email' not in df.columns:
        return pd.DataFrame()
    
    risk_factors = []
    
    for user in df['user_email'].unique():
        user_df = df[df['user_email'] == user]
        
        risk_score = 0
        risk_factors_list = []
        
        # 1. Transaction volume risk
        if len(user_df) > 10:
            risk_score += 2
            risk_factors_list.append('High Transaction Volume')
        
        # 2. Success rate risk
        if 'is_successful' in user_df.columns:
            success_rate = user_df['is_successful'].mean()
            if success_rate < 0.5:
                risk_score += 3
                risk_factors_list.append('Low Success Rate')
            elif success_rate < 0.8:
                risk_score += 1
                risk_factors_list.append('Moderate Success Rate')
        
        # 3. Geographic risk
        if 'geo_mismatch' in user_df.columns:
            mismatch_count = user_df['geo_mismatch'].sum()
            if mismatch_count > 0:
                risk_score += mismatch_count
                risk_factors_list.append(f'Geographic Mismatches ({mismatch_count})')
        
        # 4. Amount risk
        if 'amount' in user_df.columns:
            amount_std = user_df['amount'].std()
            amount_mean = user_df['amount'].mean()
            if amount_std > amount_mean * 2:  # High variance
                risk_score += 2
                risk_factors_list.append('High Amount Variance')
            
            # Suspicious amounts
            suspicious_amounts = user_df[user_df['amount'].isin([470, 496, 1878, 1978, 2000, 2313, 2420, 5000])]
            if len(suspicious_amounts) > 0:
                risk_score += len(suspicious_amounts)
                risk_factors_list.append(f'Suspicious Amounts ({len(suspicious_amounts)})')
        
        # 5. Time-based risk
        if 'created_at' in user_df.columns:
            user_df_sorted = user_df.sort_values('created_at')
            if len(user_df_sorted) > 1:
                time_span = (user_df_sorted['created_at'].max() - user_df_sorted['created_at'].min()).total_seconds() / 3600
                if time_span < 24 and len(user_df) > 5:  # High velocity
                    risk_score += 3
                    risk_factors_list.append('High Transaction Velocity')
        
        # 6. Device diversity risk
        if 'device_os' in user_df.columns:
            device_count = user_df['device_os'].nunique()
            if device_count > 3:
                risk_score += 1
                risk_factors_list.append('Multiple Devices')
        
        # 7. Browser diversity risk
        if 'user_agent' in user_df.columns:
            browser_count = user_df['user_agent'].nunique()
            if browser_count > 3:
                risk_score += 1
                risk_factors_list.append('Multiple Browsers')
        
        # Compile risk profile
        risk_profile = {
            'user_email': user,
            'total_transactions': len(user_df),
            'risk_score': risk_score,
            'risk_level': 'Low' if risk_score < 3 else 'Medium' if risk_score < 7 else 'High',
            'risk_factors': '; '.join(risk_factors_list),
            'success_rate': user_df['is_successful'].mean() if 'is_successful' in user_df.columns else 0,
            'total_amount': user_df['amount'].sum() if 'amount' in user_df.columns else 0,
            'avg_amount': user_df['amount'].mean() if 'amount' in user_df.columns else 0
        }
        
        risk_factors.append(risk_profile)
    
    return pd.DataFrame(risk_factors).sort_values('risk_score', ascending=False)

def generate_insights_report(analyses: Dict[str, Any]) -> str:
    """Generate human-readable insights report from all analyses"""
    
    report = []
    report.append("# 🔍 Payment Analysis Insights Report")
    report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # 1. Overall Performance Insights
    if 'success_analysis' in analyses:
        success_data = analyses['success_analysis']
        if 'overall_success_rate' in success_data:
            success_rate = success_data['overall_success_rate']
            report.append("## 📊 Overall Performance")
            report.append(f"- **Success Rate**: {success_rate:.2%}")
            
            if success_rate < 0.7:
                report.append("  - ⚠️ **Critical Issue**: Success rate below 70% requires immediate attention")
            elif success_rate < 0.85:
                report.append("  - ⚠️ **Warning**: Success rate below 85% indicates potential issues")
            else:
                report.append("  - ✅ **Good**: Success rate above 85%")
    
    # 2. Geographic Insights
    if 'geo_analysis' in analyses:
        geo_data = analyses['geo_analysis']
        if 'mismatch_success' in geo_data:
            mismatch_data = geo_data['mismatch_success']
            if len(mismatch_data) > 1:
                geo_match_success = mismatch_data.loc[False, ('is_successful', 'mean')] if False in mismatch_data.index else 0
                geo_mismatch_success = mismatch_data.loc[True, ('is_successful', 'mean')] if True in mismatch_data.index else 0
                
                report.append("")
                report.append("## 🌍 Geographic Insights")
                report.append(f"- **Geographic Match Success**: {geo_match_success:.2%}")
                report.append(f"- **Geographic Mismatch Success**: {geo_mismatch_success:.2%}")
                
                if geo_mismatch_success < geo_match_success * 0.8:
                    report.append("  - ⚠️ **Risk**: Geographic mismatches significantly reduce success rates")
    
    # 3. User Behavior Insights
    if 'behavior_analysis' in analyses:
        behavior_data = analyses['behavior_analysis']
        if 'retry_patterns' in behavior_data and behavior_data['retry_patterns'] is not None:
            retry_data = behavior_data['retry_patterns']
            if len(retry_data) > 0:
                avg_retry_time = retry_data['avg_retry_time'].mean()
                report.append("")
                report.append("## 👤 User Behavior Insights")
                report.append(f"- **Average Retry Time**: {avg_retry_time:.1f} minutes")
                
                if avg_retry_time < 5:
                    report.append("  - ⚠️ **Risk**: Very quick retries may indicate automated attacks")
                elif avg_retry_time > 60:
                    report.append("  - ℹ️ **Info**: Users take time to retry, may indicate genuine issues")
    
    # 4. Technical Infrastructure Insights
    if 'tech_analysis' in analyses:
        tech_data = analyses['tech_analysis']
        if 'processing_times' in tech_data:
            processing_data = tech_data['processing_times']
            if len(processing_data) > 0:
                avg_processing = processing_data[('processing_time', 'mean')].mean()
                report.append("")
                report.append("## 🔧 Technical Infrastructure Insights")
                report.append(f"- **Average Processing Time**: {avg_processing:.2f} seconds")
                
                if avg_processing > 30:
                    report.append("  - ⚠️ **Performance Issue**: Processing times above 30 seconds")
                elif avg_processing > 10:
                    report.append("  - ⚠️ **Warning**: Processing times above 10 seconds")
    
    # 5. Recommendations
    report.append("")
    report.append("## 💡 Recommendations")
    
    # Add specific recommendations based on findings
    if 'success_analysis' in analyses:
        success_data = analyses['success_analysis']
        if 'gateway_success' in success_data:
            gateway_data = success_data['gateway_success']
            worst_gateway = gateway_data[('is_successful', 'mean')].idxmin()
            worst_rate = gateway_data.loc[worst_gateway, ('is_successful', 'mean')]
            
            if worst_rate < 0.7:
                report.append(f"- **Immediate Action**: Investigate {worst_gateway} gateway (success rate: {worst_rate:.2%})")
    
    if 'fraud_analysis' in analyses:
        fraud_data = analyses['fraud_analysis']
        if 'high_velocity_users' in fraud_data:
            high_vel_count = len(fraud_data['high_velocity_users'])
            if high_vel_count > 0:
                report.append(f"- **Fraud Monitoring**: {high_vel_count} users with high transaction velocity")
    
    report.append("")
    report.append("---")
    report.append("*Report generated automatically by Comprehensive Payment Analysis Dashboard*")
    
    return "\n".join(report)

# ---------- Utility Functions ----------

def export_analysis_results(analyses: Dict[str, Any], output_dir: str = "./") -> Dict[str, str]:
    """Export all analysis results to various formats"""
    
    export_files = {}
    
    for analysis_name, analysis_data in analyses.items():
        if analysis_data is not None and not isinstance(analysis_data, str):
            try:
                # Export to CSV
                if isinstance(analysis_data, pd.DataFrame):
                    csv_filename = f"{output_dir}{analysis_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    analysis_data.to_csv(csv_filename, index=True)
                    export_files[f"{analysis_name}_csv"] = csv_filename
                
                # Export to JSON
                if isinstance(analysis_data, pd.DataFrame):
                    json_filename = f"{output_dir}{analysis_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    analysis_data.to_json(json_filename, orient='records', indent=2)
                    export_files[f"{analysis_name}_json"] = json_filename
                
            except Exception as e:
                print(f"Error exporting {analysis_name}: {e}")
    
    return export_files

def validate_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate data quality and completeness"""
    
    validation = {}
    
    # 1. Basic data info
    validation['total_rows'] = len(df)
    validation['total_columns'] = len(df.columns)
    
    # 2. Missing data analysis
    missing_data = df.isnull().sum()
    missing_percentage = (missing_data / len(df)) * 100
    
    validation['missing_data'] = missing_data
    validation['missing_percentage'] = missing_percentage
    
    # 3. Data types
    validation['data_types'] = df.dtypes.value_counts()
    
    # 4. Duplicate analysis
    validation['duplicate_rows'] = df.duplicated().sum()
    validation['duplicate_percentage'] = (validation['duplicate_rows'] / len(df)) * 100
    
    # 5. Column completeness
    completeness = {}
    for col in df.columns:
        completeness[col] = {
            'non_null_count': df[col].notna().sum(),
            'null_count': df[col].isna().sum(),
            'completeness_percentage': (df[col].notna().sum() / len(df)) * 100
        }
    validation['column_completeness'] = completeness
    
    # 6. Data quality score
    overall_completeness = (df.notna().sum().sum() / (len(df) * len(df.columns))) * 100
    validation['overall_quality_score'] = overall_completeness
    
    return validation

def run_advanced_analytics(df: pd.DataFrame) -> Dict[str, Any]:
    """Main function to run all advanced analytics"""
    
    analytics_results = {}
    
    try:
        # 1. Temporal patterns
        if 'created_at' in df.columns:
            analytics_results['temporal_patterns'] = detect_temporal_patterns(df)
        
        # 2. Anomaly detection
        numerical_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        if numerical_columns:
            df_with_anomalies = calculate_anomaly_scores(df, numerical_columns)
            anomaly_columns = [col for col in df_with_anomalies.columns if 'anomaly_score' in col]
            if anomaly_columns:
                # Get transactions with high anomaly scores
                high_anomaly_threshold = 2.0  # Z-score > 2
                high_anomalies = df_with_anomalies[df_with_anomalies[anomaly_columns].max(axis=1) > high_anomaly_threshold]
                analytics_results['anomaly_detection'] = high_anomalies
        
        # 3. User risk profiles
        if 'user_email' in df.columns:
            user_risk = analyze_transaction_sequences(df)
            if user_risk:
                analytics_results['user_risk_profiles'] = user_risk
        
        # 4. Data quality metrics
        analytics_results['data_quality_metrics'] = validate_data_quality(df)
        
        # 5. Statistical summary
        if 'amount' in df.columns:
            amount_stats = {
                'mean': df['amount'].mean(),
                'median': df['amount'].median(),
                'std': df['amount'].std(),
                'min': df['amount'].min(),
                'max': df['amount'].max(),
                'skewness': df['amount'].skew(),
                'kurtosis': df['amount'].kurtosis()
            }
            analytics_results['amount_statistics'] = amount_stats
        
        # 6. Success rate analysis
        if 'is_successful' in df.columns:
            success_analysis = {
                'overall_success_rate': df['is_successful'].mean(),
                'success_by_amount_bin': pd.cut(df['amount'], bins=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High']).value_counts().sort_index() if 'amount' in df.columns else None
            }
            analytics_results['success_analysis'] = success_analysis
        
    except Exception as e:
        print(f"Error in advanced analytics: {e}")
        analytics_results['error'] = str(e)
    
    return analytics_results
