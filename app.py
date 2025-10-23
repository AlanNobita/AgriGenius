
# ...existing code...
import os
from flask import Flask, render_template, redirect, url_for, request, jsonify, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import random
import logging
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

# Chatbot route
@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/get_response', methods=['POST'])
@csrf.exempt  # Exempt chatbot endpoint from CSRF protection
def get_response():
    try:
        user_input = request.json.get("message", "").strip()
        if not user_input:
            return jsonify({"error": "No message provided"}), 400

        # Get current sensor data
        sensor_data = get_sensor_data()

        # Simple chatbot logic based on keywords
        response = generate_chatbot_response(user_input, sensor_data)

        return jsonify({
            "response": response,
            "sensor_data": sensor_data,
            "timestamp": sensor_data.get('timestamp')
        })

    except Exception as e:
        app.logger.error(f'Chatbot error: {str(e)}')
        return jsonify({"error": "Sorry, I'm having trouble right now. Please try again later."}), 500

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
