# Nexo API

A Flask-based API backend for a video creation pipeline, managing scripts, assets, background jobs, and generating video projects for CapCut.

## Features

- **RESTful API**: Manage scripts, prompts, and background jobs.
- **Structured Logging**: Using `structlog` for machine-readable logs (JSON in production).
- **Database Migrations**: Using `Flask-Migrate` to manage database schema changes.
- **Background Tasks**: A Redis-based queue system to handle long-running tasks like video transcription, image generation, and video processing.
- **API Documentation**: Automatic Swagger UI generation with `Flasgger`.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+**
- **Redis**: Required for the background task queue.
- **FFmpeg**: Required by `whisperx` for audio processing. Make sure it's installed and available in your system's PATH.

## 1. Setup

Follow these steps to get your development environment set up.

### a. Clone the Repository

```bash
git clone <your-repository-url>
cd nexo-api
```

### b. Create and Activate a Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies.

```bash
# For Windows
python -m venv .venv
.venv\Scripts\activate

# For macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### c. Install Dependencies

Install all required Python packages from `requirements.txt`.

```bash
pip install -r requirements.txt
```

## 2. Configuration

The application uses environment variables for configuration, which are loaded from `.env` files.

### a. Flask Environment

The project includes a `.flaskenv` file which is automatically loaded by Flask. It sets essential variables for the Flask CLI:

```ini
# .flaskenv
FLASK_APP=run.py
FLASK_DEBUG=1
```

### b. Application Settings

Create a `settings.json` file in the project root to configure the main project folder.

```json
// settings.json
{
  "project_folder": "C:\\Path\\To\\Your\\Video\\Projects"
}
```

## 3. Database Setup

The project uses `Flask-Migrate` to handle database schema migrations.

1.  **Initialize the migration repository** (run this only the first time):
    ```bash
    python -m flask db init
    ```
2.  **Generate a migration script** whenever you change your models (`app/models/*.py`):
    ```bash
    python -m flask db migrate -m "Your descriptive message about the changes"
    ```
3.  **Apply the migration** to update the database:
    ```bash
    python -m flask db upgrade
    ```

## 4. Running the Application

To start the Flask development server, run:

```bash
python run.py
```

You will see output similar to this:

```
✅ Logging configured in development (console) mode with level: INFO
🚀 API docs available at: http://127.0.0.1:5000/api/docs/
 * Running on http://127.0.0.1:5000
```

- The API server is running at `http://127.0.0.1:5000`.
- The interactive API documentation (Swagger UI) is available at `http://127.0.0.1:5000/api/docs/`.

## 5. Seed dữ liệu (CLI)

Dự án có các lệnh Flask CLI để seed dữ liệu mẫu (prompts, scripts). Các lệnh này thuận tiện để khởi tạo dữ liệu demo hoặc trong môi trường phát triển.

- `flask seed-prompts`
    - Mục đích: nạp các prompt từ thư mục ví dụ (`app/api/examples`) hoặc từ thư mục tuỳ chọn.
    - Tuỳ chọn:
        - `--prompts-dir <path>`: thư mục chứa file `.json` (với keys `name`/`content`) hoặc file văn bản `.md` (tên file -> `name`, nội dung -> `content`).
        - `--create-tables`: nếu bật, sẽ gọi `db.create_all()` để tạo bảng nếu chưa tồn tại.
    - Ví dụ:

```powershell
$env:FLASK_APP='run.py'
flask seed-prompts --create-tables
# hoặc chỉ định thư mục
flask seed-prompts --prompts-dir D:\path\to\prompts
```

- `flask seed-scripts`
    - Mục đích: nạp các script mẫu từ file `.json` trong một thư mục (mặc định `app/api/examples`).
    - Tuỳ chọn:
        - `--scripts-dir <path>`: thư mục chứa file `.json` mô tả script.
        - `--create-tables`: tương tự, tạo bảng nếu cần.
    - Ví dụ:

```powershell
$env:FLASK_APP='run.py'
flask seed-scripts --create-tables
# hoặc
flask seed-scripts --scripts-dir D:\path\to\examples
```

Ghi chú:
- `--create-tables` an toàn khi gọi trên hầu hết DB dev (nó gọi `db.create_all()`); nếu bạn muốn tránh gọi tạo bảng khi không cần, tôi có thể cập nhật seeder để kiểm tra tồn tại bảng trước khi gọi `create_all()`.
