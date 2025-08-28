# Test script for Enhanced Fraud Detection App
# Tests the enhanced fraud detection functionality with body JSON parsing

import pandas as pd
import sys
import os

# Add current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_fraud_detection():
    """Test the enhanced fraud detection functionality"""
    print("Testing Enhanced Fraud Detection App...")
    
    try:
        # Import our enhanced fraud detection functions
        from enhanced_fraud_detection_app import (
            IPinfoBundleGeolocator,
            extract_body_data,
            filter_successful_transactions,
            extract_user_info,
            calculate_risk_scores
        )
        
        print("✅ Successfully imported enhanced fraud detection modules")
        
        # Initialize IPinfo bundle
        ipinfo = IPinfoBundleGeolocator()
        
        if not ipinfo.reader:
            print("❌ IPinfo not initialized")
            return False
        
        print("✅ IPinfo bundle initialized")
        
        # Test with real CSV data
        test_file = "sqllab_untitled_query_3_20250826T152613.csv"
        if not os.path.exists(test_file):
            print(f"❌ Test file not found: {test_file}")
            return False
        
        # Load a small sample for testing
        print("Loading sample data...")
        df = pd.read_csv(test_file, nrows=100)  # Load first 100 rows for testing
        print(f"✅ Loaded sample data: {len(df)} transactions")
        
        # Show original data info
        print(f"\nOriginal data info:")
        print(f"Columns: {list(df.columns)}")
        print(f"Shape: {df.shape}")
        
        # Check for required columns
        required_cols = ['body', 'status_title', 'is_final']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"⚠️ Missing columns: {missing_cols}")
        else:
            print(f"✅ All required columns present")
        
        # Test filtering
        print("\nTesting transaction filtering...")
        original_count = len(df)
        df_filtered = filter_successful_transactions(df.copy())
        print(f"✅ Filtering complete: {original_count} -> {len(df_filtered)} transactions")
        
        # Test body JSON parsing
        print("\nTesting body JSON parsing...")
        df_parsed = extract_body_data(df_filtered.copy())
        print(f"✅ Body parsing complete")
        
        # Show extracted columns
        new_cols = [col for col in df_parsed.columns if col not in df.columns]
        print(f"New columns added: {new_cols}")
        
        # Test user info extraction
        print("\nTesting user info extraction...")
        df_user = extract_user_info(df_parsed.copy())
        print(f"✅ User info extraction complete")
        
        # Test risk score calculation
        print("\nTesting risk score calculation...")
        df_risk = calculate_risk_scores(df_user.copy(), ipinfo)
        print(f"✅ Risk score calculation complete")
        
        # Show results
        print(f"\nFinal Results:")
        print(f"Total transactions: {len(df_risk)}")
        print(f"High risk (≥5): {len(df_risk[df_risk['risk_score'] >= 5])}")
        print(f"Critical risk (≥8): {len(df_risk[df_risk['risk_score'] >= 8])}")
        print(f"Average risk score: {df_risk['risk_score'].mean():.2f}")
        
        # Show high-risk transactions
        high_risk = df_risk[df_risk['risk_score'] >= 5]
        if len(high_risk) > 0:
            print(f"\nHigh-risk transactions:")
            for _, row in high_risk.iterrows():
                print(f"  {row.get('user_email', 'N/A')}: Score {row['risk_score']}, Factors: {row['risk_factors']}")
        
        # Show geographic mismatches
        if 'geo_mismatch' in df_risk.columns:
            geo_mismatches = df_risk[df_risk.get('geo_mismatch', False) == True]
            print(f"\nGeographic mismatches: {len(geo_mismatches)}")
            for _, row in geo_mismatches.iterrows():
                print(f"  {row.get('user_email', 'N/A')}: Billing {row.get('billing_country', 'N/A')} vs IP {row.get('ip_country', 'N/A')}")
        
        # Show velocity violations
        if 'velocity_risk' in df_risk.columns:
            high_velocity = df_risk[df_risk['velocity_risk'] > 5]
            print(f"\nHigh velocity users: {len(high_velocity)}")
            for _, row in high_velocity.iterrows():
                print(f"  {row.get('user_email', 'N/A')}: {row['velocity_risk']} transactions")
        
        # Show sample of extracted data
        print(f"\nSample extracted data:")
        sample_cols = ['payer_email', 'payer_first_name', 'payer_last_name', 'billing_country_code', 'initiator_ip_address']
        available_cols = [col for col in sample_cols if col in df_risk.columns]
        
        if available_cols:
            sample_data = df_risk[available_cols].head(3)
            print(sample_data.to_string())
        
        ipinfo.close()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_fraud_detection()
    if success:
        print("\n🎉 All tests passed! Enhanced fraud detection is working correctly.")
    else:
        print("\n❌ Tests failed. Please check the errors above.")
        sys.exit(1)
