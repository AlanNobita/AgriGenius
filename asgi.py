from asgiref.wsgi import WsgiToAsgi

# Import the Flask WSGI app
try:
    from app import app as flask_app
except Exception:
    # If app import fails, raise clearer error when uvicorn starts
    raise

# Wrap WSGI Flask app into ASGI app
asgi_app = WsgiToAsgi(flask_app)

if __name__ == '__main__':
    # quick local sanity check when executed directly
    import uvicorn
    uvicorn.run('asgi:asgi_app', host='127.0.0.1', port=8000, reload=True)
