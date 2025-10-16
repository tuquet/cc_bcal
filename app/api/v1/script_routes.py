from flask import request, jsonify, Blueprint, current_app
from app.extensions import db
from app.models.script import Script

scripts_bp = Blueprint('scripts', __name__)

@scripts_bp.route('/scripts', methods=['POST'])
def create_script_api():
    """Create a new script.
    ---
    tags:
      - Scripts
    parameters:
      - in: body
        name: body
        required: true
        description: The full JSON object representing the script.
        schema:
          $ref: '#/definitions/Script'
    responses:
      201:
        description: Script created successfully.
    """
    data = request.get_json()
    if not data or 'meta' not in data or 'alias' not in data['meta']:
        return jsonify({"error": "Invalid data. 'meta' and 'meta.alias' are required."}), 400
    alias = data['meta']['alias']
    if Script.query.filter_by(alias=alias).first():
        return jsonify({"error": f"Script with alias '{alias}' already exists."}), 409
    
    try:
        script = Script()
        script.script_data = data
        db.session.add(script)
        db.session.commit()
        return jsonify(script.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create script: {e}")
        return jsonify({"error": str(e)}), 500

@scripts_bp.route('/scripts', methods=['GET'])
def get_scripts():
    """Get a list of all scripts.
    ---
    tags:
      - Scripts
    responses:
      200:
        description: A list of script objects.
        schema:
          type: array
          items:
            $ref: '#/definitions/Script'
    """
    scripts = Script.query.order_by(Script.updated_at.desc()).all()
    return jsonify([s.to_dict() for s in scripts])

@scripts_bp.route('/scripts/<int:script_id>', methods=['GET'])
def get_script(script_id):
    """Get a single script by its ID.
    ---
    tags:
      - Scripts
    parameters:
      - name: script_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: The script object.
        schema:
          $ref: '#/definitions/Script'
    """
    script = db.session.get(Script, script_id)
    if not script:
        return jsonify({"error": "Script not found"}), 404
    return jsonify(script.to_dict())

@scripts_bp.route('/scripts/<int:script_id>', methods=['PUT'])
def update_script(script_id):
    """Update an existing script.
    ---
    tags:
      - Scripts
    parameters:
      - name: script_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        required: true
        description: The full JSON object to update the script with.
        schema:
          $ref: '#/definitions/Script'
    responses:
      200:
        description: Script updated successfully.
    """
    script = db.session.get(Script, script_id)
    if not script:
        return jsonify({"error": "Script not found"}), 404
    
    data = request.get_json()
    script.script_data = data
    db.session.commit()
    return jsonify(script.to_dict())

@scripts_bp.route('/scripts/<int:script_id>', methods=['DELETE'])
def delete_script(script_id):
    """Delete a script.
    ---
    tags:
      - Scripts
    parameters:
      - name: script_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Script deleted successfully.
    """
    script = db.session.get(Script, script_id)
    if not script:
        return jsonify({"error": "Script not found"}), 404
    
    db.session.delete(script)
    db.session.commit()
    return jsonify({"message": "Script deleted successfully."})