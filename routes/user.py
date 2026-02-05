from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from models import get_db_connection

user_bp = Blueprint('user', __name__)


@user_bp.route('/private/user', methods=['GET', 'POST'])
@login_required
def user():
    if request.method == 'POST':
        new_privacy = request.form.get('privacy')

        if new_privacy not in ['public', 'private']:
            flash('Configuració de privacitat no vàlida.', 'error')
            return redirect(url_for('user.user'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Update the user's privacy setting
            sql = "UPDATE users SET config = jsonb_set(config::jsonb, '{public}', %s::jsonb) WHERE id = %s"
            cursor.execute(sql, ('true' if new_privacy == 'public' else 'false', current_user.id))
            conn.commit()
            conn.close()

            flash('La configuració de privacitat s\'ha actualitzat correctament.', 'success')
        except Exception as e:
            current_app.logger.error(f"Error updating privacy: {e}")
            flash('Hi ha hagut un problema actualitzant la configuració de privacitat.', 'error')

        return redirect(url_for('user.user'))

    # Fetch the current privacy setting
    user_privacy = 'private'
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT config->>'public' FROM users WHERE id = %s"
        cursor.execute(sql, (current_user.id,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0] == 'true':
            user_privacy = 'public'
    except Exception as e:
        current_app.logger.error(f"Error fetching privacy setting: {e}")

    return render_template('user.html', user_privacy=user_privacy)
