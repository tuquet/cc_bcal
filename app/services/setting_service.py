import json
import structlog
from app.extensions import db, cache
from app.models.setting import Setting

log = structlog.get_logger()

@cache.cached(timeout=3600, key_prefix='all_settings')
def get_all_settings_as_dict():
    """
    Get all the settings from the DB, parse the JSON value and cache the result.
    """
    settings_from_db = Setting.query.all()
    settings_dict = {}
    for setting in settings_from_db:
        try:
            # Try to parse the value as JSON
            settings_dict[setting.key] = json.loads(setting.value)
        except (json.JSONDecodeError, TypeError):
            # If not JSON, returns the original string value
            settings_dict[setting.key] = setting.value
    return settings_dict

def get_setting(key: str):
    """Gets a single setting value from the database."""
    setting = Setting.query.filter_by(key=key).first()
    if not setting:
        return None
    try:
        return json.loads(setting.value)
    except (json.JSONDecodeError, TypeError):
        return setting.value

def set_setting(key: str, value):
    """Creates or updates a single setting in the database."""
    setting = Setting.query.filter_by(key=key).first()
    
    if isinstance(value, (dict, list)):
        value_str = json.dumps(value, ensure_ascii=False)
    else:
        value_str = str(value)

    if setting:
        setting.value = value_str
    else:
        new_setting = Setting(key=key, value=value_str)
        db.session.add(new_setting)
    
    db.session.commit()
    cache.delete('all_settings')
    log.info("setting.set", key=key, value=value)
    return get_setting(key)

def update_settings(settings_dict: dict):
    """
    Update or create multiple settings from one dictionary.
    """
    for key, value in settings_dict.items():
        setting = Setting.query.filter_by(key=key).first()
        
        # Convert value to JSON string if it is a dict or list
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value, ensure_ascii=False)
        else:
            value_str = str(value)

        if setting:
            setting.value = value_str
        else:
            new_setting = Setting(key=key, value=value_str)
            db.session.add(new_setting)
    
    cache.delete('all_settings')
    log.info("settings.updated", updated_keys=list(settings_dict.keys()))

def delete_setting(key: str):
    """Deletes a single setting from the database."""
    setting = Setting.query.filter_by(key=key).first()
    if setting:
        db.session.delete(setting)
        db.session.commit()
        cache.delete('all_settings')
        log.info("setting.deleted", key=key)
        return True
    return False