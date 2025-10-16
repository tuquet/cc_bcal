from flask import Flask
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

    # Register API blueprints
    from .api.v1.routes import api_v1 as api_v1_blueprint
    app.register_blueprint(api_v1_blueprint, url_prefix='/api/v1')

    return app
