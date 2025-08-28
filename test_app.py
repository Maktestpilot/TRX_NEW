# test_app.py
# Simple test script to verify the geographic analysis application functions

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Import functions from the main app
from geographic_analysis_app import (
    try_parse_json,
    deep_get,
    normalize_country_code,
    categorize_decline_reason,
    calculate_geographic_mismatch_score,
    calculate_data_quality_score,
    get_week_key,
    get_month_key
)

def create_sample_data():
    """Create sample transaction data for testing"""
    
    # Sample JSON billing data
    sample_billing = {
        "billing": {
            "country": "AU",
            "address": "123 Main St",
            "city": "Sydney",
            "zip": "2000"
        },
        "browser": {
            "language": "en-AU"
        }
    }
    
    # Sample data
    data = {
        'created_at': [
            '2025-08-26 10:00:00',
            '2025-08-26 11:00:00',
            '2025-08-26 12:00:00',
            '2025-08-26 13:00:00',
            '2025-08-26 14:00:00'
        ],
        'user_email': ['user1@test.com', 'user2@test.com', 'user3@test.com', 'user4@test.com', 'user5@test.com'],
        'amount': [1000, 2000, 3000, 4000, 5000],
        'currency': ['EUR', 'EUR', 'EUR', 'EUR', 'EUR'],
        'status': ['approved', 'declined', 'approved', 'declined', 'approved'],
        'gateway_code': [200, 37, 200, 37, 200],
        'gateway_message': [
            'Transaction approved',
            'Client verification unsuccessful',
            'Transaction approved',
            'Client verification unsuccessful',
            'Transaction approved'
        ],
        'bin_country': ['AU', 'DE', 'IT', 'HU', 'AU'],
        'ip_country': ['AU', 'DE', 'IT', 'HU', 'US'],
        'ip_address': ['192.168.1.1', '192.168.1.2', '192.168.1.3', '192.168.1.4', '192.168.1.5'],
        'billing_country': ['AU', 'DE', 'IT', 'HU', 'AU'],
        'billing_address': ['123 Main St', '456 Hauptstr', '789 Via Roma', '321 Fő utca', '123 Main St'],
        'user_agent': ['Mozilla/5.0...', 'Mozilla/5.0...', 'Mozilla/5.0...', 'Mozilla/5.0...', 'Mozilla/5.0...'],
        'browser_language': ['en-AU', 'de-DE', 'it-IT', 'hu-HU', 'en-AU'],
        'body': [json.dumps(sample_billing)] * 5
    }
    
    return pd.DataFrame(data)

def test_helper_functions():
    """Test all helper functions"""
    print("🧪 Testing Helper Functions...")
    
    # Test JSON parsing
    test_json = '{"billing": {"country": "AU"}}'
    result = try_parse_json(test_json)
    assert result is not None
    assert result['billing']['country'] == 'AU'
    print("✅ JSON parsing: PASSED")
    
    # Test deep_get
    test_data = {"billing": {"address": {"country": "DE"}}}
    result = deep_get(test_data, [['billing', 'address', 'country'], ['billing', 'country']])
    assert result == 'DE'
    print("✅ Deep get: PASSED")
    
    # Test country code normalization
    result = normalize_country_code('Australia')
    assert result == 'AU'
    result = normalize_country_code('DE')
    assert result == 'DE'
    print("✅ Country code normalization: PASSED")
    
    # Test decline categorization
    result = categorize_decline_reason(37, 'Client verification unsuccessful')
    assert result == 'user_error'
    result = categorize_decline_reason(200, 'Transaction approved')
    assert result == 'Other'
    print("✅ Decline categorization: PASSED")
    
    # Test week and month keys
    result = get_week_key('2025-08-26')
    assert '2025-W' in result
    result = get_month_key('2025-08-26')
    assert result == '2025-08'
    print("✅ Time key generation: PASSED")

def test_analysis_functions():
    """Test analysis functions with sample data"""
    print("\n🧪 Testing Analysis Functions...")
    
    # Create sample data
    df = create_sample_data()
    
    # Test geographic mismatch scoring
    df['geographic_mismatch_score'] = df.apply(calculate_geographic_mismatch_score, axis=1)
    print(f"✅ Geographic mismatch scores calculated: {df['geographic_mismatch_score'].tolist()}")
    
    # Test data quality scoring
    df['data_quality_score'] = df.apply(calculate_data_quality_score, axis=1)
    print(f"✅ Data quality scores calculated: {df['data_quality_score'].tolist()}")
    
    # Test success classification
    df['is_success'] = df['status'].isin(['approved'])
    success_rate = (df['is_success'].sum() / len(df)) * 100
    print(f"✅ Success rate calculated: {success_rate:.1f}%")
    
    # Test decline categorization
    df['decline_category'] = df.apply(
        lambda x: categorize_decline_reason(x['gateway_code'], x['gateway_message']), axis=1
    )
    print(f"✅ Decline categories: {df['decline_category'].tolist()}")

def test_data_processing():
    """Test data processing capabilities"""
    print("\n🧪 Testing Data Processing...")
    
    # Test with different column name variations
    test_data = {
        'created_at': ['2025-08-26 10:00:00'],
        'payment_status_code': ['approved'],
        'gateway_code': [200],
        'body': ['{"billing": {"country": "AU"}}']
    }
    
    df = pd.DataFrame(test_data)
    
    # Test column detection
    col_created = next((c for c in df.columns if 'created_at' in c.lower()), None)
    col_status = next((c for c in df.columns if c.lower() in ['payment_status_code', 'status']), None)
    col_gateway_code = next((c for c in df.columns if 'gateway_code' in c.lower()), None)
    
    assert col_created == 'created_at'
    assert col_status == 'payment_status_code'
    assert col_gateway_code == 'gateway_code'
    print("✅ Column detection: PASSED")
    
    # Test JSON parsing from body
    json_cols = ["body", "request_payload", "response_payload", "payload"]
    json_cols = [c for c in json_cols if c in df.columns]
    
    billing_country = []
    for _, row in df.iterrows():
        parsed = None
        for jc in json_cols:
            parsed = try_parse_json(row[jc])
            if parsed:
                break
        
        if parsed:
            bc = deep_get(parsed, [['billing', 'country'], ['billing_address', 'country'], ['address', 'country']])
            billing_country.append(normalize_country_code(bc))
        else:
            billing_country.append(None)
    
    assert billing_country[0] == 'AU'
    print("✅ JSON parsing and billing extraction: PASSED")

def main():
    """Run all tests"""
    print("🚀 Starting Geographic Analysis Application Tests...\n")
    
    try:
        test_helper_functions()
        test_analysis_functions()
        test_data_processing()
        
        print("\n🎉 All tests passed successfully!")
        print("✅ The application is ready to use!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
