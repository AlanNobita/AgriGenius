# 🚀 Quick Start Guide - AgriGenius

## First Time Setup (3 steps)

### Step 1: Generate SECRET_KEY
```bash
python generate_secret_key.py
```
✅ This creates a `.env` file with a secure SECRET_KEY

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run the App
```bash
flask run
```

🎉 Your app is now running at `http://localhost:5000`

---

## What Changed?

### Before (❌ Insecure):
```python
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Hardcoded!
```

### After (✅ Secure):
```python
from dotenv import load_dotenv
load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
```

---

## Files You Need to Know About

| File | Purpose |
|------|---------|
| `.env` | Your secrets (created by script, never commit) |
| `.env.example` | Template showing what variables exist |
| `.gitignore` | Prevents `.env` from being committed |
| `generate_secret_key.py` | Script to generate secure keys |

---

## Common Commands

```bash
# Generate a new SECRET_KEY
python generate_secret_key.py

# Install dependencies
pip install -r requirements.txt

# Run development server
flask run

# Run with custom port
flask run --port 8000

# Run in production mode
FLASK_ENV=production flask run
```

---

## ⚠️ Important

- **Never commit `.env` to git** - It's in `.gitignore` for a reason
- **Keep your SECRET_KEY secret** - Don't share it
- **Generate new keys for production** - Use a different key than development

---

## 🆘 Troubleshooting

**Problem:** `ModuleNotFoundError: No module named 'dotenv'`
```bash
pip install python-dotenv
```

**Problem:** `.env` file not found
```bash
python generate_secret_key.py
```

**Problem:** App won't start
- Check that `.env` exists
- Check that `SECRET_KEY` is set in `.env`
- Run `pip install -r requirements.txt` again

---

## 📚 Learn More

- Read `SETUP_GUIDE.md` for detailed setup instructions
- Read `SECURITY_CHECKLIST.md` for security recommendations
- Check `README.md` for project overview

