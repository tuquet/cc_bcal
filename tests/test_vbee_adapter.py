import json
from app.services.vbee_adapter import map_script_to_vbee_payload


def test_map_script_with_simple_acts():
    script = {
        'id': 1,
        'title': 'Hello',
        'acts': [
            {'id': 'a1', 'lines': [{'speaker': 'A', 'text': 'Hi'}, {'speaker': 'B', 'text': 'Hello'}]},
        ],
    }

    payload = map_script_to_vbee_payload(script, product='p1')
    assert payload['title'] == 'Hello'
    assert payload['product'] == 'p1'
    assert isinstance(payload['blocks'], list)
    assert payload['blocks'][0]['id'] == 'a1'
    assert payload['blocks'][0]['elements'][0]['text'] == 'Hi'


def test_map_script_with_string_acts():
    script = {'id': 2, 'title': 'S2', 'acts': '[{"lines": [{"text":"line1"}]}]'}
    payload = map_script_to_vbee_payload(script)
    assert payload['blocks'][0]['elements'][0]['text'] == 'line1'
