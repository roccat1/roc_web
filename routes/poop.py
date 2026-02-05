from flask import Blueprint, render_template, request, flash, current_app
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash
from datetime import datetime

from models import get_db_connection

poop_bp = Blueprint('poop', __name__)


@poop_bp.route('/private/poop', methods=['GET', 'POST'])
@login_required
def poop():
    if request.method == 'POST':
        user_date = request.form['user_time']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            sql = "INSERT INTO poop (user_id, log_time) VALUES (%s, %s)"
            cursor.execute(sql, (current_user.id, user_date))
            conn.commit()
            conn.close()

            formatted_date = datetime.strptime(user_date, '%Y-%m-%dT%H:%M').strftime('%d/%m/%Y %H:%M')
            flash(f'<strong>Èxit!</strong> Registre afegit correctament: <em>{formatted_date}</em>', 'success')

            return "OK", 200

        except Exception as e:
            flash(f"<strong>Error!</strong> Hi ha hagut un problema amb la base de dades: <em>{e}</em>", 'error')
            return str(e), 500

    return render_template('poop.html', user=current_user)


@poop_bp.route('/api/poop', methods=['POST'])
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
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, email, password_hash FROM users WHERE email = %s",
                (email,)
            )
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
            current_app.logger.error(f"API poop authentication error: {e}")
            return {'error': 'Authentication failed'}, 401

    except Exception as e:
        current_app.logger.error(f"API poop error: {e}")
        return {'error': str(e)}, 500


@poop_bp.route('/api/poop/metrics', methods=['GET'])
def api_poop_metrics():
    """API endpoint to get metrics AND the exact last entry time"""
    try:
        data = request.get_json()

        if not data or 'email' not in data or 'password' not in data:
            return {'error': 'email and password are required'}, 400

        email = data['email']
        password = data['password']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 1. Login
            cursor.execute(
                "SELECT id, username, email, password_hash FROM users WHERE email = %s",
                (email,)
            )
            user_data = cursor.fetchone()

            if not user_data or not check_password_hash(user_data[3], password):
                conn.close()
                return {'error': 'Invalid email or password'}, 401

            user_id = user_data[0]

            # 2. Metrics
            sql_metrics = """
                SELECT DATE(log_time) as date, COUNT(*) as count
                FROM poop
                WHERE user_id = %s AND log_time >= NOW() - INTERVAL '7 days'
                GROUP BY DATE(log_time)
                ORDER BY date DESC
            """
            cursor.execute(sql_metrics, (user_id,))
            metrics_data = cursor.fetchall()

            # 3. Get exact time of last entry
            sql_last = "SELECT log_time FROM poop WHERE user_id = %s ORDER BY log_time DESC LIMIT 1"
            cursor.execute(sql_last, (user_id,))
            last_row = cursor.fetchone()

            last_entry_str = "Sin datos"
            if last_row:
                last_entry_str = str(last_row[0])

            conn.close()

            # Totals
            total_entries = sum(row[1] for row in metrics_data)
            daily_metrics = [{'date': str(row[0]), 'count': row[1]} for row in metrics_data]

            return {
                'status': 'success',
                'user_id': user_id,
                'username': user_data[1],
                'total_last_7_days': total_entries,
                'average_per_day': round(total_entries / 7, 2),
                'daily_breakdown': daily_metrics,
                'last_entry': last_entry_str
            }, 200

        except Exception as e:
            current_app.logger.error(f"Authentication error: {e}")
            return {'error': 'Authentication failed'}, 401

    except Exception as e:
        current_app.logger.error(f"API error: {e}")
        return {'error': str(e)}, 500
