from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)

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
    return render_template('home.html')

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
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/dashboard')
@login_required  # This protects the route. No cookie = No access.
def dashboard():
    return render_template('dashboard.html', name=current_user.id)

@app.route('/logout')
@login_required
def logout():
    logout_user() # Deletes the cookie session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)