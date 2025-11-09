import csv
import os
from utils.extensions import db
from utils.data_manage import User
from werkzeug.security import generate_password_hash, check_password_hash




def load_data():
    try:
        return User.query.all()
    except Exception as e:
        print(f"Lỗi khi tải user từ DB: {e}")
        return []
        

def add_user(name, email, password):
    try:
        hashed_password = generate_password_hash(password)

        new_user = User(
            name=name,
            email=email,
            password=hashed_password,
            role='user'  
        )

        db.session.add(new_user)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"Lỗi khi thêm user vào DB: {e}")
        raise e



def get_user_by_email(email):
    try:
        return User.query.filter_by(email=email).first()
    except Exception as e:
        print(f"Lỗi khi tìm user bằng email: {e}")
        return None

def check_user_password(email, password):
    user = get_user_by_email(email)
    if user and check_password_hash(user.password, password):
        return True
    return False
