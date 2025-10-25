import json
from unittest.mock import patch

from app import create_app


def test_create_project_from_script_route(client, monkeypatch):
    # use the pytest 'client' fixture which has a fresh testing DB
    app = client.application

    # Mock the service requests.post via requests.post called in VbeeService
    fake_response = {'id': 'proj-123', 'title': 'script-1'}

    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = fake_response

        # We need a script in DB; create minimal script via the model
        with app.app_context():
            from app.extensions import db
            from app.models.script import Script

            s = Script(title='T1', alias='a')
            db.session.add(s)
            db.session.commit()
            sid = s.id

        res = client.post('/api/v1/vbee/projects/create-from-script', json={'script_id': sid})
        assert res.status_code == 200
        data = res.get_json()
        assert data['id'] == 'proj-123'
