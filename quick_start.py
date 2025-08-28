#!/usr/bin/env python3
# quick_start.py
# Quick start script for the Geographic Transaction Analysis Application

import os
import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 11):
        print("❌ Python 3.11 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'streamlit', 'pandas', 'numpy', 'plotly', 'openpyxl'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} is missing")
    
    return missing_packages

def install_dependencies():
    """Install missing dependencies"""
    print("\n📦 Installing missing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_virtual_environment():
    """Create and activate virtual environment"""
    print("\n🔧 Setting up virtual environment...")
    
    venv_name = "geographic_analysis_env"
    
    # Check if virtual environment already exists
    if os.path.exists(venv_name):
        print(f"✅ Virtual environment '{venv_name}' already exists")
        return venv_name
    
    try:
        # Create virtual environment
        subprocess.check_call([sys.executable, "-m", "venv", venv_name])
        print(f"✅ Virtual environment '{venv_name}' created successfully!")
        return venv_name
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return None

def get_activation_command(venv_name):
    """Get the appropriate activation command for the platform"""
    if platform.system() == "Windows":
        return f"{venv_name}\\Scripts\\activate"
    else:
        return f"source {venv_name}/bin/activate"

def run_tests():
    """Run the test suite to verify everything works"""
    print("\n🧪 Running tests to verify installation...")
    try:
        subprocess.check_call([sys.executable, "test_app.py"])
        print("✅ All tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed: {e}")
        return False

def start_application():
    """Start the Streamlit application"""
    print("\n🚀 Starting the Geographic Analysis Application...")
    print("The application will open in your web browser.")
    print("Press Ctrl+C to stop the application.")
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "geographic_analysis_app.py"])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Failed to start application: {e}")

def main():
    """Main quick start function"""
    print("🌍 Geographic Transaction Analysis Application - Quick Start")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        print("\nPlease upgrade Python to version 3.11 or higher")
        return
    
    # Check if we're in the right directory
    if not os.path.exists("geographic_analysis_app.py"):
        print("❌ Please run this script from the directory containing the application files")
        return
    
    # Check dependencies
    missing_packages = check_dependencies()
    
    if missing_packages:
        print(f"\n📦 Missing packages: {', '.join(missing_packages)}")
        
        # Try to install dependencies
        if not install_dependencies():
            print("\n❌ Failed to install dependencies automatically")
            print("Please install them manually:")
            print("pip install -r requirements.txt")
            return
    else:
        print("\n✅ All required packages are installed!")
    
    # Run tests
    if not run_tests():
        print("\n❌ Tests failed. Please check the error messages above.")
        return
    
    # Ask user if they want to start the application
    print("\n" + "=" * 60)
    print("🎉 Setup completed successfully!")
    print("\nYou can now:")
    print("1. Start the application: python quick_start.py --start")
    print("2. Run manually: streamlit run geographic_analysis_app.py")
    print("3. Run tests: python test_app.py")
    
    # Check if user wants to start immediately
    if "--start" in sys.argv:
        start_application()
    else:
        print("\n💡 To start the application now, run:")
        print("python quick_start.py --start")

if __name__ == "__main__":
    main()
