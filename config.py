import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "a-hard-to-guess-string"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CACHE_TYPE = "SimpleCache"
    SWAGGER = {"title": "Nexo API", "uiversion": 3, "specs_route": "/api/docs/"}
    # Number of background task worker threads. Can be overridden via
    # environment variable NUM_WORKERS or app config entry 'NUM_WORKERS'.
    try:
        NUM_WORKERS = int(os.environ.get('NUM_WORKERS', '4'))
    except Exception:
        NUM_WORKERS = 4
    # VBEE integration settings (external TTS/API provider)
    VBEE_API_URL = os.environ.get('VBEE_API_URL', 'https://vbee.vn/api/v1')
    VBEE_API_KEY = os.environ.get('VBEE_API_KEY') or os.environ.get('VBEE_KEY')
    

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DEV_DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "database-dev.db")


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("TEST_DATABASE_URL") or "sqlite://"
    )  # In-memory database


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "database.db")


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
