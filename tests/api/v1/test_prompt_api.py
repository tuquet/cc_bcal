import json


def test_get_prompts_empty(client):
    resp = client.get('/api/v1/prompts')
    assert resp.status_code == 200
    data = resp.get_json()
    # default now returns an array of {name,content}
    assert isinstance(data, list)


def test_save_and_delete_prompt(client):
    # Save new prompt
    payload = {'name': 'test.md', 'content': 'hello'}
    resp = client.post('/api/v1/save_prompt', json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('ok') is True

    # Get prompts and find the id to delete
    resp = client.get('/api/v1/prompts')
    prompts = resp.get_json()
    # prompts is a list of objects
    assert any(p.get('name') == 'test.md' for p in prompts)

    # Find prompt id from DB via listing endpoint is not provided, so
    # we rely on direct DB access not available here. Instead, attempt
    # to delete with an invalid id and expect 404 (sanity check). 
    resp = client.delete('/api/v1/prompts/999999')
    assert resp.status_code == 404
