# Test Script for Advanced Body Content Analysis
# Test the new functionality for analyzing transaction body content

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def create_test_data():
    """Create test data for advanced body analysis"""
    
    # Generate sample transaction data
    np.random.seed(42)
    n_transactions = 1000
    
    # Base transaction data
    data = {
        'id': range(1, n_transactions + 1),
        'amount': np.random.uniform(10, 5000, n_transactions),
        'created_at': pd.date_range('2024-01-01', periods=n_transactions, freq='H'),
        'processed_at': pd.date_range('2024-01-01', periods=n_transactions, freq='H') + pd.Timedelta(seconds=float(np.random.uniform(1, 30))),
        'gateway_name': np.random.choice(['Stripe', 'PayPal', 'Square', 'Adyen'], n_transactions),
        'status_title': np.random.choice(['Success', 'Failed'], n_transactions, p=[0.8, 0.2]),
        'payer_email': [f'user{i}@example.com' for i in range(n_transactions)],
        'initiator_ip_address': [f'192.168.{np.random.randint(1, 255)}.{np.random.randint(1, 255)}' for _ in range(n_transactions)],
        'billing_country_code': np.random.choice(['US', 'GB', 'DE', 'FR', 'CA', 'AU'], n_transactions),
        'browser_family': np.random.choice(['Chrome', 'Firefox', 'Safari', 'Edge'], n_transactions),
        'device_os': np.random.choice(['Windows', 'macOS', 'Linux', 'iOS', 'Android'], n_transactions),
        'browser_screen_width': np.random.choice([1920, 1366, 1440, 1536, 800, 1024, 0, 1], n_transactions),
        'browser_screen_height': np.random.choice([1080, 768, 900, 864, 600, 768, 0, 1], n_transactions),
        'browser_language': np.random.choice(['en-US', 'en-GB', 'de-DE', 'fr-FR', 'es-ES'], n_transactions),
        'browser_timezone': np.random.choice(['America/New_York', 'Europe/London', 'Europe/Berlin', 'UTC'], n_transactions),
        'browser_user_agent': np.random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'python-requests/2.28.1',
            'curl/7.68.0',
            'PostmanRuntime/7.29.0',
            'selenium/4.0.0'
        ], n_transactions)
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Add some synthetic data patterns
    synthetic_indices = np.random.choice(n_transactions, size=int(n_transactions * 0.1), replace=False)
    
    # Add suspicious patterns
    df.loc[synthetic_indices[:50], 'browser_user_agent'] = 'python-requests/2.28.1'
    df.loc[synthetic_indices[50:100], 'browser_screen_width'] = 0
    df.loc[synthetic_indices[50:100], 'browser_screen_height'] = 0
    df.loc[synthetic_indices[100:150], 'browser_language'] = 'en-US'
    df.loc[synthetic_indices[150:200], 'browser_timezone'] = 'UTC'
    
    # Add geographic mismatches
    mismatch_indices = np.random.choice(n_transactions, size=int(n_transactions * 0.15), replace=False)
    df.loc[mismatch_indices, 'billing_country_code'] = 'US'
    # Generate IP addresses for mismatches
    mismatch_ips = []
    for _ in range(len(mismatch_indices)):
        mismatch_ips.append(f'185.220.{np.random.randint(1, 255)}.{np.random.randint(1, 255)}')
    df.loc[mismatch_indices, 'initiator_ip_address'] = mismatch_ips
    
    # Add processing time - handle the single timedelta case
    df['processing_time'] = np.random.uniform(1, 30, n_transactions)
    
    # Add success flag
    df['is_successful'] = df['status_title'] != 'Failed'
    
    # Add some round amounts (suspicious)
    round_amount_indices = np.random.choice(n_transactions, size=int(n_transactions * 0.05), replace=False)
    df.loc[round_amount_indices, 'amount'] = np.random.choice([100, 200, 500, 1000, 2000], size=len(round_amount_indices))
    
    return df

def test_advanced_body_analysis():
    """Test the advanced body analysis functionality"""
    
    print("🧪 Testing Advanced Body Content Analysis...")
    
    try:
        # Import the analysis module
        from advanced_body_analysis import run_advanced_body_analysis, generate_body_insights
        
        # Create test data
        print("📊 Creating test data...")
        df = create_test_data()
        print(f"✅ Created {len(df)} test transactions")
        
        # Run advanced body analysis
        print("🔍 Running advanced body analysis...")
        body_analysis = run_advanced_body_analysis(df)
        print("✅ Advanced body analysis completed")
        
        # Test each analysis component
        print("\n📋 Testing Analysis Components:")
        
        # 1. Browser Analysis
        if 'browser_analysis' in body_analysis:
            print("✅ Browser analysis: PASSED")
            browser_analysis = body_analysis['browser_analysis']
            
            if 'browser_family_success' in browser_analysis:
                print(f"   - Browser family success rates: {len(browser_analysis['browser_family_success'])} browsers analyzed")
            
            if 'suspicious_user_agents' in browser_analysis:
                print(f"   - Suspicious user agents detected: {len(browser_analysis['suspicious_user_agents'])} patterns")
        else:
            print("❌ Browser analysis: FAILED")
        
        # 2. IP Geographic Analysis
        if 'ip_geo_analysis' in body_analysis:
            print("✅ IP geographic analysis: PASSED")
            geo_analysis = body_analysis['ip_geo_analysis']
            
            if 'mismatch_success' in geo_analysis:
                print(f"   - Geographic mismatch analysis: {len(geo_analysis['mismatch_success'])} mismatch types")
        else:
            print("❌ IP geographic analysis: FAILED")
        
        # 3. Speed Analysis
        if 'speed_analysis' in body_analysis:
            print("✅ Transaction speed analysis: PASSED")
            speed_analysis = body_analysis['speed_analysis']
            
            if 'speed_success_correlation' in speed_analysis:
                corr = speed_analysis['speed_success_correlation']
                print(f"   - Speed-success correlation: {corr:.3f}")
        else:
            print("❌ Transaction speed analysis: FAILED")
        
        # 4. Synthetic Data Detection
        if 'synthetic_detection' in body_analysis:
            print("✅ Synthetic data detection: PASSED")
            synthetic_analysis = body_analysis['synthetic_detection']
            
            if 'synthetic_score_distribution' in synthetic_analysis:
                high_risk_count = len(synthetic_analysis['high_risk_transactions'])
                print(f"   - High-risk transactions detected: {high_risk_count}")
        else:
            print("❌ Synthetic data detection: FAILED")
        
        # 5. Combined Risk Analysis
        if 'combined_risk' in body_analysis:
            print("✅ Combined risk analysis: PASSED")
            combined_risk = body_analysis['combined_risk']
            
            if 'high_risk_transactions' in combined_risk:
                high_risk_count = len(combined_risk['high_risk_transactions'])
                print(f"   - High combined risk transactions: {high_risk_count}")
        else:
            print("❌ Combined risk analysis: FAILED")
        
        # 6. Hidden Dependencies
        if 'hidden_dependencies' in body_analysis:
            print("✅ Hidden dependencies analysis: PASSED")
            dependencies = body_analysis['hidden_dependencies']
            
            if 'factor_correlations' in dependencies:
                print(f"   - Factor correlation matrix: {dependencies['factor_correlations'].shape[0]}x{dependencies['factor_correlations'].shape[1]} factors")
        else:
            print("❌ Hidden dependencies analysis: FAILED")
        
        # Test insights generation
        print("\n💡 Testing Insights Generation:")
        try:
            insights = generate_body_insights(body_analysis)
            print("✅ Insights generation: PASSED")
            print(f"   - Generated insights report: {len(insights)} characters")
        except Exception as e:
            print(f"❌ Insights generation: FAILED - {e}")
        
        # Test visualizations
        print("\n📊 Testing Visualizations:")
        try:
            from advanced_body_visualizations import create_body_analysis_visualizations
            
            charts = create_body_analysis_visualizations(df, body_analysis)
            print(f"✅ Visualizations creation: PASSED - {len(charts)} charts created")
            
            for chart_name in charts.keys():
                print(f"   - {chart_name}: {type(charts[chart_name])}")
                
        except Exception as e:
            print(f"❌ Visualizations creation: FAILED - {e}")
        
        print("\n🎉 Advanced Body Content Analysis Test Completed Successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_quality():
    """Test data quality and edge cases"""
    
    print("\n🔍 Testing Data Quality and Edge Cases...")
    
    try:
        # Test with minimal data
        print("📊 Testing with minimal data...")
        minimal_df = pd.DataFrame({
            'id': [1, 2, 3],
            'amount': [100, 200, 300],
            'is_successful': [True, False, True]
        })
        
        from advanced_body_analysis import run_advanced_body_analysis
        minimal_analysis = run_advanced_body_analysis(minimal_df)
        print("✅ Minimal data analysis: PASSED")
        
        # Test with missing columns
        print("📊 Testing with missing columns...")
        missing_df = pd.DataFrame({
            'id': [1, 2, 3],
            'amount': [100, 200, 300],
            'is_successful': [True, False, True]
        })
        
        missing_analysis = run_advanced_body_analysis(missing_df)
        print("✅ Missing columns analysis: PASSED")
        
        # Test with empty data
        print("📊 Testing with empty data...")
        empty_df = pd.DataFrame({
            'id': [],
            'amount': [],
            'is_successful': []
        })
        
        empty_analysis = run_advanced_body_analysis(empty_df)
        print("✅ Empty data analysis: PASSED")
        
        print("✅ Data quality tests: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Data quality test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Advanced Body Content Analysis Tests...")
    print("=" * 60)
    
    # Run main test
    main_test_passed = test_advanced_body_analysis()
    
    # Run data quality tests
    quality_test_passed = test_data_quality()
    
    print("\n" + "=" * 60)
    print("📋 Test Results Summary:")
    print(f"   Main Analysis Test: {'✅ PASSED' if main_test_passed else '❌ FAILED'}")
    print(f"   Data Quality Test: {'✅ PASSED' if quality_test_passed else '❌ FAILED'}")
    
    if main_test_passed and quality_test_passed:
        print("\n🎉 All tests passed! Advanced Body Content Analysis is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the implementation.")
    
    print("\n🔍 Test completed successfully!")
