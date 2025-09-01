"""
Data validation utilities for TRX Analysis system
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np


class DataValidator:
    """Comprehensive data validation for transaction data"""
    
    def __init__(self):
        self.validation_rules = self._initialize_validation_rules()
        self.validation_results = {}
    
    def _initialize_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize validation rules for different data types"""
        return {
            'ip_address': {
                'required': True,
                'pattern': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
                'validator': self._validate_ip_address
            },
            'email': {
                'required': True,
                'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                'validator': self._validate_email
            },
            'amount': {
                'required': True,
                'min_value': 0.01,
                'max_value': 1000000,
                'validator': self._validate_amount
            },
            'country_code': {
                'required': False,
                'pattern': r'^[A-Z]{2}$',
                'validator': self._validate_country_code
            },
            'card_type': {
                'required': False,
                'allowed_values': ['Visa', 'Mastercard', 'American Express', 'Discover'],
                'validator': self._validate_card_type
            },
            'timestamp': {
                'required': True,
                'validator': self._validate_timestamp
            }
        }
    
    def validate_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate entire DataFrame"""
        validation_results = {
            'is_valid': True,
            'total_rows': len(df),
            'validation_errors': [],
            'column_validation': {},
            'data_quality_score': 0.0
        }
        
        # Validate each column
        for column in df.columns:
            column_result = self._validate_column(df, column)
            validation_results['column_validation'][column] = column_result
            
            if not column_result['is_valid']:
                validation_results['is_valid'] = False
                validation_results['validation_errors'].extend(column_result['errors'])
        
        # Calculate overall data quality score
        validation_results['data_quality_score'] = self._calculate_quality_score(validation_results)
        
        return validation_results
    
    def _validate_column(self, df: pd.DataFrame, column: str) -> Dict[str, Any]:
        """Validate specific column"""
        result = {
            'column_name': column,
            'is_valid': True,
            'total_values': len(df[column]),
            'null_values': df[column].isnull().sum(),
            'unique_values': df[column].nunique(),
            'errors': []
        }
        
        # Check for null values in required columns
        if column in self.validation_rules and self.validation_rules[column].get('required', False):
            null_count = df[column].isnull().sum()
            if null_count > 0:
                result['errors'].append(f"Required column '{column}' has {null_count} null values")
                result['is_valid'] = False
        
        # Apply specific validators
        if column in self.validation_rules:
            validator = self.validation_rules[column].get('validator')
            if validator:
                validation_errors = validator(df[column])
                result['errors'].extend(validation_errors)
                if validation_errors:
                    result['is_valid'] = False
        
        return result
    
    def _validate_ip_address(self, series: pd.Series) -> List[str]:
        """Validate IP address format"""
        errors = []
        ip_pattern = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
        
        for idx, ip in series.items():
            if pd.notna(ip) and not ip_pattern.match(str(ip)):
                errors.append(f"Row {idx}: Invalid IP address format '{ip}'")
        
        return errors
    
    def _validate_email(self, series: pd.Series) -> List[str]:
        """Validate email format"""
        errors = []
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        for idx, email in series.items():
            if pd.notna(email) and not email_pattern.match(str(email)):
                errors.append(f"Row {idx}: Invalid email format '{email}'")
        
        return errors
    
    def _validate_amount(self, series: pd.Series) -> List[str]:
        """Validate transaction amount"""
        errors = []
        min_value = self.validation_rules['amount']['min_value']
        max_value = self.validation_rules['amount']['max_value']
        
        for idx, amount in series.items():
            if pd.notna(amount):
                try:
                    amount_float = float(amount)
                    if amount_float < min_value:
                        errors.append(f"Row {idx}: Amount {amount_float} below minimum {min_value}")
                    elif amount_float > max_value:
                        errors.append(f"Row {idx}: Amount {amount_float} above maximum {max_value}")
                except (ValueError, TypeError):
                    errors.append(f"Row {idx}: Invalid amount format '{amount}'")
        
        return errors
    
    def _validate_country_code(self, series: pd.Series) -> List[str]:
        """Validate country code format"""
        errors = []
        country_pattern = re.compile(r'^[A-Z]{2}$')
        
        for idx, country in series.items():
            if pd.notna(country) and not country_pattern.match(str(country)):
                errors.append(f"Row {idx}: Invalid country code format '{country}'")
        
        return errors
    
    def _validate_card_type(self, series: pd.Series) -> List[str]:
        """Validate card type"""
        errors = []
        allowed_values = self.validation_rules['card_type']['allowed_values']
        
        for idx, card_type in series.items():
            if pd.notna(card_type) and str(card_type) not in allowed_values:
                errors.append(f"Row {idx}: Invalid card type '{card_type}'. Allowed: {allowed_values}")
        
        return errors
    
    def _validate_timestamp(self, series: pd.Series) -> List[str]:
        """Validate timestamp format"""
        errors = []
        
        for idx, timestamp in series.items():
            if pd.notna(timestamp):
                try:
                    pd.to_datetime(timestamp)
                except (ValueError, TypeError):
                    errors.append(f"Row {idx}: Invalid timestamp format '{timestamp}'")
        
        return errors
    
    def _calculate_quality_score(self, validation_results: Dict[str, Any]) -> float:
        """Calculate overall data quality score (0-100)"""
        total_errors = len(validation_results['validation_errors'])
        total_rows = validation_results['total_rows']
        
        if total_rows == 0:
            return 0.0
        
        # Base score starts at 100
        base_score = 100.0
        
        # Deduct points for errors
        error_penalty = min(total_errors * 2, 50)  # Max 50 points deduction
        
        # Deduct points for null values in required columns
        null_penalty = 0
        for column, result in validation_results['column_validation'].items():
            if column in self.validation_rules and self.validation_rules[column].get('required', False):
                null_ratio = result['null_values'] / result['total_values']
                null_penalty += null_ratio * 10  # Up to 10 points per required column
        
        quality_score = max(0, base_score - error_penalty - null_penalty)
        return round(quality_score, 2)
    
    def get_validation_summary(self, validation_results: Dict[str, Any]) -> str:
        """Generate human-readable validation summary"""
        summary = []
        
        summary.append(f"📊 Data Validation Summary")
        summary.append(f"Total Rows: {validation_results['total_rows']}")
        summary.append(f"Data Quality Score: {validation_results['data_quality_score']}/100")
        summary.append(f"Overall Status: {'✅ VALID' if validation_results['is_valid'] else '❌ INVALID'}")
        
        if validation_results['validation_errors']:
            summary.append(f"\n🚨 Validation Errors ({len(validation_results['validation_errors'])}):")
            for error in validation_results['validation_errors'][:10]:  # Show first 10 errors
                summary.append(f"  • {error}")
            
            if len(validation_results['validation_errors']) > 10:
                summary.append(f"  ... and {len(validation_results['validation_errors']) - 10} more errors")
        
        return "\n".join(summary)


class IPValidator:
    """Specialized IP address validation"""
    
    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        """Check if IP address is valid"""
        if not ip or not isinstance(ip, str):
            return False
        
        ip_pattern = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
        return bool(ip_pattern.match(ip))
    
    @staticmethod
    def is_private_ip(ip: str) -> bool:
        """Check if IP is private"""
        if not IPValidator.is_valid_ip(ip):
            return False
        
        ip_parts = ip.split('.')
        first_octet = int(ip_parts[0])
        second_octet = int(ip_parts[1])
        
        return (
            first_octet == 10 or  # 10.0.0.0/8
            (first_octet == 172 and 16 <= second_octet <= 31) or  # 172.16.0.0/12
            (first_octet == 192 and second_octet == 168) or  # 192.168.0.0/16
            first_octet == 127  # 127.0.0.0/8 (loopback)
        )
    
    @staticmethod
    def is_public_ip(ip: str) -> bool:
        """Check if IP is public"""
        return IPValidator.is_valid_ip(ip) and not IPValidator.is_private_ip(ip)
    
    @staticmethod
    def get_ip_type(ip: str) -> str:
        """Get IP type classification"""
        if not IPValidator.is_valid_ip(ip):
            return 'invalid'
        elif IPValidator.is_private_ip(ip):
            return 'private'
        else:
            return 'public'


class JSONValidator:
    """JSON data validation utilities"""
    
    @staticmethod
    def is_valid_json(json_str: str) -> bool:
        """Check if string is valid JSON"""
        if not json_str or not isinstance(json_str, str):
            return False
        
        try:
            import json
            json.loads(json_str)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    @staticmethod
    def validate_json_structure(json_str: str, required_fields: List[str]) -> Dict[str, Any]:
        """Validate JSON structure and required fields"""
        result = {
            'is_valid': False,
            'missing_fields': [],
            'extra_fields': [],
            'parsed_data': None
        }
        
        if not JSONValidator.is_valid_json(json_str):
            return result
        
        try:
            import json
            data = json.loads(json_str)
            result['parsed_data'] = data
            
            # Check required fields
            for field in required_fields:
                if field not in data:
                    result['missing_fields'].append(field)
            
            result['is_valid'] = len(result['missing_fields']) == 0
            
        except Exception as e:
            logging.error(f"Error validating JSON structure: {e}")
        
        return result
