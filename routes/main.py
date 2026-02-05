from flask import Blueprint, render_template, request, flash, current_app
from flask_login import current_user
from datetime import datetime, timedelta

from models import get_db_connection

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    current_app.logger.info('Home page accessed')
    user_ip = request.remote_addr
    current_app.logger.info(f'User IP: {user_ip}')

    # Check if the user is logged in and prioritize their ID unless a new user_id is explicitly provided
    selected_user_id = request.args.get('user_id', type=int)
    if not selected_user_id and current_user.is_authenticated:
        selected_user_id = current_user.id
    elif not selected_user_id:
        selected_user_id = 1

    formatted_logs = []
    users = []
    last_entry_date = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all public accounts
        cursor.execute(
            "SELECT id, username, email FROM users WHERE (config->>'public')::boolean = true ORDER BY id ASC"
        )
        users = cursor.fetchall()

        # If user is logged in and their account is private, add their own account to the list
        if current_user.is_authenticated:
            cursor.execute(
                "SELECT config->>'public' FROM users WHERE id = %s",
                (current_user.id,)
            )
            privacy_result = cursor.fetchone()

            # If the user's account is private, add it to the users list
            if privacy_result and privacy_result[0] == 'false':
                cursor.execute(
                    "SELECT id, username, email FROM users WHERE id = %s",
                    (current_user.id,)
                )
                user_data = cursor.fetchone()
                if user_data and user_data not in users:
                    users.append(user_data)

        sql = "SELECT id, user_id, log_time FROM poop WHERE user_id = %s ORDER BY log_time DESC"
        cursor.execute(sql, (selected_user_id,))
        raw_logs = cursor.fetchall()

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
                elif entry_date == today - timedelta(days=1):
                    last_entry_date = f"Ahir: {time_str}"
                else:
                    days_ago = (today - entry_date).days
                    last_entry_date = f"Fa {days_ago} dies a les {time_str}"

        conn.close()

    except Exception as e:
        current_app.logger.error(f"Database error on home: {e}")
        flash(f"Could not load data: {e}", "error")

    user_is_logged_in = current_user.is_authenticated

    return render_template(
        'home.html',
        logs=formatted_logs,
        users=users,
        selected_user_id=selected_user_id,
        user_is_logged_in=user_is_logged_in,
        last_entry_date=last_entry_date
    )
