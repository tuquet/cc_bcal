from app.models.setting import Setting
from app.services import setting_service
from app import db

class TestSettingService:

    def test_get_all_settings_as_dict_with_data(self, app):
        """ 
        GIVEN 2 settings are in the database.
        WHEN get_all_settings_as_dict() is called.
        THEN it should return a dictionary with 2 items.
        """
        with app.app_context():
            # Arrange: Add mock data to the in-memory database
            setting1 = Setting(key='theme', value='dark')
            setting2 = Setting(key='version', value='1.0.2')
            db.session.add(setting1)
            db.session.add(setting2)
            db.session.commit()

            # Act: Call the service function
            settings_dict = setting_service.get_all_settings_as_dict()

            # Assert: Check the result
            assert isinstance(settings_dict, dict)
            assert len(settings_dict) == 2
            assert settings_dict['theme'] == 'dark'
            assert settings_dict['version'] == '1.0.2'

    def test_get_all_settings_as_dict_empty(self, app):
        """
        GIVEN the settings table is empty.
        WHEN get_all_settings_as_dict() is called.
        THEN it should return an empty dictionary.
        """
        with app.app_context():
            # Arrange: Ensure the table is empty (handled by fixture teardown)
            
            # Act: Call the service function
            settings_dict = setting_service.get_all_settings_as_dict()

            # Assert: Check the result
            assert isinstance(settings_dict, dict)
            assert len(settings_dict) == 0
