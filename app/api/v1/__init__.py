from flask import Blueprint

# Import individual route blueprints
from .setting_routes import settings_bp
from .prompt_routes import prompts_bp
from .script_routes import scripts_bp
from .stream_routes import stream_bp
from .video_maker_routes import video_maker_bp

# Create a master blueprint for the v1 API
api_v1 = Blueprint('api_v1', __name__)

# Register the individual blueprints onto the master v1 blueprint
api_v1.register_blueprint(settings_bp)
api_v1.register_blueprint(prompts_bp)
api_v1.register_blueprint(scripts_bp)
api_v1.register_blueprint(stream_bp)
api_v1.register_blueprint(video_maker_bp)