from flask import request, jsonify, Blueprint, current_app
from app.extensions import db
from app.services import prompt_service

prompts_bp = Blueprint('prompts', __name__)

@prompts_bp.route('/prompts', methods=['GET'])
def api_get_prompts():
    """Get all available prompts.
    This endpoint returns a list of all prompt templates stored on the server.
    The results are cached for performance.
    ---
    tags:
      - Prompts
    responses:
      200:
        description: A JSON object where keys are filenames and values are the prompt content.
        schema:
          type: object
          additionalProperties:
            type: string
          example:
            prompt1.md: "This is the content of the first prompt."
            prompt2.md: "Content of the second prompt."
    """
    return jsonify(prompt_service.get_all_prompts())

@prompts_bp.route('/save_prompt', methods=['POST'])
def api_save_prompt():
    """Create or update a prompt.
    If the filename exists, it updates the content. Otherwise, it creates a new prompt.
    ---
    tags:
      - Prompts
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: The unique name for the prompt (e.g., 'my-prompt.md').
            content:
              type: string
              description: The full markdown content of the prompt.
    responses:
      200:
        description: Prompt saved successfully.
    """
    payload = request.get_json() or {}
    name = payload.get('name')
    content = payload.get('content')

    try:
        prompt_service.save_prompt(name=name, content=content)
        return jsonify({'ok': True, 'message': f'Prompt "{name}" has been saved.'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Could not save prompt '{name}' to database: {e}")
        return jsonify({'error': str(e)}), 500

@prompts_bp.route('/prompts/<int:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Delete a prompt by its ID.
    ---
    tags:
      - Prompts
    parameters:
      - name: prompt_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Prompt deleted successfully.
    """
    return prompt_service.delete_prompt_by_id(prompt_id)