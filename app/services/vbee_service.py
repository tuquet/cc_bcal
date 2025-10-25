import json
import os
import requests
from flask import current_app as app

from .vbee_adapter import map_script_to_vbee_payload


class VbeeService:
    def __init__(self, config):
        # config may be app.config or a mapping-like object
        self.base_url = config.get('VBEE_API_URL') or 'https://vbee.vn/api/v1'
        self.api_key = config.get('VBEE_API_KEY') or config.get('VBEE_KEY')
        # allow debug/dry-run mode via config or env
        # Accept truthy strings like '1', 'true', 'yes', 'on'
        def _truthy(v):
            if isinstance(v, bool):
                return v
            if v is None:
                return False
            try:
                s = str(v).strip().lower()
            except Exception:
                return False
            return s in ('1', 'true', 'yes', 'on')

        cfg_val = config.get('VBEE_DRY_RUN')
        env_val = os.getenv('VBEE_DRY_RUN')
        self.dry_run = _truthy(cfg_val) or _truthy(env_val)

    def _headers(self):
        h = {'Content-Type': 'application/json'}
        if self.api_key:
            h['Authorization'] = f'Bearer {self.api_key}'
        return h

    def create_project_from_script(self, script_id: int, product: str | None = None, dry_run: bool | None = None) -> dict:
        """Load script data from DB, map to VBEE payload, and POST to /projects.

        Returns the JSON response from VBEE on success.
        """
        # Lazy import to avoid circular imports at module load
        from ..models.script import Script
        from ..extensions import db

        # prefer Session.get to avoid SQLAlchemy legacy warning
        script = db.session.get(Script, script_id)
        if not script:
            raise ValueError(f"Script id={script_id} not found")

        payload = map_script_to_vbee_payload(script, product=product)
        # determine effective dry run: function param overrides service config
        effective_dry = self.dry_run if dry_run is None else bool(dry_run)
        # when dry-run, log payload and return it instead of POSTing
        if effective_dry:
            # Use flask app logger at WARNING so it's visible in console runs/tests
            pretty = json.dumps(payload, indent=2, ensure_ascii=False)
            try:
                app.logger.warning('VBEE dry-run enabled; payload:\n%s', pretty)
            except Exception:
                # fallback print for contexts without app
                print('VBEE dry-run payload:\n', pretty)
            # also print unconditionally so pytest -s and other console runs always see payload
            print('VBEE dry-run payload:\n', pretty)
            # return payload so callers (or tests) can inspect it
            return {'dry_run': True, 'payload': payload}

        url = f"{self.base_url.rstrip('/')}/projects"
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()
