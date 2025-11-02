
# ...existing code...
import os
from flask import Flask, render_template, redirect, url_for, request, jsonify, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import logging
import requests
import json
from datetime import datetime, timezone
from sensors.sensors import get_sensor_data
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid

from config import Config
from flask_bcrypt import Bcrypt

from flask_compress import Compress
import sys
import os as _os

# Initialize Flask app
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)
Compress(app)

# OpenRouter API Configuration
OPENROUTER_MODEL = 'meta-llama/llama-4-maverick:free'  # Default model
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = Config.OPENROUTER_API_KEY

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

@app.after_request
def add_header(response):
    if 'Cache-Control' not in response.headers:
        response.cache_control.max_age = 31536000
    return response
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

from logging.handlers import RotatingFileHandler

# Configure logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/agrigenius.log', maxBytes=1024000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('AgriGenius startup')

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mp3', 'wav', 'ogg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'images'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'videos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'audio'), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    if filename:
        ext = filename.rsplit('.', 1)[1].lower()
        if ext in ['png', 'jpg', 'jpeg', 'gif']:
            return 'image'
        elif ext in ['mp4', 'avi', 'mov']:
            return 'video'
        elif ext in ['mp3', 'wav', 'ogg']:
            return 'audio'
    return 'none'

def save_uploaded_file(file, file_type):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add unique identifier to prevent conflicts
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        if file_type == 'image':
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'images', unique_filename)
        elif file_type == 'video':
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'videos', unique_filename)
        elif file_type == 'audio':
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', unique_filename)
        else:
            return None
            
        file.save(filepath)
        return f"uploads/{file_type}s/{unique_filename}"
    return None


# User model for authentication
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_doc_poster = db.Column(db.Boolean, default=False)  # Access for documentation posting
    is_admin = db.Column(db.Boolean, default=False)  # Admin privilege
    articles = db.relationship('Article', backref='author', lazy=True)
    docs = db.relationship('Documentation', backref='author', lazy=True)


# Article model for public articles
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    verified = db.Column(db.Boolean, default=False)  # Admin verification
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), default='General')
    tags = db.Column(db.Text, nullable=True)  # JSON string of tags
    # File upload fields
    image_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    audio_url = db.Column(db.String(500))
    file_type = db.Column(db.String(50))  # 'image', 'video', 'audio', 'none'


# Documentation model for restricted articles
class Documentation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    verified = db.Column(db.Boolean, default=False)  # Admin verification
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), default='General')
    tags = db.Column(db.Text, nullable=True)  # JSON string of tags
    # File upload fields
    image_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    audio_url = db.Column(db.String(500))
    file_type = db.Column(db.String(50))  # 'image', 'video', 'audio', 'none'

# Product model for marketplace
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_url = db.Column(db.String(500))
    stock_quantity = db.Column(db.Integer, default=1)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    
    # Relationships
    seller = db.relationship('User', backref=db.backref('products', lazy=True))

# Conversation model for chat history
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable for anonymous users
    session_id = db.Column(db.String(100), nullable=False)  # For anonymous users
    title = db.Column(db.String(200), nullable=False, default='New Chat')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)
    user = db.relationship('User', backref=db.backref('conversations', lazy=True))
    ai_mode_id = db.Column(db.Integer, db.ForeignKey('ai_mode.id'), nullable=True)  # Reference to AI mode

# Message model for individual chat messages
class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    sensor_data = db.Column(db.Text, nullable=True)  # JSON string of sensor data
    conversation = db.relationship('Conversation', backref=db.backref('messages', lazy=True, order_by='ChatMessage.timestamp'))

# User memory model for AI to remember user preferences and data
class UserMemory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    session_id = db.Column(db.String(100), nullable=True)  # For anonymous users
    memory_type = db.Column(db.String(50), nullable=False)  # 'preference', 'farm_data', 'crop_info', etc.
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', backref=db.backref('memories', lazy=True))

# AI Mode model for different AI interaction modes
class AIMode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # 'learn', 'read', 'analyze', 'assist', 'creative'
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(50), nullable=False)  # Font Awesome icon class
    color = db.Column(db.String(20), nullable=False)  # CSS color class or hex
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    conversations = db.relationship('Conversation', backref=db.backref('ai_mode', lazy=True))

# User's current AI mode preference
class UserAIModePreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    session_id = db.Column(db.String(100), nullable=True)  # For anonymous users
    mode_id = db.Column(db.Integer, db.ForeignKey('ai_mode.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('ai_mode_preferences', lazy=True))
    mode = db.relationship('AIMode', backref=db.backref('user_preferences', lazy=True))

# Like model for articles and documentation
class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=True)
    doc_id = db.Column(db.Integer, db.ForeignKey('documentation.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('likes', lazy=True))
    article = db.relationship('Article', backref=db.backref('article_likes', lazy=True))
    doc = db.relationship('Documentation', backref=db.backref('doc_likes', lazy=True))


# SavedArticle model for "Save for later" feature
class SavedArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('saved_articles', lazy=True))
    article = db.relationship('Article', backref=db.backref('saved_by', lazy=True))

# Comment model for articles and documentation
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=True)
    doc_id = db.Column(db.Integer, db.ForeignKey('documentation.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    article = db.relationship('Article', backref=db.backref('article_comments', lazy=True))
    doc = db.relationship('Documentation', backref=db.backref('doc_comments', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Home route (Sector 5)
@app.route('/')
def home():
    return render_template('home.html')

# Notifications route
@app.route('/notifications')
def notifications():
    return render_template('notifications.html')

# My Posts route
@app.route('/my-posts')
@login_required
def my_posts():
    user_articles = Article.query.filter_by(author_id=current_user.id).order_by(Article.created_at.desc()).all()
    return render_template('my-posts.html', articles=user_articles)

# Sector 1: Public Articles


# View all articles
@app.route('/articles')
def articles():
    all_articles = Article.query.all()
    return render_template('articles.html', articles=all_articles)

@app.route('/marketplace')
def marketplace():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    sort_by = request.args.get('sort', 'newest')
    
    query = Product.query.filter_by(is_available=True)
    
    if search:
        query = query.filter(Product.name.contains(search) | Product.description.contains(search))
    
    if category:
        query = query.filter_by(category=category)
    
    if sort_by == 'price_low':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'popular':
        query = query.order_by(Product.views.desc())
    else:  # newest
        query = query.order_by(Product.created_at.desc())
    
    products = query.all()
    categories = db.session.query(Product.category.distinct()).all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    return render_template('marketplace.html', products=products, categories=categories, 
                         search=search, selected_category=category, sort_by=sort_by)

@app.route('/product/<int:product_id>')
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.views += 1
    db.session.commit()
    return render_template('product_detail.html', product=product)

@app.route('/contact_seller/<int:product_id>')
def contact_seller(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('contact_seller.html', product=product)

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            price = float(request.form.get('price', 0))
            category = request.form.get('category', '').strip()
            stock_quantity = int(request.form.get('stock_quantity', 1))
            
            # Validation
            if not name or len(name) < 3:
                flash('Product name must be at least 3 characters long.')
                return render_template('add_product.html')
            
            if not description or len(description) < 10:
                flash('Description must be at least 10 characters long.')
                return render_template('add_product.html')
            
            if price <= 0:
                flash('Price must be greater than 0.')
                return render_template('add_product.html')
            
            # Handle image upload
            image_url = None
            if 'image' in request.files:
                image_file = request.files['image']
                if image_file and image_file.filename:
                    image_url = save_uploaded_file(image_file, 'image')
            
            new_product = Product(
                name=name,
                description=description,
                price=price,
                category=category,
                seller_id=current_user.id,
                image_url=image_url,
                stock_quantity=stock_quantity
            )
            
            db.session.add(new_product)
            db.session.commit()
            flash('Product added successfully!')
            return redirect(url_for('marketplace'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error adding product. Please try again.')
            app.logger.error(f'Error adding product: {str(e)}')
    
    return render_template('add_product.html')

# Post a new article
@app.route('/post_article', methods=['GET', 'POST'])
@csrf.exempt
def post_article():
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            category = request.form.get('category', 'General').strip()
            tags = request.form.get('tags', '').strip()

            # Validation
            if not title or len(title) < 3:
                flash('Title must be at least 3 characters long.')
                return render_template('post_article.html')

            if not content or len(content) < 10:
                flash('Content must be at least 10 characters long.')
                return render_template('post_article.html')

            if len(title) > 200:
                flash('Title is too long (maximum 200 characters).')
                return render_template('post_article.html')

            # Handle anonymous users
            author_id = current_user.id if current_user.is_authenticated else None
            
            # Handle file uploads
            image_url = None
            video_url = None
            audio_url = None
            file_type = 'none'
            
            # Check for image upload
            if 'image' in request.files:
                image_file = request.files['image']
                if image_file and image_file.filename:
                    image_url = save_uploaded_file(image_file, 'image')
                    if image_url:
                        file_type = 'image'
            
            # Check for video upload
            if 'video' in request.files:
                video_file = request.files['video']
                if video_file and video_file.filename:
                    video_url = save_uploaded_file(video_file, 'video')
                    if video_url:
                        file_type = 'video'
            
            # Check for audio upload
            if 'audio' in request.files:
                audio_file = request.files['audio']
                if audio_file and audio_file.filename:
                    audio_url = save_uploaded_file(audio_file, 'audio')
                    if audio_url:
                        file_type = 'audio'
            
            new_article = Article(
                title=title,
                content=content,
                author_id=author_id,
                verified=True,
                category=category,
                tags=tags,
                image_url=image_url,
                video_url=video_url,
                audio_url=audio_url,
                file_type=file_type
            )
            db.session.add(new_article)
            db.session.commit()
            flash('Article published successfully!')
            username = current_user.username if current_user.is_authenticated else 'Anonymous'
            app.logger.info(f'User {username} submitted article: {title}')
            return redirect(url_for('articles'))

        except Exception as e:
            db.session.rollback()
            flash('Error submitting article. Please try again.')
            app.logger.error(f'Error submitting article: {str(e)}')

    return render_template('post_article.html')


# Sector 2: Documentation (restricted posting)

@app.route('/documentation', methods=['GET', 'POST'])
def documentation():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('You must be logged in to post documentation.')
            return redirect(url_for('login'))
        if not current_user.is_doc_poster:
            flash('You do not have permission to post documentation.')
            return redirect(url_for('documentation'))

        try:
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            category = request.form.get('category', 'General').strip()
            tags = request.form.get('tags', '').strip()

            # Validation
            if not title or len(title) < 3:
                flash('Title must be at least 3 characters long.')
                return redirect(url_for('documentation'))

            if not content or len(content) < 10:
                flash('Content must be at least 10 characters long.')
                return redirect(url_for('documentation'))

            if len(title) > 200:
                flash('Title is too long (maximum 200 characters).')
                return redirect(url_for('documentation'))

            new_doc = Documentation(
                title=title,
                content=content,
                author_id=current_user.id,
                verified=False,
                category=category,
                tags=tags
            )
            db.session.add(new_doc)
            db.session.commit()
            flash('Documentation submitted for review!')
            app.logger.info(f'User {current_user.username} submitted documentation: {title}')
            return redirect(url_for('documentation'))

        except Exception as e:
            db.session.rollback()
            flash('Error submitting documentation. Please try again.')
            app.logger.error(f'Error submitting documentation: {str(e)}')

    try:
        all_docs = Documentation.query.filter_by(verified=True).all()
    except Exception as e:
        all_docs = []
        app.logger.error(f'Error fetching documentation: {str(e)}')
        flash('Error loading documentation.')

    return render_template('documentation.html', docs=all_docs)
# Admin route to verify articles
@app.route('/admin/verify_articles')
@login_required
def verify_articles():
    if not current_user.is_admin:
        flash('Admin access required.')
        return redirect(url_for('profile'))
    pending_articles = Article.query.filter_by(verified=False).all()
    return render_template('verify_articles.html', articles=pending_articles)

# Admin route to verify documentation
@app.route('/admin/verify_docs')
@login_required
def verify_docs():
    if not current_user.is_admin:
        flash('Admin access required.')
        return redirect(url_for('profile'))
    pending_docs = Documentation.query.filter_by(verified=False).all()
    return render_template('verify_docs.html', docs=pending_docs)

# Admin action to approve article
@app.route('/admin/approve_article/<int:article_id>')
@login_required
def approve_article(article_id):
    if not current_user.is_admin:
        flash('Admin access required.')
        return redirect(url_for('profile'))
    article = Article.query.get_or_404(article_id)
    article.verified = True
    db.session.commit()
    flash('Article approved!')
    return redirect(url_for('verify_articles'))

# Admin action to approve documentation
@app.route('/admin/approve_doc/<int:doc_id>')
@login_required
def approve_doc(doc_id):
    if not current_user.is_admin:
        flash('Admin access required.')
        return redirect(url_for('profile'))
    try:
        doc = Documentation.query.get_or_404(doc_id)
        doc.verified = True
        db.session.commit()
        flash('Documentation approved!')
        app.logger.info(f'Admin {current_user.username} approved documentation {doc_id}')
    except Exception as e:
        db.session.rollback()
        flash('Error approving documentation.')
        app.logger.error(f'Error approving documentation {doc_id}: {str(e)}')
    return redirect(url_for('verify_docs'))

# Admin action to reject article
@app.route('/admin/reject_article/<int:article_id>')
@login_required
def reject_article(article_id):
    if not current_user.is_admin:
        flash('Admin access required.')
        return redirect(url_for('profile'))
    try:
        article = Article.query.get_or_404(article_id)
        db.session.delete(article)
        db.session.commit()
        flash('Article rejected and deleted.')
        app.logger.info(f'Admin {current_user.username} rejected article {article_id}')
    except Exception as e:
        db.session.rollback()
        flash('Error rejecting article.')
        app.logger.error(f'Error rejecting article {article_id}: {str(e)}')
    return redirect(url_for('verify_articles'))

# Admin action to reject documentation
@app.route('/admin/reject_doc/<int:doc_id>')
@login_required
def reject_doc(doc_id):
    if not current_user.is_admin:
        flash('Admin access required.')
        return redirect(url_for('profile'))
    try:
        doc = Documentation.query.get_or_404(doc_id)
        db.session.delete(doc)
        db.session.commit()
        flash('Documentation rejected and deleted.')
        app.logger.info(f'Admin {current_user.username} rejected documentation {doc_id}')
    except Exception as e:
        db.session.rollback()
        flash('Error rejecting documentation.')
        app.logger.error(f'Error rejecting documentation {doc_id}: {str(e)}')
    return redirect(url_for('verify_docs'))

# Sector 4: Login/Signup

# Login route: redirects to profile after successful login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember = True if request.form.get('remember') else False

            if not username or not password:
                flash('Please enter both username and password.')
                return render_template('login.html')

            user = User.query.filter_by(username=username).first()
            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user, remember=remember)
                app.logger.info(f'User {username} logged in successfully')

                # Redirect to next page if specified
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('profile'))
            else:
                flash('Invalid username or password.')
                app.logger.warning(f'Failed login attempt for username: {username}')

        except Exception as e:
            flash('Login error. Please try again.')
            app.logger.error(f'Login error: {str(e)}')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            # Validation
            if not username or len(username) < 3:
                flash('Username must be at least 3 characters long.')
                return render_template('signup.html')

            if not password or len(password) < 6:
                flash('Password must be at least 6 characters long.')
                return render_template('signup.html')

            if password != confirm_password:
                flash('Passwords do not match.')
                return render_template('signup.html')

            # Check if username already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists. Please choose a different one.')
                return render_template('signup.html')

            # Create new user
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(username=username, password=hashed_pw)
            db.session.add(user)
            db.session.commit()

            flash('Account created successfully! Please log in.')
            app.logger.info(f'New user registered: {username}')
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            flash('Error creating account. Please try again.')
            app.logger.error(f'Signup error: {str(e)}')

    return render_template('signup.html')


# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Chatbot routes
@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/chat/<conversation_id>')
def chat_conversation(conversation_id):
    return render_template('chat.html', conversation_id=conversation_id)

# Mount RAG API blueprint under /rag
try:
    _RAG_SRC = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'static', 'rag-chatbot', 'src')
    if _RAG_SRC not in sys.path:
        sys.path.append(_RAG_SRC)
    from api.routes import api_bp as rag_api_bp  # type: ignore
    # Exempt RAG API from CSRF because it is called via fetch/XHR
    try:
        csrf.exempt(rag_api_bp)
    except Exception:
        pass
    app.register_blueprint(rag_api_bp, url_prefix='/rag')
except Exception as e:
    app.logger.error(f'Failed to mount RAG API blueprint: {e}')

# Simple Documents manager page (upload & list PDFs)
@app.route('/documents', methods=['GET'])
def documents_manager():
    try:
        pdf_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'static', 'rag-chatbot', 'data', 'pdfs')
        _os.makedirs(pdf_dir, exist_ok=True)
        pdfs = []
        for name in sorted(_os.listdir(pdf_dir)):
            if name.lower().endswith('.pdf'):
                pdfs.append({
                    'name': name,
                    'path': f"/static/rag-chatbot/data/pdfs/{name}"
                })
    except Exception:
        pdfs = []
    return render_template('documents.html', pdfs=pdfs)




# Get user's conversation history
@app.route('/api/conversations', methods=['GET'])
@csrf.exempt
def get_conversations():
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        session_id = session.get('chat_session_id')

        if user_id:
            conversations = Conversation.query.filter_by(user_id=user_id, is_active=True).order_by(Conversation.updated_at.desc()).all()
        elif session_id:
            conversations = Conversation.query.filter_by(session_id=session_id, is_active=True).order_by(Conversation.updated_at.desc()).all()
        else:
            return jsonify({"conversations": []})

        conv_list = []
        for conv in conversations:
            conv_list.append({
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": len(conv.messages)
            })

        return jsonify({"conversations": conv_list})

    except Exception as e:
        app.logger.error(f'Error fetching conversations: {str(e)}')
        return jsonify({"error": "Failed to fetch conversations"}), 500

# Get messages for a specific conversation
@app.route('/api/conversations/<int:conversation_id>/messages', methods=['GET'])
@csrf.exempt
def get_conversation_messages(conversation_id):
    try:
        conversation = Conversation.query.get_or_404(conversation_id)

        # Check if user has access to this conversation
        user_id = current_user.id if current_user.is_authenticated else None
        session_id = session.get('chat_session_id')

        if not ((user_id and conversation.user_id == user_id) or
                (session_id and conversation.session_id == session_id)):
            return jsonify({"error": "Access denied"}), 403

        messages = []
        for msg in conversation.messages:
            message_data = {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            if msg.sensor_data:
                message_data["sensor_data"] = json.loads(msg.sensor_data)
            messages.append(message_data)

        return jsonify({
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "messages": messages
            }
        })

    except Exception as e:
        app.logger.error(f'Error fetching conversation messages: {str(e)}')
        return jsonify({"error": "Failed to fetch messages"}), 500

# Main AI chat endpoint
@app.route('/api/chat', methods=['POST'])
@csrf.exempt
def ai_chat():
    try:
        data = request.json
        user_input = data.get("message", "").strip()
        conversation_id = data.get("conversation_id")

        if not user_input:
            return jsonify({"error": "No message provided"}), 400

        # Get or create session ID for anonymous users
        if not session.get('chat_session_id'):
            import uuid
            session['chat_session_id'] = str(uuid.uuid4())

        user_id = current_user.id if current_user.is_authenticated else None
        session_id = session.get('chat_session_id')

        # Get or create conversation
        if conversation_id:
            conversation = Conversation.query.get(conversation_id)
            if not conversation:
                return jsonify({"error": "Conversation not found"}), 404
        else:
            # Create new conversation
            conversation = Conversation(
                user_id=user_id,
                session_id=session_id,
                title=generate_conversation_title(user_input)
            )
            db.session.add(conversation)
            db.session.flush()  # Get the ID

        # Get current sensor data
        sensor_data = get_sensor_data()

        # Save user message
        user_message = ChatMessage(
            conversation_id=conversation.id,
            role='user',
            content=user_input,
            sensor_data=json.dumps(sensor_data)
        )
        db.session.add(user_message)

        # Get user memory for context
        user_memory = get_user_memory(user_id, session_id)

        # Get current AI mode
        current_mode = get_current_ai_mode(user_id, session_id)

        # Generate AI response
        ai_response = generate_ai_response(user_input, sensor_data, conversation, user_memory, current_mode)

        # Save AI message
        ai_message = ChatMessage(
            conversation_id=conversation.id,
            role='assistant',
            content=ai_response,
            sensor_data=json.dumps(sensor_data)
        )
        db.session.add(ai_message)

        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc)

        # Extract and save any new user information
        extract_and_save_user_info(user_input, user_id, session_id)

        db.session.commit()

        return jsonify({
            "response": ai_response,
            "conversation_id": conversation.id,
            "message_id": ai_message.id,
            "sensor_data": sensor_data,
            "timestamp": ai_message.timestamp.isoformat()
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f'AI Chat error: {str(e)}')
        return jsonify({"error": "Sorry, I'm having trouble right now. Please try again later."}), 500

# Delete conversation
@app.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
@csrf.exempt
def delete_conversation(conversation_id):
    try:
        conversation = Conversation.query.get_or_404(conversation_id)

        # Check if user has access to this conversation
        user_id = current_user.id if current_user.is_authenticated else None
        session_id = session.get('chat_session_id')

        if not ((user_id and conversation.user_id == user_id) or
                (session_id and conversation.session_id == session_id)):
            return jsonify({"error": "Access denied"}), 403

        conversation.is_active = False
        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        app.logger.error(f'Error deleting conversation: {str(e)}')
        return jsonify({"error": "Failed to delete conversation"}), 500

# Helper functions for AI chatbot
def generate_conversation_title(first_message):
    """Generate a title for the conversation based on the first message"""
    # Simple title generation - in production, you might use AI for this
    words = first_message.split()[:5]  # First 5 words
    title = ' '.join(words)
    if len(title) > 50:
        title = title[:47] + "..."
    return title or "New Chat"

def get_user_memory(user_id, session_id):
    """Get user memory for context"""
    try:
        if user_id:
            memories = UserMemory.query.filter_by(user_id=user_id).all()
        elif session_id:
            memories = UserMemory.query.filter_by(session_id=session_id).all()
        else:
            return {}

        memory_dict = {}
        for memory in memories:
            if memory.memory_type not in memory_dict:
                memory_dict[memory.memory_type] = {}
            memory_dict[memory.memory_type][memory.key] = memory.value

        return memory_dict
    except Exception as e:
        app.logger.error(f'Error getting user memory: {str(e)}')
        return {}

def save_user_memory(user_id, session_id, memory_type, key, value):
    """Save user memory"""
    try:
        # Check if memory already exists
        if user_id:
            memory = UserMemory.query.filter_by(user_id=user_id, memory_type=memory_type, key=key).first()
        else:
            memory = UserMemory.query.filter_by(session_id=session_id, memory_type=memory_type, key=key).first()

        if memory:
            memory.value = value
            memory.updated_at = datetime.now(timezone.utc)
        else:
            memory = UserMemory(
                user_id=user_id,
                session_id=session_id,
                memory_type=memory_type,
                key=key,
                value=value
            )
            db.session.add(memory)

        db.session.commit()
    except Exception as e:
        app.logger.error(f'Error saving user memory: {str(e)}')

def extract_and_save_user_info(user_input, user_id, session_id):
    """Extract and save user information from conversation"""
    try:
        user_lower = user_input.lower()

        # Extract farm information
        if any(word in user_lower for word in ['my farm', 'i grow', 'i have', 'my crop']):
            if 'tomato' in user_lower:
                save_user_memory(user_id, session_id, 'crops', 'tomatoes', 'true')
            if 'corn' in user_lower:
                save_user_memory(user_id, session_id, 'crops', 'corn', 'true')
            if 'wheat' in user_lower:
                save_user_memory(user_id, session_id, 'crops', 'wheat', 'true')

        # Extract location information
        if any(word in user_lower for word in ['i am in', 'located in', 'from']):
            # Simple location extraction - in production, use NLP
            words = user_input.split()
            for i, word in enumerate(words):
                if word.lower() in ['in', 'from'] and i + 1 < len(words):
                    location = words[i + 1].strip('.,!?')
                    save_user_memory(user_id, session_id, 'location', 'region', location)
                    break

        # Extract farm size
        if any(word in user_lower for word in ['acre', 'hectare', 'square']):
            # Extract farm size information
            import re
            size_match = re.search(r'(\d+(?:\.\d+)?)\s*(acre|hectare|sq)', user_lower)
            if size_match:
                size = size_match.group(1)
                unit = size_match.group(2)
                save_user_memory(user_id, session_id, 'farm_info', 'size', f"{size} {unit}")

    except Exception as e:
        app.logger.error(f'Error extracting user info: {str(e)}')

def generate_ai_response(user_input, sensor_data, conversation, user_memory, current_mode=None):
    """Generate AI response using OpenRouter API or fallback to local logic with mode support"""
    try:
        # Debug logging
        app.logger.info(f'API Key present: {bool(OPENROUTER_API_KEY)}')
        app.logger.info(f'API Key value: {OPENROUTER_API_KEY[:20]}...' if OPENROUTER_API_KEY else 'None')
        app.logger.info(f'Model: {OPENROUTER_MODEL}')
        app.logger.info(f'Current AI Mode: {current_mode.name if current_mode else "None"}')

        # Try OpenRouter API first
        if OPENROUTER_API_KEY and OPENROUTER_API_KEY != 'your-openrouter-api-key-here':
            app.logger.info('Attempting OpenRouter API call...')
            return call_openrouter_api(user_input, sensor_data, conversation, user_memory, current_mode)
        else:
            app.logger.info('Using local response generation (no valid API key)')
            # Fallback to enhanced local logic with mode support
            return generate_local_response(user_input, sensor_data, user_memory, current_mode)
    except Exception as e:
        app.logger.error(f'Error generating AI response: {str(e)}')
        return generate_local_response(user_input, sensor_data, user_memory, current_mode)

def call_openrouter_api(user_input, sensor_data, conversation, user_memory, current_mode=None):
    """Call OpenRouter API for AI response with RAG integration and mode support"""
    try:
        app.logger.info(f'Building API request for model: {OPENROUTER_MODEL}')
        
        # Get RAG results first
        from rag_integration import generate_answer
        rag_response, contexts = generate_answer(user_input)
        
        # Build conversation history for context
        messages = [
            {
                "role": "system",
                "content": build_system_prompt(sensor_data, user_memory, contexts, current_mode)
            }
        ]

        # Add recent conversation history (last 10 messages)
        recent_messages = conversation.messages[-10:] if conversation.messages else []
        for msg in recent_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Add current user message
        messages.append({
            "role": "user",
            "content": user_input
        })

        app.logger.info(f'Sending {len(messages)} messages to API')

        # Prepare API request
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://agri-genius.com",  # Optional
            "X-Title": "AgriGenius AI Assistant"  # Optional
        }

        payload = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7,
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1
        }

        app.logger.info(f'Making API call to: {OPENROUTER_BASE_URL}')

        # Make API call
        response = requests.post(
            OPENROUTER_BASE_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        app.logger.info(f'API response status: {response.status_code}')

        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']

            # Log API usage
            app.logger.info(f'OpenRouter API call successful. Model: {OPENROUTER_MODEL}')
            app.logger.info(f'Response length: {len(ai_response)} characters')

            return ai_response
        elif response.status_code == 404:
            # Model not found, try fallback models
            app.logger.warning(f'Model {OPENROUTER_MODEL} not available (404), trying fallback models')
            return try_fallback_models(payload, headers)
        else:
            app.logger.error(f'OpenRouter API error: {response.status_code} - {response.text}')
            raise Exception(f"API call failed with status {response.status_code}")

    except Exception as e:
        app.logger.error(f'OpenRouter API call failed: {str(e)}')
        raise e

def try_fallback_models(payload, headers):
    """Try fallback models when primary model fails"""
    fallback_models = [
        'meta-llama/llama-3.2-1b-instruct:free',
        'microsoft/phi-3-mini-128k-instruct:free',
        'google/gemma-2-9b-it:free',
        'qwen/qwen-2-7b-instruct:free'
    ]

    for model in fallback_models:
        try:
            app.logger.info(f'Trying fallback model: {model}')
            payload['model'] = model

            response = requests.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                app.logger.info(f'Fallback model {model} successful')
                return ai_response
            else:
                app.logger.warning(f'Fallback model {model} failed with status {response.status_code}')
                continue

        except Exception as e:
            app.logger.warning(f'Fallback model {model} error: {str(e)}')
            continue

    # If all fallback models fail, raise exception
    raise Exception("All models failed, including fallbacks")

def build_system_prompt(sensor_data, user_memory, contexts=None, current_mode=None):
    """Build system prompt with context including documentation, articles, and AI mode"""
    prompt = """You are AgriGenius AI, an expert agricultural assistant. You help farmers optimize their operations with intelligent advice based on real-time data and agricultural best practices.

CURRENT AI MODE: {mode_name}
MODE DESCRIPTION: {mode_description}

CURRENT SENSOR DATA:
"""
    
    # Add mode-specific instructions
    if current_mode:
        mode_instructions = get_mode_instructions(current_mode.name)
        prompt = prompt.format(
            mode_name=current_mode.display_name,
            mode_description=current_mode.description
        )
        prompt += f"\n\nMODE-SPECIFIC INSTRUCTIONS:\n{mode_instructions}\n\n"
    else:
        prompt += "\n\n"

    if sensor_data.get('status') != 'error':
        prompt += f"""
- Temperature: {sensor_data.get('temperature', 'N/A')}°C
- Humidity: {sensor_data.get('humidity', 'N/A')}%
- Soil Moisture: {sensor_data.get('soil_moisture', 'N/A')}%
- pH Level: {sensor_data.get('ph_level', 'N/A')}
- Light Intensity: {sensor_data.get('light_intensity', 'N/A')} lux
- Nitrogen: {sensor_data.get('nitrogen', 'N/A')} ppm
- Phosphorus: {sensor_data.get('phosphorus', 'N/A')} ppm
- Potassium: {sensor_data.get('potassium', 'N/A')} ppm
"""
    else:
        prompt += "- Sensor data currently unavailable\n"

    # Add relevant documentation and articles as knowledge base
    try:
        # Get recent verified articles and documentation
        recent_articles = Article.query.filter_by(verified=True).order_by(Article.created_at.desc()).limit(10).all()
        recent_docs = Documentation.query.filter_by(verified=True).order_by(Documentation.created_at.desc()).limit(10).all()

        if recent_articles:
            prompt += "\n\nRELEVANT ARTICLES FROM KNOWLEDGE BASE:\n"
            for article in recent_articles:
                prompt += f"\n- Title: {article.title}\n"
                prompt += f"  Category: {article.category}\n"
                prompt += f"  Summary: {article.content[:200]}...\n"

        if recent_docs:
            prompt += "\n\nRELEVANT DOCUMENTATION:\n"
            for doc in recent_docs:
                prompt += f"\n- Title: {doc.title}\n"
                prompt += f"  Category: {doc.category}\n"
                prompt += f"  Summary: {doc.content[:200]}...\n"

        prompt += "\n\nWhen providing information that comes from these sources, ALWAYS cite them using the format: [Source: Title]\n"
    except Exception as e:
        app.logger.error(f'Error fetching knowledge base: {str(e)}')
        
    # Add user memory context
    if user_memory:
        prompt += "\nUSER CONTEXT:\n"
        if 'crops' in user_memory:
            crops = list(user_memory['crops'].keys())
            prompt += f"- Grows: {', '.join(crops)}\n"
        if 'location' in user_memory:
            location = user_memory['location'].get('region', '')
            prompt += f"- Location: {location}\n"
        if 'farm_info' in user_memory:
            size = user_memory['farm_info'].get('size', '')
            if size:
                prompt += f"- Farm size: {size}\n"

    prompt += """
INSTRUCTIONS:
- Provide practical, actionable agricultural advice
- Reference current sensor data when relevant
- Be concise but comprehensive
- Use emojis sparingly for better readability
- Remember user's context and previous conversations
- If sensor data shows concerning values, prioritize addressing those issues
- Always consider safety and best practices
- Provide specific recommendations with reasoning

Respond as a knowledgeable agricultural expert who cares about the farmer's success."""

    return prompt

def generate_local_response(user_input, sensor_data, user_memory, current_mode=None):
    """Enhanced local response generation with user memory, source citations, and AI modes"""
    user_input_lower = user_input.lower()

    # Get user context
    user_crops = list(user_memory.get('crops', {}).keys()) if user_memory.get('crops') else []
    user_location = user_memory.get('location', {}).get('region', '') if user_memory.get('location') else ''

    # Search for relevant articles and documentation
    relevant_sources = []
    try:
        # Search in articles
        articles = Article.query.filter_by(verified=True).filter(
            (Article.title.contains(user_input)) |
            (Article.content.contains(user_input)) |
            (Article.tags.contains(user_input))
        ).limit(3).all()

        for article in articles:
            relevant_sources.append(f"[Source: {article.title}]")

        # Search in documentation
        docs = Documentation.query.filter_by(verified=True).filter(
            (Documentation.title.contains(user_input)) |
            (Documentation.content.contains(user_input)) |
            (Documentation.tags.contains(user_input))
        ).limit(3).all()

        for doc in docs:
            relevant_sources.append(f"[Ref: {doc.title}]")
    except Exception as e:
        app.logger.error(f'Error searching sources: {str(e)}')

    # Get mode-specific response style
    mode_style = get_mode_instructions(current_mode.name) if current_mode else get_mode_instructions('assist')

    # Personalized greeting
    if any(word in user_input_lower for word in ['hello', 'hi', 'hey', 'greetings']):
        greeting = "Hello! I'm your AgriGenius AI assistant. "
        if user_crops:
            greeting += f"I see you grow {', '.join(user_crops)}. "
        if user_location:
            greeting += f"How are things on your farm in {user_location}? "
        greeting += "How can I help you today?"
        
        # Add mode-specific greeting style
        if current_mode:
            if current_mode.name == 'learn':
                greeting += "\n\n📚 I'm currently in **Learning Mode** - I'll provide detailed explanations and educational content to help you understand agricultural concepts better."
            elif current_mode.name == 'read':
                greeting += "\n\n📖 I'm currently in **Reading Mode** - I'll analyze and summarize information clearly and concisely."
            elif current_mode.name == 'analyze':
                greeting += "\n\n📊 I'm currently in **Analysis Mode** - I'll focus on data-driven insights and detailed examination of your farm conditions."
            elif current_mode.name == 'creative':
                greeting += "\n\n💡 I'm currently in **Creative Mode** - I'll generate innovative ideas and creative farming solutions for you."
        
        return greeting

    # Sensor data with personalized context and mode-specific analysis
    elif any(word in user_input_lower for word in ['sensor', 'data', 'reading', 'current conditions']):
        if sensor_data.get('status') == 'error':
            return "I'm sorry, but there seems to be an issue with the sensor data right now. Please check the sensor connections."

        response = "📊 **Current Farm Conditions**\n\n"

        temp = sensor_data.get('temperature', 'N/A')
        humidity = sensor_data.get('humidity', 'N/A')
        soil_moisture = sensor_data.get('soil_moisture', 'N/A')
        ph = sensor_data.get('ph_level', 'N/A')

        # Add status indicators
        temp_status = "🟢 Optimal" if 20 <= temp <= 30 else "🟡 Monitor" if 15 <= temp <= 35 else "🔴 Alert"
        humidity_status = "🟢 Good" if 40 <= humidity <= 70 else "🟡 Watch" if 30 <= humidity <= 80 else "🔴 Concern"
        soil_status = "🟢 Good" if 40 <= soil_moisture <= 70 else "🟡 Check" if 25 <= soil_moisture <= 80 else "🔴 Action Needed"

        response += f"🌡️ **Temperature**: {temp}°C {temp_status}\n"
        response += f"💧 **Humidity**: {humidity}% {humidity_status}\n"
        response += f"🌱 **Soil Moisture**: {soil_moisture}% {soil_status}\n"
        response += f"⚗️ **pH Level**: {ph}\n"

        # Add mode-specific analysis
        if current_mode:
            if current_mode.name == 'learn':
                response += "\n📚 **Learning Mode Analysis**:\n"
                response += "Here's what these readings mean for your farm:\n"
                response += "• Temperature affects plant metabolic rates and growth\n"
                response += "• Humidity influences disease pressure and transpiration rates\n"
                response += "• Soil moisture is critical for nutrient uptake and root health\n"
                response += "• pH levels determine nutrient availability in the soil\n"
            elif current_mode.name == 'analyze':
                response += "\n📊 **Analysis Mode Insights**:\n"
                response += f"Data correlation analysis:\n"
                if temp > 30 and humidity > 70:
                    response += "• High temperature + high humidity = Increased fungal disease risk\n"
                if soil_moisture < 30 and temp > 25:
                    response += "• Low moisture + high temperature = Plant stress likely\n"
                if ph < 6.0:
                    response += "• Acidic pH may limit phosphorus and micronutrient availability\n"
            elif current_mode.name == 'creative':
                response += "\n💡 **Creative Mode Solutions**:\n"
                response += "Innovative approaches based on current conditions:\n"
                if temp > 30:
                    response += "• Consider evaporative cooling or shade cloth technology\n"
                if soil_moisture < 30:
                    response += "• Explore drip irrigation with moisture sensors for precision watering\n"
            elif current_mode.name == 'read':
                response += "\n📖 **Reading Mode Summary**:\n"
                response += f"Key observations: {temp_status}, {humidity_status}, {soil_status}\n"

        # Add crop-specific advice if user grows specific crops
        if user_crops:
            response += f"\n**For your {', '.join(user_crops)}:**\n"
            for crop in user_crops:
                if crop == 'tomatoes' and temp > 30:
                    response += "• Tomatoes may need shade in this heat\n"
                elif crop == 'lettuce' and temp > 25:
                    response += "• Lettuce prefers cooler conditions - consider shade cloth\n"

        # Add sources if found
        if relevant_sources:
            response += f"\n\n📚 **Sources**: {', '.join(relevant_sources[:3])}"

        return response

    # Enhanced watering advice with memory and mode-specific guidance
    elif any(word in user_input_lower for word in ['water', 'irrigation', 'watering']):
        soil_moisture = sensor_data.get('soil_moisture', 50)
        temp = sensor_data.get('temperature', 25)

        response = f"💧 **Watering Analysis**\n\n"
        response += f"Current soil moisture: {soil_moisture}%\n"
        response += f"Temperature: {temp}°C\n"

        if user_crops:
            response += f"Crops: {', '.join(user_crops)}\n"

        if soil_moisture < 30:
            urgency = "🔴 **URGENT**" if soil_moisture < 20 else "🟡 **SOON**"
            response += f"\n{urgency} - Watering needed!\n\n"
            response += "**Recommendations:**\n"
            response += "• Water immediately to prevent plant stress\n"
            response += "• Water early morning (6-8 AM) or evening (6-8 PM)\n"

            if 'tomatoes' in user_crops:
                response += "• Tomatoes need consistent moisture - avoid letting soil dry out\n"
            if 'lettuce' in user_crops:
                response += "• Lettuce needs frequent, light watering\n"

            # Add mode-specific watering advice
            if current_mode:
                if current_mode.name == 'learn':
                    response += "\n📚 **Learning Mode - Understanding Watering**:\n"
                    response += "Watering is crucial because:\n"
                    response += "• It transports nutrients from soil to roots\n"
                    response += "• It regulates plant temperature through transpiration\n"
                    response += "• It maintains turgor pressure for structural support\n"
                elif current_mode.name == 'analyze':
                    response += "\n📊 **Analysis Mode - Water Efficiency**:\n"
                    response += "Optimize water usage:\n"
                    response += "• Consider soil moisture sensor integration\n"
                    response += "• Calculate evapotranspiration rates\n"
                    response += "• Monitor water penetration depth\n"
                elif current_mode.name == 'creative':
                    response += "\n💡 **Creative Mode - Watering Innovations**:\n"
                    response += "Advanced watering techniques:\n"
                    response += "• Explore sub-irrigation systems\n"
                    response += "• Consider water harvesting and recycling\n"
                    response += "• Try automated irrigation scheduling\n"

        elif soil_moisture > 70:
            response += "\n🟡 **Hold off** - Soil is quite moist\n\n"
            response += "**Recommendations:**\n"
            response += "• Skip watering to prevent root rot\n"
            response += "• Ensure good drainage\n"
            response += "• Monitor for overwatering signs\n"
            
            if current_mode and current_mode.name == 'learn':
                response += "\n📚 **Learning Mode - Understanding Overwatering**:\n"
                response += "Overwatering risks include:\n"
                response += "• Root oxygen deprivation (asphyxiation)\n"
                response += "• Increased fungal disease susceptibility\n"
                response += "• Nutrient leaching from soil profile\n"
        else:
            response += "\n🟢 **Optimal** - Soil moisture is good\n\n"
            response += "**Recommendations:**\n"
            response += "• Continue current watering schedule\n"
            response += "• Water when moisture drops below 30%\n"

            if current_mode and current_mode.name == 'creative':
                response += "\n💡 **Creative Mode - Optimization Ideas**:\n"
                response += "Enhance your current system:\n"
                response += "• Implement smart irrigation controllers\n"
                response += "• Add soil moisture sensors for automation\n"
                response += "• Create custom watering schedules per crop zone\n"

        return response

    # Default response with personalization and mode-specific introduction
    else:
        response = "🤖 **AgriGenius AI Assistant**\n\n"

        if user_crops or user_location:
            response += "I remember you"
            if user_crops:
                response += f" grow {', '.join(user_crops)}"
            if user_location:
                response += f" in {user_location}"
            response += ". "

        # Add mode-specific introduction
        if current_mode:
            response += f"\n🎯 **Current Mode: {current_mode.display_name}**\n"
            response += f"{current_mode.description}\n\n"
            
            if current_mode.name == 'learn':
                response += "📚 In **Learning Mode**, I'll focus on educational content and help you understand agricultural concepts deeply.\n\n"
            elif current_mode.name == 'read':
                response += "📖 In **Reading Mode**, I'll analyze and summarize information clearly and concisely.\n\n"
            elif current_mode.name == 'analyze':
                response += "📊 In **Analysis Mode**, I'll provide data-driven insights and detailed examination of your farm conditions.\n\n"
            elif current_mode.name == 'creative':
                response += "💡 In **Creative Mode**, I'll generate innovative ideas and creative farming solutions.\n\n"
            elif current_mode.name == 'assist':
                response += "🤖 In **Assist Mode**, I'll provide general farming assistance and practical advice.\n\n"

        response += "I can help you with:\n\n"
        response += "• 📊 **Sensor Data & Analysis**\n"
        response += "• 💧 **Irrigation & Watering**\n"
        response += "• 🧪 **Fertilizers & Nutrients**\n"
        response += "• 🛡️ **Disease & Pest Prevention**\n"
        response += "• 🌤️ **Weather & Climate**\n"
        response += "• 🌾 **Crop-Specific Guidance**\n\n"

        response += "**Try asking:**\n"
        response += "• 'What are my current sensor readings?'\n"
        response += "• 'When should I water my plants?'\n"
        response += "• 'What fertilizer should I use?'\n"

        if user_crops:
            response += f"• 'How to care for my {user_crops[0]}?'\n"

        return response

def generate_chatbot_response(user_input, sensor_data):
    """Generate chatbot response based on user input and sensor data"""
    user_input_lower = user_input.lower()

    # Greeting responses
    if any(word in user_input_lower for word in ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon']):
        greetings = [
            "Hello! I'm your AgriGenius AI assistant. I can help you with farming advice, sensor data, and agricultural questions. What would you like to know?",
            "Hi there! Welcome to AgriGenius! I'm here to help you optimize your farming operations. How can I assist you today?",
            "Greetings, farmer! I'm your AI agricultural advisor. Ask me about crops, soil, weather, or check your sensor data!"
        ]
        import random
        return random.choice(greetings)

    # Sensor data requests
    elif any(word in user_input_lower for word in ['sensor', 'data', 'reading', 'temperature', 'humidity', 'current conditions']):
        if sensor_data.get('status') == 'error':
            return "I'm sorry, but there seems to be an issue with the sensor data right now. Please check the sensor connections."

        temp = sensor_data.get('temperature', 'N/A')
        humidity = sensor_data.get('humidity', 'N/A')
        soil_moisture = sensor_data.get('soil_moisture', 'N/A')
        ph = sensor_data.get('ph_level', 'N/A')
        light = sensor_data.get('light_intensity', 'N/A')

        # Add status indicators
        temp_status = "🟢 Optimal" if 20 <= temp <= 30 else "🟡 Monitor" if 15 <= temp <= 35 else "🔴 Alert"
        humidity_status = "🟢 Good" if 40 <= humidity <= 70 else "🟡 Watch" if 30 <= humidity <= 80 else "🔴 Concern"
        soil_status = "🟢 Good" if 40 <= soil_moisture <= 70 else "🟡 Check" if 25 <= soil_moisture <= 80 else "🔴 Action Needed"

        return f"""📊 **Current Farm Conditions**

🌡️ **Temperature**: {temp}°C {temp_status}
💧 **Humidity**: {humidity}% {humidity_status}
🌱 **Soil Moisture**: {soil_moisture}% {soil_status}
⚗️ **pH Level**: {ph}
☀️ **Light**: {light} lux

Would you like specific recommendations based on these readings?"""

    # Recommendations
    elif any(word in user_input_lower for word in ['recommend', 'advice', 'suggest', 'help', 'what should', 'optimize']):
        from sensors.sensors import get_sensor_recommendations
        recommendations = get_sensor_recommendations(sensor_data)
        return f"""🎯 **Smart Farming Recommendations**

Based on your current sensor readings, here's what I suggest:

{chr(10).join(f"• {rec}" for rec in recommendations)}

💡 **Pro Tip**: Regular monitoring helps catch issues early. Check your sensors daily for best results!"""

    # Watering questions
    elif any(word in user_input_lower for word in ['water', 'irrigation', 'watering', 'when to water']):
        soil_moisture = sensor_data.get('soil_moisture', 50)
        temp = sensor_data.get('temperature', 25)
        humidity = sensor_data.get('humidity', 60)

        if soil_moisture < 30:
            urgency = "🔴 **URGENT**" if soil_moisture < 20 else "🟡 **SOON**"
            return f"""{urgency} - Watering Needed!

💧 **Current soil moisture**: {soil_moisture}%
🌡️ **Temperature**: {temp}°C
💨 **Humidity**: {humidity}%

**Recommendation**: Water your plants immediately. Low soil moisture can stress plants and reduce yield.

**Best practices**:
• Water early morning (6-8 AM) or evening (6-8 PM)
• Water slowly and deeply rather than frequent shallow watering
• Check soil 2-3 inches deep before watering"""
        elif soil_moisture > 70:
            return f"""🟡 **Hold Off** - Soil is quite moist

💧 **Current soil moisture**: {soil_moisture}%
🌡️ **Temperature**: {temp}°C

**Recommendation**: Skip watering for now. Overwatering can cause root rot and fungal diseases.

**What to do**:
• Ensure good drainage
• Check for standing water
• Monitor for signs of overwatering (yellowing leaves, musty smell)
• Wait until moisture drops to 40-50% before next watering"""
        else:
            return f"""🟢 **Perfect Range** - Soil moisture is optimal

💧 **Current soil moisture**: {soil_moisture}%
🌡️ **Temperature**: {temp}°C

**Status**: Your soil moisture is in the ideal range!

**Next steps**:
• Continue monitoring daily
• Water when moisture drops below 30%
• Adjust watering schedule based on weather and plant growth stage"""

    # Fertilizer questions
    elif any(word in user_input_lower for word in ['fertilizer', 'nutrient', 'nitrogen', 'phosphorus', 'potassium', 'npk', 'feeding']):
        nitrogen = sensor_data.get('nitrogen', 0)
        phosphorus = sensor_data.get('phosphorus', 0)
        potassium = sensor_data.get('potassium', 0)
        ph = sensor_data.get('ph_level', 7)

        # Analyze nutrient levels
        n_status = "🟢 Good" if nitrogen >= 20 else "🟡 Low" if nitrogen >= 15 else "🔴 Very Low"
        p_status = "🟢 Good" if phosphorus >= 10 else "🟡 Low" if phosphorus >= 7 else "🔴 Very Low"
        k_status = "🟢 Good" if potassium >= 25 else "🟡 Low" if potassium >= 20 else "🔴 Very Low"

        response = f"""🧪 **Nutrient Analysis Report**

**Current Levels:**
• 🔵 Nitrogen (N): {nitrogen} ppm {n_status}
• 🟠 Phosphorus (P): {phosphorus} ppm {p_status}
• 🟣 Potassium (K): {potassium} ppm {k_status}
• ⚗️ pH Level: {ph}

**Recommendations:**"""

        advice = []
        if nitrogen < 20:
            advice.append(f"**Nitrogen Boost Needed**: Apply nitrogen-rich fertilizer (urea, ammonium sulfate, or compost)")
        if phosphorus < 10:
            advice.append(f"**Phosphorus Deficiency**: Use bone meal, rock phosphate, or balanced NPK fertilizer")
        if potassium < 25:
            advice.append(f"**Potassium Low**: Apply potash, wood ash, or potassium sulfate")

        if ph < 6.0:
            advice.append(f"**pH Too Acidic**: Add lime to raise pH for better nutrient uptake")
        elif ph > 7.5:
            advice.append(f"**pH Too Alkaline**: Add sulfur or organic matter to lower pH")

        if advice:
            response += "\n" + "\n".join(f"• {a}" for a in advice)
            response += f"\n\n💡 **Timing**: Best to fertilize in early morning or late evening. Water after application."
        else:
            response += f"\n• ✅ **All nutrient levels are optimal!** Continue current fertilization program."

        return response

    # Disease and pest questions
    elif any(word in user_input_lower for word in ['disease', 'pest', 'bug', 'insect', 'fungus', 'mold', 'rot', 'prevention']):
        humidity = sensor_data.get('humidity', 60)
        temp = sensor_data.get('temperature', 25)

        return f"""🛡️ **Disease & Pest Prevention Guide**

**Current Risk Assessment:**
• 🌡️ Temperature: {temp}°C
• 💨 Humidity: {humidity}%

**Risk Level**: {"🔴 High" if humidity > 80 or temp > 30 else "🟡 Moderate" if humidity > 70 or temp > 28 else "🟢 Low"}

**Prevention Strategies:**
• 🌬️ **Air Circulation**: Ensure good airflow around plants
• 💧 **Water Management**: Water at soil level, avoid wetting leaves
• 🧹 **Cleanliness**: Remove dead/diseased plant material promptly
• 🔄 **Crop Rotation**: Rotate crops to break disease cycles
• 🌿 **Companion Planting**: Use pest-repelling plants (marigolds, basil)

**Natural Treatments:**
• Neem oil for aphids and fungal issues
• Diatomaceous earth for crawling insects
• Copper fungicide for bacterial diseases
• Beneficial insects (ladybugs, lacewings)"""

    # Weather and climate questions
    elif any(word in user_input_lower for word in ['weather', 'climate', 'rain', 'sun', 'wind', 'forecast']):
        temp = sensor_data.get('temperature', 25)
        humidity = sensor_data.get('humidity', 60)
        light = sensor_data.get('light_intensity', 1000)

        return f"""🌤️ **Weather Impact Analysis**

**Current Conditions:**
• 🌡️ Temperature: {temp}°C
• 💨 Humidity: {humidity}%
• ☀️ Light Intensity: {light} lux

**Agricultural Impact:**
• **Temperature**: {"Ideal for most crops" if 20 <= temp <= 30 else "Monitor stress levels" if temp > 30 else "Cool weather crops preferred"}
• **Humidity**: {"Good for plant health" if 40 <= humidity <= 70 else "Risk of fungal diseases" if humidity > 80 else "May need irrigation"}
• **Light**: {"Excellent for photosynthesis" if light > 1000 else "Adequate light levels" if light > 500 else "Consider supplemental lighting"}

**Recommendations:**
• Plan irrigation based on humidity levels
• Adjust planting schedules for temperature
• Monitor for weather-related stress
• Use row covers or shade cloth if needed"""

    # Crop-specific questions
    elif any(word in user_input_lower for word in ['tomato', 'corn', 'wheat', 'rice', 'potato', 'lettuce', 'carrot', 'bean', 'crop']):
        return f"""🌾 **Crop-Specific Guidance**

I can help with specific crops! Here are some general tips:

**Popular Crops:**
• 🍅 **Tomatoes**: Need warm soil (60°F+), consistent watering, pH 6.0-6.8
• 🌽 **Corn**: Requires full sun, rich soil, regular watering during tasseling
• 🌾 **Wheat**: Cool season crop, plant in fall, needs good drainage
• 🥬 **Lettuce**: Cool weather crop, partial shade in summer, frequent light watering
• 🥕 **Carrots**: Deep, loose soil, consistent moisture, thin seedlings

**Current conditions suggest**: {
    "Good for warm-season crops" if sensor_data.get('temperature', 25) > 25
    else "Ideal for cool-season crops" if sensor_data.get('temperature', 25) < 20
    else "Suitable for most crops"
}

Ask me about a specific crop for detailed growing advice!"""

    # Default response with suggestions
    else:
        suggestions = [
            "🌡️ 'What are the current sensor readings?'",
            "💧 'When should I water my plants?'",
            "🧪 'What fertilizer should I use?'",
            "🛡️ 'How to prevent plant diseases?'",
            "🌤️ 'How does weather affect my crops?'",
            "🌾 'Tell me about growing tomatoes'"
        ]

        return f"""🤖 **AgriGenius AI Assistant**

I'm here to help with all your farming questions! I can provide advice on:

• 📊 **Sensor Data & Monitoring**
• 💧 **Irrigation & Watering**
• 🧪 **Fertilizers & Nutrients**
• 🛡️ **Disease & Pest Prevention**
• 🌤️ **Weather & Climate**
• 🌾 **Crop-Specific Guidance**

**Try asking me:**
{chr(10).join(suggestions)}

Or just ask me anything about farming - I'm here to help! 🌱"""


# Profile route: shows user info and access links
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/dashboard')
def public_dashboard():
    users_with_articles = db.session.query(User).join(Article).group_by(User.id).all()
    users_with_docs = db.session.query(User).join(Documentation).group_by(User.id).all()
    users = {u.id: u for u in users_with_articles + users_with_docs}.values()
    return render_template('public_dashboard.html', users=users)

# Public user profile page (define after all models and app are set up)
@app.route('/user/<int:user_id>')
def public_profile(user_id):
    user = User.query.get_or_404(user_id)
    user_articles = Article.query.filter_by(author_id=user.id).all()
    user_docs = Documentation.query.filter_by(author_id=user.id).all()
    return render_template('public_profile.html', user=user, articles=user_articles, docs=user_docs)

# Article and Documentation Enhancement Routes

# Like/Unlike article
@app.route('/api/like_article/<int:article_id>', methods=['POST'])
@login_required
def like_article(article_id):
    try:
        article = Article.query.get_or_404(article_id)
        existing_like = Like.query.filter_by(user_id=current_user.id, article_id=article_id).first()
        
        if existing_like:
            # Unlike
            db.session.delete(existing_like)
            article.likes = max(0, article.likes - 1)
            liked = False
        else:
            # Like
            new_like = Like(user_id=current_user.id, article_id=article_id)
            db.session.add(new_like)
            article.likes += 1
            liked = True
        
        # Get updated like count
        like_count = Like.query.filter_by(article_id=article_id).count()
        
        db.session.commit()
        return jsonify({
            'liked': liked,
            'likes_count': like_count,
            'message': 'Article ' + ('liked' if liked else 'unliked') + ' successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Like/Unlike documentation
@app.route('/api/like_doc/<int:doc_id>', methods=['POST'])
@login_required
def like_doc(doc_id):
    try:
        doc = Documentation.query.get_or_404(doc_id)
        existing_like = Like.query.filter_by(user_id=current_user.id, doc_id=doc_id).first()
        
        if existing_like:
            # Unlike
            db.session.delete(existing_like)
            doc.likes = max(0, doc.likes - 1)
            liked = False
        else:
            # Like
            new_like = Like(user_id=current_user.id, doc_id=doc_id)
            db.session.add(new_like)
            doc.likes += 1
            liked = True
        
        db.session.commit()
        return jsonify({'liked': liked, 'likes_count': doc.likes})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Add comment to article
@app.route('/api/comment_article/<int:article_id>', methods=['POST'])
@login_required
def comment_article(article_id):
    try:
        data = request.json
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'error': 'Comment cannot be empty'}), 400
        
        article = Article.query.get_or_404(article_id)
        comment = Comment(
            user_id=current_user.id,
            article_id=article_id,
            content=content
        )
        db.session.add(comment)
        db.session.commit()
        
        # Get updated comment count
        comment_count = Comment.query.filter_by(article_id=article_id).count()
        
        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'author': {
                    'id': current_user.id,
                    'username': current_user.username
                },
                'can_delete': True,
                'article_id': article_id,
                'created_at': comment.created_at.isoformat()
            },
            'comment_count': comment_count,
            'message': 'Comment added successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Delete comment from article
@app.route('/api/delete_comment/<int:article_id>/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(article_id, comment_id):
    try:
        comment = Comment.query.get_or_404(comment_id)
        
        # Check if user can delete (author of comment, article owner, or admin)
        if not (comment.user_id == current_user.id or 
                comment.article.author_id == current_user.id or 
                current_user.is_admin):
            return jsonify({'error': 'Permission denied'}), 403
        
        db.session.delete(comment)
        
        # Get updated comment count
        comment_count = Comment.query.filter_by(article_id=article_id).count()
        
        db.session.commit()
        return jsonify({
            'success': True,
            'comment_count': comment_count,
            'message': 'Comment deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Add comment to documentation
@app.route('/api/comment_doc/<int:doc_id>', methods=['POST'])
@login_required
def comment_doc(doc_id):
    try:
        data = request.json
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'error': 'Comment cannot be empty'}), 400
        
        doc = Documentation.query.get_or_404(doc_id)
        comment = Comment(
            user_id=current_user.id,
            doc_id=doc_id,
            content=content
        )
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'author': current_user.username,
                'created_at': comment.created_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Save/unsave article (Save for later)
@app.route('/api/save_article/<int:article_id>', methods=['POST'])
@login_required
def save_article(article_id):
    try:
        article = Article.query.get_or_404(article_id)
        existing = SavedArticle.query.filter_by(user_id=current_user.id, article_id=article_id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return jsonify({
                'saved': False,
                'message': 'Article removed from saved'
            })
        else:
            saved = SavedArticle(
                user_id=current_user.id, 
                article_id=article_id
            )
            db.session.add(saved)
            db.session.commit()
            return jsonify({
                'saved': True,
                'message': 'Article saved successfully'
            })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error saving article {article_id}: {str(e)}')
        return jsonify({'error': str(e)}), 500

# Edit article
@app.route('/edit_article/<int:article_id>', methods=['GET', 'POST'])
@login_required
def edit_article(article_id):
    article = Article.query.get_or_404(article_id)
    
    # Check if user can edit (author or admin)
    if article.author_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to edit this article.')
        return redirect(url_for('articles'))
    
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            category = request.form.get('category', 'General').strip()
            tags = request.form.get('tags', '').strip()
            
            # Validation
            if not title or len(title) < 3:
                flash('Title must be at least 3 characters long.')
                return render_template('edit_article.html', article=article)
            
            if not content or len(content) < 10:
                flash('Content must be at least 10 characters long.')
                return render_template('edit_article.html', article=article)
            
            # Update article
            article.title = title
            article.content = content
            article.category = category
            article.tags = tags
            article.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Article updated successfully!')
            return redirect(url_for('articles'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error updating article. Please try again.')
            app.logger.error(f'Error updating article: {str(e)}')
    
    return render_template('edit_article.html', article=article)

# Edit documentation
@app.route('/edit_doc/<int:doc_id>', methods=['GET', 'POST'])
@login_required
def edit_doc(doc_id):
    doc = Documentation.query.get_or_404(doc_id)
    
    # Check if user can edit (author or admin)
    if doc.author_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to edit this documentation.')
        return redirect(url_for('documentation'))
    
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            category = request.form.get('category', 'General').strip()
            tags = request.form.get('tags', '').strip()
            
            # Validation
            if not title or len(title) < 3:
                flash('Title must be at least 3 characters long.')
                return render_template('edit_doc.html', doc=doc)
            
            if not content or len(content) < 10:
                flash('Content must be at least 10 characters long.')
                return render_template('edit_doc.html', doc=doc)
            
            # Update documentation
            doc.title = title
            doc.content = content
            doc.category = category
            doc.tags = tags
            doc.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Documentation updated successfully!')
            return redirect(url_for('documentation'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error updating documentation. Please try again.')
            app.logger.error(f'Error updating documentation: {str(e)}')
    
    return render_template('edit_doc.html', doc=doc)

# Delete article
@app.route('/delete_article/<int:article_id>', methods=['POST'])
@login_required
def delete_article(article_id):
    try:
        article = Article.query.get_or_404(article_id)
        
        # Check if user can delete (author or admin)
        if article.author_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to delete this article.')
            return redirect(url_for('articles'))
        
        # Delete related likes and comments
        Like.query.filter_by(article_id=article_id).delete()
        Comment.query.filter_by(article_id=article_id).delete()
        
        # Delete article
        db.session.delete(article)
        db.session.commit()
        
        flash('Article deleted successfully!')
        app.logger.info(f'Article {article_id} deleted by user {current_user.username}')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting article. Please try again.')
        app.logger.error(f'Error deleting article {article_id}: {str(e)}')
    
    return redirect(url_for('articles'))

# Delete documentation
@app.route('/delete_doc/<int:doc_id>', methods=['POST'])
@login_required
def delete_doc(doc_id):
    try:
        doc = Documentation.query.get_or_404(doc_id)
        
        # Check if user can delete (author or admin)
        if doc.author_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to delete this documentation.')
            return redirect(url_for('documentation'))
        
        # Delete related likes and comments
        Like.query.filter_by(doc_id=doc_id).delete()
        Comment.query.filter_by(doc_id=doc_id).delete()
        
        # Delete documentation
        db.session.delete(doc)
        db.session.commit()
        
        flash('Documentation deleted successfully!')
        app.logger.info(f'Documentation {doc_id} deleted by user {current_user.username}')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting documentation. Please try again.')
        app.logger.error(f'Error deleting documentation {doc_id}: {str(e)}')
    
    return redirect(url_for('documentation'))

# View article (increment views)
@app.route('/view_article/<int:article_id>')
def view_article(article_id):
    try:
        article = Article.query.get_or_404(article_id)
        article.views += 1
        db.session.commit()
        
        # Get comments for article
        comments = Comment.query.filter_by(article_id=article_id)\
            .order_by(Comment.created_at.desc()).all()
            
        # Check if user has liked the article
        liked = False
        saved = False
        if current_user.is_authenticated:
            liked = Like.query.filter_by(
                user_id=current_user.id, 
                article_id=article_id
            ).first() is not None
            saved = SavedArticle.query.filter_by(
                user_id=current_user.id, 
                article_id=article_id
            ).first() is not None
        
        # Get related articles based on category
        related_articles = Article.query\
            .filter(Article.id != article_id)\
            .filter_by(category=article.category)\
            .filter_by(verified=True)\
            .order_by(Article.created_at.desc())\
            .limit(3)\
            .all()
        
        return render_template('view_article.html', 
            article=article,
            comments=comments,
            liked=liked,
            saved=saved,
            related_articles=related_articles
        )
    except Exception as e:
        app.logger.error(f'Error viewing article {article_id}: {str(e)}')
        return redirect(url_for('articles'))

# View documentation (increment views)
@app.route('/view_doc/<int:doc_id>')
def view_doc(doc_id):
    try:
        doc = Documentation.query.get_or_404(doc_id)
        doc.views += 1
        db.session.commit()
        return render_template('view_doc.html', doc=doc)
    except Exception as e:
        app.logger.error(f'Error viewing documentation {doc_id}: {str(e)}')
        return redirect(url_for('documentation'))



@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


# Initialize AI Modes
def initialize_ai_modes():
    """Initialize default AI modes if they don't exist"""
    default_modes = [
        {
            'name': 'learn',
            'display_name': 'Learn',
            'description': 'Focus on educational content and agricultural learning',
            'icon': 'fa-graduation-cap',
            'color': '#4CAF50'
        },
        {
            'name': 'read',
            'display_name': 'Read',
            'description': 'Document analysis and content summarization',
            'icon': 'fa-book-open',
            'color': '#2196F3'
        },
        {
            'name': 'analyze',
            'display_name': 'Analyze',
            'description': 'Data analysis and agricultural insights',
            'icon': 'fa-chart-line',
            'color': '#FF9800'
        },
        {
            'name': 'assist',
            'display_name': 'Assist',
            'description': 'General farming assistance and advice',
            'icon': 'fa-robot',
            'color': '#9C27B0'
        },
        {
            'name': 'creative',
            'display_name': 'Creative',
            'description': 'Innovative farming ideas and creative solutions',
            'icon': 'fa-lightbulb',
            'color': '#E91E63'
        }
    ]
    
    for mode_data in default_modes:
        existing_mode = AIMode.query.filter_by(name=mode_data['name']).first()
        if not existing_mode:
            mode = AIMode(**mode_data)
            db.session.add(mode)
    
    db.session.commit()
    app.logger.info('AI modes initialized successfully')

# AI Mode Helper Functions
def get_current_ai_mode(user_id, session_id):
    """Get the current AI mode for user or session"""
    try:
        # First try to get from user preference
        if user_id:
            preference = UserAIModePreference.query.filter_by(user_id=user_id).order_by(UserAIModePreference.updated_at.desc()).first()
            if preference:
                return preference.mode
        
        # Then try session preference
        if session_id:
            preference = UserAIModePreference.query.filter_by(session_id=session_id).order_by(UserAIModePreference.updated_at.desc()).first()
            if preference:
                return preference.mode
        
        # Default to 'assist' mode
        default_mode = AIMode.query.filter_by(name='assist').first()
        return default_mode
    except Exception as e:
        app.logger.error(f'Error getting current AI mode: {str(e)}')
        return None

def set_current_ai_mode(user_id, session_id, mode_name):
    """Set the current AI mode for user or session"""
    try:
        mode = AIMode.query.filter_by(name=mode_name).first()
        if not mode:
            return False
        
        # Check if preference already exists
        if user_id:
            existing_preference = UserAIModePreference.query.filter_by(user_id=user_id).first()
            if existing_preference:
                existing_preference.mode_id = mode.id
                existing_preference.updated_at = datetime.now(timezone.utc)
            else:
                preference = UserAIModePreference(user_id=user_id, mode_id=mode.id)
                db.session.add(preference)
        else:
            existing_preference = UserAIModePreference.query.filter_by(session_id=session_id).first()
            if existing_preference:
                existing_preference.mode_id = mode.id
                existing_preference.updated_at = datetime.now(timezone.utc)
            else:
                preference = UserAIModePreference(session_id=session_id, mode_id=mode.id)
                db.session.add(preference)
        
        db.session.commit()
        return True
    except Exception as e:
        app.logger.error(f'Error setting AI mode: {str(e)}')
        return False

def get_all_ai_modes():
    """Get all active AI modes"""
    try:
        return AIMode.query.filter_by(is_active=True).order_by(AIMode.display_name).all()
    except Exception as e:
        app.logger.error(f'Error getting AI modes: {str(e)}')
        return []

# API endpoints for AI mode management
@app.route('/api/ai-modes', methods=['GET'])
def get_ai_modes():
    """Get all available AI modes"""
    try:
        modes = get_all_ai_modes()
        modes_data = []
        for mode in modes:
            modes_data.append({
                'id': mode.id,
                'name': mode.name,
                'display_name': mode.display_name,
                'description': mode.description,
                'icon': mode.icon,
                'color': mode.color
            })
        
        return jsonify({'modes': modes_data})
    except Exception as e:
        app.logger.error(f'Error fetching AI modes: {str(e)}')
        return jsonify({'error': 'Failed to fetch AI modes'}), 500

@app.route('/api/ai-modes/<mode_name>/set', methods=['POST'])
def set_ai_mode(mode_name):
    """Set the current AI mode for the user or session"""
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        session_id = session.get('chat_session_id')
        
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())
            session['chat_session_id'] = session_id
        
        success = set_current_ai_mode(user_id, session_id, mode_name)
        if success:
            return jsonify({'success': True, 'message': f'Mode changed to {mode_name}'})
        else:
            return jsonify({'success': False, 'message': 'Invalid mode name'}), 400
    except Exception as e:
        app.logger.error(f'Error setting AI mode: {str(e)}')
        return jsonify({'error': 'Failed to set AI mode'}), 500

@app.route('/api/current-ai-mode', methods=['GET'])
def get_current_mode():
    """Get the current AI mode"""
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        session_id = session.get('chat_session_id')
        
        current_mode = get_current_ai_mode(user_id, session_id)
        if current_mode:
            return jsonify({
                'mode': {
                    'id': current_mode.id,
                    'name': current_mode.name,
                    'display_name': current_mode.display_name,
                    'description': current_mode.description,
                    'icon': current_mode.icon,
                    'color': current_mode.color
                }
            })
        else:
            return jsonify({'error': 'No current mode found'}), 404
    except Exception as e:
        app.logger.error(f'Error getting current mode: {str(e)}')
        return jsonify({'error': 'Failed to get current mode'}), 500

# Initialize AI modes on app startup (will be called after db creation)
def initialize_app():
    with app.app_context():
        initialize_ai_modes()

def get_mode_instructions(mode_name):
    """Get mode-specific instructions for AI behavior"""
    mode_instructions = {
        'learn': """
- Focus on educational content and agricultural learning
- Provide detailed explanations of farming concepts
- Include step-by-step guides and tutorials
- Recommend learning resources and further reading
- Ask follow-up questions to deepen understanding
- Use teaching language and examples
- Prioritize accuracy and completeness of information
""",
        'read': """
- Specialize in document analysis and content summarization
- Provide concise summaries of agricultural content
- Extract key information and main points
- Organize information in a clear, readable format
- Highlight important data and recommendations
- Maintain the original meaning and context
- Focus on actionable insights from documents
""",
        'analyze': """
- Focus on data analysis and agricultural insights
- Examine sensor data and trends carefully
- Provide data-driven recommendations
- Identify patterns and correlations
- Use analytical language and evidence-based reasoning
- Consider multiple factors before giving advice
- Provide quantitative insights when possible
""",
        'assist': """
- Provide general farming assistance and advice
- Be helpful, practical, and solution-oriented
- Adapt to user's specific needs and context
- Give clear, actionable recommendations
- Be conversational and approachable
- Focus on solving immediate problems
- Balance expertise with user-friendliness
""",
        'creative': """
- Generate innovative farming ideas and creative solutions
- Think outside traditional agricultural approaches
- Suggest novel applications and techniques
- Encourage experimentation and new methods
- Use imaginative language and examples
- Focus on possibilities and opportunities
- Inspire users to try new things
"""
    }
    return mode_instructions.get(mode_name, mode_instructions['assist'])

# Run the app
if __name__ == '__main__':
    # Use 0.0.0.0 to make the app accessible on your local network
    app.run(host='0.0.0.0', port=5000, debug=True)


# Notes:
# - home.html, articles.html, documentation.html, login.html, signup.html templates are required in the templates/ folder.
# - Replace 'your_secret_key_here' and 'https://your-n8n-chatbot-url.com' with your actual values.
# - Use Bootstrap in your templates for styling.
# - Comments are provided above each section for clarity.