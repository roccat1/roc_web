import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
db_config = {
    'host': os.environ['DATABASE_HOST'],
    'user': os.environ['DATABASE_USER'],
    'password': os.environ['DATABASE_PASSWORD'],
    'database': os.environ['DATABASE_NAME'],
    'sslmode': 'require'
}

# Flask configuration
SECRET_KEY = os.environ['SECRET_KEY']
