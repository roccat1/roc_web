import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
db_config = {
    'user': os.environ['MYSQL_ADDON_USER'],
    'password': os.environ['MYSQL_ADDON_PASSWORD'],
    'host': os.environ['MYSQL_ADDON_HOST'],
    'database': os.environ['MYSQL_ADDON_DATABASE'],
    'port': os.environ['MYSQL_ADDON_PORT']
}

# Flask configuration
SECRET_KEY = os.environ['SECRET_KEY']
