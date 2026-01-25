from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

import mysql.connector, os

from dotenv import load_dotenv

load_dotenv()

db_config = {
    'user': os.environ['MYSQL_ADDON_USER'],
    'password': os.environ['MYSQL_ADDON_PASSWORD'],
    'host': os.environ['MYSQL_ADDON_HOST'],
    'database': os.environ['MYSQL_ADDON_DATABASE'],
    'port': os.environ['MYSQL_ADDON_PORT']
}

app = Flask(__name__, static_folder='static', static_url_path='/static')
application = app 

# SECURITY CRITICAL: This key signs the cookie. 
# In production, make this a long random string and hide it in environment variables.
app.secret_key = os.environ['SECRET_KEY']

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Where to send users who aren't logged in

# User Class (Standard requirement for Flask-Login)
class User(UserMixin):
    def __init__(self, id, email, username=None, config=None):
        self.id = id
        self.email = email
        self.username = username
        self.config = config

# This function helps Flask-Login load a user from the Cookie (session)
@login_manager.user_loader
def load_user(user_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, password_hash, config, created_at FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return User(user_data[0], user_data[2], user_data[1], user_data[4])
    except Exception as e:
        app.logger.error(f"Error loading user: {e}")
    
    return None

# --- ROUTES ---

@app.route('/')
def home():
    app.logger.info('Home page accessed')
    user_ip = request.remote_addr
    app.logger.info(f'User IP: {user_ip}')

    # Check if the user is logged in and prioritize their ID unless a new user_id is explicitly provided
    selected_user_id = request.args.get('user_id', type=int)
    if not selected_user_id and current_user.is_authenticated:
        selected_user_id = current_user.id
    elif not selected_user_id:
        selected_user_id = 1

    formatted_logs = []
    users = []

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Fetch all public accounts
        cursor.execute("SELECT id, username, email FROM users WHERE JSON_EXTRACT(config, '$.public') = true ORDER BY id ASC")
        users = cursor.fetchall()
        
        # If user is logged in and their account is private, add their own account to the list
        if current_user.is_authenticated:
            cursor.execute("SELECT JSON_EXTRACT(config, '$.public') FROM users WHERE id = %s", (current_user.id,))
            privacy_result = cursor.fetchone()
            
            # If the user's account is private, add it to the users list
            if privacy_result and privacy_result[0] == 'false':
                cursor.execute("SELECT id, username, email FROM users WHERE id = %s", (current_user.id,))
                user_data = cursor.fetchone()
                if user_data and user_data not in users:
                    users.append(user_data)

        sql = "SELECT id, user_id, log_time FROM poop WHERE user_id = %s ORDER BY log_time DESC"
        cursor.execute(sql, (selected_user_id,))
        raw_logs = cursor.fetchall()

        last_entry_date = None
        for row in raw_logs:
            log_id = row[0]
            u_id = row[1]
            dt_obj = row[2]

            clean_date = None
            if dt_obj:
                clean_date = dt_obj.strftime('%Y-%m-%dT%H:%M:%S')

            formatted_logs.append([log_id, u_id, clean_date])
            
            # Set last_entry_date on first iteration (most recent)
            if last_entry_date is None and dt_obj:
                # Format date in a visual way (Today, Yesterday, etc.)
                today = datetime.now().date()
                entry_date = dt_obj.date()
                time_str = dt_obj.strftime('%H:%M')
                
                if entry_date == today:
                    last_entry_date = f"Avui: {time_str}"
                elif entry_date == today - __import__('datetime').timedelta(days=1):
                    last_entry_date = f"Ahir: {time_str}"
                else:
                    days_ago = (today - entry_date).days
                    last_entry_date = f"Fa {days_ago} dies a les {time_str}"

        conn.close()

    except Exception as e:
        app.logger.error(f"Database error on home: {e}")
        flash(f"Could not load data: {e}", "error")

    user_is_logged_in = current_user.is_authenticated

    return render_template('home.html', logs=formatted_logs, users=users, selected_user_id=selected_user_id, user_is_logged_in=user_is_logged_in, last_entry_date=last_entry_date)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, password_hash, config, created_at FROM users WHERE email = %s", (email,))
            user_data = cursor.fetchone()
            conn.close()

            if user_data and check_password_hash(user_data[3], password):
                user = User(user_data[0], user_data[2], user_data[1], user_data[4])
                login_user(user, remember=True)
                flash('Has iniciat sessió correctament!', 'success')
                return redirect(url_for('poop', _external=True))
            else:
                flash('Correu electrònic o contrasenya incorrectes', 'error')
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            flash(f"Error d'inici de sessió: {e}", 'error')
    
    if current_user.is_authenticated:
        return redirect(url_for('poop'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        privacy = request.form.get('privacy', 'private')

        if not username or not email or not password:
            flash('Username, email and password are required', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('register.html')

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                conn.close()
                flash('Email already exists', 'error')
                return render_template('register.html')

            # Create new user
            import json
            password_hash = generate_password_hash(password)
            created_at = datetime.now()
            config_json = json.dumps({"public": privacy == "public"})
            cursor.execute("INSERT INTO users (username, email, password_hash, config, created_at) VALUES (%s, %s, %s, %s, %s)", (username, email, password_hash, config_json, created_at))
            conn.commit()
            conn.close()

            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            app.logger.error(f"Registration error: {e}")
            flash(f"Registration error: {e}", 'error')
            return render_template('register.html')
    
    if current_user.is_authenticated:
        return redirect(url_for('poop'))

    return render_template('register.html')

@app.route('/private/poop', methods=['GET', 'POST'])
@login_required  # This protects the route. No cookie = No access.
def poop():
    if request.method == 'POST':
        user_date = request.form['user_time']

        try:
            # 1. Connect using the config dictionary
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            # 2. INSERT (Note: MySQL uses %s, not ?)
            sql = "INSERT INTO poop (user_id, log_time) VALUES (%s, %s)"
            cursor.execute(sql, (current_user.id, user_date))
            conn.commit()
            conn.close()

            # Format the datetime for a more user-friendly display
            formatted_date = datetime.strptime(user_date, '%Y-%m-%dT%H:%M').strftime('%d/%m/%Y %H:%M')

            flash(f'<strong>Èxit!</strong> Registre afegit correctament: <em>{formatted_date}</em>', 'success')
            
            return "OK", 200  # Return a simple response for AJAX
            
        except Exception as e:
            flash(f"<strong>Error!</strong> Hi ha hagut un problema amb la base de dades: <em>{e}</em>", 'error')
            
            return str(e), 500
            
    return render_template('poop.html')

@app.route('/api/poop', methods=['POST'])
def api_poop():
    """API endpoint to create a poop entry with credentials in JSON data"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'email' not in data or 'password' not in data or 'user_time' not in data:
            return {'error': 'email, password, and user_time are required'}, 400
        
        email = data['email']
        password = data['password']
        user_date = data['user_time']
        
        # Validate date format
        try:
            datetime.strptime(user_date, '%Y-%m-%dT%H:%M')
        except ValueError:
            return {'error': 'Invalid date format. Use YYYY-MM-DDTHH:MM'}, 400
        
        # Authenticate user
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, password_hash FROM users WHERE email = %s", (email,))
            user_data = cursor.fetchone()
            
            if not user_data or not check_password_hash(user_data[3], password):
                conn.close()
                return {'error': 'Invalid email or password'}, 401
            
            user_id = user_data[0]
            
            # Insert poop entry
            sql = "INSERT INTO poop (user_id, log_time) VALUES (%s, %s)"
            cursor.execute(sql, (user_id, user_date))
            conn.commit()
            conn.close()
            
            formatted_date = datetime.strptime(user_date, '%Y-%m-%dT%H:%M').strftime('%d/%m/%Y %H:%M')
            
            return {
                'status': 'success',
                'message': f'Registre afegit correctament: {formatted_date}',
                'timestamp': formatted_date,
                'user_id': user_id
            }, 201
            
        except Exception as e:
            app.logger.error(f"API poop authentication error: {e}")
            return {'error': 'Authentication failed'}, 401
        
    except Exception as e:
        app.logger.error(f"API poop error: {e}")
        return {'error': str(e)}, 500

@app.route('/api/poop/metrics', methods=['GET'])
def api_poop_metrics():
    """API endpoint to get metrics AND the exact last entry time"""
    try:
        data = request.get_json()
        
        if not data or 'email' not in data or 'password' not in data:
            return {'error': 'email and password are required'}, 400
        
        email = data['email']
        password = data['password']
        
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            # 1. Login
            cursor.execute("SELECT id, username, email, password_hash FROM users WHERE email = %s", (email,))
            user_data = cursor.fetchone()
            
            if not user_data or not check_password_hash(user_data[3], password):
                conn.close()
                return {'error': 'Invalid email or password'}, 401
            
            user_id = user_data[0]
            
            # 2. Métricas (Tu código original para la gráfica)
            sql_metrics = """
                SELECT DATE(log_time) as date, COUNT(*) as count
                FROM poop
                WHERE user_id = %s AND log_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY DATE(log_time)
                ORDER BY date DESC
            """
            cursor.execute(sql_metrics, (user_id,))
            metrics_data = cursor.fetchall()

            # 3. --- NUEVO: OBTENER HORA EXACTA DE LA ÚLTIMA ENTRADA ---
            sql_last = "SELECT log_time FROM poop WHERE user_id = %s ORDER BY log_time DESC LIMIT 1"
            cursor.execute(sql_last, (user_id,))
            last_row = cursor.fetchone()
            
            last_entry_str = "Sin datos"
            if last_row:
                # Convertimos el objeto datetime a string para JSON
                last_entry_str = str(last_row[0]) 

            conn.close()
            
            # Totales
            total_entries = sum(row[1] for row in metrics_data)
            daily_metrics = [{'date': str(row[0]), 'count': row[1]} for row in metrics_data]
            
            return {
                'status': 'success',
                'user_id': user_id,
                'username': user_data[1],
                'total_last_7_days': total_entries,
                'average_per_day': round(total_entries / 7, 2),
                'daily_breakdown': daily_metrics,
                'last_entry': last_entry_str  # <--- ESTO ES LO QUE LEERÁ EL ARDUINO
            }, 200
            
        except Exception as e:
            app.logger.error(f"Authentication error: {e}")
            return {'error': 'Authentication failed'}, 401
        
    except Exception as e:
        app.logger.error(f"API error: {e}")
        return {'error': str(e)}, 500

@app.route('/logout')
@login_required
def logout():
    logout_user() # Deletes the cookie session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/private/user', methods=['GET', 'POST'])
@login_required
def user():
    if request.method == 'POST':
        new_privacy = request.form.get('privacy')

        if new_privacy not in ['public', 'private']:
            flash('Configuració de privacitat no vàlida.', 'error')
            return redirect(url_for('user'))

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            # Update the user's privacy setting
            sql = "UPDATE users SET config = JSON_SET(config, '$.public', %s) WHERE id = %s"
            cursor.execute(sql, (new_privacy == 'public', current_user.id))
            conn.commit()
            conn.close()

            flash('La configuració de privacitat s\'ha actualitzat correctament.', 'success')
        except Exception as e:
            app.logger.error(f"Error updating privacy: {e}")
            flash('Hi ha hagut un problema actualitzant la configuració de privacitat.', 'error')

        return redirect(url_for('user'))

    # Fetch the current privacy setting
    user_privacy = 'private'
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        sql = "SELECT JSON_EXTRACT(config, '$.public') FROM users WHERE id = %s"
        cursor.execute(sql, (current_user.id,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0] == 'true':
            user_privacy = 'public'
    except Exception as e:
        app.logger.error(f"Error fetching privacy setting: {e}")

    return render_template('user.html', user_privacy=user_privacy)

if __name__ == '__main__':
    app.run(debug=True)