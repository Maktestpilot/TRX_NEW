"""
Abstract interfaces and base classes for TRX Analysis system
Defines contracts for all major components
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd


class GeolocationProvider(ABC):
    """Abstract base class for geolocation providers"""
    
    @abstractmethod
    def get_location(self, ip: str) -> Optional[Dict[str, Any]]:
        """Get complete location information for IP address"""
        pass
    
    @abstractmethod
    def get_country(self, ip: str) -> Optional[str]:
        """Get country code for IP address"""
        pass
    
    @abstractmethod
    def get_asn(self, ip: str) -> Optional[str]:
        """Get ASN information for IP address"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if geolocation service is available"""
        pass


class DataProcessor(ABC):
    """Abstract base class for data processing"""
    
    @abstractmethod
    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and transform data"""
        pass
    
    @abstractmethod
    def validate(self, df: pd.DataFrame) -> bool:
        """Validate data integrity"""
        pass
    
    @abstractmethod
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        pass


class AnalyticsEngine(ABC):
    """Abstract base class for analytics engines"""
    
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Perform comprehensive analysis"""
        pass
    
    @abstractmethod
    def get_insights(self, df: pd.DataFrame) -> List[str]:
        """Extract actionable insights"""
        pass
    
    @abstractmethod
    def generate_report(self, df: pd.DataFrame) -> str:
        """Generate analysis report"""
        pass


class FraudDetector(ABC):
    """Abstract base class for fraud detection"""
    
    @abstractmethod
    def detect_fraud(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect fraudulent transactions"""
        pass
    
    @abstractmethod
    def calculate_risk_score(self, transaction: Dict[str, Any]) -> float:
        """Calculate risk score for single transaction"""
        pass
    
    @abstractmethod
    def get_fraud_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify fraud patterns"""
        pass


class ConversionOptimizer(ABC):
    """Abstract base class for conversion optimization"""
    
    @abstractmethod
    def analyze_conversion_factors(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze factors affecting conversion"""
        pass
    
    @abstractmethod
    def get_optimization_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Get recommendations for improving conversion"""
        pass
    
    @abstractmethod
    def calculate_conversion_impact(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate impact of various factors on conversion"""
        pass


class DataQualityAnalyzer(ABC):
    """Abstract base class for data quality analysis"""
    
    @abstractmethod
    def analyze_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data quality metrics"""
        pass
    
    @abstractmethod
    def get_quality_score(self, df: pd.DataFrame) -> float:
        """Get overall data quality score"""
        pass
    
    @abstractmethod
    def get_quality_issues(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify data quality issues"""
        pass


class ReportGenerator(ABC):
    """Abstract base class for report generation"""
    
    @abstractmethod
    def generate_summary_report(self, df: pd.DataFrame) -> str:
        """Generate summary report"""
        pass
    
    @abstractmethod
    def generate_detailed_report(self, df: pd.DataFrame) -> str:
        """Generate detailed analysis report"""
        pass
    
    @abstractmethod
    def export_to_format(self, df: pd.DataFrame, format_type: str) -> bytes:
        """Export data to specified format"""
        pass
