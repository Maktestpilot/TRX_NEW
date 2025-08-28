# Test script for IPinfo database integration
# This script tests the IPinfo MMDB database functionality

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

def test_database_connection():
    """Test if the database can be opened and queried"""
    print("\nTesting database connection...")
    
    if not test_ipinfo_imports():
        return False
    
    try:
        import geoip2.database
        
        db_path = "ipinfo_lite.mmdb"
        reader = geoip2.database.Reader(db_path)
        
        # Test with a known IP address - try different methods
        test_ip = "8.8.8.8"  # Google DNS
        
        # Try different database types
        try:
            # Try city database first
            response = reader.city(test_ip)
            print(f"✅ Database connection successful (City database)")
            print(f"   Test IP: {test_ip}")
            print(f"   Country: {response.country.name} ({response.country.iso_code})")
            print(f"   City: {response.city.name}")
            print(f"   Latitude: {response.location.latitude}")
            print(f"   Longitude: {response.location.longitude}")
        except Exception as city_error:
            try:
                # Try country database
                response = reader.country(test_ip)
                print(f"✅ Database connection successful (Country database)")
                print(f"   Test IP: {test_ip}")
                print(f"   Country: {response.country.name} ({response.country.iso_code})")
            except Exception as country_error:
                try:
                    # Try ASN database
                    response = reader.asn(test_ip)
                    print(f"✅ Database connection successful (ASN database)")
                    print(f"   Test IP: {test_ip}")
                    print(f"   ASN: {response.autonomous_system_number}")
                    print(f"   Organization: {response.autonomous_system_organization}")
                except Exception as asn_error:
                    print(f"❌ All database methods failed:")
                    print(f"   City: {city_error}")
                    print(f"   Country: {country_error}")
                    print(f"   ASN: {asn_error}")
                    reader.close()
                    return False
        
        reader.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_sample_ips():
    """Test with sample IP addresses from the transaction data"""
    print("\nTesting sample IP addresses...")
    
    if not test_ipinfo_imports():
        return False
    
    try:
        import geoip2.database
        
        db_path = "ipinfo_lite.mmdb"
        reader = geoip2.database.Reader(db_path)
        
        # Sample IPs from the transaction analysis report
        sample_ips = [
            "31.0.95.177",  # Poland (from report)
            "2.37.164.197", # Italy (from report)
            "8.8.8.8",      # Google DNS (known)
            "1.1.1.1",      # Cloudflare DNS (known)
        ]
        
        success_count = 0
        for ip in sample_ips:
            try:
                # Try different methods to find what works
                try:
                    response = reader.city(ip)
                    print(f"✅ {ip}: {response.country.name} ({response.country.iso_code}) - {response.city.name}")
                    success_count += 1
                except:
                    try:
                        response = reader.country(ip)
                        print(f"✅ {ip}: {response.country.name} ({response.country.iso_code})")
                        success_count += 1
                    except:
                        try:
                            response = reader.asn(ip)
                            print(f"✅ {ip}: ASN {response.autonomous_system_number} - {response.autonomous_system_organization}")
                            success_count += 1
                        except Exception as e:
                            print(f"❌ {ip}: All methods failed - {e}")
            except Exception as e:
                print(f"❌ {ip}: Error - {e}")
        
        reader.close()
        
        if success_count > 0:
            print(f"\n✅ Successfully processed {success_count}/{len(sample_ips)} IP addresses")
            return True
        else:
            print(f"\n❌ Failed to process any IP addresses")
            return False
        
    except Exception as e:
        print(f"❌ Sample IP testing failed: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 50)
    print("IPinfo Database Integration Test")
    print("=" * 50)
    
    # Run all tests
    tests = [
        ("Package Imports", test_ipinfo_imports),
        ("Database File", test_database_file),
        ("Database Connection", test_database_connection),
        ("Sample IP Testing", test_sample_ips),
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
        print("🎉 All tests passed! IPinfo integration is ready.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
