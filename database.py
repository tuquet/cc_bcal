from flask_sqlalchemy import SQLAlchemy

# Khởi tạo SQLAlchemy mà không cần app instance để tránh circular imports
db = SQLAlchemy()
