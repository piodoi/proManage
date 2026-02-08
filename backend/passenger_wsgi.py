"""
Phusion Passenger WSGI entry point for FastAPI application.

This file is required by Passenger to launch the application.
Passenger looks for 'application' object in this file.
"""
import os
import sys

# Add the backend directory to the Python path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, '.env'))

# Import the FastAPI app
from app.main import app as fastapi_app

# For Passenger with ASGI support (Passenger 6.0.0+)
# Passenger will detect this is an ASGI app and handle it appropriately
application = fastapi_app

# Alternative: If your Passenger version requires WSGI,
# uncomment the following to use a2wsgi adapter:
# from a2wsgi import ASGIMiddleware
# application = ASGIMiddleware(fastapi_app)
