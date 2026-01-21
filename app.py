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
    # log
    app.logger.info('Home page accessed')
    # Get the user's IP address
    user_ip = request.remote_addr
    app.logger.info(f'User IP: {user_ip}')
    
    selected_user_id = request.args.get('user_id', 1, type=int)
    formatted_logs = []  # We will store the clean data here
    users = []

    try:
        # 1. Connect to database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Fetch all users for the selector (only public users)
        cursor.execute("SELECT id, username, email FROM users WHERE JSON_EXTRACT(config, '$.public') = true ORDER BY username")
        users = cursor.fetchall()

        # 2. SELECT data for selected user
        sql = "SELECT id, user_id, log_time FROM poop WHERE user_id = %s ORDER BY log_time DESC"
        cursor.execute(sql, (selected_user_id,))
        raw_logs = cursor.fetchall()

        # 3. CLEAN DATA (The Fix)
        # We loop through the results and force the date to be a simple string
        for row in raw_logs:
            log_id = row[0]
            u_id = row[1]
            dt_obj = row[2] # This is a python datetime object
            
            clean_date = None
            if dt_obj:
                # Formats as "2026-01-21T21:52:00" (ISO 8601 without 'Z' or timezone)
                clean_date = dt_obj.strftime('%Y-%m-%dT%H:%M:%S')
            
            formatted_logs.append([log_id, u_id, clean_date])

        # 4. Clean up
        conn.close()

    except Exception as e:
        app.logger.error(f"Database error on home: {e}")
        flash(f"Could not load data: {e}", "error")
    
    # Pass 'formatted_logs' instead of the raw cursor result
    return render_template('home.html', logs=formatted_logs, users=users, selected_user_id=selected_user_id)

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
                flash('Logged in successfully!', 'success')
                return redirect(url_for('poop'))
            else:
                flash('Invalid email or password', 'error')
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            flash(f"Login error: {e}", 'error')
    
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
            flash(f'Logged to MySQL successfully: {user_date}', 'success')
            
        except Exception as e:
            flash(f"Database error: {e}", 'error')
            
    return render_template('poop.html')

@app.route('/logout')
@login_required
def logout():
    logout_user() # Deletes the cookie session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)