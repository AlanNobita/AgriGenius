# AgriGenius Startup Guide

## Prerequisites
- Python 3.8 or higher
- pip package manager

## Quick Start

### 1. Setup Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Database
```bash
# Initialize database and create tables
python setup_db.py
```

### 4. Start the Server
```bash
# Start the Flask server
python start_server.py
```

### 5. Access the Application
Open your browser and navigate to:
- http://localhost:5000
- http://127.0.0.1:5000
- http://192.168.10.65:5000 (on your local network)

## Available Routes

### Main Pages
- `/` - Home page
- `/articles` - Public articles
- `/documentation` - Documentation (restricted posting)
- `/marketplace` - Agricultural marketplace
- `/chat` - AI chatbot
- `/profile` - User profile
- `/dashboard` - Public dashboard

### Authentication
- `/login` - User login
- `/signup` - User registration
- `/logout` - User logout

### Article Management
- `/post_article` - Create new article
- `/my-posts` - User's articles
- `/view_article/<id>` - View specific article
- `/edit_article/<id>` - Edit article
- `/delete_article/<id>` - Delete article

### Documentation Management
- `/view_doc/<id>` - View specific documentation
- `/edit_doc/<id>` - Edit documentation
- `/delete_doc/<id>` - Delete documentation

### Admin Functions
- `/admin/verify_articles` - Verify articles
- `/admin/verify_docs` - Verify documentation
- `/admin/approve_article/<id>` - Approve article
- `/admin/approve_doc/<id>` - Approve documentation
- `/admin/reject_article/<id>` - Reject article
- `/admin/reject_doc/<id>` - Reject documentation

### Product Management
- `/add_product` - Add new product
- `/product/<id>` - View product details
- `/contact_seller/<id>` - Contact seller

### API Endpoints
- `/api/chat` - AI chat endpoint
- `/api/conversations` - Get conversation history
- `/api/conversations/<id>/messages` - Get conversation messages
- `/api/ai-modes` - Get AI modes
- `/api/current-ai-mode` - Get current AI mode
- `/api/like_article/<id>` - Like/unlike article
- `/api/like_doc/<id>` - Like/unlike documentation
- `/api/save_article/<id>` - Save/unsave article

## Environment Variables

The application uses the following environment variables (set in `.env` file):

```env
SECRET_KEY=a_very_secret_key
OPENROUTER_API_KEY=your-openrouter-api-key-here
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_EMBED_MODEL=nomic-embed-text:latest
OLLAMA_MODEL=tinydolphin
```

## Features

### AI Chatbot
- Multiple AI interaction modes (Learn, Read, Analyze, Assist, Creative)
- Integration with OpenRouter API for AI responses
- Local fallback when API is unavailable
- Conversation history and memory
- Sensor data integration

### User Management
- User registration and authentication
- Role-based access control (Admin, Doc Poster, Regular User)
- User profiles and preferences

### Content Management
- Public articles with verification system
- Restricted documentation posting
- Like and comment system
- File upload support (images, videos, audio)

### Marketplace
- Product listing and management
- Category-based filtering
- Search functionality
- Contact seller feature

### Database
- SQLite database (easily configurable for PostgreSQL/MySQL)
- SQLAlchemy ORM
- Automatic table creation
- Data initialization scripts

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you've activated the virtual environment and installed all dependencies
2. **Database Errors**: Run `python setup_db.py` to recreate the database
3. **Port Already in Use**: Change the port in `start_server.py` or kill the existing process
4. **Template Not Found**: Ensure all required HTML templates are in the `templates/` directory

### Logs
- Application logs are stored in `logs/agrigenius.log`
- Database operations are logged for debugging

## Development

### Running in Development Mode
```bash
# With debug mode and auto-reload
python app.py
```

### Adding New Routes
1. Define the route in `app.py`
2. Create the corresponding HTML template in `templates/`
3. Add navigation links in `templates/navbar.html`

### Database Changes
1. Modify the model classes in `app.py`
2. Run `python setup_db.py` to update the database schema

## Security Notes
- Use a strong SECRET_KEY in production
- Set proper file permissions for uploads
- Use HTTPS in production
- Regularly update dependencies
- Implement rate limiting for API endpoints