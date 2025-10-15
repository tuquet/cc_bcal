import json
from datetime import datetime, timezone
from database import db

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

    @property
    def script_data(self):
        data = {
            "id": self.id,
            "meta": self.meta,
            "scenes": self.scenes,
            "duration": self.duration
        }
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
        return json.loads(self._meta)
    @meta.setter
    def meta(self, value):
        self._meta = json.dumps(value, ensure_ascii=False)

    @property
    def scenes(self):
        return json.loads(self._scenes)
    @scenes.setter
    def scenes(self, value):
        self._scenes = json.dumps(value, ensure_ascii=False)

    @property
    def generation_params(self):
        return json.loads(self._generation_params) if self._generation_params else None
    @generation_params.setter
    def generation_params(self, value):
        self._generation_params = json.dumps(value, ensure_ascii=False) if value else None

    def __repr__(self):
        return f'<Script {self.id}: {self.title}>'
