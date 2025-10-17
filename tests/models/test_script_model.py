from app.models.script import Script
from app import db
from datetime import datetime


class TestScriptModel:

    def test_create_and_to_dict(self, app):
        with app.app_context():
            s = Script()
            s.title = 'My Script'
            s.alias = 'my-script'
            s.meta = {'title': 'My Script', 'alias': 'my-script'}
            s.scenes = []
            db.session.add(s)
            db.session.commit()

            d = s.to_dict()
            assert d['title'] == 'My Script'
            assert d['alias'] == 'my-script'
            assert 'created_at' in d and d['created_at'] is not None

    def test_script_data_setter_getter(self, app):
        with app.app_context():
            s = Script()
            payload = {
                'meta': {'title': 'T', 'alias': 't'},
                'scenes': [[{'lines': [{'text': 'hello'}]}]],
                'duration': 12.5,
                'audio_status': 'done',
                'images_status': 'pending',
                'transcript_status': None,
                'generation_params': {'x': 1}
            }
            s.script_data = payload
            db.session.add(s)
            db.session.commit()

            # getter
            data = s.script_data
            assert data['meta']['title'] == 'T'
            assert data['duration'] == 12.5
            assert data['generation_params']['x'] == 1

    def test_full_narration_text(self, app):
        with app.app_context():
            s = Script()
            s.meta = {'title': 'N', 'alias': 'n'}
            # title and alias are non-nullable columns; ensure they're set
            s.title = 'N'
            s.alias = 'n'
            s.scenes = [
                {'lines': [{'text': 'first line'}, {'text': ''}]},
                {'lines': [{'text': 'second line'}]}
            ]
            db.session.add(s)
            db.session.commit()

            text = s.full_narration_text
            assert 'first line' in text
            assert 'second line' in text
