import os
import sys
import subprocess
import json
from flask import render_template, redirect, url_for, flash, request, jsonify, Response
from pathlib import Path

from app_core import app, asset_check_once, generator_run_once, load_config, save_config, project_root
# Avoid importing `db` and `Script` at module import time to prevent circular-import
# issues that can cause linters (and runtime) to see names as undefined.
# We'll import them lazily inside functions that need them.


@app.route('/')
def ui_index():
    from models import Script
    scripts = Script.query.order_by(Script.id.desc()).all()
    # Attach derived script_json_path (capcut-api.json) for each script so the UI can trigger generation
    from utils import get_project_path
    annotated = []
    for s in scripts:
        try:
            proj = get_project_path(s.script_data)
            script_json = proj / 'capcut-api.json'
        except Exception:
            script_json = None
        # Create a simple object for template usage
        s_dict = s
        setattr(s_dict, 'script_json_path', str(script_json) if script_json is not None else '')
        annotated.append(s_dict)
    return render_template('index.html', scripts=annotated)


@app.route('/scripts/new', methods=['GET', 'POST'])
def ui_create_script():
    if request.method == 'POST':
        try:
            raw_data = request.form['script_data']
            data = json.loads(raw_data)
            alias = data.get('meta', {}).get('alias')
            if not alias:
                flash('Lỗi: Dữ liệu JSON phải có "meta.alias".', 'danger')
            else:
                from models import Script
                from database import db

                if Script.query.filter_by(alias=alias).first():
                    flash(f"Lỗi: Kịch bản với alias '{alias}' đã tồn tại.", 'danger')
                else:
                    new_script = Script()
                    new_script.script_data = data
                    new_script.status = 'new'
                    db.session.add(new_script)
                    db.session.commit()
                    flash('Tạo kịch bản thành công!', 'success')
                    return redirect(url_for('ui_index'))
            
        except json.JSONDecodeError:
            flash('Lỗi: Dữ liệu JSON không hợp lệ.', 'danger')
        return render_template('script_form.html', form_title="Tạo Kịch Bản Mới", script_data_json=request.form.get('script_data', ''))
    return render_template('script_form.html', form_title="Tạo Kịch Bản Mới")


@app.route('/scripts/edit/<int:script_id>', methods=['GET', 'POST'])
def ui_edit_script(script_id):
    from models import Script
    from database import db
    script = Script.query.get_or_404(script_id)
    if request.method == 'POST':
        data = json.loads(request.form['script_data'])
        script.script_data = data
        script.status = request.form['status']
        db.session.commit()
        flash('Cập nhật kịch bản thành công!', 'success')
        return redirect(url_for('ui_index'))
    script_data_json = json.dumps(script.script_data, indent=2, ensure_ascii=False)
    return render_template('script_form.html', form_title="Chỉnh Sửa Kịch Bản", script=script, script_data_json=script_data_json)


@app.route('/scripts/delete/<int:script_id>', methods=['POST'])
def ui_delete_script(script_id):
    from models import Script
    from database import db
    script = Script.query.get_or_404(script_id)
    db.session.delete(script)
    db.session.commit()
    flash('Đã xóa kịch bản.', 'success')
    return redirect(url_for('ui_index'))


@app.route('/settings', methods=['GET', 'POST'])
def ui_settings():
    cfg = load_config()
    if request.method == 'POST':
        project_folder = request.form.get('project_folder', '').strip()
        cfg['project_folder'] = project_folder
        save_config(cfg)
        flash('Cấu hình đã được lưu.', 'success')
        return redirect(url_for('ui_index'))
    return render_template('settings.html', config=cfg)


@app.route('/scripts/bulk_update_status', methods=['POST'])
def ui_bulk_update_status():
    ids = request.form.getlist('ids')
    new_status = request.form.get('new_status')
    if not ids:
        flash('Không có kịch bản nào được chọn.', 'warning')
        return redirect(url_for('ui_index'))
    try:
        from models import Script
        from database import db
        scripts = Script.query.filter(Script.id.in_(ids)).all()
        for s in scripts:
            s.status = new_status
        db.session.commit()
        flash(f'Đã cập nhật {len(scripts)} kịch bản -> {new_status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Không thể cập nhật trạng thái: {e}', 'danger')
    return redirect(url_for('ui_index'))


@app.route('/open_project_folder', methods=['POST'])
def ui_open_project_folder():
    cfg = load_config()
    project_folder = cfg.get('project_folder')
    if not project_folder:
        flash('Không có cấu hình project folder. Vui lòng thiết lập trong Cấu hình.', 'warning')
        return redirect(url_for('ui_index'))

    if os.path.isabs(project_folder):
        target = project_folder
    else:
        target = os.path.normpath(os.path.join(project_root, project_folder))

    if not os.path.exists(target):
        flash(f"Folder không tồn tại: {target}", 'danger')
        return redirect(url_for('ui_index'))

    try:
        if sys.platform.startswith('win'):
            subprocess.Popen(['explorer', target])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', target])
        else:
            subprocess.Popen(['xdg-open', target])
    except Exception as e:
        flash(f"Không thể mở thư mục: {e}", 'danger')

    return redirect(url_for('ui_index'))

@app.route('/logs/asset_check', methods=['GET'])
def view_asset_log():
    logs_dir = os.path.join(project_root, 'logs')
    asset_log = os.path.join(logs_dir, 'asset_check.log')
    if not os.path.exists(asset_log):
        return Response('Không tìm thấy asset_check.log', status=404, mimetype='text/plain')
    try:
        with open(asset_log, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/plain; charset=utf-8')
    except Exception as e:
        return Response(f'Không thể đọc log: {e}', status=500, mimetype='text/plain')


# API endpoints
@app.route('/api/scripts', methods=['POST'])
def create_script_api():
    from database import db
    from models import Script
    data = request.get_json()
    if not data or 'meta' not in data or 'alias' not in data['meta']:
        return jsonify({"error": "Dữ liệu không hợp lệ. Cần có 'meta' và 'meta.alias'."}), 400
    alias = data['meta']['alias']
    if Script.query.filter_by(alias=alias).first():
        return jsonify({"error": f"Kịch bản với alias '{alias}' đã tồn tại."}), 409
    try:
        new_script = Script()
        new_script.script_data = data
        new_script.status = data.get('status', 'new')
        db.session.add(new_script)
        db.session.commit()
        return jsonify(new_script.script_data), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/scripts', methods=['GET'])
def get_all_scripts_api():
    from models import Script
    scripts = Script.query.order_by(Script.id).all()
    out = []
    for s in scripts:
        updated = getattr(s, 'updated_at', None)
        if updated and hasattr(updated, 'strftime'):
            updated_str = updated.strftime('%Y-%m-%d %H:%M')
        else:
            updated_str = str(updated) if updated is not None else None

        out.append({
            'id': s.id,
            'title': getattr(s, 'title', None),
            'alias': getattr(s, 'alias', None),
            'status': getattr(s, 'status', None),
            'audio_status': getattr(s, 'audio_status', None),
            'images_status': getattr(s, 'images_status', None),
            'transcript_status': getattr(s, 'transcript_status', None),
            'updated_at': updated_str,
        })
    return jsonify(out)

@app.route('/api/scripts/<int:script_id>', methods=['GET'])
def get_script_api(script_id):
    from models import Script
    script = Script.query.get_or_404(script_id)
    return jsonify(script.script_data)


@app.route('/api/scripts/<int:script_id>', methods=['PUT'])
def update_script_api(script_id):
    from models import Script
    from database import db
    script = Script.query.get_or_404(script_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "Không có dữ liệu để cập nhật."}), 400
    try:
        script.script_data = data
        script.status = data.get('status', script.status)
        db.session.commit()
        return jsonify(script.script_data)
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/scripts/<int:script_id>', methods=['DELETE'])
def delete_script_api(script_id):
    from models import Script
    from database import db
    script = Script.query.get_or_404(script_id)
    db.session.delete(script)
    db.session.commit()
    return '', 204
