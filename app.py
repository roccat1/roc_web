from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

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

app = Flask(__name__)
application = app 

# SECURITY CRITICAL: This key signs the cookie. 
# In production, make this a long random string and hide it in environment variables.
app.secret_key = 'caca culo pedo pis 58426'

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Where to send users who aren't logged in

# --- MOCK DATABASE ---
# In a real app, you would use SQLite, PostgreSQL, etc.
# Here we verify against a simple dictionary.
users_db = ["roc"]

# User Class (Standard requirement for Flask-Login)
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# This function helps Flask-Login load a user from the Cookie (session)
@login_manager.user_loader
def load_user(password):
    if password in users_db:
        return User(password)
    return None

# --- ROUTES ---

@app.route('/')
def home():
    # log
    app.logger.info('Home page accessed')
    # Get the user's IP address
    user_ip = request.remote_addr
    app.logger.info(f'User IP: {user_ip}')
    
    all_logs = []

    try:
        # 1. Connect to database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # 2. SELECT data (Ordered by latest first)
        # We assume your table has columns like 'id' and 'log_time'
        sql = "SELECT * FROM poop ORDER BY log_time DESC"
        cursor.execute(sql)

        # 3. Fetch all results
        all_logs = cursor.fetchall()

        # 4. Clean up
        conn.close()

    except Exception as e:
        app.logger.error(f"Database error on home: {e}")
        # Optional: Flash an error if you want the user to know the DB failed
        flash(f"AVISAM PORFA Could not load data: {e}", "error")
    
    return render_template('home.html', logs=all_logs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']

        # verify username and password
        if password in users_db:
            user = User(password)

            # This creates the Secure Cookie containing the user ID
            login_user(user, remember=True) 
            
            flash('Logged in successfully!', 'success')
            return redirect(url_for('poop'))
        else:
            flash('Invalid password', 'error')
    
    if current_user.is_authenticated:
        return redirect(url_for('poop'))

    return render_template('login.html')

@app.route('/poop', methods=['GET', 'POST'])
@login_required  # This protects the route. No cookie = No access.
def poop():
    if request.method == 'POST':
        user_date = request.form['user_time']

        try:
            # 1. Connect using the config dictionary
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            # 2. INSERT (Note: MySQL uses %s, not ?)
            sql = "INSERT INTO poop (log_time) VALUES (%s)"
            cursor.execute(sql, (user_date,))
            
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