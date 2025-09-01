#!/usr/bin/env python3
"""
Simple CSV-based geolocator for testing
"""

import pandas as pd
import json
import random
from typing import Dict, Any, Optional

class SimpleGeolocator:
    """Simple geolocator that extracts IPs from transaction data and provides mock geolocation"""
    
    def __init__(self):
        self.countries = ['US', 'GB', 'DE', 'FR', 'IT', 'ES', 'NL', 'CA', 'AU', 'JP', 'CN', 'IN', 'BR', 'MX', 'RU']
        self.cities = {
            'US': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'],
            'GB': ['London', 'Manchester', 'Birmingham', 'Liverpool'],
            'DE': ['Berlin', 'Munich', 'Hamburg', 'Frankfurt'],
            'FR': ['Paris', 'Lyon', 'Marseille', 'Toulouse'],
            'IT': ['Rome', 'Milan', 'Naples', 'Turin'],
            'ES': ['Madrid', 'Barcelona', 'Valencia', 'Seville'],
            'NL': ['Amsterdam', 'Rotterdam', 'The Hague', 'Utrecht'],
            'CA': ['Toronto', 'Vancouver', 'Montreal', 'Calgary'],
            'AU': ['Sydney', 'Melbourne', 'Brisbane', 'Perth'],
            'JP': ['Tokyo', 'Osaka', 'Kyoto', 'Yokohama'],
            'CN': ['Beijing', 'Shanghai', 'Guangzhou', 'Shenzhen'],
            'IN': ['Mumbai', 'Delhi', 'Bangalore', 'Chennai'],
            'BR': ['São Paulo', 'Rio de Janeiro', 'Brasília', 'Salvador'],
            'MX': ['Mexico City', 'Guadalajara', 'Monterrey', 'Puebla'],
            'RU': ['Moscow', 'Saint Petersburg', 'Novosibirsk', 'Yekaterinburg']
        }
        
    def extract_ips_from_data(self, df: pd.DataFrame) -> list:
        """Extract unique IP addresses from transaction data"""
        ips = set()
        
        if 'body' in df.columns:
            for body_str in df['body'].dropna():
                try:
                    if isinstance(body_str, str):
                        body_data = json.loads(body_str)
                        if 'ip' in body_data:
                            ip = body_data['ip']
                            if self._is_valid_ip(ip):
                                ips.add(ip)
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
                    
        return list(ips)
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Simple IP validation"""
        if not isinstance(ip, str):
            return False
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False
    
    def get_location(self, ip: str) -> Dict[str, Any]:
        """Get mock location data for an IP"""
        if not self._is_valid_ip(ip):
            return {}
            
        # Use IP as seed for consistent results
        random.seed(hash(ip) % 1000000)
        
        country = random.choice(self.countries)
        city = random.choice(self.cities.get(country, ['Unknown']))
        
        return {
            'country': country,
            'city': city,
            'region': self._get_region(country),
            'org': f'ISP-{random.randint(1000, 9999)}',
            'asn': f'AS{random.randint(10000, 99999)}'
        }
    
    def _get_region(self, country: str) -> str:
        """Get region for country"""
        regions = {
            'US': 'NY', 'GB': 'ENG', 'DE': 'BY', 'FR': 'IDF', 'IT': 'LAZ',
            'ES': 'MD', 'NL': 'NH', 'CA': 'ON', 'AU': 'NSW', 'JP': '13',
            'CN': 'BJ', 'IN': 'MH', 'BR': 'SP', 'MX': 'CMX', 'RU': 'MOW'
        }
        return regions.get(country, 'XX')
    
    def create_ip_mapping_csv(self, df: pd.DataFrame, output_file: str = 'ip_mapping.csv'):
        """Create a CSV file with IP to location mapping"""
        ips = self.extract_ips_from_data(df)
        
        if not ips:
            print("No valid IPs found in data")
            return None
            
        print(f"Found {len(ips)} unique IPs")
        
        # Create mapping
        mapping_data = []
        for ip in ips:
            location = self.get_location(ip)
            mapping_data.append({
                'ip': ip,
                'country': location.get('country', 'Unknown'),
                'city': location.get('city', 'Unknown'),
                'region': location.get('region', 'Unknown'),
                'org': location.get('org', 'Unknown'),
                'asn': location.get('asn', 'Unknown')
            })
        
        # Save to CSV
        mapping_df = pd.DataFrame(mapping_data)
        mapping_df.to_csv(output_file, index=False)
        print(f"IP mapping saved to {output_file}")
        
        return output_file

def main():
    """Test the geolocator"""
    print("🧪 Testing Simple Geolocator...")
    
    # Load sample data
    try:
        df = pd.read_csv('sqllab_untitled_query_3_20250827T113634 Apollone  U-PROD.csv')
        print(f"Loaded {len(df)} transactions")
        
        geolocator = SimpleGeolocator()
        
        # Extract IPs
        ips = geolocator.extract_ips_from_data(df)
        print(f"Extracted {len(ips)} unique IPs")
        
        if ips:
            # Test geolocation
            test_ip = ips[0]
            location = geolocator.get_location(test_ip)
            print(f"Test IP {test_ip} -> {location}")
            
            # Create mapping file
            mapping_file = geolocator.create_ip_mapping_csv(df)
            if mapping_file:
                print(f"✅ Geolocator test successful! Mapping file: {mapping_file}")
            else:
                print("❌ Failed to create mapping file")
        else:
            print("❌ No IPs found in data")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
