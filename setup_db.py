#!/usr/bin/env python3
"""
Simple database setup script for AgriGenius
Creates database tables and AI modes without interactive prompts
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, initialize_app


def setup_database():
    """Setup the database with all tables and AI modes"""
    print("🔧 Setting up AgriGenius database...")
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Initialize AI modes after database creation
            initialize_app()
            print("✅ AI modes initialized successfully!")
            
            print("🎉 Database setup complete!")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up database: {e}")
            return False


if __name__ == "__main__":
    setup_database()