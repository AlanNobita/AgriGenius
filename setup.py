#!/usr/bin/env python3
"""
Setup script for AgriGenius Flask Application
Installs dependencies and sets up the application
"""

import os
import sys
import subprocess
import platform


def run_command(command, description=""):
    """Run a command and handle errors"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"✅ {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required!")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True


def check_virtual_environment():
    """Check if virtual environment exists and is activated"""
    venv_path = "venv"
    
    if not os.path.exists(venv_path):
        print("📦 Virtual environment not found. Creating one...")
        if not run_command(f"python -m venv {venv_path}", "Creating virtual environment"):
            return False
    
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment is active")
        return True
    else:
        print("⚠️  Virtual environment exists but is not activated")
        print("Please activate it manually:")
        if platform.system() == "Windows":
            print("   venv\\Scripts\\activate")
        else:
            print("   source venv/bin/activate")
        return False


def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    
    # Upgrade pip first
    if not run_command("python -m pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing requirements"):
        return False
    
    return True


def setup_environment():
    """Set up environment variables"""
    env_file = ".env"
    
    if os.path.exists(env_file):
        print("✅ .env file already exists")
        return True
    
    print("🔑 Setting up environment variables...")
    if not run_command("python generate_secret_key.py", "Generating secret key"):
        print("⚠️  Could not generate .env file automatically")
        print("Please run: python generate_secret_key.py")
        return False
    
    return True


def initialize_database():
    """Initialize the database"""
    print("🗄️  Initializing database...")
    
    try:
        # Import here to avoid import errors before dependencies are installed
        from app import app, db
        
        with app.app_context():
            db.create_all()
            print("✅ Database initialized successfully")
            return True
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        print("You can try running: python init_db.py")
        return False


def main():
    """Main setup function"""
    print("🌱 AgriGenius Setup Script")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Check virtual environment
    if not check_virtual_environment():
        print("\n⚠️  Please activate the virtual environment and run this script again")
        return False
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        return False
    
    # Setup environment
    if not setup_environment():
        print("❌ Failed to setup environment")
        return False
    
    # Initialize database
    if not initialize_database():
        print("❌ Failed to initialize database")
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Run the application: python app.py")
    print("2. Open http://localhost:5000 in your browser")
    print("3. Create an admin user: python init_db.py")
    
    # Ask if user wants to run the app now
    response = input("\nDo you want to start the application now? (y/N): ").strip().lower()
    if response == 'y':
        print("\n🚀 Starting AgriGenius...")
        try:
            subprocess.run("python app.py", shell=True)
        except KeyboardInterrupt:
            print("\n👋 Application stopped")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
