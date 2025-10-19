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

    with app.app_context():
        # Load settings from the database after the app and db are initialized
        # but skip loading when running tests to avoid querying tables
        # before the test fixtures create them. Also allow an explicit
        # opt-out (SKIP_SETTINGS_LOAD) to make CLI operations like
        # `flask db migrate`/`flask db init` work on a fresh clone.
        skip_settings = app.config.get("TESTING", False) or os.getenv('SKIP_SETTINGS_LOAD') == '1'
        if not skip_settings:
            from .settings import settings
            try:
                settings.load()
            except Exception as e:
                # Do not abort app creation if the DB/tables aren't present yet
                # (common when the developer just cloned the repo). Log a warning
                # and continue so migration commands can run.
                import logging
                logging.getLogger(__name__).warning(
                    "settings.load() skipped due to error (DB may not be ready): %s", e
                )

        # Register the master v1 API blueprint
        from .api.v1 import api_v1
        app.register_blueprint(api_v1, url_prefix='/api/v1')

        # After blueprints are registered, inject swagger extras (e.g. pagination)
        try:
            from .api.swagger_helpers import apply_swagger_extras

            apply_swagger_extras(app)
        except Exception:
            # Non-fatal: if helpers fail, continue and Flasgger will still work
            pass

    # Initialize Flasgger after blueprints are registered and docs injected
    Flasgger(app)  # Initialize Flasgger

    # Configure CORS for API endpoints and set secure Referrer-Policy
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    @app.after_request
    def set_security_headers(response):
        # Set Referrer-Policy as requested
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    return app
