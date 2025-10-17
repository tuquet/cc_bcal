from flask import Flask
from flask_cors import CORS
from config import config
from .extensions import db, cache
from flask_migrate import Migrate
from flasgger import Flasgger
from .logging_config import configure_logging
import os

def create_app(config_name=None):
    """
    Application factory function.
    """
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Configure logging
    configure_logging(
        log_level=app.config.get("LOG_LEVEL", "INFO"),
        is_debug=app.config.get("DEBUG", False)
    )

    # Initialize extensions
    db.init_app(app)
    cache.init_app(app)
    Migrate(app, db)
    Flasgger(app)  # Initialize Flasgger

    with app.app_context():
        # Load settings from the database after the app and db are initialized
        # but skip loading when running tests to avoid querying tables
        # before the test fixtures create them.
        if not app.config.get("TESTING", False):
            from .settings import settings
            settings.load()

        # Register the master v1 API blueprint
        from .api.v1 import api_v1
        app.register_blueprint(api_v1, url_prefix='/api/v1')

    # Configure CORS for API endpoints and set secure Referrer-Policy
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    @app.after_request
    def set_security_headers(response):
        # Set Referrer-Policy as requested
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    return app
