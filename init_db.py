#!/usr/bin/env python3
"""
Database initialization script for AgriGenius
Creates database tables and optionally creates an admin user
"""

import os
import sys
from getpass import getpass
from werkzeug.security import generate_password_hash

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Article, Documentation, Conversation, ChatMessage, UserMemory


def init_database():
    """Initialize the database with all tables"""
    print("🔧 Initializing database...")
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully!")
            return True
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
            return False


def create_admin_user():
    """Create an admin user interactively"""
    print("\n👤 Creating admin user...")
    
    with app.app_context():
        try:
            # Check if admin already exists
            existing_admin = User.query.filter_by(is_admin=True).first()
            if existing_admin:
                print(f"⚠️  Admin user already exists: {existing_admin.username}")
                response = input("Do you want to create another admin? (y/N): ").strip().lower()
                if response != 'y':
                    return True
            
            # Get admin details
            print("\nEnter admin user details:")
            username = input("Username: ").strip()
            
            if not username:
                print("❌ Username cannot be empty!")
                return False
            
            # Check if username already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                print(f"❌ Username '{username}' already exists!")
                return False
            
            # Get password securely
            while True:
                password = getpass("Password: ")
                if len(password) < 6:
                    print("❌ Password must be at least 6 characters long!")
                    continue
                
                password_confirm = getpass("Confirm password: ")
                if password != password_confirm:
                    print("❌ Passwords don't match!")
                    continue
                break
            
            # Create admin user
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            admin_user = User(
                username=username,
                password=hashed_password,
                is_admin=True,
                is_doc_poster=True  # Admins can also post documentation
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"✅ Admin user '{username}' created successfully!")
            print("   - Admin privileges: ✅")
            print("   - Documentation posting: ✅")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating admin user: {e}")
            return False


def create_sample_data():
    """Create some sample data for testing"""
    print("\n📝 Creating sample data...")
    
    with app.app_context():
        try:
            # Create a regular user
            regular_user = User(
                username="demo_user",
                password=generate_password_hash("demo123", method='pbkdf2:sha256'),
                is_admin=False,
                is_doc_poster=False
            )
            
            # Create a doc poster user
            doc_poster = User(
                username="doc_poster",
                password=generate_password_hash("doc123", method='pbkdf2:sha256'),
                is_admin=False,
                is_doc_poster=True
            )
            
            db.session.add(regular_user)
            db.session.add(doc_poster)
            db.session.commit()
            
            # Create sample article
            sample_article = Article(
                title="Welcome to AgriGenius",
                content="This is a sample article about modern farming techniques and sustainable agriculture practices.",
                author_id=regular_user.id,
                verified=True
            )
            
            # Create sample documentation
            sample_doc = Documentation(
                title="Getting Started with Smart Farming",
                content="This documentation covers the basics of implementing smart farming solutions using IoT sensors and data analytics.",
                author_id=doc_poster.id,
                verified=True
            )
            
            db.session.add(sample_article)
            db.session.add(sample_doc)
            db.session.commit()
            
            print("✅ Sample data created successfully!")
            print("   - Demo users: demo_user (password: demo123)")
            print("   - Doc poster: doc_poster (password: doc123)")
            print("   - Sample article and documentation added")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating sample data: {e}")
            return False


def main():
    """Main initialization function"""
    print("🌱 AgriGenius Database Initialization")
    print("=" * 40)
    
    # Initialize database
    if not init_database():
        print("❌ Database initialization failed!")
        return False
    
    # Create admin user
    create_admin = input("\nDo you want to create an admin user? (Y/n): ").strip().lower()
    if create_admin != 'n':
        if not create_admin_user():
            print("⚠️  Admin user creation failed, but database is initialized.")
    
    # Create sample data
    create_samples = input("\nDo you want to create sample data for testing? (y/N): ").strip().lower()
    if create_samples == 'y':
        if not create_sample_data():
            print("⚠️  Sample data creation failed, but database is initialized.")
    
    print("\n🎉 Database initialization complete!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run the application: python app.py")
    print("3. Open http://localhost:5000 in your browser")
    
    return True


if __name__ == "__main__":
    main()
