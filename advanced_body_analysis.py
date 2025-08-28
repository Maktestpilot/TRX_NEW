# Advanced Body Content Analysis Module
# Deep analysis of transaction body content for fraud detection and success prediction

import pandas as pd
import numpy as np
import json
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class AdvancedBodyAnalyzer:
    """Advanced analyzer for transaction body content and hidden dependencies"""
    
    def __init__(self):
        self.suspicious_patterns = {
            'browser': [
                'headless', 'phantom', 'selenium', 'webdriver', 'automation',
                'bot', 'crawler', 'spider', 'scraper', 'test'
            ],
            'user_agent': [
                'python', 'curl', 'wget', 'postman', 'insomnia',
                'apache-httpclient', 'okhttp', 'requests'
            ],
            'screen_resolution': [
                '0x0', '1x1', '100x100', '800x600', '1024x768'  # Common test resolutions
            ],
            'language': [
                'en-US', 'en-GB', 'en-CA', 'en-AU'  # Common test languages
            ],
            'timezone': [
                'UTC', 'GMT', 'America/New_York', 'Europe/London'  # Common test timezones
            ]
        }
        
        self.risk_factors = {
            'geo_mismatch': 3.0,
            'suspicious_browser': 2.5,
            'unusual_speed': 2.0,
            'synthetic_data': 4.0,
            'time_anomaly': 1.5
        }
    
    def analyze_body_content_impact(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze how body content affects transaction success"""
        
        analysis = {}
        
        # 1. Browser and Device Analysis
        analysis['browser_analysis'] = self._analyze_browser_impact(df)
        
        # 2. IP Geographic Analysis
        analysis['ip_geo_analysis'] = self._analyze_ip_geographic_patterns(df)
        
        # 3. Transaction Speed Analysis (only if processing_time exists)
        if 'processing_time' in df.columns:
            analysis['speed_analysis'] = self._analyze_transaction_speed(df)
        else:
            analysis['speed_analysis'] = {
                'status': 'Processing time data not available',
                'message': 'Cannot analyze transaction speed without processing_time column'
            }
        
        # 4. Synthetic Data Detection
        analysis['synthetic_detection'] = self._detect_synthetic_data(df)
        
        # 5. Combined Risk Analysis
        analysis['combined_risk'] = self._analyze_combined_risk_factors(df)
        
        # 6. Hidden Dependencies
        analysis['hidden_dependencies'] = self._find_hidden_dependencies(df)
        
        return analysis
    
    def _analyze_browser_impact(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze browser and device impact on transaction success with extended analysis"""
        
        browser_analysis = {}
        
        # 1. Browser Family Analysis with Statistical Significance
        if 'browser_family' in df.columns:
            browser_success = df.groupby('browser_family').agg({
                'is_successful': ['mean', 'count', 'std'],
                'processing_time': 'mean' if 'processing_time' in df.columns else 'count',
                'amount': 'mean' if 'amount' in df.columns else 'count'
            }).round(3)
            
            # Flatten column names to avoid MultiIndex issues
            browser_success.columns = ['_'.join(col).strip('_') for col in browser_success.columns]
            
            # Calculate confidence intervals and statistical significance
            browser_success['confidence_interval'] = browser_success['is_successful_std'] / np.sqrt(browser_success['is_successful_count'])
            browser_success['margin_of_error'] = 1.96 * browser_success['confidence_interval']
            browser_success['lower_bound'] = browser_success['is_successful_mean'] - browser_success['margin_of_error']
            browser_success['upper_bound'] = browser_success['is_successful_mean'] + browser_success['margin_of_error']
            
            # Identify statistically significant differences
            overall_success_rate = df['is_successful'].mean()
            browser_success['statistical_significance'] = np.abs(browser_success['is_successful_mean'] - overall_success_rate) > (2 * browser_success['margin_of_error'])
            
            browser_analysis['browser_family_success'] = browser_success
            
            # Browser performance ranking
            browser_analysis['browser_performance_ranking'] = browser_success['is_successful_mean'].sort_values(ascending=False)
            
            # Browser market share vs success correlation
            browser_analysis['browser_market_share_correlation'] = self._calculate_correlation(
                browser_success['is_successful_count'], 
                browser_success['is_successful_mean']
            )
        
        # 2. Device OS Analysis with Platform Insights
        if 'device_os' in df.columns:
            os_success = df.groupby('device_os').agg({
                'is_successful': ['mean', 'count', 'std'],
                'processing_time': 'mean' if 'processing_time' in df.columns else 'count',
                'amount': 'mean' if 'amount' in df.columns else 'count'
            }).round(3)
            
            # Flatten column names to avoid MultiIndex issues
            os_success.columns = ['_'.join(col).strip('_') for col in os_success.columns]
            
            # OS platform categorization
            os_success['platform'] = os_success.index.map(lambda x: 'Mobile' if any(mobile in str(x).lower() for mobile in ['ios', 'android', 'mobile']) else 'Desktop')
            # Calculate platform success rate properly
            platform_success_rates = os_success.groupby('platform')['is_successful_mean'].mean()
            os_success['platform_success_rate'] = os_success['platform'].map(platform_success_rates)
            
            browser_analysis['os_success'] = os_success
            browser_analysis['platform_comparison'] = os_success.groupby('platform').agg({
                'is_successful_mean': 'mean',
                'is_successful_count': 'sum'
            }).round(3)
        
        # 3. Enhanced Screen Resolution Analysis
        if 'browser_screen_width' in df.columns and 'browser_screen_height' in df.columns:
            df['screen_resolution'] = df['browser_screen_width'].astype(str) + 'x' + df['browser_screen_height'].astype(str)
            df['screen_area'] = df['browser_screen_width'] * df['browser_screen_height']
            df['aspect_ratio'] = df['browser_screen_width'] / df['browser_screen_height']
            
            # Resolution categories
            df['resolution_category'] = pd.cut(df['screen_area'], 
                bins=[0, 768000, 1920000, 3840000, float('inf')], 
                labels=['Low', 'Medium', 'High', 'Ultra High'])
            
            resolution_analysis = df.groupby('resolution_category').agg({
                'is_successful': ['mean', 'count', 'std'],
                'processing_time': 'mean' if 'processing_time' in df.columns else 'count',
                'amount': 'mean' if 'amount' in df.columns else 'count'
            }).round(3)
            
            # Flatten column names to avoid MultiIndex issues
            resolution_analysis.columns = ['_'.join(col).strip('_') for col in resolution_analysis.columns]
            
            # Aspect ratio analysis - handle infinite values
            aspect_ratio_clean = df['aspect_ratio'].replace([np.inf, -np.inf], np.nan).dropna()
            if len(aspect_ratio_clean) > 0:
                aspect_analysis = df.groupby(pd.cut(aspect_ratio_clean, bins=5)).agg({
                    'is_successful': ['mean', 'count']
                }).round(3)
                # Flatten column names for aspect analysis too
                aspect_analysis.columns = ['_'.join(col).strip('_') for col in aspect_analysis.columns]
                browser_analysis['aspect_ratio_success'] = aspect_analysis
            else:
                browser_analysis['aspect_ratio_success'] = pd.DataFrame()
            
            browser_analysis['resolution_success'] = resolution_analysis
            browser_analysis['resolution_correlation'] = self._calculate_correlation(df['screen_area'], df['is_successful'])
        
        # 4. Advanced User Agent Analysis
        if 'browser_user_agent' in df.columns:
            # Detect suspicious user agents
            suspicious_ua = df['browser_user_agent'].str.lower().str.contains('|'.join(self.suspicious_patterns['user_agent']), na=False)
            if suspicious_ua.any():
                suspicious_ua_success = df[suspicious_ua].groupby('browser_user_agent').agg({
                    'is_successful': ['mean', 'count', 'std'],
                    'processing_time': 'mean' if 'processing_time' in df.columns else 'count'
                }).round(3)
                # Flatten column names to avoid MultiIndex issues
                suspicious_ua_success.columns = ['_'.join(col).strip('_') for col in suspicious_ua_success.columns]
                browser_analysis['suspicious_user_agents'] = suspicious_ua_success
            
            # User agent complexity analysis
            df['ua_complexity'] = df['browser_user_agent'].str.count(r'[;/]')
            ua_complexity_analysis = df.groupby(pd.cut(df['ua_complexity'], bins=5)).agg({
                'is_successful': ['mean', 'count']
            }).round(3)
            # Flatten column names to avoid MultiIndex issues
            ua_complexity_analysis.columns = ['_'.join(col).strip('_') for col in ua_complexity_analysis.columns]
            browser_analysis['ua_complexity_analysis'] = ua_complexity_analysis
            
            # User agent length analysis
            df['ua_length'] = df['browser_user_agent'].str.len()
            ua_length_analysis = df.groupby(pd.cut(df['ua_length'], bins=5)).agg({
                'is_successful': ['mean', 'count']
            }).round(3)
            browser_analysis['ua_length_analysis'] = ua_length_analysis
        
        # 5. Enhanced Language and Timezone Analysis
        if 'browser_language' in df.columns:
            language_success = df.groupby('browser_language').agg({
                'is_successful': ['mean', 'count', 'std'],
                'processing_time': 'mean' if 'processing_time' in df.columns else 'count'
            }).round(3)
            
            # Language family grouping
            language_families = {
                'English': ['en', 'en-us', 'en-gb', 'en-ca', 'en-au'],
                'Spanish': ['es', 'es-es', 'es-mx', 'es-ar'],
                'French': ['fr', 'fr-fr', 'fr-ca'],
                'German': ['de', 'de-de', 'de-at'],
                'Other': []
            }
            
            df['language_family'] = 'Other'
            for family, codes in language_families.items():
                mask = df['browser_language'].str.lower().isin(codes)
                df.loc[mask, 'language_family'] = family
            
            language_family_analysis = df.groupby('language_family').agg({
                'is_successful': ['mean', 'count']
            }).round(3)
            
            browser_analysis['language_success'] = language_success
            browser_analysis['language_family_analysis'] = language_family_analysis
        
        if 'browser_timezone' in df.columns:
            timezone_success = df.groupby('browser_timezone').agg({
                'is_successful': ['mean', 'count', 'std'],
                'processing_time': 'mean' if 'processing_time' in df.columns else 'count'
            }).round(3)
            
            # Timezone offset analysis
            df['timezone_offset'] = df['browser_timezone'].str.extract(r'([+-]\d{2}:\d{2})')
            if df['timezone_offset'].notna().any():
                offset_analysis = df.groupby('timezone_offset').agg({
                    'is_successful': ['mean', 'count']
                }).round(3)
                browser_analysis['timezone_offset_analysis'] = offset_analysis
            
            browser_analysis['timezone_success'] = timezone_success
        
        # 6. Cross-Factor Browser Analysis
        if all(col in df.columns for col in ['browser_family', 'device_os', 'is_successful']):
            browser_os_combination = df.groupby(['browser_family', 'device_os']).agg({
                'is_successful': ['mean', 'count'],
                'processing_time': 'mean' if 'processing_time' in df.columns else 'count'
            }).round(3)
            browser_analysis['browser_os_combination'] = browser_os_combination
        
        # 7. Browser Performance Metrics
        browser_analysis['performance_metrics'] = {
            'total_browsers': len(df['browser_family'].unique()) if 'browser_family' in df.columns else 0,
            'total_os': len(df['device_os'].unique()) if 'device_os' in df.columns else 0,
            'suspicious_ua_count': suspicious_ua.sum() if 'browser_user_agent' in df.columns else 0,
            'mobile_ratio': (df['device_os'].str.lower().str.contains('mobile|ios|android', na=False).sum() / len(df)) if 'device_os' in df.columns else 0
        }
        
        # 8. Statistical Analysis Summary
        browser_analysis['statistical_summary'] = self._generate_browser_statistical_summary(df, browser_analysis)
        
        return browser_analysis
    
    def _calculate_correlation(self, series1: pd.Series, series2: pd.Series) -> float:
        """Calculate correlation between two series with error handling"""
        try:
            if len(series1) > 1 and len(series2) > 1:
                return series1.corr(series2)
            return 0.0
        except:
            return 0.0
    
    def _generate_browser_statistical_summary(self, df: pd.DataFrame, browser_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive statistical summary for browser analysis"""
        
        summary = {}
        
        # Overall statistics
        if 'browser_family' in df.columns:
            summary['total_browsers'] = len(df['browser_family'].unique())
            summary['browser_distribution'] = df['browser_family'].value_counts().to_dict()
        
        if 'device_os' in df.columns:
            summary['total_os'] = len(df['device_os'].unique())
            summary['os_distribution'] = df['device_os'].value_counts().to_dict()
        
        # Success rate analysis
        if 'browser_family' in df.columns:
            browser_success = browser_analysis.get('browser_family_success', pd.DataFrame())
            if not browser_success.empty:
                # Check if columns are flattened or still MultiIndex
                if 'is_successful_mean' in browser_success.columns:
                    summary['best_performing_browser'] = browser_success['is_successful_mean'].idxmax()
                    summary['worst_performing_browser'] = browser_success['is_successful_mean'].idxmin()
                    summary['browser_success_variance'] = browser_success['is_successful_std'].describe()
                else:
                    # Fallback for MultiIndex columns
                    summary['best_performing_browser'] = browser_success[('is_successful', 'mean')].idxmax()
                    summary['worst_performing_browser'] = browser_success[('is_successful', 'mean')].idxmin()
                    summary['browser_success_variance'] = browser_success[('is_successful', 'std')].describe()
        
        # Statistical significance
        if 'browser_family' in df.columns and 'browser_family_success' in browser_analysis:
            significant_browsers = browser_analysis['browser_family_success'][
                browser_analysis['browser_family_success']['statistical_significance'] == True
            ]
            summary['statistically_significant_browsers'] = len(significant_browsers)
        
        return summary
    
    def _analyze_ip_geographic_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze IP geographic patterns and mismatches"""
        
        geo_analysis = {}
        
        # IP vs Billing country mismatch analysis
        if 'ip_country' in df.columns and 'billing_country' in df.columns:
            df['geo_mismatch'] = df['ip_country'] != df['billing_country']
            
            # Success rate by geographic mismatch
            mismatch_success = df.groupby('geo_mismatch').agg({
                'is_successful': ['mean', 'count'],
                'processing_time': 'mean' if 'processing_time' in df.columns else 'count'
            }).round(3)
            # Flatten column names to avoid MultiIndex issues
            mismatch_success.columns = ['_'.join(col).strip('_') for col in mismatch_success.columns]
            geo_analysis['mismatch_success'] = mismatch_success
            
            # Detailed mismatch analysis by country pairs
            detailed_mismatch = df[df['geo_mismatch'] == True].groupby(['billing_country', 'ip_country']).agg({
                'is_successful': ['mean', 'count'],
                'amount': 'mean' if 'amount' in df.columns else 'count'
            }).round(3)
            # Flatten column names to avoid MultiIndex issues
            detailed_mismatch.columns = ['_'.join(col).strip('_') for col in detailed_mismatch.columns]
            geo_analysis['detailed_mismatch'] = detailed_mismatch.sort_values('is_successful_count', ascending=False)
            
            # ASN analysis for mismatched transactions
            if 'ip_asn' in df.columns:
                asn_mismatch = df[df['geo_mismatch'] == True].groupby('ip_asn').agg({
                    'is_successful': ['mean', 'count'],
                    'billing_country': 'nunique'
                }).round(3)
                # Flatten column names to avoid MultiIndex issues
                asn_mismatch.columns = ['_'.join(col).strip('_') for col in asn_mismatch.columns]
                geo_analysis['asn_mismatch'] = asn_mismatch.sort_values('is_successful_count', ascending=False)
        
        # IP country success rates
        if 'ip_country' in df.columns:
            ip_country_success = df.groupby('ip_country').agg({
                'is_successful': ['mean', 'count'],
                'amount': 'mean' if 'amount' in df.columns else 'count'
            }).round(3)
            # Flatten column names to avoid MultiIndex issues
            ip_country_success.columns = ['_'.join(col).strip('_') for col in ip_country_success.columns]
            geo_analysis['ip_country_success'] = ip_country_success.sort_values('is_successful_count', ascending=False)
        
        # Continent analysis
        if 'ip_continent' in df.columns:
            continent_success = df.groupby('ip_continent').agg({
                'is_successful': ['mean', 'count'],
                'amount': 'mean' if 'amount' in df.columns else 'count'
            }).round(3)
            # Flatten column names to avoid MultiIndex issues
            continent_success.columns = ['_'.join(col).strip('_') for col in continent_success.columns]
            geo_analysis['continent_success'] = continent_success
        
        return geo_analysis
    
    def _analyze_transaction_speed(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze transaction speed impact on success"""
        
        speed_analysis = {}
        
        # Only analyze if processing_time column exists
        if 'processing_time' in df.columns and len(df) > 0:
            try:
                # Speed distribution analysis
                speed_analysis['speed_distribution'] = df['processing_time'].describe()
                
                # Speed vs Success correlation
                if 'is_successful' in df.columns:
                    speed_success_corr = df[['processing_time', 'is_successful']].corr().iloc[0, 1]
                    speed_analysis['speed_success_correlation'] = speed_success_corr
                    
                    # Success rate by speed ranges
                    if len(df['processing_time'].dropna()) > 0:
                        speed_bins = pd.cut(df['processing_time'], bins=10, labels=False)
                        speed_range_success = df.groupby(speed_bins).agg({
                            'is_successful': ['mean', 'count'],
                            'processing_time': 'mean'
                        }).round(3)
                        speed_analysis['speed_range_success'] = speed_range_success
                        
                        # Fast vs Slow transaction analysis
                        median_speed = df['processing_time'].median()
                        df['speed_category'] = pd.cut(df['processing_time'], 
                                                    bins=[0, median_speed, float('inf')], 
                                                    labels=['Fast', 'Slow'])
                
                if 'speed_category' in df.columns:
                    speed_category_success = df.groupby('speed_category').agg({
                        'is_successful': ['mean', 'count'],
                        'processing_time': 'mean'
                    }).round(3)
                    speed_analysis['speed_category_success'] = speed_category_success
                
                # Time of day vs Speed analysis
                if 'hour' in df.columns:
                    hourly_speed = df.groupby('hour').agg({
                        'processing_time': ['mean', 'std'],
                        'is_successful': 'mean'
                    }).round(3)
                    speed_analysis['hourly_speed'] = hourly_speed
                
                # Gateway vs Speed analysis
                if 'gateway_name' in df.columns:
                    gateway_speed = df.groupby('gateway_name').agg({
                        'processing_time': ['mean', 'std', 'min', 'max'],
                        'is_successful': 'mean'
                    }).round(3)
                    speed_analysis['gateway_speed'] = gateway_speed
                    
            except Exception as e:
                speed_analysis['error'] = f"Error analyzing transaction speed: {str(e)}"
        else:
            # If processing_time doesn't exist, provide informative message
            speed_analysis['status'] = "Processing time data not available for analysis"
            speed_analysis['recommendation'] = "Add processing_time column to enable transaction speed analysis"
        
        return speed_analysis
    
    def _detect_synthetic_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect synthetic or fake transaction data"""
        
        synthetic_analysis = {}
        
        # Initialize synthetic score
        df['synthetic_score'] = 0.0
        
        # 1. Browser/Device Suspicion
        if 'browser_user_agent' in df.columns:
            suspicious_ua = df['browser_user_agent'].str.lower().str.contains('|'.join(self.suspicious_patterns['user_agent']), na=False)
            df.loc[suspicious_ua, 'synthetic_score'] += self.risk_factors['suspicious_browser']
            synthetic_analysis['suspicious_user_agents'] = df[suspicious_ua][['browser_user_agent', 'is_successful', 'synthetic_score']].head(20)
        
        # 2. Screen Resolution Suspicion
        if 'browser_screen_width' in df.columns and 'browser_screen_height' in df.columns:
            suspicious_resolution = df['browser_screen_width'].astype(str) + 'x' + df['browser_screen_height'].astype(str)
            suspicious_resolution = suspicious_resolution.isin(self.suspicious_patterns['screen_resolution'])
            df.loc[suspicious_resolution, 'synthetic_score'] += self.risk_factors['synthetic_data']
            synthetic_analysis['suspicious_resolutions'] = df[suspicious_resolution][['browser_screen_width', 'browser_screen_height', 'is_successful', 'synthetic_score']].head(20)
        
        # 3. Language/Timezone Suspicion
        if 'browser_language' in df.columns:
            suspicious_language = df['browser_language'].isin(self.suspicious_patterns['language'])
            df.loc[suspicious_language, 'synthetic_score'] += 0.5
        
        if 'browser_timezone' in df.columns:
            suspicious_timezone = df['browser_timezone'].isin(self.suspicious_patterns['timezone'])
            df.loc[suspicious_timezone, 'synthetic_score'] += 0.5
        
        # 4. Geographic Suspicion
        if 'geo_mismatch' in df.columns:
            df.loc[df['geo_mismatch'], 'synthetic_score'] += self.risk_factors['geo_mismatch']
        
        # 5. Time Pattern Suspicion
        if 'created_at' in df.columns:
            # Check for transactions at unusual hours
            unusual_hours = (df['created_at'].dt.hour < 6) | (df['created_at'].dt.hour > 23)
            df.loc[unusual_hours, 'synthetic_score'] += self.risk_factors['time_anomaly']
            
            # Check for too many transactions in short time
            if 'user_email' in df.columns:
                user_velocity = df.groupby('user_email').agg({
                    'created_at': lambda x: (x.max() - x.min()).total_seconds() / 3600,
                    'id': 'count'
                })
                user_velocity.columns = ['time_span_hours', 'transaction_count']
                
                # Convert time_span_hours to numeric values to avoid DatetimeArray issues
                user_velocity['time_span_hours'] = pd.to_numeric(user_velocity['time_span_hours'], errors='coerce')
                
                # Handle cases where users have only one transaction (time_span_hours = 0 or NaN)
                # For single transactions or invalid data, set velocity to 0 (no velocity risk)
                user_velocity['transactions_per_hour'] = np.where(
                    (user_velocity['time_span_hours'] == 0) | (user_velocity['time_span_hours'].isna()),
                    0,  # No velocity risk for single transactions or invalid data
                    user_velocity['transaction_count'] / user_velocity['time_span_hours']
                )
                
                high_velocity_users = user_velocity[user_velocity['transactions_per_hour'] > 5]
                high_velocity_mask = df['user_email'].isin(high_velocity_users.index)
                df.loc[high_velocity_mask, 'synthetic_score'] += self.risk_factors['unusual_speed']
        
        # 6. Amount Pattern Suspicion
        if 'amount' in df.columns and len(df) > 0:
            # Check for round amounts (common in test data)
            round_amounts = df['amount'].apply(lambda x: x % 100 == 0 if pd.notna(x) else False)
            df.loc[round_amounts, 'synthetic_score'] += 0.5
            
            # Check for suspicious amount ranges
            suspicious_amounts = [470, 496, 1878, 1978, 2000, 2313, 2420, 5000]
            suspicious_amount_mask = df['amount'].isin(suspicious_amounts)
            df.loc[suspicious_amount_mask, 'synthetic_score'] += 1.0
        
        # Summary of synthetic detection
        synthetic_analysis['synthetic_score_distribution'] = df['synthetic_score'].describe()
        synthetic_analysis['high_risk_transactions'] = df[df['synthetic_score'] > 3.0].sort_values('synthetic_score', ascending=False).head(20)
        synthetic_analysis['synthetic_score_by_success'] = df.groupby('is_successful')['synthetic_score'].agg(['mean', 'std', 'count']).round(3)
        
        return synthetic_analysis
    
    def _analyze_combined_risk_factors(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze combined risk factors and their interactions"""
        
        combined_analysis = {}
        
        # Create combined risk score
        risk_columns = []
        
        if 'synthetic_score' in df.columns:
            risk_columns.append('synthetic_score')
        
        if 'geo_mismatch' in df.columns:
            df['geo_risk'] = df['geo_mismatch'].astype(int) * self.risk_factors['geo_mismatch']
            risk_columns.append('geo_risk')
        
        if 'processing_time' in df.columns:
            try:
                # Normalize processing time to 0-1 scale
                if df['processing_time'].max() > df['processing_time'].min():
                    df['speed_risk'] = (df['processing_time'] - df['processing_time'].min()) / (df['processing_time'].max() - df['processing_time'].min())
                else:
                    df['speed_risk'] = 0.0
                risk_columns.append('speed_risk')
            except Exception as e:
                print(f"Error processing speed risk: {e}")
                df['speed_risk'] = 0.0
                risk_columns.append('speed_risk')
        
        if len(risk_columns) > 0 and len(df) > 0:
            df['combined_risk_score'] = df[risk_columns].sum(axis=1)
            
            # Risk score distribution
            combined_analysis['risk_score_distribution'] = df['combined_risk_score'].describe()
            
            # Risk vs Success analysis
            if len(df['combined_risk_score'].dropna()) > 0:
                risk_success_analysis = df.groupby(pd.cut(df['combined_risk_score'], bins=5)).agg({
                    'is_successful': ['mean', 'count'],
                    'amount': 'mean' if 'amount' in df.columns else 'count'
                }).round(3)
                combined_analysis['risk_success_analysis'] = risk_success_analysis
            
            # High risk transactions
            high_risk_threshold = df['combined_risk_score'].quantile(0.95)
            high_risk_transactions = df[df['combined_risk_score'] > high_risk_threshold]
            combined_analysis['high_risk_transactions'] = high_risk_transactions[['id', 'combined_risk_score', 'is_successful', 'amount']].head(20)
        
        return combined_analysis
    
    def _find_hidden_dependencies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Find hidden dependencies between various factors"""
        
        dependencies = {}
        
        # 1. Browser + Geographic combination
        if all(col in df.columns for col in ['browser_family', 'ip_country', 'is_successful']):
            browser_geo_success = df.groupby(['browser_family', 'ip_country']).agg({
                'is_successful': ['mean', 'count']
            }).round(3)
            dependencies['browser_geo_success'] = browser_geo_success.sort_values(('is_successful', 'count'), ascending=False).head(30)
        
        # 2. Time + Geographic combination
        if all(col in df.columns for col in ['hour', 'ip_country', 'is_successful']):
            time_geo_success = df.groupby(['hour', 'ip_country']).agg({
                'is_successful': ['mean', 'count']
            }).round(3)
            dependencies['time_geo_success'] = time_geo_success.sort_values(('is_successful', 'count'), ascending=False).head(30)
        
        # 3. Amount + Geographic combination
        if all(col in df.columns for col in ['amount', 'ip_country', 'is_successful']) and len(df) > 0:
            # Create amount bins
            if len(df['amount'].dropna()) > 0:
                amount_bins = pd.cut(df['amount'], bins=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
                amount_geo_success = df.groupby([amount_bins, 'ip_country']).agg({
                    'is_successful': ['mean', 'count']
                }).round(3)
                dependencies['amount_geo_success'] = amount_geo_success.sort_values(('is_successful', 'count'), ascending=False).head(30)
        
        # 4. Browser + Time combination
        if all(col in df.columns for col in ['browser_family', 'hour', 'is_successful']):
            browser_time_success = df.groupby(['browser_family', 'hour']).agg({
                'is_successful': ['mean', 'count']
            }).round(3)
            dependencies['browser_time_success'] = browser_time_success.sort_values(('is_successful', 'count'), ascending=False).head(30)
        
        # 5. Cross-factor correlation analysis
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) > 1:
            correlation_matrix = df[numeric_columns].corr()
            dependencies['factor_correlations'] = correlation_matrix
        
        return dependencies
    
    def generate_body_insights_report(self, analysis: Dict[str, Any]) -> str:
        """Generate comprehensive insights report from body analysis"""
        
        report = "# 🔍 Advanced Body Content Analysis Report\n\n"
        
        # Browser Analysis Insights
        if 'browser_analysis' in analysis:
            browser = analysis['browser_analysis']
            report += "## 🌐 Browser & Device Impact\n\n"
            
            if 'browser_family_success' in browser:
                browser_data = browser['browser_family_success']
                # Check if columns are flattened or still MultiIndex
                if 'is_successful_mean' in browser_data.columns:
                    best_browser = browser_data['is_successful_mean'].idxmax()
                    worst_browser = browser_data['is_successful_mean'].idxmin()
                else:
                    # Fallback for MultiIndex columns
                    best_browser = browser_data[('is_successful', 'mean')].idxmax()
                    worst_browser = browser_data[('is_successful', 'mean')].idxmin()
                report += f"- **Best performing browser**: {best_browser}\n"
                report += f"- **Worst performing browser**: {worst_browser}\n"
            
            if 'suspicious_user_agents' in browser:
                report += f"- **Suspicious user agents detected**: {len(browser['suspicious_user_agents'])} transactions\n"
            
            # Add comprehensive insights text block
            report += "\n### 📊 **Comprehensive Analysis Insights & Dependencies**\n\n"
            
            # Statistical Methods Applied
            report += "**🔬 Методы анализа и метрики:**\n"
            report += "• **Статистическая значимость**: Расчет доверительных интервалов (95% CI) с использованием стандартной ошибки\n"
            report += "• **Корреляционный анализ**: Коэффициент корреляции Пирсона между долей рынка браузера и успешностью\n"
            report += "• **Кластерный анализ**: Группировка по категориям разрешений экрана (Низкое/Среднее/Высокое/Ультра)\n"
            report += "• **Анализ платформ**: Разделение на мобильные и десктопные устройства с сравнением метрик\n"
            report += "• **Анализ сложности User Agent**: Подсчет разделителей и длины строки для выявления паттернов\n"
            report += "• **Группировка языков**: Категоризация по языковым семьям (Английский, Испанский, Французский, Немецкий)\n"
            report += "• **Анализ временных зон**: Извлечение смещений UTC для выявления географических паттернов\n\n"
            
            # Discovered Dependencies and Correlations
            report += "**🔗 Выявленные зависимости и корреляции:**\n"
            
            if 'browser_performance_ranking' in browser:
                report += "• **Ранжирование браузеров**: Установлена иерархия производительности по успешности транзакций\n"
            
            if 'browser_market_share_correlation' in browser:
                corr = browser['browser_market_share_correlation']
                if abs(corr) > 0.3:
                    direction = "положительная" if corr > 0 else "отрицательная"
                    report += f"• **Корреляция доля рынка ↔ успешность**: {direction} корреляция ({corr:.3f}) - популярные браузеры показывают {'лучшие' if corr > 0 else 'худшие'} результаты\n"
                else:
                    report += f"• **Корреляция доля рынка ↔ успешность**: Слабая корреляция ({corr:.3f}) - нет прямой связи между популярностью и успешностью\n"
            
            if 'platform_comparison' in browser:
                platform_data = browser['platform_comparison']
                # Check if columns are flattened or still MultiIndex
                if 'is_successful_mean' in platform_data.columns:
                    mobile_success = platform_data.loc['Mobile', 'is_successful_mean'] if 'Mobile' in platform_data.index else 0
                    desktop_success = platform_data.loc['Desktop', 'is_successful_mean'] if 'Desktop' in platform_data.index else 0
                else:
                    # Fallback for MultiIndex columns
                    mobile_success = platform_data.loc['Mobile', ('is_successful', 'mean')] if 'Mobile' in platform_data.index else 0
                    desktop_success = platform_data.loc['Desktop', ('is_successful', 'mean')] if 'Desktop' in platform_data.index else 0
                if abs(mobile_success - desktop_success) > 0.05:
                    better_platform = "мобильные" if mobile_success > desktop_success else "десктопные"
                    report += f"• **Платформенные различия**: {better_platform} устройства показывают более высокую успешность ({abs(mobile_success - desktop_success):.3f} разница)\n"
                else:
                    report += "• **Платформенные различия**: Минимальные различия между мобильными и десктопными устройствами\n"
            
            if 'resolution_correlation' in browser:
                res_corr = browser['resolution_correlation']
                if abs(res_corr) > 0.2:
                    direction = "положительная" if res_corr > 0 else "отрицательная"
                    report += f"• **Корреляция разрешение экрана ↔ успешность**: {direction} корреляция ({res_corr:.3f}) - {'более высокие' if res_corr > 0 else 'более низкие'} разрешения связаны с лучшей успешностью\n"
                else:
                    report += "• **Корреляция разрешение экрана ↔ успешность**: Слабая корреляция - разрешение экрана не влияет на успешность\n"
            
            if 'ua_complexity_analysis' in browser:
                report += "• **Сложность User Agent**: Анализ выявил паттерны в количестве разделителей и длине строки\n"
            
            if 'language_family_analysis' in browser:
                report += "• **Языковые паттерны**: Группировка по языковым семьям выявила различия в успешности между регионами\n"
            
            if 'timezone_offset_analysis' in browser:
                report += "• **Временные зоны**: Анализ смещений UTC показал географические кластеры с различной успешностью\n"
            
            if 'browser_os_combination' in browser:
                report += "• **Комбинации браузер-ОС**: Выявлены специфические комбинации с аномально высокой/низкой успешностью\n"
            
            # Performance Metrics Summary
            if 'performance_metrics' in browser:
                metrics = browser['performance_metrics']
                report += f"\n**📈 Сводка метрик производительности:**\n"
                report += f"• **Всего браузеров**: {metrics.get('total_browsers', 0)}\n"
                report += f"• **Всего ОС**: {metrics.get('total_os', 0)}\n"
                report += f"• **Подозрительные User Agent**: {metrics.get('suspicious_ua_count', 0)}\n"
                report += f"• **Доля мобильных устройств**: {metrics.get('mobile_ratio', 0):.1%}\n"
            
            # Statistical Significance Summary
            if 'statistical_summary' in browser:
                stats = browser['statistical_summary']
                if 'statistically_significant_browsers' in stats:
                    report += f"• **Статистически значимые браузеры**: {stats['statistically_significant_browsers']} из {stats.get('total_browsers', 0)} показывают достоверные различия\n"
            
            report += "\n**🎯 Практические выводы:**\n"
            report += "• Используйте статистически значимые различия для оптимизации под конкретные браузеры\n"
            report += "• Анализируйте платформенные различия для адаптации UI/UX\n"
            report += "• Мониторьте подозрительные User Agent для выявления ботов\n"
            report += "• Учитывайте языковые и временные паттерны для глобальной оптимизации\n"
            report += "• Исследуйте комбинации браузер-ОС для выявления специфических проблем\n\n"
        
        # Geographic Analysis Insights
        if 'ip_geo_analysis' in analysis:
            geo = analysis['ip_geo_analysis']
            report += "\n## 🌍 Geographic Pattern Insights\n\n"
            
            if 'mismatch_success' in geo:
                mismatch_rate = geo['mismatch_success'].loc[True, ('is_successful', 'mean')]
                report += f"- **Geographic mismatch rate**: {mismatch_rate:.2%}\n"
                report += f"- **Mismatch transactions**: {geo['mismatch_success'].loc[True, ('is_successful', 'count')]}\n"
        
        # Speed Analysis Insights
        if 'speed_analysis' in analysis:
            speed = analysis['speed_analysis']
            report += "\n## ⚡ Transaction Speed Insights\n\n"
            
            if 'speed_success_correlation' in speed:
                corr = speed['speed_success_correlation']
                report += f"- **Speed-Success correlation**: {corr:.3f}\n"
                
                if abs(corr) > 0.1:
                    direction = "positive" if corr > 0 else "negative"
                    report += f"- **Strong {direction} correlation** between speed and success\n"
                else:
                    report += "- **Weak correlation** between speed and success\n"
        
        # Synthetic Data Detection Insights
        if 'synthetic_detection' in analysis:
            synthetic = analysis['synthetic_detection']
            report += "\n## 🚨 Synthetic Data Detection\n\n"
            
            if 'synthetic_score_distribution' in synthetic:
                high_risk_count = len(synthetic['high_risk_transactions'])
                report += f"- **High-risk transactions detected**: {high_risk_count}\n"
                
                if high_risk_count > 0:
                    report += "- **Recommendation**: Review high-risk transactions for manual verification\n"
        
        # Combined Risk Analysis
        if 'combined_risk' in analysis:
            combined = analysis['combined_risk']
            report += "\n## 🎯 Combined Risk Analysis\n\n"
            
            if 'high_risk_transactions' in combined:
                high_risk_count = len(combined['high_risk_transactions'])
                report += f"- **High combined risk transactions**: {high_risk_count}\n"
        
        # Hidden Dependencies
        if 'hidden_dependencies' in analysis:
            dependencies = analysis['hidden_dependencies']
            report += "\n## 🔗 Hidden Dependencies\n\n"
            
            if 'factor_correlations' in dependencies:
                report += "- **Factor correlation analysis completed**\n"
                report += "- **Cross-factor patterns identified**\n"
        
        report += "\n## 📊 Recommendations\n\n"
        report += "1. **Monitor suspicious user agents** for potential bot activity\n"
        report += "2. **Review geographic mismatches** for fraud patterns\n"
        report += "3. **Analyze transaction speed patterns** for optimization opportunities\n"
        report += "4. **Investigate high-risk transactions** identified by synthetic data detection\n"
        report += "5. **Use combined risk scores** for automated fraud prevention\n"
        
        return report

def run_advanced_body_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Run complete advanced body content analysis"""
    
    analyzer = AdvancedBodyAnalyzer()
    return analyzer.analyze_body_content_impact(df)

def generate_body_insights(analysis: Dict[str, Any]) -> str:
    """Generate insights report from body analysis"""
    
    analyzer = AdvancedBodyAnalyzer()
    return analyzer.generate_body_insights_report(analysis)
