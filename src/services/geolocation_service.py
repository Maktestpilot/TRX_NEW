"""
Enhanced Geolocation Service
Supports multiple providers with fallback mechanisms
"""

import logging
from typing import Dict, List, Optional, Any
import pandas as pd
from ..core.interfaces import GeolocationProvider


class IPinfoGeolocationProvider(GeolocationProvider):
    """IPinfo MMDB-based geolocation provider"""
    
    def __init__(self, mmdb_path: str):
        self.mmdb_path = mmdb_path
        self._reader = None
        self._initialize()
    
    def _initialize(self):
        """Initialize MMDB reader"""
        try:
            import maxminddb
            self._reader = maxminddb.open_database(self.mmdb_path)
            logging.info(f"IPinfo MMDB initialized: {self.mmdb_path}")
        except Exception as e:
            logging.error(f"Failed to initialize IPinfo MMDB: {e}")
            self._reader = None
    
    def get_location(self, ip: str) -> Optional[Dict[str, Any]]:
        """Get complete location information"""
        if not self._reader or not ip:
            return None
        
        try:
            result = self._reader.get(ip)
            if result:
                return {
                    'country': result.get('country', {}).get('iso_code'),
                    'country_name': result.get('country', {}).get('names', {}).get('en'),
                    'region': result.get('subdivisions', [{}])[0].get('names', {}).get('en'),
                    'city': result.get('city', {}).get('names', {}).get('en'),
                    'latitude': result.get('location', {}).get('latitude'),
                    'longitude': result.get('location', {}).get('longitude'),
                    'timezone': result.get('location', {}).get('time_zone'),
                    'postal_code': result.get('postal', {}).get('code'),
                    'asn': result.get('traits', {}).get('autonomous_system_number'),
                    'org': result.get('traits', {}).get('autonomous_system_organization'),
                    'accuracy_radius': result.get('location', {}).get('accuracy_radius'),
                    'metro_code': result.get('location', {}).get('metro_code')
                }
        except Exception as e:
            logging.warning(f"Error geolocating IP {ip}: {e}")
        
        return None
    
    def get_country(self, ip: str) -> Optional[str]:
        """Get country code for IP"""
        location = self.get_location(ip)
        return location.get('country') if location else None
    
    def get_asn(self, ip: str) -> Optional[str]:
        """Get ASN for IP"""
        location = self.get_location(ip)
        return location.get('asn') if location else None
    
    def is_available(self) -> bool:
        """Check if service is available"""
        return self._reader is not None


class CSVGeolocationProvider(GeolocationProvider):
    """CSV-based geolocation provider (fallback)"""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._ip_mapping = {}
        self._load_mapping()
    
    def _load_mapping(self):
        """Load IP mapping from CSV"""
        try:
            df = pd.read_csv(self.csv_path)
            self._ip_mapping = dict(zip(df['ip'], df['country']))
            logging.info(f"Loaded {len(self._ip_mapping)} IP mappings from CSV")
        except Exception as e:
            logging.error(f"Failed to load IP mapping CSV: {e}")
            self._ip_mapping = {}
    
    def get_location(self, ip: str) -> Optional[Dict[str, Any]]:
        """Get location from CSV mapping"""
        if ip in self._ip_mapping:
            return {
                'country': self._ip_mapping[ip],
                'country_name': self._ip_mapping[ip],
                'region': None,
                'city': None,
                'latitude': None,
                'longitude': None,
                'timezone': None,
                'postal_code': None,
                'asn': None,
                'org': None,
                'accuracy_radius': None,
                'metro_code': None
            }
        return None
    
    def get_country(self, ip: str) -> Optional[str]:
        """Get country from CSV mapping"""
        return self._ip_mapping.get(ip)
    
    def get_asn(self, ip: str) -> Optional[str]:
        """CSV provider doesn't support ASN"""
        return None
    
    def is_available(self) -> bool:
        """Check if CSV mapping is loaded"""
        return len(self._ip_mapping) > 0


class MockGeolocationProvider(GeolocationProvider):
    """Mock geolocation provider for testing"""
    
    def get_location(self, ip: str) -> Optional[Dict[str, Any]]:
        """Return mock location data"""
        return {
            'country': 'US',
            'city': 'New York',
            'region': 'NY',
            'org': 'Mock ISP',
            'asn': 'AS12345'
        }
    
    def get_country(self, ip: str) -> Optional[str]:
        """Return mock country"""
        return 'US'
    
    def get_asn(self, ip: str) -> Optional[str]:
        """Return mock ASN"""
        return 'AS12345'
    
    def is_available(self) -> bool:
        """Mock provider is always available"""
        return True


class GeolocationService:
    """Enhanced geolocation service with multiple providers and caching"""
    
    def __init__(self, providers: List[GeolocationProvider]):
        self.providers = providers
        self._cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_location(self, ip: str) -> Optional[Dict[str, Any]]:
        """Get location with caching and fallback"""
        if not ip:
            return None
        
        # Check cache first
        if ip in self._cache:
            self._cache_hits += 1
            return self._cache[ip]
        
        self._cache_misses += 1
        
        # Try providers in order
        for provider in self.providers:
            if provider.is_available():
                try:
                    location = provider.get_location(ip)
                    if location:
                        self._cache[ip] = location
                        return location
                except Exception as e:
                    logging.warning(f"Provider {type(provider).__name__} failed for IP {ip}: {e}")
                    continue
        
        # Cache negative result
        self._cache[ip] = None
        return None
    
    def get_country(self, ip: str) -> Optional[str]:
        """Get country with caching"""
        location = self.get_location(ip)
        return location.get('country') if location else None
    
    def get_asn(self, ip: str) -> Optional[str]:
        """Get ASN with caching"""
        location = self.get_location(ip)
        return location.get('asn') if location else None
    
    def enrich_dataframe(self, df: pd.DataFrame, ip_column: str = 'ip_address') -> pd.DataFrame:
        """Enrich DataFrame with geolocation data"""
        if ip_column not in df.columns:
            logging.warning(f"IP column '{ip_column}' not found in DataFrame")
            return df
        
        # Get unique IPs to minimize API calls
        unique_ips = df[ip_column].dropna().unique()
        
        # Process each unique IP
        for ip in unique_ips:
            location = self.get_location(ip)
            if location:
                # Apply location data to all rows with this IP
                mask = df[ip_column] == ip
                for key, value in location.items():
                    df.loc[mask, f'ip_{key}'] = value
        
        return df
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get caching statistics"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            'cache_size': len(self._cache),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }
    
    def clear_cache(self):
        """Clear geolocation cache"""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logging.info("Geolocation cache cleared")
