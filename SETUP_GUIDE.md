# AgriGenius Setup Guide

## 🔐 Security Configuration

This project now uses environment variables to securely manage sensitive configuration like the Flask SECRET_KEY.

### Quick Start

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Generate SECRET_KEY
Run the key generation script:
```bash
python generate_secret_key.py
```

This will:
- Generate a cryptographically secure random key
- Create a `.env` file with your SECRET_KEY
- Ensure the `.env` file is never committed to git

#### 3. Run the Application
```bash
flask run
```

---

## 📋 Environment Variables

The application uses the following environment variables (defined in `.env`):

| Variable | Purpose | Default |
|----------|---------|---------|
| `SECRET_KEY` | Flask session encryption key | `dev-key-change-in-production` |
| `DATABASE_URL` | Database connection string | `sqlite:///farmgenius.db` |
| `FLASK_ENV` | Environment mode | `development` |
| `FLASK_DEBUG` | Debug mode | `True` |

### Example `.env` file:
```
SECRET_KEY=a7f3c9e2b1d4f6a8c5e7b9d1f3a5c7e9b1d3f5a7c9e1b3d5f7a9c1e3b5d7f9
DATABASE_URL=sqlite:///farmgenius.db
FLASK_ENV=development
FLASK_DEBUG=True
```

---

## 🛡️ Security Best Practices

### ✅ DO:
- Keep `.env` file in `.gitignore` (already configured)
- Generate a new SECRET_KEY for production
- Use strong, random SECRET_KEYs
- Never commit `.env` to version control
- Use environment variables for all sensitive data

### ❌ DON'T:
- Hardcode secrets in source code
- Commit `.env` files to git
- Share your SECRET_KEY
- Use the same SECRET_KEY across environments
- Use weak or predictable keys

---

## 🚀 Production Deployment

For production deployment:

1. **Generate a new SECRET_KEY:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Set environment variables on your server:**
   - Use your hosting platform's environment variable settings
   - Or create a `.env` file on the server (not in git)

3. **Update configuration:**
   ```
   FLASK_ENV=production
   FLASK_DEBUG=False
   SECRET_KEY=<your-production-key>
   DATABASE_URL=<your-production-database>
   ```

4. **Use a production WSGI server:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 app:app
   ```

---

## 📚 Additional Resources

- [Flask Configuration Documentation](https://flask.palletsprojects.com/config/)
- [python-dotenv Documentation](https://python-dotenv.readthedocs.io/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/security/)

---

## ❓ Troubleshooting

### `.env` file not being loaded
- Ensure `python-dotenv` is installed: `pip install python-dotenv`
- Check that `.env` is in the project root directory
- Restart your Flask application

### SECRET_KEY errors
- Run `python generate_secret_key.py` to create a new `.env` file
- Verify the `.env` file exists and contains `SECRET_KEY=...`

### Database errors
- Ensure `DATABASE_URL` is correctly set in `.env`
- For SQLite, the path should be relative: `sqlite:///farmgenius.db`

