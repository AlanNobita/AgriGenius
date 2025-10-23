#!/usr/bin/env python3
"""
Generate a secure SECRET_KEY for Flask application.
Run this script to generate a new SECRET_KEY and add it to your .env file.
"""

import secrets
import os
from pathlib import Path


def generate_secret_key():
    """Generate a cryptographically secure random key."""
    return secrets.token_hex(32)


def create_env_file():
    """Create or update .env file with a new SECRET_KEY."""
    env_path = Path('.env')
    secret_key = generate_secret_key()
    
    # Check if .env already exists
    if env_path.exists():
        print(f"⚠️  .env file already exists at {env_path}")
        response = input("Do you want to overwrite it? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled. Your existing .env file was not modified.")
            print(f"\nYour new SECRET_KEY (if you want to update manually):\n{secret_key}")
            return
    
    # Create .env file with SECRET_KEY
    env_content = f"""# Flask Configuration
# Generated SECRET_KEY - keep this secret!
SECRET_KEY={secret_key}

# Database Configuration
DATABASE_URL=sqlite:///farmgenius.db

# Flask Environment
FLASK_ENV=development
FLASK_DEBUG=True
"""
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"✅ .env file created successfully at {env_path}")
    print(f"\n🔐 Your SECRET_KEY has been generated and saved.")
    print(f"⚠️  Keep this file secure and never commit it to version control!")
    print(f"\n📝 Make sure .env is in your .gitignore (it already is if you used our setup)")


if __name__ == '__main__':
    print("🔑 Flask SECRET_KEY Generator")
    print("=" * 50)
    create_env_file()

