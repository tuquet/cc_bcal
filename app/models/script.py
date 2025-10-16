import json
from datetime import datetime, timezone
from pathlib import Path
from flask import current_app

# Corrected import to work within the application factory structure
from ..extensions import db

class Script(db.Model):
    __tablename__ = 'scripts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    alias = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='new')
    duration = db.Column(db.Float, nullable=True)
    audio_status = db.Column(db.String(50), nullable=True)
    images_status = db.Column(db.String(50), nullable=True)
    transcript_status = db.Column(db.String(50), nullable=True)

    _meta = db.Column('meta', db.Text, nullable=False)
    _scenes = db.Column('scenes', db.Text, nullable=False)
    _generation_params = db.Column('generation_params', db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), server_default=db.func.now())
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), server_default=db.func.now())

    def to_dict(self):
        """Returns a dictionary representation of the script for API responses."""
        updated_str = self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None
        created_str = self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        return {
            'id': self.id,
            'title': self.title,
            'alias': self.alias,
            'status': self.status,
            'duration': self.duration,
            'audio_status': self.audio_status,
            'images_status': self.images_status,
            'transcript_status': self.transcript_status,
            'created_at': created_str,
            'updated_at': updated_str,
        }

    @property
    def script_data(self):
        data = {
            "id": self.id,
            "meta": self.meta,
            "scenes": self.scenes
        }
        if self.duration is not None:
            data['duration'] = self.duration
        if self.audio_status:
            data['audio_status'] = self.audio_status
        if self.images_status:
            data['images_status'] = self.images_status
        if self.transcript_status:
            data['transcript_status'] = self.transcript_status
        if self.generation_params:
            data["generation_params"] = self.generation_params
        return data

    @script_data.setter
    def script_data(self, value):
        self.meta = value.get('meta', {})
        self.scenes = value.get('scenes', [])
        self.generation_params = value.get('generation_params')
        self.duration = value.get('duration')
        self.audio_status = value.get('audio_status')
        self.images_status = value.get('images_status')
        self.transcript_status = value.get('transcript_status')
        self.title = self.meta.get('title', '')
        self.alias = self.meta.get('alias', '')

    @property
    def meta(self):
        if not hasattr(self, '_cached_meta'):
            self._cached_meta = json.loads(self._meta)
        return self._cached_meta
    @meta.setter
    def meta(self, value):
        self._meta = json.dumps(value, ensure_ascii=False)
        if hasattr(self, '_cached_meta'):
            del self._cached_meta

    @property
    def scenes(self):
        return json.loads(self._scenes)
    @scenes.setter
    def scenes(self, value):
        self._scenes = json.dumps(value, ensure_ascii=False)

    @property
    def generation_params(self):
        if not hasattr(self, '_cached_generation_params'):
            self._cached_generation_params = json.loads(self._generation_params) if self._generation_params else None
        return self._cached_generation_params
    @generation_params.setter
    def generation_params(self, value):
        self._generation_params = json.dumps(value, ensure_ascii=False) if value else None
        if hasattr(self, '_cached_generation_params'):
            del self._cached_generation_params

    @property
    def _derived_paths(self) -> dict:
        """Internal property to calculate and cache paths only once."""
        if hasattr(self, '_cached_paths'):
            return self._cached_paths

        from ..utils import get_project_path
        
        paths = {'project_folder': '', 'script_json_path': ''}
        try:
            with current_app.app_context():
                project_root = current_app.root_path.parent
                project_folder = get_project_path(self.script_data, project_root)
                paths['project_folder'] = str(project_folder)
                paths['script_json_path'] = str(project_folder / 'capcut-api.json')
        except Exception:
            pass
        
        self._cached_paths = paths
        return self._cached_paths

    @property
    def project_path(self) -> str:
        return self._derived_paths['project_folder']

    @property
    def script_json_path(self) -> str:
        return self._derived_paths['script_json_path']

    @property
    def full_narration_text(self) -> str:
        narration_parts = [line.get('text', '') for scene in self.scenes for line in scene.get('lines', []) if line.get('text')]
        return "\n\n".join(narration_parts)

    def __repr__(self):
        return f'<Script {self.id}: {self.title}>'