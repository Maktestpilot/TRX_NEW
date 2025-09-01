#!/usr/bin/env python3
"""
Setup script to download and configure IPinfo MMDB
"""

import os
import sys
from pathlib import Path

def setup_ipinfo():
    """Setup IPinfo MMDB database"""
    try:
        from ipinfo_db import IPInfo
        
        print("🔍 Initializing IPinfo...")
        ipinfo = IPInfo()
        
        print("📥 Downloading IPinfo MMDB...")
        ipinfo.download()
        
        # Find the downloaded file
        current_dir = Path.cwd()
        mmdb_files = list(current_dir.glob("*.mmdb"))
        
        if mmdb_files:
            mmdb_file = mmdb_files[0]
            print(f"✅ IPinfo MMDB downloaded: {mmdb_file}")
            
            # Test the database
            print("🧪 Testing IPinfo database...")
            test_ip = "8.8.8.8"
            location = ipinfo.get_location(test_ip)
            if location:
                print(f"✅ Test successful: {test_ip} -> {location.get('country', 'Unknown')}")
            else:
                print("⚠️ Test failed: No location data returned")
                
            return str(mmdb_file)
        else:
            print("❌ No MMDB file found after download")
            return None
            
    except ImportError:
        print("❌ ipinfo-db not installed. Installing...")
        os.system("pip install ipinfo-db")
        return setup_ipinfo()
    except Exception as e:
        print(f"❌ Error setting up IPinfo: {e}")
        return None

if __name__ == "__main__":
    mmdb_path = setup_ipinfo()
    if mmdb_path:
        print(f"🎉 IPinfo setup complete! MMDB path: {mmdb_path}")
    else:
        print("❌ IPinfo setup failed")
