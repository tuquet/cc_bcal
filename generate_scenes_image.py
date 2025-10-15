import sys
import time
import subprocess
import atexit
import argparse
import json
from selenium import webdriver

from utils import get_project_path
from selenium.webdriver.common.by import By
from pathlib import Path
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- Constants for CSS Selectors for easier maintenance ---
INPUT_BOX_SELECTOR = "div.ql-editor.ql-blank"
SEND_BUTTON_SELECTOR = "button.send-button"
MARKDOWN_RESPONSE_SELECTOR = ".markdown"
GENERATED_IMAGE_SELECTOR = "img.image.loaded" # Selector cụ thể hơn cho ảnh đã tải xong

# Global variable to hold the chrome process so we can terminate it later
chrome_process = None

def cleanup_chrome_process():
    """Ensures the Chrome process is terminated when the script exits."""
    global chrome_process
    if chrome_process:
        print("\n🧹 Dọn dẹp: Đang đóng tiến trình Chrome...")
        chrome_process.terminate()
        chrome_process.wait()
        print("✅ Tiến trình Chrome đã được đóng.")

# Register the cleanup function to be called automatically on script exit
atexit.register(cleanup_chrome_process)

def start_or_connect_to_chrome():
    """
    Starts a new Chrome instance in debug mode and connects Selenium to it.
    Returns the Selenium driver instance.
    """
    global chrome_process

    # --- Start Chrome in debug mode ---
    chrome_exe_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data_dir = Path.cwd() / "chrome-profile"
    debugging_port = 9222
    chrome_command = [chrome_exe_path, f"--remote-debugging-port={debugging_port}", f'--user-data-dir={user_data_dir}']
    
    print(f"🚀 Đang khởi động Chrome ở chế độ debug trên port {debugging_port}...")
    chrome_process = subprocess.Popen(chrome_command)
    time.sleep(5)

    # --- Connect Selenium to the new Chrome instance ---
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debugging_port}")
    print("🔌 Đang kết nối Selenium vào trình duyệt...")
    driver = webdriver.Chrome(options=options)
    return driver

def main(script_path: Path):
    """
    Main function to automate image generation for a given script file.
    """
    if not script_path.exists():
        print(f"❌ Lỗi: File kịch bản không tồn tại: {script_path}")
        sys.exit(1)

    with open(script_path, 'r', encoding='utf-8') as f:
        script_data = json.load(f)

    scenes = script_data.get("scenes", [])
    if not scenes:
        print("❌ Lỗi: Không tìm thấy 'scenes' trong file kịch bản.")
        sys.exit(1)

    # Determine the output project directory
    output_dir = get_project_path(script_data)

    driver = start_or_connect_to_chrome()
    wait = WebDriverWait(driver, 240) # Wait up to 4 minutes for image generation

    try:
        print("🚀 Đang mở Gemini...")
        driver.get("https://gemini.google.com/")

        print("⏳ Đang chờ trang Gemini tải xong...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, INPUT_BOX_SELECTOR)))
        print("✅ Trang đã sẵn sàng! Bắt đầu tự động hóa...")

        # --- Logic mới: Gửi 1 prompt, nhận tất cả ảnh ---

        # 2. Gửi prompt duy nhất
        scenes_json_string = json.dumps(scenes, ensure_ascii=False, indent=2)
        prompt = f"tạo ảnh dựa theo JSON scenes sau : {scenes_json_string}"
        
        input_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, INPUT_BOX_SELECTOR)))
        driver.execute_script("arguments[0].innerText = arguments[1];", input_box, prompt)
        time.sleep(1)
        submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SEND_BUTTON_SELECTOR)))
        submit_button.click()
        print("💬 Đã gửi prompt tổng hợp. Chờ Gemini tạo tất cả ảnh...")

        # 3. Chờ cho đến khi đủ số lượng ảnh được tạo
        expected_image_count = len(scenes)
        wait.until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, GENERATED_IMAGE_SELECTOR)) >= expected_image_count
        )
        print(f"✅ Đã phát hiện đủ {expected_image_count} ảnh.")

        # Thêm bước chờ cuối cùng: Đợi cho đến khi TẤT CẢ các ảnh mới đều có 'src' hợp lệ.
        # Điều này giải quyết race condition khi một số ảnh có src trước các ảnh khác.
        wait.until(
            lambda d: all(
                img.get_attribute("src") and img.get_attribute("src").startswith(('blob:', 'data:', 'http'))
                for img in d.find_elements(By.CSS_SELECTOR, GENERATED_IMAGE_SELECTOR)[-expected_image_count:]
            )
        )
        print("✅ Đã xác nhận tất cả ảnh sẵn sàng để tải về.")

        # 4. Lấy URL của tất cả ảnh
        image_elements = driver.find_elements(By.CSS_SELECTOR, GENERATED_IMAGE_SELECTOR)
        new_image_urls = [img.get_attribute("src") for img in image_elements[-expected_image_count:]]

        # 5. Mở từng URL trong tab mới để tải về
        main_tab_handle = driver.current_window_handle

        for i, image_url in enumerate(new_image_urls):
            download_image_in_new_tab(driver, wait, image_url, i, output_dir, main_tab_handle)

    except TimeoutException:
        print("❌ Đã hết thời gian chờ. Không thể tìm thấy phần tử trên trang.")
        print("   Vui lòng kiểm tra lại kết nối mạng hoặc giao diện Gemini có thể đã thay đổi.")
    except Exception as e:
        print(f"❌ Đã xảy ra lỗi không mong muốn: {e}")
    finally:
        # Cleanup is handled by atexit
        print("✅ Tác vụ hoàn tất.")

def download_image_in_new_tab(driver: webdriver.Chrome, wait: WebDriverWait, image_url: str, index: int, output_dir: Path, main_tab_handle: str):
    """Opens an image URL in a new tab, screenshots it, and closes the tab."""
    image_output_path = output_dir / f"{index + 1}.png"

    print(f"...Đang tải và ghi đè ảnh {index + 1}...")
    # Mở tab mới và chuyển sang nó
    driver.switch_to.new_window('tab')
    driver.get(image_url)

    # Chờ ảnh trong tab mới được tải và chụp lại
    img_in_new_tab = wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
    img_in_new_tab.screenshot(str(image_output_path))
    print(f"🖼️  Đã ghi đè ảnh thành công: {image_output_path.name}")

    # Đóng tab hiện tại và quay lại tab chính
    driver.close()
    driver.switch_to.window(main_tab_handle)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tự động tạo ảnh cho kịch bản video bằng Gemini.")
    parser.add_argument("script_file", type=Path, help="Đường dẫn đến file kịch bản JSON (ví dụ: data/1.json).")
    args = parser.parse_args()

    main(args.script_file)
