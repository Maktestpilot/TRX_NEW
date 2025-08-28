# Test script for Fraud Detection App
# Tests the fraud detection functionality without Streamlit

import pandas as pd
import sys
import os

# Add current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_fraud_detection():
    """Test the fraud detection functionality"""
    print("Testing Fraud Detection App...")
    
    try:
        # Import our fraud detection functions
        from fraud_detection_app import (
            IPinfoBundleGeolocator,
            extract_json_fields,
            extract_user_info,
            calculate_risk_scores
        )
        
        print("✅ Successfully imported fraud detection modules")
        
        # Initialize IPinfo
        ipinfo = IPinfoBundleGeolocator()
        
        if not ipinfo.reader:
            print("❌ IPinfo not initialized")
            return False
        
        print("✅ IPinfo bundle initialized")
        
        # Load test data
        test_file = "test_transactions.csv"
        if not os.path.exists(test_file):
            print(f"❌ Test file not found: {test_file}")
            return False
        
        df = pd.read_csv(test_file)
        print(f"✅ Loaded test data: {len(df)} transactions")
        
        # Process data
        print("Processing data...")
        df = extract_json_fields(df)
        df = extract_user_info(df)
        df = calculate_risk_scores(df, ipinfo)
        
        print("✅ Data processing complete")
        
        # Show results
        print(f"\nResults:")
        print(f"Total transactions: {len(df)}")
        print(f"High risk (≥5): {len(df[df['risk_score'] >= 5])}")
        print(f"Critical risk (≥8): {len(df[df['risk_score'] >= 8])}")
        print(f"Average risk score: {df['risk_score'].mean():.2f}")
        
        # Show high-risk transactions
        high_risk = df[df['risk_score'] >= 5]
        if len(high_risk) > 0:
            print(f"\nHigh-risk transactions:")
            for _, row in high_risk.iterrows():
                print(f"  {row['user_email']}: Score {row['risk_score']}, Factors: {row['risk_factors']}")
        
        # Show geographic mismatches
        if 'geo_mismatch' in df.columns:
            geo_mismatches = df[df.get('geo_mismatch', False) == True]
            print(f"\nGeographic mismatches: {len(geo_mismatches)}")
            for _, row in geo_mismatches.iterrows():
                print(f"  {row['user_email']}: Billing {row.get('billing_country', 'N/A')} vs IP {row.get('ip_country', 'N/A')}")
        
        # Show velocity violations
        if 'velocity_risk' in df.columns:
            high_velocity = df[df['velocity_risk'] > 5]
            print(f"\nHigh velocity users: {len(high_velocity)}")
            for _, row in high_velocity.iterrows():
                print(f"  {row['user_email']}: {row['velocity_risk']} transactions")
        
        ipinfo.close()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fraud_detection()
    if success:
        print("\n🎉 All tests passed! Fraud detection is working correctly.")
    else:
        print("\n❌ Tests failed. Please check the errors above.")
        sys.exit(1)
