#!/usr/bin/env python3
"""
Simple script to start the Flask server
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == "__main__":
    print("🌱 Starting AgriGenius server...")
    print("📍 Server will be available at:")
    print("   - http://localhost:5000")
    print("   - http://127.0.0.1:5000")
    print("   - http://192.168.10.65:5000")
    print("\nPress Ctrl+C to stop the server")
    
    # Use 0.0.0.0 to make the app accessible on your local network
    app.run(host='0.0.0.0', port=5000, debug=True)