import json


def test_create_get_update_delete_script(client):
    # Create script
    payload = {
        'meta': {'title': 'S', 'alias': 's'},
        'acts': [],
    }
    resp = client.post('/api/v1/scripts', json=payload)
    assert resp.status_code == 201
    created = resp.get_json()
    sid = created['id']

    # Get list
    resp = client.get('/api/v1/scripts')
    assert resp.status_code == 200
    lst = resp.get_json()
    assert any(s['id'] == sid for s in lst)

    # Get single
    resp = client.get(f'/api/v1/scripts/{sid}')
    assert resp.status_code == 200
    s = resp.get_json()
    assert s['alias'] == 's'

    # Update
    update_payload = {'meta': {'title': 'S2', 'alias': 's'}, 'acts': []}
    resp = client.put(f'/api/v1/scripts/{sid}', json=update_payload)
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated['title'] == 'S2'

    # Delete
    resp = client.delete(f'/api/v1/scripts/{sid}')
    assert resp.status_code == 200
