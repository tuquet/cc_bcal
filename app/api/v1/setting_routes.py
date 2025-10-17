from flask import request, jsonify, Blueprint, current_app
from app.extensions import db
from app.services import setting_service
from app.settings import settings
from app.api.pagination import paginate_query, has_pagination_args
from app.models.setting import Setting

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
    args = request.args or {}

    # If no pagination params provided, return the cached dict (existing behavior)
    if not has_pagination_args(args):
        return jsonify(setting_service.get_all_settings_as_dict())

    # Build a simple list view of settings for pagination
    base_q = Setting.query

    def _serialize(s: Setting):
        try:
            # Try to parse JSON values for consistency with service
            import json as _json

            val = _json.loads(s.value)
        except Exception:
            val = s.value
        return {"id": s.id, "key": s.key, "value": val}

    resp = paginate_query(
        base_q,
        Setting,
        args,
        serialize=_serialize,
        default_sort="key",
        allowed_sort_fields={"id", "key"},
    )
    return jsonify(resp)

@settings_bp.route('/settings', methods=['POST'])
def update_settings():
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

@settings_bp.route('/settings/<string:key>', methods=['GET'])
def get_setting(key: str):
  """Get a single setting by key."""
  try:
    value = setting_service.get_setting(key)
    if value is None:
      return jsonify({"error": "Setting not found"}), 404
    return jsonify({"key": key, "value": value})
  except Exception as e:
    current_app.logger.exception(e)
    return jsonify({"error": str(e)}), 500


@settings_bp.route('/settings/<string:key>', methods=['PUT'])
def put_setting(key: str):
  """Create or update a single setting by key."""
  payload = request.get_json()
  if payload is None or 'value' not in payload:
    return jsonify({"error": "Request body must be JSON and include 'value' field."}), 400
  try:
    new_value = setting_service.set_setting(key, payload['value'])
    db.session.commit()
    # reload global settings
    settings.load()
    return jsonify({"key": key, "value": new_value})
  except Exception as e:
    db.session.rollback()
    current_app.logger.exception(e)
    return jsonify({"error": str(e)}), 500


@settings_bp.route('/settings/<string:key>', methods=['DELETE'])
def delete_setting(key: str):
  """Delete a single setting by key."""
  try:
    deleted = setting_service.delete_setting(key)
    if not deleted:
      return jsonify({"error": "Setting not found"}), 404
    db.session.commit()
    settings.load()
    return jsonify({"key": key, "deleted": True})
  except Exception as e:
    db.session.rollback()
    current_app.logger.exception(e)
    return jsonify({"error": str(e)}), 500