from flask import Flask, render_template, session
from utils.data_manage import *
from utils.extensions import db
from utils.auth_user import auth
from utils.auth_admin import admin_bp  
from utils.test_controller import test_bp
from utils.user_dashboard import dashboard_bp
from werkzeug.security import generate_password_hash
import os  
import click

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = "your_secret_key"
app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(test_bp, url_prefix="/tests")
app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
    os.path.join(basedir, 'list_tests.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
upload_path = os.path.join(basedir, 'static', 'audio')

os.makedirs(upload_path, exist_ok=True)

app.config['UPLOAD_FOLDER'] = upload_path
db.init_app(app)


@app.cli.command("create-admin")
def create_admin():
    """Tạo tài khoản admin từ dòng lệnh."""
    print("--- Tạo tài khoản Admin ---")

    # 1. Lấy thông tin an toàn
    email = click.prompt("Nhập Email")
    name = click.prompt("Nhập Tên")
    password = click.prompt(
        "Nhập Mật khẩu", hide_input=True, confirmation_prompt=True)

    try:
        # 2. Kiểm tra xem admin đã tồn tại chưa
        existing_admin = User.query.filter_by(email=email).first()
        if existing_admin:
            print(f"Lỗi: Email '{email}' đã tồn tại.")
            return

        # 3. Tạo user mới với role='admin'
        hashed_password = generate_password_hash(password)
        new_admin = User(
            name=name,
            email=email,
            password=hashed_password,
            role='admin'  # <-- ĐÂY LÀ ĐIỂM QUAN TRỌNG
        )

        db.session.add(new_admin)
        db.session.commit()

        print(f"✅ Đã tạo tài khoản admin thành công cho: {email}")

    except Exception as e:
        db.session.rollback()
        print(f"Lỗi khi tạo admin: {e}")

@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print(
            f"✅ All tables created successfully in {os.path.join(basedir, 'list_tests.db')}")
        
    app.run(debug=True)
