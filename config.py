import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_default_secret_key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///farmgenius.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
