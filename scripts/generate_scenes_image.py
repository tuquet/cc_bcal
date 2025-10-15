"""scripts/2_generate_scenes_image.py

Phiên bản API-friendly của trình tạo ảnh tự động (Gemini). File này
xuất ra hàm generate_images(...) để có thể gọi từ một API (ví dụ: main.py).

Tính năng:
- generate_images(script_path, output_dir=None, headless=True, chrome_exe=None, user_data_dir=None, timeout=240)
  trả về dict {'ok': True, 'images': n, 'paths': [...] } hoặc {'ok': False, 'error': '...'}

Giữ CLI entrypoint để chạy trực tiếp từ dòng lệnh.
Trả lời bằng tiếng Việt trong log để dễ đọc khi chạy thủ công.
"""

from pathlib import Path
import json
import time
import argparse
from typing import Optional, Dict, Any, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from utils import get_project_path

# --- Selectors ---
INPUT_BOX_SELECTOR = "div.ql-editor.ql-blank"
SEND_BUTTON_SELECTOR = "button.send-button"
GENERATED_IMAGE_SELECTOR = "img.image.loaded"


def generate_images(
    script_path: Path,
    output_dir: Optional[Path] = None,
    headless: bool = True,
    chrome_exe: Optional[str] = None,
    user_data_dir: Optional[Path] = None,
    timeout: int = 240,
) -> Dict[str, Any]:
    """Generate images for the scenes defined in script_path.

    Parameters:
    - script_path: Path to the script JSON file (must contain key 'scenes').
    - output_dir: Optional directory where images will be written. If not provided,
      will use get_project_path(script_data) from utils.
    - headless: Run Chrome headlessly when True. When False, you can optionally
      pass user_data_dir to reuse a profile.
    - chrome_exe: Optional path to Chrome binary. If None, system default is used.
    - user_data_dir: Optional Path for Chrome user-data (useful when headless=False).
    - timeout: max seconds to wait for generation (passed to WebDriverWait).

    Returns:
    - dict with keys 'ok' (bool). On success also includes 'images' (int) and 'paths' (list).
    """
    # Validate script file
    if not script_path or not script_path.exists():
        return {"ok": False, "error": f"File kịch bản không tồn tại: {script_path}"}

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_data = json.load(f)
    except Exception as e:
        return {"ok": False, "error": f"Không thể đọc file kịch bản: {e}"}

    scenes = script_data.get("scenes", [])
    if not scenes:
        return {"ok": False, "error": "Không tìm thấy 'scenes' trong file kịch bản."}

    # Determine output dir
    if output_dir:
        out_dir = Path(output_dir)
    else:
        try:
            out_dir = Path(get_project_path(script_data))
        except Exception:
            out_dir = Path.cwd() / "output_images"

    out_dir.mkdir(parents=True, exist_ok=True)

    # Setup Chrome options
    options = Options()
    if chrome_exe:
        options.binary_location = chrome_exe
    # If user didn't pass a user_data_dir, default to repo-root/chrome-profile when running non-headless
    if not user_data_dir:
        try:
            repo_root = Path(__file__).parent.parent.resolve()
            default_profile = repo_root / "chrome-profile"
            user_data_dir = default_profile
        except Exception:
            user_data_dir = None

    if headless:
        # new headless flags for modern chrome
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    else:
        if user_data_dir:
            options.add_argument(f"--user-data-dir={str(user_data_dir)}")

    # Common options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = None
    wait = None
    try:
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, timeout)

        print("🚀 Đang mở Gemini...")
        driver.get("https://gemini.google.com/")

        print("⏳ Chờ trang Gemini sẵn sàng...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, INPUT_BOX_SELECTOR)))
        print("✅ Trang sẵn sàng. Bắt đầu gửi prompt...")

        scenes_json_string = json.dumps(scenes, ensure_ascii=False, indent=2)
        prompt = (
            f"tạo ảnh dựa theo JSON scenes sau: {scenes_json_string} "
            "lưu ý: ảnh không chứa text, mọi nhân vật đều đủ 18 tuổi trở lên"
        )

        input_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, INPUT_BOX_SELECTOR)))
        # Use JS to set the content reliably
        driver.execute_script("arguments[0].innerText = arguments[1];", input_box, prompt)
        time.sleep(0.8)

        submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SEND_BUTTON_SELECTOR)))
        submit_button.click()
        print("💬 Prompt đã gửi. Đang chờ Gemini tạo ảnh...")

        expected_image_count = len(scenes)

        # Wait until at least expected_image_count images are found
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, GENERATED_IMAGE_SELECTOR)) >= expected_image_count)
        print(f"✅ Đã phát hiện tối thiểu {expected_image_count} ảnh trên trang.")

        # Wait until the last N images have valid src attributes
        def last_n_have_src(d):
            imgs = d.find_elements(By.CSS_SELECTOR, GENERATED_IMAGE_SELECTOR)
            if len(imgs) < expected_image_count:
                return False
            recent = imgs[-expected_image_count:]
            return all(img.get_attribute("src") and img.get_attribute("src").startswith(('blob:', 'data:', 'http')) for img in recent)

        wait.until(last_n_have_src)
        print("✅ Tất cả ảnh đã có src hợp lệ.")

        # Collect URLs and save each by opening in new tab and screenshot
        image_elements = driver.find_elements(By.CSS_SELECTOR, GENERATED_IMAGE_SELECTOR)
        new_image_urls = [img.get_attribute("src") for img in image_elements[-expected_image_count:]]

        main_tab = driver.current_window_handle
        saved_paths: List[str] = []

        for i, url in enumerate(new_image_urls):
            image_path = out_dir / f"{i+1}.png"
            try:
                _download_image_in_new_tab(driver, wait, url, image_path, main_tab)
                saved_paths.append(str(image_path))
            except Exception as e:
                print(f"⚠️ Lỗi khi lưu ảnh {i+1}: {e}")

        return {"ok": True, "images": len(saved_paths), "paths": saved_paths}

    except TimeoutException:
        return {"ok": False, "error": "timeout"}
    except WebDriverException as e:
        return {"ok": False, "error": f"WebDriver error: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def _download_image_in_new_tab(driver: webdriver.Chrome, wait: WebDriverWait, image_url: str, image_output_path: Path, main_tab_handle: str):
    """Open image_url in a new tab, wait for img and save screenshot to image_output_path."""
    print(f"...Đang tải và ghi đè ảnh: {image_output_path.name}")
    driver.switch_to.new_window('tab')
    driver.get(image_url)

    img = wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
    # save screenshot of the image element (works even for blob/data urls)
    img.screenshot(str(image_output_path))

    driver.close()
    driver.switch_to.window(main_tab_handle)


def _cli_main():
    parser = argparse.ArgumentParser(description="Tự động tạo ảnh cho kịch bản video bằng Gemini.")
    parser.add_argument("script_file", type=Path, help="Đường dẫn đến file kịch bản JSON (ví dụ: data/1.json).")
    parser.add_argument("--out", type=Path, default=None, help="Thư mục xuất ảnh (mặc định là project path).")
    parser.add_argument("--no-headless", dest='headless', action='store_false', help="Chạy chrome không headless (useful for debugging).")
    parser.add_argument("--chrome", type=str, default=None, help="Đường dẫn tới Chrome binary (nếu cần).")
    parser.add_argument("--user-data-dir", type=Path, default=None, help="User data dir cho chrome khi không headless.")
    parser.add_argument("--timeout", type=int, default=240, help="Timeout chờ tạo ảnh (giây).")
    args = parser.parse_args()

    res = generate_images(
        args.script_file,
        output_dir=args.out,
        headless=args.headless,
        chrome_exe=args.chrome,
        user_data_dir=args.user_data_dir,
        timeout=args.timeout,
    )

    if res.get('ok'):
        print(f"✅ Hoàn tất: {res.get('images',0)} ảnh được xử lý. Lưu tại: {res.get('paths')}")
    else:
        print(f"❌ Lỗi: {res.get('error')}")


if __name__ == '__main__':
    _cli_main()

