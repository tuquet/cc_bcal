import pytest
from app import create_app, db

@pytest.fixture(scope='function')
def app():
    """
    Fixture that creates a test app instance with a new database.
    """
    # Create a Flask app configured for testing
    # create_app expects a config name (e.g., 'testing'), not a keyword arg
    app = create_app('testing')

    with app.app_context():
        # Create the database tables
        db.create_all()

        yield app

        # Teardown: drop all tables after tests are done
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()
