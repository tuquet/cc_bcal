from flask import Blueprint, request, jsonify
from flask import current_app as app

from ...services.vbee_service import VbeeService

vbee_bp = Blueprint('vbee', __name__)


@vbee_bp.route('/vbee/projects/create-from-script', methods=['POST'])
def create_project_from_script():
    """Create a VBEE project from a local Script record.

    Expected JSON: {"script_id": <int>, "product": "voice_product"}
    """
    payload = request.get_json() or {}
    script_id = payload.get('script_id')
    product = payload.get('product')

    if not script_id:
        return jsonify({"error": "script_id is required"}), 400

    service = VbeeService(app.config)
    try:
        result = service.create_project_from_script(script_id, product=product)
        return jsonify(result), 200
    except Exception as e:
        app.logger.exception('VBEE create project failed')
        return jsonify({"error": str(e)}), 500
