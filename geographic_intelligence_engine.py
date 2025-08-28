# Geographic Intelligence Engine
# Advanced geographic analysis for fraud detection and transaction pattern analysis

import pandas as pd
import numpy as np
import json
import re
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime, timedelta
import warnings
from ipinfo_bundle_geolocator import IPinfoBundleGeolocator
import logging

warnings.filterwarnings('ignore')

class GeographicIntelligenceEngine:
    """Advanced geographic analysis engine for fraud detection and transaction patterns"""
    
    def __init__(self, ipinfo_db_path: str = "ipinfo_lite.mmdb"):
        """Initialize the geographic intelligence engine"""
        self.ipinfo_db_path = ipinfo_db_path
        self.geolocator = None
        self.geographic_risk_factors = {
            'cross_border': 3.0,
            'high_risk_country': 4.0,
            'unusual_region': 2.5,
            'ip_velocity': 2.0,
            'geographic_clustering': 1.5,
            'timezone_mismatch': 2.0
        }
        
        # High-risk countries and regions (configurable)
        self.high_risk_countries = {
            'XX': 5.0,  # Example high-risk country
            'YY': 4.5,  # Example medium-risk country
        }
        
        # Suspicious geographic patterns
        self.suspicious_patterns = {
            'unusual_hours_for_region': 2.0,
            'rapid_location_changes': 3.5,
            'vpn_proxy_indicators': 2.5,
            'geographic_outliers': 2.0
        }
        
        self._initialize_geolocator()
    
    def _initialize_geolocator(self):
        """Initialize the IPinfo geolocator"""
        try:
            self.geolocator = IPinfoBundleGeolocator(self.ipinfo_db_path)
            logging.info(f"✅ IPinfo database loaded: {self.ipinfo_db_path}")
        except Exception as e:
            logging.warning(f"⚠️ Could not load IPinfo database: {e}")
            self.geolocator = None
    
    def analyze_geographic_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Comprehensive geographic analysis of transaction patterns"""
        
        analysis = {}
        
        try:
            # 1. IP Geolocation and Enrichment
            analysis['ip_geolocation'] = self._enrich_ip_geolocation(df)
            
            # 2. Geographic Transaction Patterns
            analysis['geographic_patterns'] = self._analyze_geographic_transaction_patterns(df)
            
            # 3. Suspicious Regional Activity Detection
            analysis['suspicious_regional_activity'] = self._detect_suspicious_regional_activity(df)
            
            # 4. Cross-Border Transaction Analysis
            analysis['cross_border_analysis'] = self._analyze_cross_border_transactions(df)
            
            # 5. Geographic Risk Scoring
            analysis['geographic_risk_scoring'] = self._calculate_geographic_risk_scores(df)
            
            # 6. Geographic Clustering Analysis
            analysis['geographic_clustering'] = self._analyze_geographic_clustering(df)
            
            # 7. Time-Geographic Correlation Analysis
            analysis['time_geographic_correlation'] = self._analyze_time_geographic_correlation(df)
            
        except Exception as e:
            # Fallback: create basic geographic analysis with available data
            analysis['ip_geolocation'] = {
                'status': f"Analysis failed: {str(e)}",
                'total_unique_ips': 0,
                'successful_lookups': 0,
                'failed_lookups': 0,
                'success_rate': 0.0
            }
            
            # Create basic geographic patterns if possible
            if 'ip_country' in df.columns:
                analysis['geographic_patterns'] = self._create_basic_geographic_patterns(df)
            else:
                analysis['geographic_patterns'] = {'status': 'No geographic data available'}
            
            analysis['suspicious_regional_activity'] = {'status': 'Analysis not available'}
            analysis['cross_border_analysis'] = {'status': 'Analysis not available'}
            analysis['geographic_risk_scoring'] = {'status': 'Analysis not available'}
            analysis['geographic_clustering'] = {'status': 'Analysis not available'}
            analysis['time_geographic_correlation'] = {'status': 'Analysis not available'}
        
        return analysis
    
    def _enrich_ip_geolocation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Enrich DataFrame with IP geolocation data"""
        
        geolocation_data = {}
        
        if self.geolocator is None:
            geolocation_data['status'] = "IPinfo database not available"
            return geolocation_data
        
        if 'ip_address' not in df.columns:
            geolocation_data['status'] = "No IP address column found"
            return geolocation_data
        
        # Extract unique IP addresses
        unique_ips = df['ip_address'].dropna().unique()
        geolocation_data['total_unique_ips'] = len(unique_ips)
        
        # Geolocation results storage
        ip_geo_data = {}
        successful_lookups = 0
        failed_lookups = 0
        
        for ip in unique_ips:
            try:
                if pd.isna(ip) or ip == '':
                    continue
                    
                geo_info = self.geolocator.get_location(ip)
                if geo_info:
                    ip_geo_data[ip] = {
                        'country': geo_info.get('country', 'Unknown'),
                        'region': geo_info.get('region', 'Unknown'),
                        'city': geo_info.get('city', 'Unknown'),
                        'latitude': geo_info.get('latitude', np.nan),
                        'longitude': geo_info.get('longitude', np.nan),
                        'timezone': geo_info.get('timezone', 'Unknown'),
                        'postal_code': geo_info.get('postal_code', 'Unknown'),
                        'asn': geo_info.get('asn', 'Unknown'),
                        'org': geo_info.get('org', 'Unknown')
                    }
                    successful_lookups += 1
                else:
                    failed_lookups += 1
                    
            except Exception as e:
                failed_lookups += 1
                continue
        
        geolocation_data['successful_lookups'] = successful_lookups
        geolocation_data['failed_lookups'] = failed_lookups
        geolocation_data['success_rate'] = successful_lookups / (successful_lookups + failed_lookups) if (successful_lookups + failed_lookups) > 0 else 0
        
        # Add geolocation data to DataFrame
        if successful_lookups > 0:
            df['ip_country'] = df['ip_address'].map(lambda x: ip_geo_data.get(x, {}).get('country', 'Unknown'))
            df['ip_region'] = df['ip_address'].map(lambda x: ip_geo_data.get(x, {}).get('region', 'Unknown'))
            df['ip_city'] = df['ip_address'].map(lambda x: ip_geo_data.get(x, {}).get('city', 'Unknown'))
            df['ip_latitude'] = df['ip_address'].map(lambda x: ip_geo_data.get(x, {}).get('latitude', np.nan))
            df['ip_longitude'] = df['ip_address'].map(lambda x: ip_geo_data.get(x, {}).get('longitude', np.nan))
            df['ip_timezone'] = df['ip_address'].map(lambda x: ip_geo_data.get(x, {}).get('timezone', 'Unknown'))
            df['ip_asn'] = df['ip_address'].map(lambda x: ip_geo_data.get(x, {}).get('asn', 'Unknown'))
            df['ip_org'] = df['ip_address'].map(lambda x: ip_geo_data.get(x, {}).get('org', 'Unknown'))
            
            geolocation_data['enriched_columns'] = [
                'ip_country', 'ip_region', 'ip_city', 'ip_latitude', 'ip_longitude', 
                'ip_timezone', 'ip_asn', 'ip_org'
            ]
        else:
            # If no successful lookups, create basic columns from existing data
            if 'ip_country' not in df.columns and 'ip_address' in df.columns:
                # Try to use existing IP country data if available
                if 'ip_country' in df.columns:
                    pass  # Already exists
                else:
                    # Create basic country column
                    df['ip_country'] = 'Unknown'
                    df['ip_region'] = 'Unknown'
                    df['ip_city'] = 'Unknown'
                    df['ip_latitude'] = np.nan
                    df['ip_longitude'] = np.nan
                    df['ip_timezone'] = 'Unknown'
                    df['ip_asn'] = 'Unknown'
                    df['ip_org'] = 'Unknown'
                    
                    geolocation_data['enriched_columns'] = [
                        'ip_country', 'ip_region', 'ip_city', 'ip_latitude', 'ip_longitude', 
                        'ip_timezone', 'ip_asn', 'ip_org'
                    ]
        
        geolocation_data['ip_geo_data'] = ip_geo_data
        return geolocation_data
    
    def _analyze_geographic_transaction_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze geographic transaction patterns and success rates"""
        
        patterns = {}
        
        # Country-level analysis
        if 'ip_country' in df.columns:
            country_analysis = df.groupby('ip_country').agg({
                'is_successful': ['mean', 'count', 'std'],
                'amount': 'mean' if 'amount' in df.columns else 'count',
                'processing_time': 'mean' if 'processing_time' in df.columns else 'count'
            }).round(3)
            
            # Flatten column names
            country_analysis.columns = ['_'.join(col).strip('_') for col in country_analysis.columns]
            
            # Calculate confidence intervals for statistical significance
            if 'is_successful_std' in country_analysis.columns:
                country_analysis['confidence_interval'] = country_analysis['is_successful_std'] / np.sqrt(country_analysis['is_successful_count'])
                country_analysis['margin_of_error'] = 1.96 * country_analysis['confidence_interval']
                country_analysis['lower_bound'] = country_analysis['is_successful_mean'] - country_analysis['margin_of_error']
                country_analysis['upper_bound'] = country_analysis['is_successful_mean'] + country_analysis['margin_of_error']
                
                # Statistical significance
                overall_success_rate = df['is_successful'].mean()
                country_analysis['statistical_significance'] = np.abs(country_analysis['is_successful_mean'] - overall_success_rate) > (2 * country_analysis['margin_of_error'])
            
            patterns['country_analysis'] = country_analysis.sort_values('is_successful_count', ascending=False)
            
            # Top and bottom performing countries
            if 'is_successful_mean' in country_analysis.columns:
                patterns['top_performing_countries'] = country_analysis.nlargest(10, 'is_successful_mean')[['is_successful_mean', 'is_successful_count']]
                patterns['bottom_performing_countries'] = country_analysis.nsmallest(10, 'is_successful_mean')[['is_successful_mean', 'is_successful_count']]
        
        # Region-level analysis
        if 'ip_region' in df.columns:
            region_analysis = df.groupby(['ip_country', 'ip_region']).agg({
                'is_successful': ['mean', 'count'],
                'amount': 'mean' if 'amount' in df.columns else 'count'
            }).round(3)
            
            # Flatten column names
            region_analysis.columns = ['_'.join(col).strip('_') for col in region_analysis.columns]
            patterns['region_analysis'] = region_analysis.sort_values('is_successful_count', ascending=False).head(20)
        
        # City-level analysis
        if 'ip_city' in df.columns:
            city_analysis = df.groupby(['ip_country', 'ip_city']).agg({
                'is_successful': ['mean', 'count'],
                'amount': 'mean' if 'amount' in df.columns else 'count'
            }).round(3)
            
            # Flatten column names
            city_analysis.columns = ['_'.join(col).strip('_') for col in city_analysis.columns]
            patterns['city_analysis'] = city_analysis.sort_values('is_successful_count', ascending=False).head(30)
        
        # Geographic distribution statistics
        if 'ip_country' in df.columns:
            patterns['geographic_distribution'] = {
                'total_countries': len(df['ip_country'].unique()),
                'total_regions': len(df['ip_region'].unique()) if 'ip_region' in df.columns else 0,
                'total_cities': len(df['ip_city'].unique()) if 'ip_city' in df.columns else 0,
                'country_concentration': (df['ip_country'].value_counts().iloc[0] / len(df)) * 100
            }
        
        return patterns
    
    def _detect_suspicious_regional_activity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect suspicious activity patterns by region"""
        
        suspicious_activity = {}
        
        # 1. High-risk country detection
        if 'ip_country' in df.columns:
            high_risk_transactions = df[df['ip_country'].isin(self.high_risk_countries.keys())]
            suspicious_activity['high_risk_country_transactions'] = {
                'count': len(high_risk_transactions),
                'percentage': (len(high_risk_transactions) / len(df)) * 100,
                'transactions': high_risk_transactions[['id', 'ip_country', 'is_successful', 'amount']].head(20)
            }
        
        # 2. Unusual transaction hours for region
        if 'ip_timezone' in df.columns and 'created_at' in df.columns:
            df['local_hour'] = df['created_at'].dt.hour  # Simplified - should use timezone conversion
            unusual_hours = df[df['local_hour'].isin([0, 1, 2, 3, 4, 5, 23])]
            
            unusual_hours_by_region = unusual_hours.groupby('ip_country').agg({
                'id': 'count',
                'is_successful': 'mean'
            }).rename(columns={'id': 'unusual_hour_count', 'is_successful': 'unusual_hour_success_rate'})
            
            suspicious_activity['unusual_hours_by_region'] = unusual_hours_by_region.sort_values('unusual_hour_count', ascending=False)
        
        # 3. Geographic velocity analysis (rapid location changes)
        if 'user_email' in df.columns and 'ip_country' in df.columns and 'created_at' in df.columns:
            user_location_changes = df.groupby('user_email').agg({
                'ip_country': 'nunique',
                'ip_city': 'nunique' if 'ip_city' in df.columns else lambda x: 1,
                'created_at': lambda x: (x.max() - x.min()).total_seconds() / 3600
            }).rename(columns={'ip_country': 'countries_visited', 'ip_city': 'cities_visited', 'created_at': 'time_span_hours'})
            
            # Detect suspicious velocity patterns
            suspicious_velocity = user_location_changes[
                (user_location_changes['countries_visited'] > 2) | 
                (user_location_changes['cities_visited'] > 3)
            ]
            
            suspicious_activity['suspicious_velocity'] = {
                'count': len(suspicious_velocity),
                'users': suspicious_velocity.head(20)
            }
        
        # 4. VPN/Proxy indicators
        if 'ip_org' in df.columns:
            vpn_indicators = ['vpn', 'proxy', 'tor', 'anonymous', 'data center']
            vpn_transactions = df[df['ip_org'].str.lower().str.contains('|'.join(vpn_indicators), na=False)]
            
            suspicious_activity['vpn_proxy_indicators'] = {
                'count': len(vpn_transactions),
                'percentage': (len(vpn_transactions) / len(df)) * 100,
                'transactions': vpn_transactions[['id', 'ip_org', 'ip_country', 'is_successful']].head(20)
            }
        
        # 5. Geographic outliers detection
        if 'ip_latitude' in df.columns and 'ip_longitude' in df.columns:
            # Simple outlier detection based on distance from centroid
            valid_coords = df[df['ip_latitude'].notna() & df['ip_longitude'].notna()]
            if len(valid_coords) > 0:
                centroid_lat = valid_coords['ip_latitude'].mean()
                centroid_lon = valid_coords['longitude'].mean()
                
                # Calculate distance from centroid (simplified)
                valid_coords['distance_from_centroid'] = np.sqrt(
                    (valid_coords['ip_latitude'] - centroid_lat)**2 + 
                    (valid_coords['ip_longitude'] - centroid_lon)**2
                )
                
                # Identify outliers (transactions far from centroid)
                outlier_threshold = valid_coords['distance_from_centroid'].quantile(0.95)
                geographic_outliers = valid_coords[valid_coords['distance_from_centroid'] > outlier_threshold]
                
                suspicious_activity['geographic_outliers'] = {
                    'count': len(geographic_outliers),
                    'percentage': (len(geographic_outliers) / len(df)) * 100,
                    'transactions': geographic_outliers[['id', 'ip_country', 'ip_city', 'distance_from_centroid']].head(20)
                }
        
        return suspicious_activity
    
    def _analyze_cross_border_transactions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze cross-border transactions and geographic mismatches"""
        
        cross_border_analysis = {}
        
        # Check if we have both IP country and billing country
        if 'ip_country' in df.columns and 'billing_country' in df.columns:
            df['cross_border'] = df['ip_country'] != df['billing_country']
            
            cross_border_analysis['cross_border_rate'] = {
                'total_cross_border': df['cross_border'].sum(),
                'cross_border_percentage': (df['cross_border'].sum() / len(df)) * 100
            }
            
            # Success rate by cross-border status
            cross_border_success = df.groupby('cross_border').agg({
                'is_successful': ['mean', 'count', 'std'],
                'amount': 'mean' if 'amount' in df.columns else 'count'
            }).round(3)
            
            # Flatten column names
            cross_border_success.columns = ['_'.join(col).strip('_') for col in cross_border_success.columns]
            cross_border_analysis['cross_border_success_analysis'] = cross_border_success
            
            # Detailed cross-border analysis by country pairs
            cross_border_transactions = df[df['cross_border'] == True]
            if len(cross_border_transactions) > 0:
                country_pair_analysis = cross_border_transactions.groupby(['billing_country', 'ip_country']).agg({
                    'is_successful': ['mean', 'count'],
                    'amount': 'mean' if 'amount' in df.columns else 'count'
                }).round(3)
                
                # Flatten column names
                country_pair_analysis.columns = ['_'.join(col).strip('_') for col in country_pair_analysis.columns]
                cross_border_analysis['country_pair_analysis'] = country_pair_analysis.sort_values('is_successful_count', ascending=False).head(20)
                
                # Risk assessment for country pairs
                cross_border_analysis['high_risk_country_pairs'] = country_pair_analysis[
                    country_pair_analysis['is_successful_mean'] < 0.5
                ].head(10)
        
        # ASN analysis for cross-border transactions
        if 'ip_asn' in df.columns and 'cross_border' in df.columns:
            asn_cross_border = df[df['cross_border'] == True].groupby('ip_asn').agg({
                'is_successful': ['mean', 'count'],
                'billing_country': 'nunique'
            }).round(3)
            
            # Flatten column names
            asn_cross_border.columns = ['_'.join(col).strip('_') for col in asn_cross_border.columns]
            cross_border_analysis['asn_cross_border_analysis'] = asn_cross_border.sort_values('is_successful_count', ascending=False).head(15)
        
        return cross_border_analysis
    
    def _calculate_geographic_risk_scores(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate comprehensive geographic risk scores"""
        
        risk_scoring = {}
        
        # Initialize risk score
        df['geographic_risk_score'] = 0.0
        
        # 1. Cross-border risk
        if 'cross_border' in df.columns:
            df.loc[df['cross_border'], 'geographic_risk_score'] += self.geographic_risk_factors['cross_border']
        
        # 2. High-risk country risk
        if 'ip_country' in df.columns:
            for country, risk_factor in self.high_risk_countries.items():
                df.loc[df['ip_country'] == country, 'geographic_risk_score'] += risk_factor
        
        # 3. Unusual region risk
        if 'ip_region' in df.columns:
            region_counts = df['ip_region'].value_counts()
            unusual_regions = region_counts[region_counts < region_counts.quantile(0.1)]
            df.loc[df['ip_region'].isin(unusual_regions.index), 'geographic_risk_score'] += self.geographic_risk_factors['unusual_region']
        
        # 4. IP velocity risk
        if 'user_email' in df.columns and 'ip_country' in df.columns:
            user_ip_changes = df.groupby('user_email')['ip_country'].nunique()
            high_velocity_users = user_ip_changes[user_ip_changes > 2]
            df.loc[df['user_email'].isin(high_velocity_users.index), 'geographic_risk_score'] += self.geographic_risk_factors['ip_velocity']
        
        # 5. Geographic clustering risk
        if 'ip_latitude' in df.columns and 'ip_longitude' in df.columns:
            # Detect geographic clustering (multiple transactions from same location)
            location_groups = df.groupby(['ip_latitude', 'ip_longitude']).size()
            clustered_locations = location_groups[location_groups > 5]  # More than 5 transactions from same location
            
            for (lat, lon), count in clustered_locations.items():
                mask = (df['ip_latitude'] == lat) & (df['ip_longitude'] == lon)
                df.loc[mask, 'geographic_risk_score'] += self.geographic_risk_factors['geographic_clustering']
        
        # 6. Timezone mismatch risk
        if 'ip_timezone' in df.columns and 'created_at' in df.columns:
            # Simplified timezone analysis
            df['hour'] = df['created_at'].dt.hour
            unusual_hours = (df['hour'] < 6) | (df['hour'] > 23)
            df.loc[unusual_hours, 'geographic_risk_score'] += self.geographic_risk_factors['timezone_mismatch']
        
        # Risk score distribution and analysis
        risk_scoring['risk_score_distribution'] = df['geographic_risk_score'].describe()
        risk_scoring['high_risk_transactions'] = df[df['geographic_risk_score'] > 3.0].sort_values('geographic_risk_score', ascending=False).head(20)
        
        # Risk vs Success analysis
        if len(df['geographic_risk_score'].dropna()) > 0:
            risk_bins = pd.cut(df['geographic_risk_score'], bins=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
            risk_success_analysis = df.groupby(risk_bins).agg({
                'is_successful': ['mean', 'count'],
                'amount': 'mean' if 'amount' in df.columns else 'count'
            }).round(3)
            
            # Flatten column names
            risk_success_analysis.columns = ['_'.join(col).strip('_') for col in risk_success_analysis.columns]
            risk_scoring['risk_success_analysis'] = risk_success_analysis
        
        return risk_scoring
    
    def _analyze_geographic_clustering(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze geographic clustering patterns"""
        
        clustering_analysis = {}
        
        if 'ip_latitude' in df.columns and 'ip_longitude' in df.columns:
            # Remove invalid coordinates
            valid_coords = df[df['ip_latitude'].notna() & df['ip_longitude'].notna()].copy()
            
            if len(valid_coords) > 0:
                # 1. Location-based clustering
                location_clusters = valid_coords.groupby(['ip_latitude', 'ip_longitude']).agg({
                    'id': 'count',
                    'is_successful': 'mean',
                    'amount': 'mean' if 'amount' in df.columns else 'count'
                }).rename(columns={'id': 'transaction_count', 'is_successful': 'success_rate', 'amount': 'avg_amount'})
                
                clustering_analysis['location_clusters'] = location_clusters.sort_values('transaction_count', ascending=False).head(20)
                
                # 2. City-level clustering
                if 'ip_city' in valid_coords.columns:
                    city_clusters = valid_coords.groupby(['ip_country', 'ip_city']).agg({
                        'id': 'count',
                        'is_successful': 'mean',
                        'amount': 'mean' if 'amount' in df.columns else 'count'
                    }).rename(columns={'id': 'transaction_count', 'is_successful': 'success_rate', 'amount': 'avg_amount'})
                    
                    clustering_analysis['city_clusters'] = city_clusters.sort_values('transaction_count', ascending=False).head(20)
                
                # 3. Geographic density analysis
                clustering_analysis['geographic_density'] = {
                    'total_locations': len(location_clusters),
                    'clustered_transactions': location_clusters[location_clusters['transaction_count'] > 1]['transaction_count'].sum(),
                    'clustering_ratio': location_clusters[location_clusters['transaction_count'] > 1]['transaction_count'].sum() / len(valid_coords) * 100
                }
        
        return clustering_analysis
    
    def _analyze_time_geographic_correlation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze correlation between time patterns and geographic factors"""
        
        time_geo_correlation = {}
        
        if 'created_at' in df.columns and 'ip_country' in df.columns:
            # Extract time components
            df['hour'] = df['created_at'].dt.hour
            df['day_of_week'] = df['created_at'].dt.dayofweek
            df['month'] = df['created_at'].dt.month
            
            # Hourly patterns by country
            hourly_by_country = df.groupby(['hour', 'ip_country']).agg({
                'is_successful': ['mean', 'count']
            }).round(3)
            
            # Flatten column names
            hourly_by_country.columns = ['_'.join(col).strip('_') for col in hourly_by_country.columns]
            time_geo_correlation['hourly_by_country'] = hourly_by_country.sort_values('is_successful_count', ascending=False).head(30)
            
            # Day of week patterns by country
            dow_by_country = df.groupby(['day_of_week', 'ip_country']).agg({
                'is_successful': ['mean', 'count']
            }).round(3)
            
            # Flatten column names
            dow_by_country.columns = ['_'.join(col).strip('_') for col in dow_by_country.columns]
            time_geo_correlation['day_of_week_by_country'] = dow_by_country.sort_values('is_successful_count', ascending=False).head(30)
            
            # Peak activity times by country
            peak_times = df.groupby('ip_country').agg({
                'hour': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else x.mean(),
                'is_successful': 'mean'
            }).rename(columns={'hour': 'peak_hour', 'is_successful': 'success_rate'})
            
            time_geo_correlation['peak_activity_times'] = peak_times.sort_values('success_rate', ascending=False)
        
        return time_geo_correlation
    
    def _create_basic_geographic_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create basic geographic patterns when detailed analysis is not available"""
        
        patterns = {}
        
        # Basic country-level analysis if ip_country exists
        if 'ip_country' in df.columns:
            country_analysis = df.groupby('ip_country').agg({
                'is_successful': ['mean', 'count'],
                'amount': 'mean' if 'amount' in df.columns else 'count'
            }).round(3)
            
            # Flatten column names
            country_analysis.columns = ['_'.join(col).strip('_') for col in country_analysis.columns]
            
            patterns['country_analysis'] = country_analysis.sort_values('is_successful_count', ascending=False)
            
            # Basic geographic distribution
            patterns['geographic_distribution'] = {
                'total_countries': len(df['ip_country'].unique()),
                'total_regions': 0,  # Not available in basic mode
                'total_cities': 0,   # Not available in basic mode
                'country_concentration': (df['ip_country'].value_counts().iloc[0] / len(df)) * 100 if len(df) > 0 else 0
            }
        else:
            patterns['status'] = 'No geographic data available for analysis'
        
        return patterns
    
    def generate_geographic_insights_report(self, analysis: Dict[str, Any]) -> str:
        """Generate comprehensive geographic insights report"""
        
        report = "# 🌍 Geographic Intelligence Analysis Report\n\n"
        
        # IP Geolocation Summary
        if 'ip_geolocation' in analysis:
            geo = analysis['ip_geolocation']
            report += "## 📍 IP Geolocation Summary\n\n"
            report += f"- **Total unique IPs analyzed**: {geo.get('total_unique_ips', 0):,}\n"
            report += f"- **Successful lookups**: {geo.get('successful_lookups', 0):,}\n"
            report += f"- **Failed lookups**: {geo.get('failed_lookups', 0):,}\n"
            report += f"- **Success rate**: {geo.get('success_rate', 0):.1%}\n\n"
        
        # Geographic Transaction Patterns
        if 'geographic_patterns' in analysis:
            patterns = analysis['geographic_patterns']
            report += "## 🌐 Geographic Transaction Patterns\n\n"
            
            if 'country_analysis' in patterns:
                country_data = patterns['country_analysis']
                report += "### 📊 Country-Level Analysis\n\n"
                
                if 'top_performing_countries' in patterns:
                    report += "**🏆 Top Performing Countries:**\n"
                    for idx, row in patterns['top_performing_countries'].head(5).iterrows():
                        report += f"- **{idx}**: {row['is_successful_mean']:.1%} success rate ({row['is_successful_count']:,} transactions)\n"
                    report += "\n"
                
                if 'bottom_performing_countries' in patterns:
                    report += "**⚠️ Bottom Performing Countries:**\n"
                    for idx, row in patterns['bottom_performing_countries'].head(5).iterrows():
                        report += f"- **{idx}**: {row['is_successful_mean']:.1%} success rate ({row['is_successful_count']:,} transactions)\n"
                    report += "\n"
            
            if 'geographic_distribution' in patterns:
                dist = patterns['geographic_distribution']
                report += f"**📈 Geographic Distribution:**\n"
                report += f"- **Total countries**: {dist.get('total_countries', 0):,}\n"
                report += f"- **Total regions**: {dist.get('total_regions', 0):,}\n"
                report += f"- **Total cities**: {dist.get('total_cities', 0):,}\n"
                report += f"- **Country concentration**: {dist.get('country_concentration', 0):.1f}% in top country\n\n"
        
        # Suspicious Regional Activity
        if 'suspicious_regional_activity' in analysis:
            suspicious = analysis['suspicious_regional_activity']
            report += "## 🚨 Suspicious Regional Activity Detection\n\n"
            
            if 'high_risk_country_transactions' in suspicious:
                hr = suspicious['high_risk_country_transactions']
                report += f"**🔴 High-Risk Country Transactions**: {hr['count']:,} ({hr['percentage']:.1f}% of total)\n\n"
            
            if 'vpn_proxy_indicators' in suspicious:
                vpn = suspicious['vpn_proxy_indicators']
                report += f"**🕵️ VPN/Proxy Indicators**: {vpn['count']:,} transactions ({vpn['percentage']:.1f}% of total)\n\n"
            
            if 'suspicious_velocity' in suspicious:
                vel = suspicious['suspicious_velocity']
                report += f"**⚡ Suspicious Velocity Patterns**: {vel['count']:,} users with rapid location changes\n\n"
        
        # Cross-Border Analysis
        if 'cross_border_analysis' in analysis:
            cross_border = analysis['cross_border_analysis']
            report += "## 🌍 Cross-Border Transaction Analysis\n\n"
            
            if 'cross_border_rate' in cross_border:
                rate = cross_border['cross_border_rate']
                report += f"**🌐 Cross-Border Rate**: {rate['total_cross_border']:,} transactions ({rate['cross_border_percentage']:.1f}% of total)\n\n"
            
            if 'high_risk_country_pairs' in cross_border:
                report += "**⚠️ High-Risk Country Pairs:**\n"
                for (billing, ip), row in cross_border['high_risk_country_pairs'].head(5).iterrows():
                    report += f"- **{billing} → {ip}**: {row['is_successful_mean']:.1%} success rate ({row['is_successful_count']:,} transactions)\n"
                report += "\n"
        
        # Geographic Risk Scoring
        if 'geographic_risk_scoring' in analysis:
            risk = analysis['geographic_risk_scoring']
            report += "## 🎯 Geographic Risk Scoring\n\n"
            
            if 'risk_score_distribution' in risk:
                dist = risk['risk_score_distribution']
                report += f"**📊 Risk Score Distribution:**\n"
                report += f"- **Mean risk score**: {dist.get('mean', 0):.2f}\n"
                report += f"- **Median risk score**: {dist.get('50%', 0):.2f}\n"
                report += f"- **95th percentile**: {dist.get('95%', 0):.2f}\n\n"
            
            if 'high_risk_transactions' in risk:
                high_risk_count = len(risk['high_risk_transactions'])
                report += f"**🚨 High-Risk Transactions**: {high_risk_count:,} transactions with risk score > 3.0\n\n"
        
        # Geographic Clustering
        if 'geographic_clustering' in analysis:
            clustering = analysis['geographic_clustering']
            report += "## 🗺️ Geographic Clustering Analysis\n\n"
            
            if 'geographic_density' in clustering:
                density = clustering['geographic_density']
                report += f"**📈 Clustering Metrics:**\n"
                report += f"- **Total unique locations**: {density.get('total_locations', 0):,}\n"
                report += f"- **Clustered transactions**: {density.get('clustered_transactions', 0):,}\n"
                report += f"- **Clustering ratio**: {density.get('clustering_ratio', 0):.1f}%\n\n"
        
        # Time-Geographic Correlation
        if 'time_geographic_correlation' in analysis:
            time_geo = analysis['time_geographic_correlation']
            report += "## ⏰ Time-Geographic Correlation\n\n"
            
            if 'peak_activity_times' in time_geo:
                report += "**🕐 Peak Activity Times by Country:**\n"
                for country, row in time_geo['peak_activity_times'].head(10).iterrows():
                    report += f"- **{country}**: Peak at {row['peak_hour']:.0f}:00 ({row['success_rate']:.1%} success rate)\n"
                report += "\n"
        
        # Recommendations
        report += "## 📋 Recommendations\n\n"
        report += "1. **Monitor high-risk countries** for unusual transaction patterns\n"
        report += "2. **Investigate cross-border transactions** with low success rates\n"
        report += "3. **Review VPN/Proxy transactions** for potential fraud\n"
        report += "4. **Analyze geographic clustering** for coordinated attacks\n"
        report += "5. **Use geographic risk scores** for automated fraud prevention\n"
        report += "6. **Implement location-based velocity checks** for suspicious patterns\n"
        
        return report

def run_geographic_intelligence_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Run complete geographic intelligence analysis"""
    
    engine = GeographicIntelligenceEngine()
    return engine.analyze_geographic_patterns(df)

def generate_geographic_insights(analysis: Dict[str, Any]) -> str:
    """Generate insights report from geographic analysis"""
    
    engine = GeographicIntelligenceEngine()
    return engine.generate_geographic_insights_report(analysis)
