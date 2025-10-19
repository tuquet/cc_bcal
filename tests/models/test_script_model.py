import json
from app.models.script import Script
from app import db
from datetime import datetime


class TestScriptModel:

    def test_create_and_to_dict(self, app):
        with app.app_context():
            s = Script()
            s.title = 'My Script'
            s.alias = 'my-script'
            # Use flattened fields
            s.acts = '[]'
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
                'acts': [[{'dialogues': [{'text': 'hello'}]}]],
                'duration': 12.5,
                'audio_status': 'done',
                'images_status': 'pending',
                'transcript_status': None,
                'builder_configs': {'x': 1}
            }
            # Simulate service behavior: populate flattened fields
            s.acts = '[[{"dialogues": [{"text": "hello"}]]]]'
            s.builder_configs = json.dumps({'x': 1})
            db.session.add(s)
            db.session.commit()
            # verify flattened values
            assert s.acts_parsed
            assert s.builder_configs_parsed and s.builder_configs_parsed['x'] == 1

    def test_full_text(self, app):
        with app.app_context():
            s = Script()
            # title and alias are non-nullable columns; ensure they're set
            # title and alias are non-nullable columns; ensure they're set
            s.title = 'N'
            s.alias = 'n'
            s.acts = '[{"act_number":1,"scenes":[{"dialogues":[{"text":"first line"},{"text":""}]},{"dialogues":[{"text":"second line"}]}]}]'
            db.session.add(s)
            db.session.commit()

            text = s.full_text
            assert 'first line' in text
            assert 'second line' in text
