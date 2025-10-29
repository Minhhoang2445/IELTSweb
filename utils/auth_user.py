from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.users_manage import get_user_by_email, add_user, load_data
from utils.data_manage import Test, Passage
auth = Blueprint('auth', __name__, template_folder='templates',
                 static_folder='static')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        print("Người dùng vừa ấn nút Đăng ký!")
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']
        if password != confirm:
            flash("Mật khẩu không khớp!")
            return redirect(url_for('auth.register'))

        if not name or not email or not password:
            flash("Vui lòng điền đầy đủ thông tin.")
            return redirect(url_for('auth.register'))
        if len(password) < 8 or not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
            flash("Mật khẩu phải có ít nhất 8 ký tự, 1 chữ hoa và 1 số.")
            return redirect(url_for('auth.register'))
        add_user(name, email, password)
        flash("Đăng ký thành công! Hãy đăng nhập.")
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)
        if user and user['password'] == password:
            session['user_name'] = user['name']
            session['email'] = user['email']
            session['role'] = user.get('role', 'user')
            return redirect(url_for('index'))
        else:
            flash("Sai email hoặc mật khẩu.")
            return redirect(url_for('auth.login'))
        
    return render_template('login.html')


@auth.route('/logout')
def logout():
    session.pop('user_name', None)
    session.pop('email', None)
    session.pop('role', None)
    return redirect(url_for('index'))


