from flask_login import UserMixin
import mysql.connector
from config import db_config


class User(UserMixin):
    def __init__(self, id, email, username=None, config=None):
        self.id = id
        self.email = email
        self.username = username
        self.config = config


def load_user_by_id(user_id):
    """Load a user from the database by ID."""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, password_hash, config, created_at FROM users WHERE id = %s",
            (user_id,)
        )
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            return User(user_data[0], user_data[2], user_data[1], user_data[4])
    except Exception as e:
        print(f"Error loading user: {e}")

    return None


def get_user_by_email(email):
    """Load a user from the database by email."""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, password_hash, config, created_at FROM users WHERE email = %s",
            (email,)
        )
        user_data = cursor.fetchone()
        conn.close()
        return user_data
    except Exception as e:
        print(f"Error loading user by email: {e}")
        return None
