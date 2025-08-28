# IPinfo Bundle Geolocator
# Proper implementation for ipinfo bundle_location_lite.mmdb database

import json
from typing import Any, Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    import maxminddb
    MAXMINDDB_AVAILABLE = True
except ImportError:
    MAXMINDDB_AVAILABLE = False

class IPinfoBundleGeolocator:
    """IP geolocation using local IPinfo bundle MMDB database"""
    
    def __init__(self, db_path: str = "ipinfo_lite.mmdb"):
        self.db_path = db_path
        self.reader = None
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize the MMDB database reader"""
        try:
            if MAXMINDDB_AVAILABLE:
                self.reader = maxminddb.open_database(self.db_path)
                print(f"✅ IPinfo bundle database loaded: {self.db_path}")
            else:
                print("❌ maxminddb package not available")
                self.reader = None
        except Exception as e:
            print(f"❌ Failed to load IPinfo bundle database: {e}")
            self.reader = None
    
    def get_location(self, ip: str) -> Dict[str, Any]:
        """Get location information for an IP address"""
        if not self.reader or not ip:
            return {}
        
        try:
            # Clean IP address
            ip = str(ip).strip()
            if not ip or ip.lower() in ['nan', 'none', '']:
                return {}
            
            # Query the database
            result = self.reader.get(ip)
            
            if not result:
                return {}
            
            # Extract information from ipinfo bundle format
            location_data = {}
            
            # Country information
            if 'country' in result:
                location_data['country_name'] = result['country']
            if 'country_code' in result:
                location_data['country'] = result['country_code']
            
            # Continent information
            if 'continent' in result:
                location_data['continent_name'] = result['continent']
            if 'continent_code' in result:
                location_data['continent'] = result['continent_code']
            
            # ASN information
            if 'asn' in result:
                location_data['asn'] = result['asn']
            if 'as_name' in result:
                location_data['org'] = result['as_name']
            if 'as_domain' in result:
                location_data['as_domain'] = result['as_domain']
            
            # Additional fields that might be available
            for key in ['city', 'region', 'postal_code', 'latitude', 'longitude', 'timezone']:
                if key in result:
                    location_data[key] = result[key]
            
            return location_data
            
        except Exception as e:
            print(f"IP lookup error for {ip}: {e}")
            return {}
    
    def get_country(self, ip: str) -> Optional[str]:
        """Get country code for an IP address"""
        location = self.get_location(ip)
        return location.get('country')
    
    def get_country_name(self, ip: str) -> Optional[str]:
        """Get country name for an IP address"""
        location = self.get_location(ip)
        return location.get('country_name')
    
    def get_asn(self, ip: str) -> Optional[str]:
        """Get ASN for an IP address"""
        location = self.get_location(ip)
        return location.get('asn')
    
    def get_organization(self, ip: str) -> Optional[str]:
        """Get organization name for an IP address"""
        location = self.get_location(ip)
        return location.get('org')
    
    def close(self):
        """Close the database reader"""
        if self.reader:
            self.reader.close()

def test_geolocator():
    """Test the IPinfo bundle geolocator"""
    print("Testing IPinfo Bundle Geolocator...")
    
    # Test IPs from the transaction analysis report
    test_ips = [
        "31.0.95.177",  # Poland (from report)
        "2.37.164.197", # Italy (from report)
        "8.8.8.8",      # Google DNS (known)
        "1.1.1.1",      # Cloudflare DNS (known)
    ]
    
    geolocator = IPinfoBundleGeolocator()
    
    if not geolocator.reader:
        print("❌ Geolocator not initialized")
        return False
    
    print(f"\nTesting {len(test_ips)} IP addresses:")
    
    for ip in test_ips:
        try:
            location = geolocator.get_location(ip)
            if location:
                print(f"✅ {ip}:")
                print(f"   Country: {location.get('country', 'N/A')} ({location.get('country_name', 'N/A')})")
                print(f"   Continent: {location.get('continent', 'N/A')} ({location.get('continent_name', 'N/A')})")
                print(f"   ASN: {location.get('asn', 'N/A')}")
                print(f"   Organization: {location.get('org', 'N/A')}")
            else:
                print(f"❌ {ip}: No data found")
        except Exception as e:
            print(f"❌ {ip}: Error - {e}")
    
    geolocator.close()
    return True

if __name__ == "__main__":
    test_geolocator()
