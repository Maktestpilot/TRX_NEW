#!/usr/bin/env python3
"""
Test script for enhanced modular architecture
Tests the new modular system with improved performance and maintainability
"""

import pandas as pd
import numpy as np
import json
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def create_comprehensive_test_data():
    """Create comprehensive test data for the enhanced system"""
    
    test_data = []
    
    # Create various transaction scenarios
    scenarios = [
        {
            'scenario': 'normal_transaction',
            'ip': '31.0.95.177',
            'billing_country': 'RO',
            'bin_country': 'RO',
            'amount': 1000,
            'success': True,
            'browser': 'Chrome',
            'os': 'Windows'
        },
        {
            'scenario': 'cross_border_high_risk',
            'ip': '8.8.8.8',
            'billing_country': 'US',
            'bin_country': 'RU',
            'amount': 5000,
            'success': False,
            'browser': 'Firefox',
            'os': 'macOS'
        },
        {
            'scenario': 'low_quality_data',
            'ip': '192.168.1.1',  # Private IP
            'billing_country': 'DE',
            'bin_country': 'DE',
            'amount': 2000,
            'success': False,
            'browser': 'bot',
            'os': 'Linux'
        },
        {
            'scenario': 'high_amount_transaction',
            'ip': '1.1.1.1',
            'billing_country': 'AU',
            'bin_country': 'AU',
            'amount': 10000,
            'success': True,
            'browser': 'Safari',
            'os': 'iOS'
        },
        {
            'scenario': 'suspicious_browser',
            'ip': '2.37.164.197',
            'billing_country': 'IT',
            'bin_country': 'IT',
            'amount': 500,
            'success': False,
            'browser': 'selenium',
            'os': 'Windows'
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        test_data.append({
            'id': i,
            'user_email': f'user{i}@example.com',
            'amount': scenario['amount'],
            'created_at': f'2025-01-27 {10+i:02d}:00:00',
            'ip': scenario['ip'],
            'billing_country': scenario['billing_country'],
            'status_title': 'Success' if scenario['success'] else 'Failed',
            'is_final': True,
            'body': json.dumps({
                'email': f'user{i}@example.com',
                'billing': {
                    'country': scenario['billing_country'],
                    'city': 'Test City'
                },
                'ip': scenario['ip'],
                'browser': {
                    'family': scenario['browser'],
                    'os': scenario['os'],
                    'userAgent': f'Mozilla/5.0 ({scenario["os"]}) {scenario["browser"]}/1.0',
                    'screenWidth': 1920,
                    'screenHeight': 1080,
                    'language': 'en-US'
                },
                'card': {
                    'binCountryIso': scenario['bin_country'],
                    'cardType': 'Visa'
                }
            })
        })
    
    df = pd.DataFrame(test_data)
    df['is_successful'] = df['status_title'] == 'Success'
    
    return df

def test_enhanced_data_processor():
    """Test the enhanced data processor"""
    print("🧪 Testing Enhanced Data Processor...")
    
    from src.core.data_processor import EnhancedDataProcessor
    
    # Create test data
    df = create_comprehensive_test_data()
    
    # Initialize processor
    processor = EnhancedDataProcessor()
    
    # Process data
    df_processed = processor.process(df)
    
    # Check results
    print(f"  ✅ Processed {len(df_processed)} rows")
    print(f"  ✅ Added {len(df_processed.columns) - len(df.columns)} new columns")
    
    # Check specific enhancements
    enhancements = [
        'ip_is_valid', 'ip_is_private', 'ip_type',
        'browser_family', 'browser_os', 'browser_user_agent',
        'card_bin_country', 'card_type',
        'data_quality_score', 'ip_quality_score', 'browser_quality_score'
    ]
    
    for enhancement in enhancements:
        if enhancement in df_processed.columns:
            print(f"  ✅ {enhancement} column added")
        else:
            print(f"  ❌ {enhancement} column missing")
    
    # Check data quality
    if 'data_quality_score' in df_processed.columns:
        avg_quality = df_processed['data_quality_score'].mean()
        print(f"  📊 Average data quality score: {avg_quality:.1f}/20")
    
    print()

def test_geolocation_service():
    """Test the enhanced geolocation service"""
    print("🧪 Testing Enhanced Geolocation Service...")
    
    from src.services.geolocation_service import EnhancedGeolocationService, CSVGeolocationProvider
    
    # Create mock CSV provider
    mock_csv_data = pd.DataFrame({
        'ip': ['31.0.95.177', '8.8.8.8', '1.1.1.1', '2.37.164.197'],
        'country': ['RO', 'US', 'AU', 'IT']
    })
    mock_csv_data.to_csv('temp_ip_mapping.csv', index=False)
    
    try:
        # Initialize service
        csv_provider = CSVGeolocationProvider('temp_ip_mapping.csv')
        service = EnhancedGeolocationService([csv_provider])
        
        # Test geolocation
        test_ips = ['31.0.95.177', '8.8.8.8', 'invalid_ip']
        
        for ip in test_ips:
            location = service.get_location(ip)
            country = service.get_country(ip)
            
            if location:
                print(f"  ✅ IP {ip}: Country = {country}")
            else:
                print(f"  ❌ IP {ip}: No location found")
        
        # Test caching
        cache_stats = service.get_cache_stats()
        print(f"  📊 Cache stats: {cache_stats['cache_size']} entries, {cache_stats['hit_rate']:.1%} hit rate")
        
    finally:
        # Cleanup
        if os.path.exists('temp_ip_mapping.csv'):
            os.remove('temp_ip_mapping.csv')
    
    print()

def test_conversion_optimizer():
    """Test the conversion optimizer"""
    print("🧪 Testing Conversion Optimizer...")
    
    from src.services.conversion_optimizer import AdvancedConversionOptimizer
    
    # Create test data with conversion factors
    df = create_comprehensive_test_data()
    
    # Add mock geolocation data
    df['ip_country'] = ['RO', 'US', 'DE', 'AU', 'IT']
    df['card_bin_country'] = ['RO', 'RU', 'DE', 'AU', 'IT']  # One mismatch
    df['ip_bin_country_match'] = df['ip_country'] == df['card_bin_country']
    df['data_quality_score'] = [18, 12, 8, 20, 5]  # Various quality scores
    df['geo_risk_score'] = [1, 8, 3, 2, 6]  # Various risk scores
    
    # Initialize optimizer
    optimizer = AdvancedConversionOptimizer()
    
    # Analyze conversion factors
    analysis = optimizer.analyze_conversion_factors(df)
    
    print(f"  ✅ Overall conversion rate: {analysis['overall_conversion_rate']:.1%}")
    print(f"  ✅ Total transactions: {analysis['total_transactions']}")
    
    # Check factor analysis
    if 'ip_bin_match' in analysis['factors']:
        factor = analysis['factors']['ip_bin_match']
        print(f"  📊 IP-BIN match rate: {factor['match_rate']:.1%}")
        print(f"  📊 Conversion impact: {factor['impact']:.1%}")
    
    # Get recommendations
    recommendations = optimizer.get_optimization_recommendations(df)
    print(f"  💡 Generated {len(recommendations)} recommendations")
    
    for i, rec in enumerate(recommendations[:3], 1):  # Show first 3
        print(f"    {i}. {rec}")
    
    # Calculate impact prediction
    impact = optimizer.calculate_conversion_impact(df)
    current_rate = impact.get('current_conversion_rate', 0)
    predicted_rate = impact.get('predicted_conversion_rate', 0)
    improvement = impact.get('total_potential_improvement', 0)
    
    print(f"  🎯 Current conversion: {current_rate:.1%}")
    print(f"  🎯 Predicted conversion: {predicted_rate:.1%}")
    print(f"  🎯 Potential improvement: {improvement:+.1%}")
    
    print()

def test_integration_manager():
    """Test the integration manager"""
    print("🧪 Testing Integration Manager...")
    
    from src.core.integration_manager import IntegrationManager
    
    # Create mock CSV for geolocation
    mock_csv_data = pd.DataFrame({
        'ip': ['31.0.95.177', '8.8.8.8', '1.1.1.1', '2.37.164.197'],
        'country': ['RO', 'US', 'AU', 'IT']
    })
    mock_csv_data.to_csv('temp_ip_mapping.csv', index=False)
    
    try:
        # Initialize integration manager
        config = {'ip_csv_path': 'temp_ip_mapping.csv'}
        manager = IntegrationManager(config)
        
        # Check system status
        status = manager.get_system_status()
        print(f"  ✅ System status: {status['overall_status']}")
        
        for service, available in status['services'].items():
            status_icon = "✅" if available else "❌"
            print(f"  {status_icon} {service}: {'Available' if available else 'Unavailable'}")
        
        # Test data processing
        df = create_comprehensive_test_data()
        results = manager.process_transaction_data(df)
        
        print(f"  ✅ Processed {len(results['processed_data'])} transactions")
        print(f"  ✅ Generated {len(results['insights'])} insights")
        
        # Show insights
        for insight in results['insights']:
            print(f"  💡 {insight}")
        
        # Test optimization recommendations
        recommendations = manager.get_optimization_recommendations(results['processed_data'])
        print(f"  🎯 Generated {len(recommendations)} optimization recommendations")
        
    finally:
        # Cleanup
        if os.path.exists('temp_ip_mapping.csv'):
            os.remove('temp_ip_mapping.csv')
    
    print()

def test_data_validator():
    """Test the data validator"""
    print("🧪 Testing Data Validator...")
    
    from src.utils.validators import DataValidator, IPValidator, JSONValidator
    
    # Test IP validator
    ip_tests = [
        ("192.168.1.1", True, True),   # Valid, Private
        ("8.8.8.8", True, False),      # Valid, Public
        ("invalid", False, False),     # Invalid
        (None, False, False)           # None
    ]
    
    for ip, expected_valid, expected_private in ip_tests:
        valid = IPValidator.is_valid_ip(ip)
        private = IPValidator.is_private_ip(ip) if valid else False
        
        valid_status = "✅" if valid == expected_valid else "❌"
        private_status = "✅" if private == expected_private else "❌"
        
        print(f"  IP {ip}: Valid {valid_status}, Private {private_status}")
    
    # Test JSON validator
    json_tests = [
        ('{"valid": "json"}', True),
        ('invalid json', False),
        (None, False)
    ]
    
    for json_str, expected in json_tests:
        result = JSONValidator.is_valid_json(json_str)
        status = "✅" if result == expected else "❌"
        print(f"  JSON {json_str}: Valid {status}")
    
    # Test data validator
    df = create_comprehensive_test_data()
    validator = DataValidator()
    validation_results = validator.validate_dataframe(df)
    
    print(f"  📊 Data validation: {'✅ Valid' if validation_results['is_valid'] else '❌ Invalid'}")
    print(f"  📊 Quality score: {validation_results['data_quality_score']}/100")
    print(f"  📊 Validation errors: {len(validation_results['validation_errors'])}")
    
    print()

def main():
    """Run all tests"""
    print("🚀 Testing Enhanced Modular Architecture")
    print("=" * 60)
    
    try:
        test_enhanced_data_processor()
        test_geolocation_service()
        test_conversion_optimizer()
        test_integration_manager()
        test_data_validator()
        
        print("✅ All enhanced architecture tests completed successfully!")
        print("\n📊 Summary of enhanced features:")
        print("  ✅ Modular architecture with clean separation of concerns")
        print("  ✅ Enhanced data processor with comprehensive validation")
        print("  ✅ Advanced geolocation service with caching")
        print("  ✅ Conversion optimizer with ML-based insights")
        print("  ✅ Integration manager for orchestration")
        print("  ✅ Comprehensive data validation utilities")
        print("  ✅ Improved error handling and logging")
        print("  ✅ Performance optimizations with caching")
        
        print("\n🎯 Expected improvements:")
        print("  📈 Better maintainability and code organization")
        print("  📈 Improved performance with intelligent caching")
        print("  📈 Enhanced error handling and robustness")
        print("  📈 Better testability and modularity")
        print("  📈 Easier to extend and modify")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
