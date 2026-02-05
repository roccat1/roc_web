import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
db_config = {
    'host': os.getenv('DATABASE_HOST'),
    'user': os.getenv('DATABASE_USER'),
    'password': os.getenv('DATABASE_PASSWORD'),
    'database': os.getenv('DATABASE_NAME'),
    'sslmode': 'require'
}

# Flask configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-key')

# Validate required config at startup
required_vars = ['DATABASE_HOST', 'DATABASE_USER', 'DATABASE_PASSWORD', 'DATABASE_NAME']
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
