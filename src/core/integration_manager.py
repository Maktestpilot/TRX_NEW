"""
Integration Manager
Orchestrates all services and provides unified interface for the application
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from ..core.interfaces import (
    GeolocationProvider, DataProcessor, AnalyticsEngine, 
    FraudDetector, ConversionOptimizer, DataQualityAnalyzer, ReportGenerator
)
from ..core.data_processor import EnhancedDataProcessor
from ..services.geolocation_service import GeolocationService, IPinfoGeolocationProvider, CSVGeolocationProvider
from ..services.conversion_optimizer import AdvancedConversionOptimizer


class IntegrationManager:
    """Main integration manager for TRX Analysis system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.services = {}
        self.processors = {}
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all services"""
        try:
            # Initialize data processor
            self.processors['data_processor'] = EnhancedDataProcessor()
            
            # Initialize geolocation service
            geolocation_providers = []
            
            # Add IPinfo provider if MMDB file is available
            if self.config.get('ipinfo_mmdb_path'):
                try:
                    ipinfo_provider = IPinfoGeolocationProvider(self.config['ipinfo_mmdb_path'])
                    if ipinfo_provider.is_available():
                        geolocation_providers.append(ipinfo_provider)
                        logging.info("IPinfo MMDB provider initialized")
                except Exception as e:
                    logging.warning(f"Failed to initialize IPinfo provider: {e}")
            
            # Add CSV provider if CSV file is available
            if self.config.get('ip_csv_path'):
                try:
                    csv_provider = CSVGeolocationProvider(self.config['ip_csv_path'])
                    if csv_provider.is_available():
                        geolocation_providers.append(csv_provider)
                        logging.info("CSV geolocation provider initialized")
                except Exception as e:
                    logging.warning(f"Failed to initialize CSV provider: {e}")
            
            if geolocation_providers:
                self.services['geolocation'] = GeolocationService(geolocation_providers)
            else:
                # Create a mock geolocation service for testing
                from ..services.geolocation_service import MockGeolocationProvider
                mock_provider = MockGeolocationProvider()
                self.services['geolocation'] = GeolocationService([mock_provider])
                logging.info("Using mock geolocation provider for testing")
            
            # Initialize conversion optimizer
            self.services['conversion_optimizer'] = AdvancedConversionOptimizer()
            
            logging.info("Integration manager initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize integration manager: {e}")
            raise
    
    def process_transaction_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Process transaction data through the complete pipeline"""
        try:
            logging.info(f"Starting transaction data processing for {len(df)} rows")
            
            # Step 1: Data processing and validation
            df_processed = self.processors['data_processor'].process(df)
            
            # Step 2: Geolocation enrichment
            if 'geolocation' in self.services:
                df_processed = self.services['geolocation'].enrich_dataframe(df_processed)
            
            # Step 3: IP vs BIN analysis
            df_processed = self._analyze_ip_bin_relationship(df_processed)
            
            # Step 4: Geographic risk analysis
            df_processed = self._calculate_geographic_risk(df_processed)
            
            # Step 5: Conversion analysis
            conversion_analysis = {}
            if 'conversion_optimizer' in self.services:
                conversion_analysis = self.services['conversion_optimizer'].analyze_conversion_factors(df_processed)
            
            # Step 6: Generate insights
            insights = self._generate_insights(df_processed, conversion_analysis)
            
            result = {
                'processed_data': df_processed,
                'conversion_analysis': conversion_analysis,
                'insights': insights,
                'processing_stats': self.processors['data_processor'].get_processing_stats(),
                'geolocation_stats': self._get_geolocation_stats()
            }
            
            logging.info("Transaction data processing completed successfully")
            return result
            
        except Exception as e:
            logging.error(f"Transaction data processing failed: {e}")
            raise
    
    def _analyze_ip_bin_relationship(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze IP vs BIN country relationship"""
        if 'ip_country' not in df.columns or 'card_bin_country' not in df.columns:
            return df
        
        # Create IP vs BIN country match indicator
        df['ip_bin_country_match'] = df['ip_country'] == df['card_bin_country']
        
        # Add cross-border transaction indicator
        df['is_cross_border'] = ~df['ip_bin_country_match']
        
        return df
    
    def _calculate_geographic_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate geographic risk score"""
        risk_scores = []
        
        for _, row in df.iterrows():
            score = 0
            
            # Base risk for country mismatch
            if row.get('ip_country') != row.get('card_bin_country'):
                score += 3.0
                
                # Additional risk for specific high-risk combinations
                ip_country = row.get('ip_country', '')
                bin_country = row.get('card_bin_country', '')
                
                high_risk_combinations = [
                    (['US', 'CA'], ['RU', 'CN', 'IR']),
                    (['RU', 'CN'], ['US', 'CA', 'EU']),
                    (['EU'], ['RU', 'CN', 'IR'])
                ]
                
                for ip_list, bin_list in high_risk_combinations:
                    if ip_country in ip_list and bin_country in bin_list:
                        score += 2.0
                        break
            
            # Risk for high-risk countries (configurable)
            high_risk_countries = ['XX', 'YY', 'ZZ']  # Replace with actual high-risk country codes
            if row.get('ip_country') in high_risk_countries:
                score += 2.0
            if row.get('card_bin_country') in high_risk_countries:
                score += 1.5
            
            # Risk for VPN/Proxy (if detected)
            ip_org = row.get('ip_org', '') or ''
            if isinstance(ip_org, str) and ip_org.lower() in ['vpn', 'proxy', 'tor']:
                score += 2.5
            
            # Risk for datacenter IPs
            if isinstance(ip_org, str) and ip_org.lower() in ['amazon', 'google', 'microsoft', 'cloudflare']:
                score += 1.0
            
            # Normalize to 0-10 scale
            risk_scores.append(min(score, 10.0))
        
        df['geo_risk_score'] = pd.Series(risk_scores, index=df.index)
        return df
    
    def _generate_insights(self, df: pd.DataFrame, conversion_analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable insights"""
        insights = []
        
        # IP-BIN match insights
        if 'ip_bin_country_match' in df.columns:
            match_rate = df['ip_bin_country_match'].mean()
            if match_rate < 0.7:
                insights.append(f"🚨 CRITICAL: IP-BIN country match rate is {match_rate:.1%}. Target: >70%")
            else:
                insights.append(f"✅ IP-BIN country match rate is good: {match_rate:.1%}")
        
        # Data quality insights
        if 'data_quality_score' in df.columns:
            avg_quality = df['data_quality_score'].mean()
            if avg_quality < 15:
                insights.append(f"⚠️ Data quality score is low: {avg_quality:.1f}/20. Target: >15")
            else:
                insights.append(f"✅ Data quality score is good: {avg_quality:.1f}/20")
        
        # Geographic risk insights
        if 'geo_risk_score' in df.columns:
            avg_risk = df['geo_risk_score'].mean()
            high_risk_count = (df['geo_risk_score'] > 5).sum()
            if avg_risk > 3:
                insights.append(f"⚠️ High geographic risk: {avg_risk:.1f}/10 average, {high_risk_count} high-risk transactions")
            else:
                insights.append(f"✅ Geographic risk is manageable: {avg_risk:.1f}/10 average")
        
        # Conversion insights
        if conversion_analysis:
            overall_rate = conversion_analysis.get('overall_conversion_rate', 0)
            if overall_rate < 0.8:
                insights.append(f"🎯 Conversion rate needs improvement: {overall_rate:.1%}. Target: >80%")
            else:
                insights.append(f"✅ Conversion rate is good: {overall_rate:.1%}")
        
        return insights
    
    def _get_geolocation_stats(self) -> Dict[str, Any]:
        """Get geolocation service statistics"""
        if 'geolocation' in self.services:
            return self.services['geolocation'].get_cache_stats()
        return {}
    
    def get_optimization_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Get optimization recommendations"""
        if 'conversion_optimizer' in self.services:
            return self.services['conversion_optimizer'].get_optimization_recommendations(df)
        return ["Conversion optimizer not available"]
    
    def get_conversion_impact_prediction(self, df: pd.DataFrame) -> Dict[str, float]:
        """Get conversion impact predictions"""
        if 'conversion_optimizer' in self.services:
            return self.services['conversion_optimizer'].calculate_conversion_impact(df)
        return {}
    
    def clear_caches(self):
        """Clear all service caches"""
        if 'geolocation' in self.services:
            self.services['geolocation'].clear_cache()
        logging.info("All caches cleared")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        status = {
            'services': {},
            'processors': {},
            'overall_status': 'healthy'
        }
        
        # Check service status
        for name, service in self.services.items():
            if hasattr(service, 'is_available'):
                status['services'][name] = service.is_available()
            else:
                status['services'][name] = True
        
        # Check processor status
        for name, processor in self.processors.items():
            if hasattr(processor, 'get_processing_stats'):
                stats = processor.get_processing_stats()
                status['processors'][name] = {
                    'available': True,
                    'stats': stats
                }
            else:
                status['processors'][name] = {'available': True}
        
        # Determine overall status
        if not all(status['services'].values()):
            status['overall_status'] = 'degraded'
        
        return status
