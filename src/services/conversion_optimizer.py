"""
Conversion Optimization Service
Analyzes factors affecting transaction conversion and provides optimization recommendations
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from ..core.interfaces import ConversionOptimizer


class AdvancedConversionOptimizer(ConversionOptimizer):
    """Advanced conversion optimization with ML-based insights"""
    
    def __init__(self):
        self.conversion_factors = {}
        self.optimization_rules = []
        self._initialize_rules()
    
    def _initialize_rules(self):
        """Initialize optimization rules based on industry best practices"""
        self.optimization_rules = [
            {
                'name': 'IP_BIN_Country_Match',
                'description': 'IP country should match BIN country',
                'weight': 0.3,
                'threshold': 0.7,
                'impact': 'high'
            },
            {
                'name': 'Data_Quality',
                'description': 'High data quality improves conversion',
                'weight': 0.25,
                'threshold': 0.8,
                'impact': 'high'
            },
            {
                'name': 'Geographic_Risk',
                'description': 'Low geographic risk improves conversion',
                'weight': 0.2,
                'threshold': 3.0,
                'impact': 'medium'
            },
            {
                'name': 'Browser_Compatibility',
                'description': 'Modern browsers have higher conversion',
                'weight': 0.15,
                'threshold': 0.9,
                'impact': 'medium'
            },
            {
                'name': 'Transaction_Amount',
                'description': 'Optimal amount ranges improve conversion',
                'weight': 0.1,
                'threshold': 0.85,
                'impact': 'low'
            }
        ]
    
    def analyze_conversion_factors(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze factors affecting conversion"""
        if 'is_successful' not in df.columns:
            logging.warning("No 'is_successful' column found for conversion analysis")
            return {}
        
        analysis = {
            'overall_conversion_rate': df['is_successful'].mean(),
            'total_transactions': len(df),
            'successful_transactions': df['is_successful'].sum(),
            'failed_transactions': (~df['is_successful']).sum(),
            'factors': {}
        }
        
        # Analyze IP vs BIN country match impact
        if 'ip_bin_country_match' in df.columns:
            match_analysis = df.groupby('ip_bin_country_match')['is_successful'].agg(['mean', 'count'])
            analysis['factors']['ip_bin_match'] = {
                'match_rate': df['ip_bin_country_match'].mean(),
                'conversion_when_matched': match_analysis.loc[True, 'mean'] if True in match_analysis.index else 0,
                'conversion_when_mismatched': match_analysis.loc[False, 'mean'] if False in match_analysis.index else 0,
                'impact': self._calculate_factor_impact(df, 'ip_bin_country_match')
            }
        
        # Analyze data quality impact
        if 'data_quality_score' in df.columns:
            quality_analysis = self._analyze_quality_impact(df)
            analysis['factors']['data_quality'] = quality_analysis
        
        # Analyze geographic risk impact
        if 'geo_risk_score' in df.columns:
            risk_analysis = self._analyze_risk_impact(df)
            analysis['factors']['geographic_risk'] = risk_analysis
        
        # Analyze browser impact
        if 'browser_family' in df.columns:
            browser_analysis = self._analyze_browser_impact(df)
            analysis['factors']['browser'] = browser_analysis
        
        # Analyze amount impact
        if 'amount' in df.columns:
            amount_analysis = self._analyze_amount_impact(df)
            analysis['factors']['amount'] = amount_analysis
        
        return analysis
    
    def _calculate_factor_impact(self, df: pd.DataFrame, factor_column: str) -> float:
        """Calculate the impact of a factor on conversion"""
        if factor_column not in df.columns:
            return 0.0
        
        # Calculate conversion rates for different factor values
        factor_analysis = df.groupby(factor_column, observed=True)['is_successful'].mean()
        
        if len(factor_analysis) < 2:
            return 0.0
        
        # Calculate impact as difference between best and worst performing groups
        max_conversion = factor_analysis.max()
        min_conversion = factor_analysis.min()
        
        return max_conversion - min_conversion
    
    def _analyze_quality_impact(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data quality impact on conversion"""
        # Create quality bins
        df['quality_bin'] = pd.cut(df['data_quality_score'], 
                                  bins=[0, 10, 15, 20], 
                                  labels=['Low', 'Medium', 'High'])
        
        quality_analysis = df.groupby('quality_bin', observed=True)['is_successful'].agg(['mean', 'count'])
        
        return {
            'avg_quality_score': df['data_quality_score'].mean(),
            'quality_distribution': quality_analysis.to_dict(),
            'impact': self._calculate_factor_impact(df, 'quality_bin')
        }
    
    def _analyze_risk_impact(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze geographic risk impact on conversion"""
        # Create risk bins
        df['risk_bin'] = pd.cut(df['geo_risk_score'], 
                               bins=[0, 3, 6, 10], 
                               labels=['Low', 'Medium', 'High'])
        
        risk_analysis = df.groupby('risk_bin', observed=True)['is_successful'].agg(['mean', 'count'])
        
        return {
            'avg_risk_score': df['geo_risk_score'].mean(),
            'risk_distribution': risk_analysis.to_dict(),
            'impact': self._calculate_factor_impact(df, 'risk_bin')
        }
    
    def _analyze_browser_impact(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze browser impact on conversion"""
        browser_analysis = df.groupby('browser_family')['is_successful'].agg(['mean', 'count'])
        
        # Identify top performing browsers
        top_browsers = browser_analysis.nlargest(3, 'mean')
        
        return {
            'browser_distribution': browser_analysis.to_dict(),
            'top_performing_browsers': top_browsers.to_dict(),
            'impact': self._calculate_factor_impact(df, 'browser_family')
        }
    
    def _analyze_amount_impact(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze transaction amount impact on conversion"""
        # Create amount bins
        df['amount_bin'] = pd.cut(df['amount'], 
                                 bins=5, 
                                 labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
        
        amount_analysis = df.groupby('amount_bin', observed=True)['is_successful'].agg(['mean', 'count'])
        
        return {
            'avg_amount': df['amount'].mean(),
            'amount_distribution': amount_analysis.to_dict(),
            'optimal_amount_range': self._find_optimal_amount_range(df),
            'impact': self._calculate_factor_impact(df, 'amount_bin')
        }
    
    def _find_optimal_amount_range(self, df: pd.DataFrame) -> Dict[str, float]:
        """Find optimal amount range for conversion"""
        # Calculate conversion rate by amount quartiles
        quartiles = df['amount'].quantile([0.25, 0.5, 0.75])
        
        optimal_range = {
            'min_amount': quartiles[0.25],
            'max_amount': quartiles[0.75],
            'median_amount': quartiles[0.5]
        }
        
        return optimal_range
    
    def get_optimization_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Get actionable optimization recommendations"""
        recommendations = []
        analysis = self.analyze_conversion_factors(df)
        
        if not analysis:
            return ["No data available for optimization analysis"]
        
        # Check IP-BIN country match
        if 'ip_bin_match' in analysis['factors']:
            match_rate = analysis['factors']['ip_bin_match']['match_rate']
            if match_rate < 0.7:
                recommendations.append(
                    f"🚨 CRITICAL: IP-BIN country match rate is {match_rate:.1%}. "
                    f"Improve to >70% for +15-25% conversion boost"
                )
        
        # Check data quality
        if 'data_quality' in analysis['factors']:
            avg_quality = analysis['factors']['data_quality']['avg_quality_score']
            if avg_quality < 15:
                recommendations.append(
                    f"⚠️ Data quality score is {avg_quality:.1f}/20. "
                    f"Improve data validation for +10-15% conversion boost"
                )
        
        # Check geographic risk
        if 'geographic_risk' in analysis['factors']:
            avg_risk = analysis['factors']['geographic_risk']['avg_risk_score']
            if avg_risk > 5:
                recommendations.append(
                    f"⚠️ High geographic risk score: {avg_risk:.1f}/10. "
                    f"Review high-risk country combinations"
                )
        
        # Check browser compatibility
        if 'browser' in analysis['factors']:
            browser_impact = analysis['factors']['browser']['impact']
            if browser_impact > 0.1:
                recommendations.append(
                    f"💡 Browser compatibility impact: {browser_impact:.1%}. "
                    f"Optimize for top-performing browsers"
                )
        
        # Overall conversion rate
        overall_rate = analysis['overall_conversion_rate']
        if overall_rate < 0.8:
            recommendations.append(
                f"🎯 Overall conversion rate: {overall_rate:.1%}. "
                f"Target: >80% for optimal performance"
            )
        
        return recommendations
    
    def calculate_conversion_impact(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate potential impact of optimization on conversion"""
        analysis = self.analyze_conversion_factors(df)
        current_rate = analysis.get('overall_conversion_rate', 0)
        
        impact_predictions = {
            'current_conversion_rate': current_rate,
            'potential_improvements': {}
        }
        
        # Predict impact of IP-BIN optimization
        if 'ip_bin_match' in analysis['factors']:
            match_rate = analysis['factors']['ip_bin_match']['match_rate']
            if match_rate < 0.7:
                potential_boost = 0.15 * (0.7 - match_rate) / 0.7
                impact_predictions['potential_improvements']['ip_bin_optimization'] = potential_boost
        
        # Predict impact of data quality improvement
        if 'data_quality' in analysis['factors']:
            avg_quality = analysis['factors']['data_quality']['avg_quality_score']
            if avg_quality < 15:
                quality_boost = 0.1 * (15 - avg_quality) / 15
                impact_predictions['potential_improvements']['data_quality_improvement'] = quality_boost
        
        # Calculate total potential improvement
        total_potential = sum(impact_predictions['potential_improvements'].values())
        impact_predictions['total_potential_improvement'] = total_potential
        impact_predictions['predicted_conversion_rate'] = min(current_rate + total_potential, 1.0)
        
        return impact_predictions
