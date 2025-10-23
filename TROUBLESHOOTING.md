# 🔧 AgriGenius Troubleshooting Guide

This guide helps you solve common issues when running the AgriGenius Flask application.

## 🚀 Quick Start (If Nothing Works)

```bash
# 1. Activate virtual environment
venv\Scripts\activate  # Windows
# OR
source venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
python generate_secret_key.py

# 4. Initialize database
python init_db.py

# 5. Run the app
python app.py
```

---

## 🐛 Common Issues and Solutions

### 1. **Import Errors**

**Problem:** `ModuleNotFoundError: No module named 'flask'`

**Solution:**
```bash
# Make sure virtual environment is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. **Virtual Environment Issues**

**Problem:** Virtual environment not working

**Solution:**
```bash
# Delete and recreate virtual environment
rmdir /s venv  # Windows
rm -rf venv    # Linux/Mac

# Create new virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 3. **Database Errors**

**Problem:** `sqlite3.OperationalError: no such table`

**Solution:**
```bash
# Delete existing database
del instance\farmgenius.db  # Windows
rm instance/farmgenius.db   # Linux/Mac

# Reinitialize database
python init_db.py
```

### 4. **Secret Key Errors**

**Problem:** `RuntimeError: The session is unavailable`

**Solution:**
```bash
# Generate new secret key
python generate_secret_key.py

# Or manually create .env file with:
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///farmgenius.db
FLASK_ENV=development
FLASK_DEBUG=True
```

### 5. **Port Already in Use**

**Problem:** `OSError: [Errno 98] Address already in use`

**Solution:**
```bash
# Find process using port 5000
netstat -ano | findstr :5000  # Windows
lsof -i :5000                 # Linux/Mac

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F        # Windows
kill -9 <PID>                 # Linux/Mac

# Or run on different port
python app.py --port 5001
```

### 6. **Template Not Found**

**Problem:** `TemplateNotFound: verify_articles.html`

**Solution:**
- Check that all template files exist in `templates/` folder
- Missing templates have been created in this fix
- Restart the application

### 7. **CSRF Token Errors**

**Problem:** `CSRFError: The CSRF token is missing`

**Solution:**
- This has been fixed by adding proper CSRF protection
- Make sure Flask-WTF is installed: `pip install Flask-WTF`

---

## 🔍 Debugging Steps

### Step 1: Check Python and Dependencies
```bash
python --version  # Should be 3.8+
pip list          # Check installed packages
```

### Step 2: Check Environment Variables
```bash
# Check if .env file exists
dir .env          # Windows
ls -la .env       # Linux/Mac

# Check contents
type .env         # Windows
cat .env          # Linux/Mac
```

### Step 3: Check Database
```bash
# Check if database file exists
dir instance\farmgenius.db  # Windows
ls -la instance/farmgenius.db  # Linux/Mac
```

### Step 4: Check Logs
```bash
# Check Flask logs
type flask.log    # Windows
cat flask.log     # Linux/Mac
```

---

## 🆘 Still Having Issues?

### Check These Files Exist:
- [ ] `app.py` - Main application file
- [ ] `requirements.txt` - Dependencies list
- [ ] `.env` - Environment variables
- [ ] `templates/` folder with all HTML files
- [ ] `static/` folder with CSS/JS files
- [ ] `sensors/sensors.py` - Sensor module

### Verify Dependencies:
```bash
pip install Flask==3.1.2
pip install Flask-Login==0.6.3
pip install Flask-SQLAlchemy==3.1.1
pip install Flask-WTF==1.2.1
pip install python-dotenv==1.0.0
pip install Werkzeug==3.1.3
```

### Reset Everything:
```bash
# 1. Delete virtual environment
rmdir /s venv  # Windows
rm -rf venv    # Linux/Mac

# 2. Delete database
del instance\farmgenius.db  # Windows
rm instance/farmgenius.db   # Linux/Mac

# 3. Delete .env file
del .env       # Windows
rm .env        # Linux/Mac

# 4. Run setup script
python setup.py
```

---

## 📞 Getting Help

If you're still having issues:

1. **Check the error message carefully** - it usually tells you what's wrong
2. **Look at the Flask logs** in `flask.log`
3. **Try the "Reset Everything" steps above**
4. **Make sure you're in the correct directory** with all the project files

---

## ✅ Verification Checklist

After fixing issues, verify everything works:

- [ ] Virtual environment is activated
- [ ] All dependencies are installed (`pip list`)
- [ ] `.env` file exists with SECRET_KEY
- [ ] Database is initialized (`instance/farmgenius.db` exists)
- [ ] Application starts without errors (`python app.py`)
- [ ] Can access http://localhost:5000
- [ ] Can create user account
- [ ] Can log in and out
- [ ] Can post articles
- [ ] Admin features work (if admin user created)

---

## 🎯 Performance Tips

- Use `python app.py` for development
- For production, use a proper WSGI server like Gunicorn
- Monitor the `flask.log` file for errors
- Regularly backup your database file
