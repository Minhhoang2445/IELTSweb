import csv
import os

# Đường dẫn tuyệt đối đến file CSV (dựa trên vị trí file data_manage.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, '..', 'data', 'users.csv')



def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_data(users):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['name', 'email', 'password', 'role']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(users)


def add_user(name, email, password):
    users = load_data()
    users.append({'name': name, 'email': email, 'password': password, 'role': 'user'})
    save_data(users)


def get_user_by_email(email):
    users = load_data()
    for user in users:
        if user['email'] == email:
            return user
    return None


