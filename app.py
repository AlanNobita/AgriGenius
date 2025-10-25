
# ...existing code...
import os
from flask import Flask, render_template, redirect, url_for, request, jsonify, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import logging
import requests
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from sensors.sensors import get_sensor_data
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///farmgenius.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', 'your-openrouter-api-key-here')
# Force reload environment variables
from dotenv import load_dotenv
load_dotenv(override=True)
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'meta-llama/llama-4-maverick:free')  # Default model
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('flask.log'),
        logging.StreamHandler()
    ]
)


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


# Documentation model for restricted articles
class Documentation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    verified = db.Column(db.Boolean, default=False)  # Admin verification

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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home route (Sector 5)
@app.route('/')
def home():
    return render_template('home.html')


# Sector 1: Public Articles


# View all articles
@app.route('/articles')
def articles():
    all_articles = Article.query.all()
    return render_template('articles.html', articles=all_articles)

@app.route('/marketplace')
def marketplace():
    return render_template('marketplace.html')

# Post a new article
@app.route('/post_article', methods=['GET', 'POST'])
@login_required
def post_article():
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()

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

            new_article = Article(
                title=title,
                content=content,
                author_id=current_user.id,
                verified=False
            )
            db.session.add(new_article)
            db.session.commit()
            flash('Article submitted for review!')
            app.logger.info(f'User {current_user.username} submitted article: {title}')
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
                verified=False
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

            if not username or not password:
                flash('Please enter both username and password.')
                return render_template('login.html')

            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
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
            hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
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

        # Generate AI response
        ai_response = generate_ai_response(user_input, sensor_data, conversation, user_memory)

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

def generate_ai_response(user_input, sensor_data, conversation, user_memory):
    """Generate AI response using OpenRouter API or fallback to local logic"""
    try:
        # Debug logging
        app.logger.info(f'API Key present: {bool(OPENROUTER_API_KEY)}')
        app.logger.info(f'API Key value: {OPENROUTER_API_KEY[:20]}...' if OPENROUTER_API_KEY else 'None')
        app.logger.info(f'Model: {OPENROUTER_MODEL}')

        # Try OpenRouter API first
        if OPENROUTER_API_KEY and OPENROUTER_API_KEY != 'your-openrouter-api-key-here':
            app.logger.info('Attempting OpenRouter API call...')
            return call_openrouter_api(user_input, sensor_data, conversation, user_memory)
        else:
            app.logger.info('Using local response generation (no valid API key)')
            # Fallback to enhanced local logic
            return generate_local_response(user_input, sensor_data, user_memory)
    except Exception as e:
        app.logger.error(f'Error generating AI response: {str(e)}')
        return generate_local_response(user_input, sensor_data, user_memory)

def call_openrouter_api(user_input, sensor_data, conversation, user_memory):
    """Call OpenRouter API for AI response"""
    try:
        app.logger.info(f'Building API request for model: {OPENROUTER_MODEL}')

        # Build conversation history for context
        messages = [
            {
                "role": "system",
                "content": build_system_prompt(sensor_data, user_memory)
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

def build_system_prompt(sensor_data, user_memory):
    """Build system prompt with context"""
    prompt = """You are AgriGenius AI, an expert agricultural assistant. You help farmers optimize their operations with intelligent advice based on real-time data and agricultural best practices.

CURRENT SENSOR DATA:
"""

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

def generate_local_response(user_input, sensor_data, user_memory):
    """Enhanced local response generation with user memory"""
    user_input_lower = user_input.lower()

    # Get user context
    user_crops = list(user_memory.get('crops', {}).keys()) if user_memory.get('crops') else []
    user_location = user_memory.get('location', {}).get('region', '') if user_memory.get('location') else ''

    # Personalized greeting
    if any(word in user_input_lower for word in ['hello', 'hi', 'hey', 'greetings']):
        greeting = "Hello! I'm your AgriGenius AI assistant. "
        if user_crops:
            greeting += f"I see you grow {', '.join(user_crops)}. "
        if user_location:
            greeting += f"How are things on your farm in {user_location}? "
        greeting += "How can I help you today?"
        return greeting

    # Sensor data with personalized context
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

        # Add crop-specific advice if user grows specific crops
        if user_crops:
            response += f"\n**For your {', '.join(user_crops)}:**\n"
            for crop in user_crops:
                if crop == 'tomatoes' and temp > 30:
                    response += "• Tomatoes may need shade in this heat\n"
                elif crop == 'lettuce' and temp > 25:
                    response += "• Lettuce prefers cooler conditions - consider shade cloth\n"

        return response

    # Enhanced watering advice with memory
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

        elif soil_moisture > 70:
            response += "\n🟡 **Hold off** - Soil is quite moist\n\n"
            response += "**Recommendations:**\n"
            response += "• Skip watering to prevent root rot\n"
            response += "• Ensure good drainage\n"
            response += "• Monitor for overwatering signs\n"
        else:
            response += "\n🟢 **Optimal** - Soil moisture is good\n\n"
            response += "**Recommendations:**\n"
            response += "• Continue current watering schedule\n"
            response += "• Water when moisture drops below 30%\n"

        return response

    # Default response with personalization
    else:
        response = "🤖 **AgriGenius AI Assistant**\n\n"

        if user_crops or user_location:
            response += "I remember you"
            if user_crops:
                response += f" grow {', '.join(user_crops)}"
            if user_location:
                response += f" in {user_location}"
            response += ". "

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



# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

# Notes:
# - home.html, articles.html, documentation.html, login.html, signup.html templates are required in the templates/ folder.
# - Replace 'your_secret_key_here' and 'https://your-n8n-chatbot-url.com' with your actual values.
# - Use Bootstrap in your templates for styling.
# - Comments are provided above each section for clarity.
