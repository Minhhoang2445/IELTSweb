from datetime import datetime
from utils.extensions import db
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')


class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    audio_url = db.Column(db.String(200), nullable=True)
    passages = db.relationship('Passage', backref='test',
                           cascade="all, delete-orphan")

class Passage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    passage_text = db.Column(db.Text, nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    question_blocks = db.relationship('QuestionBlock', backref='passage', cascade="all, delete-orphan")

class QuestionBlock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    passage_id = db.Column(db.Integer, db.ForeignKey(
        'passage.id'), nullable=False)
    question_type = db.Column(db.String(50), nullable=False)
    question_range = db.Column(db.String(10), nullable=False, index=True)
    instruction_text = db.Column(db.Text, nullable=False) 
    simple_answer = db.Column(db.Text, nullable=True)
    extra_data = db.Column(db.Text, nullable=True)  # Lưu trữ JSON string


class UserTestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    taken_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship(
        'User', backref=db.backref('test_results', lazy=True))
    test = db.relationship(
        'Test', backref=db.backref('user_results', lazy=True))

class UserAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_test_result_id = db.Column(db.Integer, db.ForeignKey(
        'user_test_result.id'), nullable=False)
    question_block_id = db.Column(db.Integer, db.ForeignKey(
        'question_block.id'), nullable=False)
    sub_question_index = db.Column(db.Integer, nullable=True, default=0)
    user_answer = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=True)
    test_result = db.relationship('UserTestResult', backref=db.backref(
        'answers', lazy='dynamic')) 
    question_block = db.relationship(
        'QuestionBlock', backref=db.backref('user_answers', lazy='dynamic'))
    
