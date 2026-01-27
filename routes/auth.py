from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import mysql.connector

from config import db_config
from models import User, get_user_by_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user_data = get_user_by_email(email)

            if user_data and check_password_hash(user_data[3], password):
                user = User(user_data[0], user_data[2], user_data[1], user_data[4])
                login_user(user, remember=True)
                flash('Has iniciat sessió correctament!', 'success')
                return redirect(url_for('poop.poop', _external=True))
            else:
                flash('Correu electrònic o contrasenya incorrectes', 'error')
        except Exception as e:
            current_app.logger.error(f"Login error: {e}")
            flash(f"Error d'inici de sessió: {e}", 'error')

    if current_user.is_authenticated:
        return redirect(url_for('poop.poop'))

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
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
            password_hash = generate_password_hash(password)
            created_at = datetime.now()
            config_json = json.dumps({"public": privacy == "public"})
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, config, created_at) VALUES (%s, %s, %s, %s, %s)",
                (username, email, password_hash, config_json, created_at)
            )
            conn.commit()
            conn.close()

            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            current_app.logger.error(f"Registration error: {e}")
            flash(f"Registration error: {e}", 'error')
            return render_template('register.html')

    if current_user.is_authenticated:
        return redirect(url_for('poop.poop'))

    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
