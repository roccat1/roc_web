"""
API endpoints for the mobile app.
All endpoints use JSON auth (email + password in request body).
"""

from flask import Blueprint, request, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json

from models import get_db_connection

api_bp = Blueprint('api', __name__, url_prefix='/api')


def _authenticate(data):
    """Authenticate a user from JSON data. Returns (user_tuple, error_response)."""
    if not data or 'email' not in data or 'password' not in data:
        return None, ({'error': 'email and password are required'}, 400)

    email = data['email']
    password = data['password']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, password_hash, config FROM users WHERE email = %s",
            (email,)
        )
        user_data = cursor.fetchone()
        conn.close()

        if not user_data or not check_password_hash(user_data[3], password):
            return None, ({'error': 'Invalid email or password'}, 401)

        return user_data, None

    except Exception as e:
        current_app.logger.error(f"Auth error: {e}")
        return None, ({'error': 'Authentication failed'}, 500)


# ── Login ──────────────────────────────────────────────────────────────────────

@api_bp.route('/login', methods=['POST'])
def api_login():
    """Validate credentials and return user info."""
    data = request.get_json()
    user_data, err = _authenticate(data)
    if err:
        return err

    config = {}
    if user_data[4]:
        config = json.loads(user_data[4]) if isinstance(user_data[4], str) else user_data[4]

    return {
        'status': 'success',
        'user': {
            'id': user_data[0],
            'username': user_data[1],
            'email': user_data[2],
            'config': config,
        }
    }, 200


# ── Register ───────────────────────────────────────────────────────────────────

@api_bp.route('/register', methods=['POST'])
def api_register():
    """Create a new user account."""
    data = request.get_json()
    if not data:
        return {'error': 'JSON body required'}, 400

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    privacy = data.get('privacy', 'private')

    if not username or not email or not password:
        return {'error': 'username, email and password are required'}, 400

    if password != confirm_password:
        return {'error': 'Passwords do not match'}, 400

    if len(password) < 6:
        return {'error': 'Password must be at least 6 characters'}, 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            conn.close()
            return {'error': 'Email already exists'}, 409

        password_hash = generate_password_hash(password)
        config_json = json.dumps({"public": privacy == "public"})
        created_at = datetime.now()

        cursor.execute(
            "INSERT INTO users (username, email, password_hash, config, created_at) VALUES (%s, %s, %s, %s, %s)",
            (username, email, password_hash, config_json, created_at)
        )
        conn.commit()
        conn.close()

        return {'status': 'success', 'message': 'Account created successfully'}, 201

    except Exception as e:
        current_app.logger.error(f"Register error: {e}")
        return {'error': str(e)}, 500


# ── Home / Dashboard Data ─────────────────────────────────────────────────────

@api_bp.route('/home', methods=['POST'])
def api_home():
    """
    Return dashboard data (logs, users list, stats).
    Optionally pass 'view_user_id' to see another public user's data.
    """
    data = request.get_json()
    user_data, err = _authenticate(data)
    if err:
        return err

    my_id = user_data[0]
    view_user_id = data.get('view_user_id', my_id)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch public users
        cursor.execute(
            "SELECT id, username, email FROM users WHERE (config->>'public')::boolean = true ORDER BY id ASC"
        )
        public_users = [{'id': r[0], 'username': r[1]} for r in cursor.fetchall()]

        # If the authenticated user is private, ensure they appear in the list
        cursor.execute("SELECT config->>'public' FROM users WHERE id = %s", (my_id,))
        priv = cursor.fetchone()
        my_is_public = priv and priv[0] == 'true'
        if not my_is_public:
            already = any(u['id'] == my_id for u in public_users)
            if not already:
                public_users.append({'id': my_id, 'username': user_data[1]})

        # Fetch logs for the viewed user
        cursor.execute(
            "SELECT id, user_id, log_time FROM poop WHERE user_id = %s ORDER BY log_time DESC",
            (view_user_id,)
        )
        raw_logs = cursor.fetchall()
        logs = []
        last_entry = None
        for row in raw_logs:
            dt_str = row[2].strftime('%Y-%m-%dT%H:%M:%S') if row[2] else None
            logs.append({'id': row[0], 'user_id': row[1], 'log_time': dt_str})
            if last_entry is None and row[2]:
                today = datetime.now().date()
                entry_date = row[2].date()
                time_str = row[2].strftime('%H:%M')
                if entry_date == today:
                    last_entry = f"Avui: {time_str}"
                elif entry_date == today - timedelta(days=1):
                    last_entry = f"Ahir: {time_str}"
                else:
                    days_ago = (today - entry_date).days
                    last_entry = f"Fa {days_ago} dies a les {time_str}"

        conn.close()

        return {
            'status': 'success',
            'users': public_users,
            'selected_user_id': view_user_id,
            'logs': logs,
            'last_entry': last_entry,
        }, 200

    except Exception as e:
        current_app.logger.error(f"Home API error: {e}")
        return {'error': str(e)}, 500


# ── User Privacy ───────────────────────────────────────────────────────────────

@api_bp.route('/user/privacy', methods=['POST'])
def api_get_privacy():
    """Return the user's current privacy setting."""
    data = request.get_json()
    user_data, err = _authenticate(data)
    if err:
        return err

    config = {}
    if user_data[4]:
        config = json.loads(user_data[4]) if isinstance(user_data[4], str) else user_data[4]

    return {
        'status': 'success',
        'privacy': 'public' if config.get('public') else 'private',
    }, 200


@api_bp.route('/user/privacy/update', methods=['POST'])
def api_update_privacy():
    """Update the user's privacy setting."""
    data = request.get_json()
    user_data, err = _authenticate(data)
    if err:
        return err

    new_privacy = data.get('privacy')
    if new_privacy not in ('public', 'private'):
        return {'error': 'privacy must be "public" or "private"'}, 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "UPDATE users SET config = jsonb_set(config::jsonb, '{public}', %s::jsonb) WHERE id = %s"
        cursor.execute(sql, ('true' if new_privacy == 'public' else 'false', user_data[0]))
        conn.commit()
        conn.close()

        return {'status': 'success', 'privacy': new_privacy}, 200

    except Exception as e:
        current_app.logger.error(f"Privacy update error: {e}")
        return {'error': str(e)}, 500


# ── Delete Poop Entry ─────────────────────────────────────────────────────────

@api_bp.route('/poop/delete', methods=['POST'])
def api_poop_delete():
    """Delete a poop entry by ID (only owner can delete)."""
    data = request.get_json()
    user_data, err = _authenticate(data)
    if err:
        return err

    entry_id = data.get('entry_id')
    if not entry_id:
        return {'error': 'entry_id is required'}, 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM poop WHERE id = %s AND user_id = %s", (entry_id, user_data[0]))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted == 0:
            return {'error': 'Entry not found or not owned by user'}, 404

        return {'status': 'success', 'message': 'Entry deleted'}, 200

    except Exception as e:
        current_app.logger.error(f"Delete error: {e}")
        return {'error': str(e)}, 500
