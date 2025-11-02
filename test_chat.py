from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
import time
import subprocess
import sys
import os
import signal

def test_chat_page():
    # Set up Firefox options for headless mode
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    firefox_options.set_preference("browser.console.loglevel", "error")
    
    # Initialize the driver with automatic webdriver management
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=firefox_options)
    
    try:
        print("Starting headless browser test...")
        # Navigate to the chat page
        driver.get("http://localhost:5000/chat")
        print("Loaded chat page, waiting for JS to initialize...")
        time.sleep(2)  # Give time for JS to load
        
        # Get any console logs
        console_logs = driver.get_log('browser')
        
        # Print any errors found
        errors_found = False
        for log in console_logs:
            if log['level'] in ['SEVERE', 'ERROR']:
                errors_found = True
                print(f"Error: {log['message']}")
        
        if not errors_found:
            print("✅ No JavaScript errors found in console!")
            print("Page title:", driver.title)
        
        # Check if key elements are present
        try:
            chat_container = driver.find_element("id", "chat-container")
            print("✅ Chat container found")
        except:
            print("❌ Chat container not found")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    finally:
        driver.quit()
        print("Test completed, browser closed.")

if __name__ == "__main__":
    print("Starting Flask development server...")
    flask_process = subprocess.Popen([sys.executable, "app.py"], 
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
    
    # Give the server some time to start
    time.sleep(3)
    
    try:
        test_chat_page()
    finally:
        print("Shutting down Flask server...")
        os.kill(flask_process.pid, signal.SIGTERM)
        flask_process.wait()