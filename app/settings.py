import structlog
from app.services import setting_service
from pathlib import Path
import shutil
import sys

log = structlog.get_logger()

def _find_chrome_executable() -> str | None:
    """
    Tries to find the path to the Google Chrome/Chromium executable on the system.
    Returns the path as a string if found, otherwise None.
    """
    # List of common executable names for different OS
    if sys.platform == "win32":
        executables = ["chrome.exe"]
    elif sys.platform == "darwin": # macOS
        executables = ["Google Chrome"]
    else: # Linux
        executables = ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]

    for exe in executables:
        path = shutil.which(exe)
        if path:
            return path
    
    # Fallback for macOS where it might not be in PATH
    if sys.platform == "darwin":
        mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if Path(mac_path).exists():
            return mac_path
            
    return None

class AppSettings:
    """
    A centralized, typed configuration object for the application.
    It defines default values and is then populated/overridden by
    settings from the database.
    """
    # --- Define all settings with their types and default values ---
    PROJECT_FOLDER: str = str(Path.home() / "NexoAPI" / "Projects") # type: ignore
    CHROME_PROFILE_PATH: str = str(Path.home() / "NexoAPI" / "ChromeProfile") # type: ignore
    CHROME_EXE_PATH: str | None = _find_chrome_executable()
    # Add more settings here as needed...

    def __init__(self):
        # Do not load automatically. This will be called from the app factory.
        # The `load()` method is called explicitly from `create_app`.
        pass

    def load(self):
        """
        Loads all settings from the database. If a setting is not in the DB,
        the class default is used.
        """
        db_settings = setting_service.get_all_settings_as_dict()
        
        # Iterate over class annotations (the defined settings)
        for key in self.__class__.__annotations__:
            # Get value from DB if it exists, otherwise use the class default
            value = db_settings.get(key, getattr(self.__class__, key))
            setattr(self, key, value)
        
        log.info("settings.loaded", source="database")

        # After loading, perform initialization tasks that depend on settings
        self._initialize_environment()

    def _initialize_environment(self):
        """Ensures that necessary directories exist."""
        project_folder = Path(self.PROJECT_FOLDER)
        project_folder.mkdir(parents=True, exist_ok=True)
        log.info("project_folder.checked", path=str(project_folder))

# Create a singleton instance that will be imported and used across the app.
# This object will be populated once when the application starts.
settings = AppSettings()