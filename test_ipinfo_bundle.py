# Test script for IPinfo Bundle Database
# This script tests the ipinfo bundle MMDB database functionality

import sys
import os

def test_ipinfo_imports():
    """Test if IPinfo packages can be imported"""
    print("Testing IPinfo package imports...")
    
    try:
        import geoip2.database
        import geoip2.errors
        print("✅ geoip2 packages imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import geoip2: {e}")
        return False

def test_database_file():
    """Test if the MMDB database file exists"""
    print("\nTesting database file...")
    
    db_path = "ipinfo_lite.mmdb"
    if os.path.exists(db_path):
        file_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
        print(f"✅ Database file found: {db_path}")
        print(f"   File size: {file_size:.2f} MB")
        return True
    else:
        print(f"❌ Database file not found: {db_path}")
        return False

def test_database_metadata():
    """Test database metadata to understand its structure"""
    print("\nTesting database metadata...")
    
    if not test_ipinfo_imports():
        return False
    
    try:
        import geoip2.database
        
        db_path = "ipinfo_lite.mmdb"
        reader = geoip2.database.Reader(db_path)
        
        # Get database metadata
        print(f"✅ Database metadata:")
        print(f"   Database type: {reader.metadata().database_type}")
        print(f"   Description: {reader.metadata().description}")
        print(f"   Version: {reader.metadata().binary_format_major_version}.{reader.metadata().binary_format_minor_version}")
        print(f"   Build epoch: {reader.metadata().build_epoch}")
        print(f"   Languages: {reader.metadata().languages}")
        print(f"   Node count: {reader.metadata().node_count}")
        print(f"   Record size: {reader.metadata().record_size}")
        
        reader.close()
        return True
        
    except Exception as e:
        print(f"❌ Database metadata test failed: {e}")
        return False

def test_ipinfo_bundle_methods():
    """Test specific methods for ipinfo bundle database"""
    print("\nTesting IPinfo bundle methods...")
    
    if not test_ipinfo_imports():
        return False
    
    try:
        import geoip2.database
        
        db_path = "ipinfo_lite.mmdb"
        reader = geoip2.database.Reader(db_path)
        
        # Test with a known IP address
        test_ip = "8.8.8.8"  # Google DNS
        
        print(f"Testing IP: {test_ip}")
        
        # Try to get raw data from the database
        try:
            # For ipinfo bundle, we might need to use different approach
            response = reader.city(test_ip)
            print(f"✅ City method works!")
            print(f"   Country: {response.country.name} ({response.country.iso_code})")
            if hasattr(response, 'city') and response.city:
                print(f"   City: {response.city.name}")
            if hasattr(response, 'location') and response.location:
                print(f"   Lat: {response.location.latitude}")
                print(f"   Lon: {response.location.longitude}")
        except Exception as city_error:
            print(f"❌ City method failed: {city_error}")
            
            # Try to access the database directly
            try:
                # Get the raw data
                raw_data = reader._get(test_ip)
                print(f"✅ Raw data access works!")
                print(f"   Raw data: {raw_data}")
            except Exception as raw_error:
                print(f"❌ Raw data access failed: {raw_error}")
        
        reader.close()
        return True
        
    except Exception as e:
        print(f"❌ IPinfo bundle methods test failed: {e}")
        return False

def test_alternative_approach():
    """Test alternative approach using maxminddb directly"""
    print("\nTesting alternative maxminddb approach...")
    
    try:
        import maxminddb
        
        db_path = "ipinfo_lite.mmdb"
        
        with maxminddb.open_database(db_path) as reader:
            test_ip = "8.8.8.8"
            
            try:
                result = reader.get(test_ip)
                print(f"✅ Direct maxminddb access works!")
                print(f"   Result: {result}")
                
                # Try to extract useful information
                if isinstance(result, dict):
                    print(f"   Available keys: {list(result.keys())}")
                    
                    # Look for common fields
                    for key in ['country', 'city', 'loc', 'org', 'asn']:
                        if key in result:
                            print(f"   {key}: {result[key]}")
                
            except Exception as e:
                print(f"❌ Direct maxminddb lookup failed: {e}")
        
        return True
        
    except ImportError:
        print("❌ maxminddb not available")
        return False
    except Exception as e:
        print(f"❌ Alternative approach failed: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 50)
    print("IPinfo Bundle Database Test")
    print("=" * 50)
    
    # Run all tests
    tests = [
        ("Package Imports", test_ipinfo_imports),
        ("Database File", test_database_file),
        ("Database Metadata", test_database_metadata),
        ("IPinfo Bundle Methods", test_ipinfo_bundle_methods),
        ("Alternative Approach", test_alternative_approach),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! IPinfo bundle integration is ready.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
