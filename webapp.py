from flask import Flask, render_template, session
from utils.data_manage import *
from utils.extensions import db
from utils.auth_user import auth
from utils.auth_admin import admin_bp  
from utils.test_controller import test_bp
import os  

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = "your_secret_key"
app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(test_bp, url_prefix="/tests")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
    os.path.join(basedir, 'list_tests.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print(
            f"✅ All tables created successfully in {os.path.join(basedir, 'list_tests.db')}")
    app.run(debug=True)
