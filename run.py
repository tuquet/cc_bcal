import os
from app import create_app, db
from app.tasks import init_tasks

# Create the Flask app instance using the application factory
# It will load the config based on FLASK_CONFIG or default to 'development'
config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)

# Initialize background tasks (Redis connection and worker thread)
init_tasks(app)

@app.shell_context_processor
def make_shell_context():
    """Provides a shell context for `flask shell` command."""
    from app.models.script import Script
    return {'db': db, 'Script': Script}

@app.cli.command('create-db')
def create_db_command():
    """Creates the database tables."""
    with app.app_context():
        db.create_all()
    print('Database tables created.')

if __name__ == '__main__':
    # For production, use a proper WSGI server like Gunicorn or Waitress.
    # The `debug` and `port` values will be loaded from your config file.
    host = '127.0.0.1'
    port = 5000
    print(f"🚀 API docs available at: http://{host}:{port}/api/docs/")
    app.run(threaded=True)