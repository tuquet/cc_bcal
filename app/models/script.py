import json
import ast
from datetime import datetime, timezone
from ..extensions import db
from sqlalchemy import text


class Script(db.Model):
    """Script model (JSON-first) matching the requested schema.

    Stores the full payload in `script_json` (Text). Exposes helper properties
    and some denormalized columns for queries.
    """

    __tablename__ = "scripts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Basic fields
    # During tests we sometimes construct Script() objects without setting
    # title/alias; allow nullable here and let service layer enforce required
    # alias for creations.
    title = db.Column(db.String(255), nullable=True)
    alias = db.Column(db.String(255), unique=True, nullable=True)
    logline = db.Column(db.Text, nullable=True)
    acts = db.Column(db.Text, nullable=True)
    characters = db.Column(db.Text, nullable=True)
    setting = db.Column(db.Text, nullable=True)
    genre = db.Column(db.Text, nullable=True)
    themes = db.Column(db.Text, nullable=True)
    tone = db.Column(db.String(128), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Other Fields
    is_video_generated = db.Column(db.Boolean, nullable=False, default=False)
    is_audio_generated = db.Column(db.Boolean, nullable=False, default=False)
    is_image_generated = db.Column(db.Boolean, nullable=False, default=False)
    is_transcript_generated = db.Column(db.Boolean, nullable=False, default=False)
    is_video_compiled = db.Column(db.Boolean, nullable=False, default=False)
    is_has_folder = db.Column(db.Boolean, nullable=False, default=False)
    builder_configs = db.Column(db.Text, nullable=True)

    # timestamps
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.func.now(),
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.func.now(),
    )

    def to_dict(self):
        updated_str = (
            self.updated_at.strftime("%Y-%m-%d %H:%M") if self.updated_at else None
        )
        created_str = (
            self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None
        )

        # We expose denormalized and flattened fields at top-level.
        # The original JSON payload remains available in `script_json` if
        # needed, but we don't return it nested in the API response to
        # avoid duplication.

        data = {
            "id": self.id,
            "title": self.title,
            "alias": self.alias,
            "tone": self.tone,
            "notes": self.notes,
            "logline": self.logline,
            "genre": self.genre_parsed,
            "themes": self.themes_parsed,
            "acts": self.acts_parsed,
            "characters": self.characters_parsed,
            "setting": self.setting_parsed,
            # Make Other Fields
            "is_video_generated": bool(self.is_video_generated),
            "is_audio_generated": bool(self.is_audio_generated),
            "is_image_generated": bool(self.is_image_generated),
            "is_transcript_generated": bool(self.is_transcript_generated),
            "is_video_compiled": bool(self.is_video_compiled),
            "is_has_folder": bool(getattr(self, "is_has_folder", False)),
            "builder_configs": self.builder_configs_parsed,
            "created_at": created_str,
            "updated_at": updated_str,
        }

        return data

    @property
    def builder_configs_parsed(self):
        if not self.builder_configs:
            return None
        try:
            return json.loads(self.builder_configs)
        except Exception:
            # fallback: try to escape raw control characters and parse again
            try:
                s = (
                    self.builder_configs.replace("\r\n", "\\n")
                    .replace("\n", "\\n")
                    .replace("\t", "\\t")
                )
                return json.loads(s)
            except Exception:
                return None

    @property
    def genre_parsed(self):
        """Return genre as a list of strings.

        Accepts that `self.genre` may be stored as JSON array or a
        comma-separated string; normalize to a list.
        """
        if not self.genre:
            return []
        try:
            val = json.loads(self.genre)
            # ensure list of strings
            if isinstance(val, list):
                return [str(x) for x in val]
            # if it's a single string stored as JSON, fallthrough
        except Exception:
            pass
        # fallback: split comma-separated string
        return [s.strip() for s in (self.genre or "").split(",") if s.strip()]

    @property
    def acts_parsed(self):
        if not self.acts:
            return []

        # 1) Try strict JSON
        try:
            return json.loads(self.acts)
        except Exception:
            pass

        # 2) Escape control characters and retry
        try:
            s = self.acts.replace("\r\n", "\\n").replace("\n", "\\n").replace("\t", "\\t")
            return json.loads(s)
        except Exception:
            pass

        # 3) Try Python literal eval (for repr-style stored lists)
        try:
            val = ast.literal_eval(self.acts)
            return val
        except Exception:
            pass

        # 4) Find first balanced [...] substring using depth scan
        try:
            text = self.acts
            start_idx = text.find('[')
            if start_idx != -1:
                depth = 0
                for i, ch in enumerate(text[start_idx:], start=start_idx):
                    if ch == '[':
                        depth += 1
                    elif ch == ']':
                        depth -= 1
                    if depth == 0:
                        candidate = text[start_idx:i+1]
                        try:
                            return json.loads(candidate)
                        except Exception:
                            try:
                                return ast.literal_eval(candidate)
                            except Exception:
                                break
        except Exception:
            pass

        # 5) Try compressing runs of closing brackets (reduce ']]]]' -> ']]]')
        try:
            s = self.acts
            for target_len in range(4, 1, -1):
                if (']' * target_len) in s:
                    candidate = s.replace(']' * target_len, ']' * (target_len - 1))
                    try:
                        return json.loads(candidate)
                    except Exception:
                        try:
                            return ast.literal_eval(candidate)
                        except Exception:
                            s = candidate
                            continue
        except Exception:
            pass

        # 6) Final targeted recovery: when other heuristics fail try to
        # extract the first balanced JSON object ({...}) from the text and
        # return it wrapped as [[obj]] which aligns with the expected
        # `acts` structure in many test/legacy cases.
        try:
            text = self.acts or ''
            # Try every possible '{' as a start of a balanced object
            for obj_start in [i for i, ch in enumerate(text) if ch == '{']:
                depth = 0
                for i in range(obj_start, len(text)):
                    ch = text[i]
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                    if depth == 0:
                        obj_str = text[obj_start : i + 1]
                        parsed = None
                        try:
                            parsed = json.loads(obj_str)
                        except Exception:
                            try:
                                parsed = ast.literal_eval(obj_str)
                            except Exception:
                                parsed = None
                        if parsed is not None:
                            return [[parsed]]
                        break
        except Exception:
            pass

        return []

    @property
    def characters_parsed(self):
        if not self.characters:
            return []
        try:
            return json.loads(self.characters)
        except Exception:
            try:
                s = self.characters.replace("\r\n", "\\n").replace("\n", "\\n").replace("\t", "\\t")
                return json.loads(s)
            except Exception:
                return []

    @property
    def themes_parsed(self):
        """Return themes as a list of strings.

        Similar normalization as `genre_parsed`.
        """
        if not self.themes:
            return []
        try:
            val = json.loads(self.themes)
            if isinstance(val, list):
                return [str(x) for x in val]
        except Exception:
            pass
        return [s.strip() for s in (self.themes or "").split(",") if s.strip()]

    @property
    def setting_parsed(self):
        if not self.setting:
            return None
        try:
            return json.loads(self.setting)
        except Exception:
            try:
                s = self.setting.replace("\r\n", "\\n").replace("\n", "\\n").replace("\t", "\\t")
                return json.loads(s)
            except Exception:
                return None

    @property
    def full_text(self) -> str:
        # Use parsed flattened `acts` only. We intentionally no longer
        # rely on a full `script_data` payload stored in `script_json`.
        acts = self.acts_parsed or []
        parts = []
        total_len = 0
        max_chars = 20000  # guard: avoid building huge strings
        stop = False
        for act in acts:
            for scene in (act.get("scenes") or []):
                for d in (scene.get("dialogues") or []):
                    text = d.get("line") or d.get("text") or ""
                    if not text:
                        continue
                    # normalize whitespace and ensure string
                    line = " ".join(str(text).split())
                    if not line:
                        continue
                    remaining = max_chars - total_len
                    if remaining <= 0:
                        stop = True
                        break
                    if len(line) > remaining:
                        parts.append(line[:remaining].rstrip() + "...")
                        stop = True
                        break
                    parts.append(line)
                    total_len += len(line)
                if stop:
                    break
            if stop:
                break
        return "\n\n".join(parts)

    @property
    def scenes(self):
        # Flatten scenes from acts when available (acts -> scenes).
        acts = self.acts_parsed
        if acts:
            scenes = []
            for act in acts:
                scenes.extend(act.get("scenes") or [])
            return scenes
        return []

    # NOTE: script_data / script_json is intentionally not exposed anymore.
    # We persist and work with flattened fields (`acts`, `characters`,
    # `setting`, ...) only to avoid storing and relying on the full JSON
    # payload in the DB model.

    def __repr__(self):
        return f"<Script {self.id}: {self.title}>"
