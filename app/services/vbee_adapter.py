from typing import Any, Dict, List


def _line_to_element(line: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a dialogue line into a VBEE element representation.

    Expected input line shape: {"speaker": "Name", "text": "..."} or other variants.
    """
    text = line.get('text') or line.get('content') or line.get('line') or ''
    speaker = line.get('speaker') or line.get('role') or line.get('name') or None

    element: Dict[str, Any] = {
        'type': 'dialogue',
        'text': text,
    }
    if speaker:
        element['speaker'] = speaker
    return element


def _act_to_block(act: Dict[str, Any]) -> Dict[str, Any]:
    """Map an act (which contains scenes/lines) into a VBEE block.

    VBEE block shape is simplified to {id, characters, speed, elements: [...]}
    """
    elements: List[Dict[str, Any]] = []
    # acts may have 'lines' or 'scenes' or be a list of dialogue objects
    if isinstance(act, dict):
        lines = act.get('lines') or act.get('scenes') or act.get('dialogues') or act.get('content') or []
    else:
        lines = []

    if isinstance(lines, str):
        # try to split lines by newlines
        lines = [{'text': l.strip()} for l in lines.splitlines() if l.strip()]

    for l in lines:
        if isinstance(l, dict):
            elements.append(_line_to_element(l))
        else:
            elements.append({'type': 'dialogue', 'text': str(l)})

    block = {
        'id': act.get('id') if isinstance(act, dict) else None,
        'characters': len(elements),
        'speed': act.get('speed') if isinstance(act, dict) else 1.0,
        'elements': elements,
    }
    return block


def map_script_to_vbee_payload(script, product: str | None = None) -> Dict[str, Any]:
    """Map a Script SQLAlchemy model instance into a payload suitable for vbee /projects.

    This is conservative: we only include known flattened fields and map acts -> blocks.
    """
    # Accept both dict-like or model instance with attributes
    if isinstance(script, dict):
        data = script
    elif hasattr(script, 'to_dict'):
        data = script.to_dict()
    else:
        # try attribute access
        data = {
            'id': getattr(script, 'id', None),
            'title': getattr(script, 'title', getattr(script, 'name', 'Untitled')),
            'alias': getattr(script, 'alias', None),
            'acts': getattr(script, 'acts', None),
            'characters': getattr(script, 'characters', None),
        }

    acts = data.get('acts') or []
    # acts may be JSON string; try to parse if necessary
    if isinstance(acts, str):
        try:
            import json

            acts = json.loads(acts)
        except Exception:
            acts = []

    blocks = []
    if isinstance(acts, list):
        for act in acts:
            if isinstance(act, dict):
                blocks.append(_act_to_block(act))
            else:
                # fallback: treat act as raw text
                blocks.append({'id': None, 'characters': 1, 'speed': 1.0, 'elements': [{'type': 'dialogue', 'text': str(act)}]})

    payload = {
        'title': data.get('title') or f"script-{data.get('id')}",
        'product': product or 'default',
        'isDeleted': False,
        'blocks': blocks,
    }

    return payload
