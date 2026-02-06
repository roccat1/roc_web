from flask import Flask
from flask_login import LoginManager

from config import SECRET_KEY
from models import load_user_by_id

# Import blueprints
from routes.auth import auth_bp
from routes.main import main_bp
from routes.poop import poop_bp
from routes.user import user_bp
from routes.api import api_bp

# Create Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')
application = app

# Configuration
app.secret_key = SECRET_KEY

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'


@login_manager.user_loader
def load_user(user_id):
    return load_user_by_id(user_id)


# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(poop_bp)
app.register_blueprint(user_bp)
app.register_blueprint(api_bp)


if __name__ == '__main__':
    app.run(debug=True)