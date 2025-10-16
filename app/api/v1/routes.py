from flask import request, jsonify, Blueprint, current_app, Response, stream_with_context
import os
import sys
import subprocess
from pathlib import Path
import uuid
import json

from app.extensions import db, cache
from app.models.script import Script
from app.models.prompt import Prompt
from app.utils import asset_check_once, generator_run_once
from app.services.prompt_service import get_all_prompts
from app.tasks import (
    JOB_QUEUE, 
    BACKGROUND_JOBS, 
    redis_client, 
    REDIS_CHANNEL,
    _run_generate_images,
    _run_transcript,
    _run_generate_capcut,
    _run_align_scenes
)

api_v1 = Blueprint('api_v1', __name__)

# --- API Endpoints ---

@api_v1.route('/prompts', methods=['GET'])
def api_get_prompts():
    """Get all available prompts.
    This endpoint returns a list of all prompt templates stored on the server.
    The results are cached for performance.
    ---
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
    return jsonify(get_all_prompts())

@api_v1.route('/save_prompt', methods=['POST'])
def api_save_prompt():
    payload = request.get_json() or {}
    filename = payload.get('filename')
    content = payload.get('content')
    if not filename or not filename.endswith('.md'):
        return jsonify({'error': 'Filename is required and must end with .md'}), 400
    
    try:
        prompt = Prompt.query.filter_by(filename=filename).first()
        if prompt:
            # Cập nhật prompt đã có
            prompt.content = content
        else:
            # Tạo prompt mới
            prompt = Prompt(filename=filename, content=content)
            db.session.add(prompt)
        db.session.commit()
        cache.delete('all_prompts')
        return jsonify({'ok': True, 'message': f'Prompt "{filename}" has been saved.'})
    except Exception as e:
        current_app.logger.error(f"Could not save prompt '{filename}' to database: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_v1.route('/scripts', methods=['POST'])
def create_script_api():
    data = request.get_json()
    if not data or 'meta' not in data or 'alias' not in data['meta']:
        return jsonify({"error": "Invalid data. 'meta' and 'meta.alias' are required."}), 400
    alias = data['meta']['alias']
    if Script.query.filter_by(alias=alias).first():
        return jsonify({"error": f"Script with alias '{alias}' already exists."}), 409