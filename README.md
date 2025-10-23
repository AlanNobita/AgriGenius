# FarmGenius Website

This is a Flask-based web application for a science fair project focused on agriculture. The website includes:

- Public article posting and viewing
- Documentation section with restricted posting
- Chatbot integration (n8n)
- User authentication (login/signup)
- Home/About/Dashboard sector

## How to Run

1. Ensure you have Python 3.8+ installed.
2. Create a virtual environment and activate it:
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Run the app:
   ```sh
   flask run
   ```

## Project Structure
- `app.py`: Main Flask application
- `templates/`: HTML templates
- `static/`: CSS and static files
- `requirements.txt`: Python dependencies

---

**Replace any placeholder values (like the n8n chatbot URL) with your actual project details.**

from app import db, app
with app.app_context():
    db.create_all()
