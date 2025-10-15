from pathlib import Path
from typing import Any, Dict
import json
import os


def get_project_path(script_data: Dict[str, Any], root_dir: Path = None) -> Path:
    """
    Xác định đường dẫn đầy đủ cho một thư mục project dựa trên dữ liệu kịch bản.

    Args:
        script_data: Dữ liệu JSON đã được tải của kịch bản.
        root_dir: Thư mục gốc của dự án. Nếu là None, sẽ sử dụng thư mục làm việc hiện tại.

    Returns:
        Một đối tượng Path trỏ đến đường dẫn đầy đủ của thư mục project.
        Ví dụ: /path/to/project/projects/tech-mentor/22.vuot-qua-imposter-syndrome-loi-khuyen-dev
    """
    if root_dir is None:
        # Use the repository root (this file is in the repo root)
        root_dir = Path(__file__).parent.resolve()

    # Prefer a configured project folder in settings.json if present
    settings_path = root_dir / "settings.json"
    if settings_path.exists():
        try:
            cfg = json.loads(settings_path.read_text(encoding='utf-8'))
            proj_folder = cfg.get('project_folder')
            if proj_folder:
                proj_path = Path(proj_folder)
                if not proj_path.is_absolute():
                    projects_root = (root_dir / proj_folder).resolve()
                else:
                    projects_root = proj_path.resolve()
            else:
                projects_root = (root_dir / "projects").resolve()
        except Exception:
            projects_root = (root_dir / "projects").resolve()
    else:
        projects_root = (root_dir / "projects").resolve()
    meta = script_data.get("meta", {})

    video_type = (meta.get("series") or meta.get("video_type", "general")).replace(" ", "-").lower()
    alias = meta.get("alias", "untitled")
    project_id = script_data.get("id")
    folder_name = f"{project_id}.{alias}"

    return projects_root / video_type / folder_name