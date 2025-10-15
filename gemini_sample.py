import time
import subprocess
# import atexit # Tạm thời vô hiệu hóa để không tự động đóng trình duyệt
from selenium import webdriver
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

# Global variable to hold the chrome process so we can terminate it later
chrome_process = None

# def cleanup_chrome_process():
#     """Ensures the Chrome process is terminated when the script exits."""
#     global chrome_process
#     if chrome_process:
#         print("\n🧹 Dọn dẹp: Đang đóng tiến trình Chrome...")
#         chrome_process.terminate()
#         chrome_process.wait()
#         print("✅ Tiến trình Chrome đã được đóng.")

# Register the cleanup function to be called automatically on script exit
# atexit.register(cleanup_chrome_process)

def automate_gemini(prompt: str):
    """
    Sử dụng Selenium để tự động mở Gemini, gửi một prompt và lấy kết quả.
    """
    global chrome_process

    # --- Bước 1: Tự động khởi động Chrome ở chế độ debug ---
    chrome_exe_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data_dir = Path.cwd() / "chrome-profile"  # Dùng profile cục bộ trong thư mục dự án
    debugging_port = 9222
    chrome_command = [chrome_exe_path, f"--remote-debugging-port={debugging_port}", f'--user-data-dir={user_data_dir}']
    
    print(f"🚀 Đang khởi động Chrome ở chế độ debug trên port {debugging_port}...")
    chrome_process = subprocess.Popen(chrome_command)
    time.sleep(5)  # Đợi vài giây để Chrome khởi động hoàn toàn

    # --- Bước 2: Kết nối Selenium vào Chrome vừa khởi động ---
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debugging_port}")
    print("🔌 Đang kết nối Selenium vào trình duyệt...")
    driver = webdriver.Chrome(options=options)
    # Tăng thời gian chờ để xử lý các phản hồi dài hoặc mạng chậm
    wait = WebDriverWait(driver, 120)

    try:
        # 1. Truy cập vào trang Gemini
        print("🚀 Đang mở Gemini...")
        driver.get("https://gemini.google.com/")

        # 4. Chờ trang chính của Gemini tải xong.
        print("⏳ Đang chờ trang Gemini tải xong...")
        input_box = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, INPUT_BOX_SELECTOR))
        )
        print("✅ Trang đã sẵn sàng! Bắt đầu tự động hóa...")

        # Đếm số lượng câu trả lời hiện có trước khi gửi prompt mới
        initial_response_count = len(driver.find_elements(By.CSS_SELECTOR, MARKDOWN_RESPONSE_SELECTOR))

        # 5. Nhập prompt vào ô chat
        print(f"💬 Đang gửi prompt: '{prompt}'")
        input_box.send_keys(prompt)

        # 4. Tìm và nhấn nút "Gửi"
        # Nút gửi thường là một button chứa SVG
        submit_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SEND_BUTTON_SELECTOR))
        )
        submit_button.click()

        # 7. Chờ Gemini trả lời và lấy kết quả
        print("🤖 Gemini đang suy nghĩ... Vui lòng chờ.")
        
        # Chiến lược chờ đợi đáng tin cậy hơn:
        # 1. Chờ cho đến khi số lượng phần tử chứa câu trả lời tăng lên.
        wait.until(
            lambda driver: len(driver.find_elements(By.CSS_SELECTOR, MARKDOWN_RESPONSE_SELECTOR)) > initial_response_count
        )

        # 2. Chờ cho đến khi nút "Stop generating" biến mất.
        # Đây là dấu hiệu chắc chắn nhất cho thấy Gemini đã viết xong.
        # Selector này tìm một thẻ <button> có thuộc tính aria-label là "Stop generating".
        stop_generating_button_selector = 'button[aria-label="Stop generating"]'
        try:
            wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, stop_generating_button_selector)))
            print("✅ Gemini đã trả lời xong.")
        except TimeoutException:
            print("⚠️ Không tìm thấy nút 'Stop generating' hoặc đã hết thời gian chờ. Tiếp tục lấy kết quả.")

        # Thêm một bước chờ cuối cùng: Đợi cho đến khi phần tử markdown cuối cùng có nội dung.
        # Điều này giải quyết trường hợp race condition khi nút stop biến mất nhưng text chưa render xong.
        wait.until(
            lambda driver: driver.find_elements(By.CSS_SELECTOR, MARKDOWN_RESPONSE_SELECTOR)[-1].text.strip() != ""
        )
        print("✅ Đã xác nhận nội dung trả lời.")

        # --- DEBUGGING: Tạm dừng script để kiểm tra ---
        # Thay vì dùng alert (gây lỗi), chúng ta dùng input() trong terminal.
        # Script sẽ dừng lại ở đây cho đến khi bạn nhấn Enter trong cửa sổ terminal.
        input("⏸️  Script đã tạm dừng. Vui lòng kiểm tra màn hình trình duyệt và nhấn Enter trong terminal này để tiếp tục...")

        # Lấy tất cả các phần tử chứa câu trả lời và chọn cái cuối cùng
        response_elements = driver.find_elements(By.CSS_SELECTOR, MARKDOWN_RESPONSE_SELECTOR)
        if not response_elements:
            raise Exception("Không tìm thấy phần tử chứa câu trả lời.")
            
        latest_response_text = response_elements[-1].text
        
        print("\n--- KẾT QUẢ TỪ GEMINI ---")
        print(latest_response_text)
        print("-------------------------\n")

        return latest_response_text

    except TimeoutException:
        print("❌ Đã hết thời gian chờ. Không thể tìm thấy phần tử trên trang.")
        print("   Vui lòng kiểm tra lại kết nối mạng hoặc giao diện Gemini có thể đã thay đổi.")
    except Exception as e:
        print(f"❌ Đã xảy ra lỗi không mong muốn: {e}")
    finally:
        # Trình duyệt sẽ không tự động đóng để bạn có thể gỡ lỗi.
        print("✅ Tác vụ hoàn tất. Trình duyệt vẫn mở để kiểm tra.")


if __name__ == "__main__":
    # Bạn có thể thay đổi prompt ở đây
    my_prompt = "Hãy viết một bài thơ ngắn về lập trình bằng Python."
    automate_gemini(my_prompt)
