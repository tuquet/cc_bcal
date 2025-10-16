from flask import request, jsonify, Blueprint, current_app
from app.extensions import db
from app.services import setting_service
from app.settings import settings

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET'])
def get_settings():
    """Get all settings.
    ---
    tags:
      - Settings
    responses:
      200:
        description: A dictionary of all settings.
    """
    return jsonify(setting_service.get_all_settings_as_dict())

@settings_bp.route('/settings', methods=['POST'])
def update_settings_api():
    """Update a batch of settings.
    ---
    tags:
      - Settings
    parameters:
      - in: body
        name: body
        schema:
          type: object
          additionalProperties:
            type: string
          example:
            project_folder: "C:/MyProjects"
            another_key: "some_value"
    responses:
      200:
        description: Settings updated successfully.
    """
    settings_data = request.get_json()
    if not isinstance(settings_data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400
    try:
        setting_service.update_settings(settings_data)
        db.session.commit()
        # Reload the global settings object to reflect changes immediately
        settings.load()
        return jsonify({"message": "Settings updated successfully."})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update settings: {e}")
        return jsonify({"error": str(e)}), 500