from flask import Blueprint, Flask, abort, json, render_template, session
from utils.data_manage import *
from utils.extensions import db

test_bp = Blueprint(
    'test', __name__, template_folder='templates', static_folder='static')


@test_bp.route('/choose_test/<category>')
def choose_test(category):
    valid_category = category.capitalize()
    latest_reading_tests = Test.query.filter_by(
        category='Reading').order_by(Test.id.desc()).limit(3).all()
    latest_listening_tests = Test.query.filter_by(
        category='Listening').order_by(Test.id.desc()).limit(3).all()
    start_test_endpoint = f"{valid_category.lower()}_test_page"
    tests_in_category = Test.query.filter_by(
        category=valid_category).all()
    return render_template(
        'choose_test.html',
        # Truyền category đã chuẩn hóa ('Reading' hoặc 'Listening')
        current_category=valid_category,
        tests=tests_in_category,          # Danh sách test chính để hiển thị
        latest_reading=latest_reading_tests,    # Cho dropdown Reading sidebar
        latest_listening=latest_listening_tests,  # Cho dropdown Listening sidebar
        start_test_endpoint=start_test_endpoint  # Tên route để bắt đầu làm bài
    )


@test_bp.route('/reading_page/<int:test_id>')  # URL sẽ là /reading_page/1
def reading_test_page(test_id):
    # Lấy dữ liệu Test, bao gồm cả passages và question_blocks liên quan
    test = Test.query.options(
        db.joinedload(Test.passages).joinedload(Passage.question_blocks)
    ).get_or_404(test_id)

    # Đảm bảo đây là bài Reading
    if test.category != 'Reading':
        abort(404)
    # Xử lý trước extra_data để template dễ dùng hơn
    for passage in test.passages:
        for block in passage.question_blocks:
            if block.extra_data:
                try:
                    # Tạo thuộc tính mới để không ghi đè extra_data gốc
                    block.extra_data_dict = json.loads(block.extra_data)
                except json.JSONDecodeError:
                    block.extra_data_dict = {}
            else:
                block.extra_data_dict = {}

    # Render template trang làm bài
    return render_template('reading_test.html', test=test)


@test_bp.route('/listening_page/<int:test_id>')  # URL sẽ là /listening_page/1
def listening_test_page(test_id):
    """Route to display the actual Listening test page."""
    test = Test.query.options(
        db.joinedload(Test.passages).joinedload(Passage.question_blocks)
    ).get_or_404(test_id)

    if test.category != 'Listening':
        abort(404)

    question_blocks = []
    if test.passages:
        question_blocks = test.passages[0].question_blocks
        question_blocks.sort(key=lambda block: int(
            block.question_range.split('-')[0]))

    for block in question_blocks:
        if block.extra_data:
            try:
                block.extra_data_dict = json.loads(block.extra_data)
            except json.JSONDecodeError:
                block.extra_data_dict = {}
        else:
            block.extra_data_dict = {}

    # Giả sử bạn sẽ thêm trường 'audio_url' vào model Test
    # audio_url = test.audio_url if hasattr(test, 'audio_url') and test.audio_url else "https://placehold.co/audio/mp3"
    audio_url = "https://placehold.co/audio/mp3"  # Placeholder

    return render_template('listening_test.html',
                           test=test,
                           question_blocks=question_blocks,
                           audio_url=audio_url)
