"""
Enhanced Data Processor
Handles data loading, processing, and transformation with improved error handling
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
import json
from datetime import datetime
from ..core.interfaces import DataProcessor
from ..utils.validators import DataValidator, IPValidator, JSONValidator


class EnhancedDataProcessor(DataProcessor):
    """Enhanced data processor with comprehensive validation and transformation"""
    
    def __init__(self):
        self.validator = DataValidator()
        self.processing_stats = {
            'total_processed': 0,
            'successful_processed': 0,
            'failed_processed': 0,
            'processing_errors': []
        }
        self.data_quality_metrics = {}
    
    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and transform data with comprehensive validation"""
        try:
            logging.info(f"Starting data processing for {len(df)} rows")
            
            # Step 1: Validate input data
            validation_results = self.validator.validate_dataframe(df)
            self.data_quality_metrics = validation_results
            
            if not validation_results['is_valid']:
                logging.warning(f"Data validation failed: {len(validation_results['validation_errors'])} errors")
            
            # Step 2: Clean and standardize data
            df_cleaned = self._clean_data(df)
            
            # Step 3: Extract and enrich data
            df_enriched = self._enrich_data(df_cleaned)
            
            # Step 4: Transform data
            df_transformed = self._transform_data(df_enriched)
            
            # Step 5: Calculate derived metrics
            df_final = self._calculate_derived_metrics(df_transformed)
            
            # Update processing stats
            self.processing_stats['total_processed'] += len(df)
            self.processing_stats['successful_processed'] += len(df_final)
            
            logging.info(f"Data processing completed successfully: {len(df_final)} rows")
            return df_final
            
        except Exception as e:
            logging.error(f"Data processing failed: {e}")
            self.processing_stats['failed_processed'] += len(df)
            self.processing_stats['processing_errors'].append(str(e))
            raise
    
    def validate(self, df: pd.DataFrame) -> bool:
        """Validate data integrity"""
        validation_results = self.validator.validate_dataframe(df)
        return validation_results['is_valid']
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'processing_stats': self.processing_stats,
            'data_quality_metrics': self.data_quality_metrics,
            'quality_score': self.data_quality_metrics.get('data_quality_score', 0)
        }
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize data"""
        df_cleaned = df.copy()
        
        # Clean string columns
        string_columns = df_cleaned.select_dtypes(include=['object']).columns
        for col in string_columns:
            df_cleaned[col] = df_cleaned[col].astype(str).str.strip()
            df_cleaned[col] = df_cleaned[col].replace('nan', np.nan)
        
        # Clean numeric columns
        if 'amount' in df_cleaned.columns:
            df_cleaned['amount'] = pd.to_numeric(df_cleaned['amount'], errors='coerce')
        
        # Clean timestamp columns
        timestamp_columns = ['created_at', 'updated_at']
        for col in timestamp_columns:
            if col in df_cleaned.columns:
                df_cleaned[col] = pd.to_datetime(df_cleaned[col], errors='coerce')
        
        # Remove completely empty rows
        df_cleaned = df_cleaned.dropna(how='all')
        
        return df_cleaned
    
    def _enrich_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich data with extracted information"""
        df_enriched = df.copy()
        
        # Extract data from JSON body column
        if 'body' in df_enriched.columns:
            df_enriched = self._extract_body_data(df_enriched)
        
        # Extract IP addresses
        if 'ip' in df_enriched.columns:
            df_enriched['ip_address'] = df_enriched['ip']
        
        # Validate and classify IP addresses
        if 'ip_address' in df_enriched.columns:
            df_enriched['ip_is_valid'] = df_enriched['ip_address'].apply(IPValidator.is_valid_ip)
            df_enriched['ip_is_private'] = df_enriched['ip_address'].apply(IPValidator.is_private_ip)
            df_enriched['ip_type'] = df_enriched['ip_address'].apply(IPValidator.get_ip_type)
        
        return df_enriched
    
    def _extract_body_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract structured data from JSON body column"""
        def extract_from_body(body_str: str, field_path: str) -> Optional[str]:
            """Extract field from JSON body using dot notation"""
            if not body_str or not isinstance(body_str, str):
                return None
            
            try:
                body_data = json.loads(body_str)
                
                # Handle dot notation (e.g., 'browser.family')
                keys = field_path.split('.')
                current = body_data
                
                for key in keys:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        return None
                
                return str(current) if current is not None else None
                
            except (json.JSONDecodeError, KeyError, TypeError):
                return None
        
        # Extract common fields
        extraction_fields = {
            'browser_family': 'browser.family',
            'browser_os': 'browser.os',
            'browser_user_agent': 'browser.userAgent',
            'browser_screen_width': 'browser.screenWidth',
            'browser_screen_height': 'browser.screenHeight',
            'browser_language': 'browser.language',
            'card_bin_country': 'card.binCountryIso',
            'card_type': 'card.cardType',
            'billing_country': 'billing.country',
            'billing_city': 'billing.city',
            'user_email': 'email'
        }
        
        for new_col, field_path in extraction_fields.items():
            df[new_col] = df['body'].apply(lambda x: extract_from_body(x, field_path))
        
        return df
    
    def _transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform data for analysis"""
        df_transformed = df.copy()
        
        # Create success indicator
        if 'status_title' in df_transformed.columns and 'is_final' in df_transformed.columns:
            df_transformed['is_successful'] = (
                (df_transformed['status_title'] != 'Failed') & 
                (df_transformed['is_final'] == True)
            )
        elif 'status' in df_transformed.columns:
            df_transformed['is_successful'] = df_transformed['status'] == 'success'
        
        # Create amount categories
        if 'amount' in df_transformed.columns:
            df_transformed['amount_category'] = pd.cut(
                df_transformed['amount'],
                bins=[0, 100, 500, 1000, 5000, float('inf')],
                labels=['Micro', 'Small', 'Medium', 'Large', 'Enterprise']
            )
        
        # Create time-based features
        if 'created_at' in df_transformed.columns:
            df_transformed['transaction_hour'] = df_transformed['created_at'].dt.hour
            df_transformed['transaction_day_of_week'] = df_transformed['created_at'].dt.dayofweek
            df_transformed['transaction_month'] = df_transformed['created_at'].dt.month
        
        return df_transformed
    
    def _calculate_derived_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate derived metrics and scores"""
        df_metrics = df.copy()
        
        # Calculate data quality score
        df_metrics['data_quality_score'] = self._calculate_row_quality_score(df_metrics)
        
        # Calculate IP quality score
        if 'ip_address' in df_metrics.columns:
            df_metrics['ip_quality_score'] = self._calculate_ip_quality_score(df_metrics)
        
        # Calculate browser quality score
        if 'browser_user_agent' in df_metrics.columns:
            df_metrics['browser_quality_score'] = self._calculate_browser_quality_score(df_metrics)
        
        return df_metrics
    
    def _calculate_row_quality_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate quality score for each row"""
        scores = []
        
        for _, row in df.iterrows():
            score = 0
            max_score = 20
            
            # IP quality (5 points)
            if row.get('ip_is_valid', False):
                score += 3
                if not row.get('ip_is_private', False):
                    score += 2
            
            # Browser quality (5 points)
            if pd.notna(row.get('browser_family')):
                score += 2
            if pd.notna(row.get('browser_user_agent')):
                score += 2
            if not self._is_suspicious_user_agent(row.get('browser_user_agent')):
                score += 1
            
            # Card quality (5 points)
            if pd.notna(row.get('card_bin_country')):
                score += 2
            if pd.notna(row.get('card_type')):
                score += 2
            if pd.notna(row.get('billing_country')):
                score += 1
            
            # Data completeness (5 points)
            required_fields = ['user_email', 'amount', 'created_at']
            for field in required_fields:
                if pd.notna(row.get(field)):
                    score += 1
            
            scores.append(min(score, max_score))
        
        return pd.Series(scores, index=df.index)
    
    def _calculate_ip_quality_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate IP quality score"""
        scores = []
        
        for _, row in df.iterrows():
            score = 0
            
            if row.get('ip_is_valid', False):
                score += 5
                if not row.get('ip_is_private', False):
                    score += 3
                if row.get('ip_type') == 'public':
                    score += 2
            
            scores.append(score)
        
        return pd.Series(scores, index=df.index)
    
    def _calculate_browser_quality_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate browser quality score"""
        scores = []
        
        for _, row in df.iterrows():
            score = 0
            
            if pd.notna(row.get('browser_family')):
                score += 3
            if pd.notna(row.get('browser_os')):
                score += 2
            if not self._is_suspicious_user_agent(row.get('browser_user_agent')):
                score += 3
            if pd.notna(row.get('browser_screen_width')) and pd.notna(row.get('browser_screen_height')):
                score += 2
            
            scores.append(score)
        
        return pd.Series(scores, index=df.index)
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious"""
        if not user_agent or not isinstance(user_agent, str):
            return False
        
        suspicious_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'headless',
            'phantom', 'selenium', 'webdriver', 'automation'
        ]
        
        ua_lower = user_agent.lower()
        return any(pattern in ua_lower for pattern in suspicious_patterns)
