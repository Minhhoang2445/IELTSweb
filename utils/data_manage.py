# test_manage.py
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

    # 'fill_in_blank', 'multiple_choice', 'true_false_not_given', 'yes_no_not_given', 'matching'
    question_type = db.Column(db.String(50), nullable=False)
    # Dải câu hỏi mà khối này áp dụng (VÍ DỤ: "1-5", "6-7", "8")
    question_range = db.Column(db.String(10), nullable=False, index=True)

    # Câu hỏi/hướng dẫn chính cho CẢ KHỐI
    # Ví dụ: "Điền vào chỗ trống..."
    # Hoặc: "Nối các tiêu đề (i-v) với các đoạn văn (A-E)"
    instruction_text = db.Column(db.Text, nullable=False)

    # Dùng cho các loại câu hỏi ĐƠN GIẢN (simple, multiple_choice)
    # Ví dụ: "True" (cho T/F/NG)
    # Hoặc: "A" (cho Multiple Choice)
    # *Sẽ là NULL cho loại 'matching'*
    simple_answer = db.Column(db.Text, nullable=True)

    # (QUAN TRỌNG NHẤT) Dữ liệu JSON linh hoạt
    # Dùng để lưu trữ mọi thứ khác
    # - multiple_choice: `{"options": ["A. ...", "B. ..."]}`
    # - matching:
    #   `{
    #       "matching_items": ["i. ...", "ii. ..."],
    #       "sub_questions": [
    #           {"query": "Paragraph A", "answer": "ii"},
    #           {"query": "Paragraph B", "answer": "i"}
    #       ]
    #   }`
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


# Thêm class này vào file utils/test_manage.py của bạn

class UserAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Liên kết đến lần làm bài cụ thể (bảng UserTestResult)
    user_test_result_id = db.Column(db.Integer, db.ForeignKey(
        'user_test_result.id'), nullable=False)

    # Liên kết đến khối câu hỏi (bảng QuestionBlock)
    question_block_id = db.Column(db.Integer, db.ForeignKey(
        'question_block.id'), nullable=False)

    # (QUAN TRỌNG) Chỉ số câu hỏi con (nếu có)
    # Dùng để xác định câu trả lời này là cho câu hỏi con nào trong một khối matching
    # Ví dụ: Câu 2 trong khối 1-5 -> sub_question_index = 1 (vì index bắt đầu từ 0)
    # Sẽ là 0 hoặc NULL cho các câu hỏi đơn giản (Fill, MC, T/F/NG)
    sub_question_index = db.Column(db.Integer, nullable=True, default=0)

    # Câu trả lời thực tế của người dùng
    user_answer = db.Column(db.Text, nullable=False)

    # (Tùy chọn) Cột này có thể tính toán khi chấm bài và lưu lại
    is_correct = db.Column(db.Boolean, nullable=True)

    # Relationship để dễ truy vấn ngược
    test_result = db.relationship('UserTestResult', backref=db.backref(
        'answers', lazy='dynamic'))  # 'dynamic' tốt hơn cho list dài
    question_block = db.relationship(
        'QuestionBlock', backref=db.backref('user_answers', lazy='dynamic'))
    
