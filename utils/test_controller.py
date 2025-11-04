from flask import Blueprint, Flask, abort, json, render_template, session, request, flash, redirect, url_for
from utils.data_manage import *
from utils.extensions import db
import json

test_bp = Blueprint(
    'test', __name__, template_folder='templates', static_folder='static')


def get_sort_key(block):
    """
    Lấy số bắt đầu của question_range để sắp xếp.
    """
    try:
        start_num_str = block.question_range.split('-')[0].strip()
        return int(start_num_str)
    except:
        return 0

# (MỚI) HÀM HELPER ĐỂ "GIẢI NÉN" DẢI CÂU HỎI


def parse_range(range_str):
    """
    Chuyển đổi '1-5' thành [1, 2, 3, 4, 5], '6' thành [6], '13-14' thành [13, 14].
    """
    try:
        if '-' in range_str:
            parts = range_str.split('-')
            start = int(parts[0].strip())
            end = int(parts[1].strip())
            return list(range(start, end + 1))
        else:
            # Nếu chỉ là một số (ví dụ: '6')
            return [int(range_str.strip())]
    except:
        # Fallback nếu range_str không hợp lệ
        return [range_str]

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
    if 'email' not in session:
        flash("Bạn cần đăng nhập để làm test.", "error")
        return redirect(url_for('auth.login'))
    test = Test.query.options(
       db.joinedload(Test.passages).joinedload(Passage.question_blocks)
       ).get_or_404(test_id)

    if test.category != 'Reading':
        abort(404)

    # Xử lý JSON VÀ SẮP XẾP VÀ GIẢI NÉN RANGE
    for passage in test.passages:
        if passage.question_blocks:
            passage.question_blocks.sort(key=get_sort_key) # Sắp xếp

        for block in passage.question_blocks:
            # Xử lý JSON (giữ nguyên)
            if block.extra_data:
                try:
                    block.extra_data_dict = json.loads(block.extra_data)
                except json.JSONDecodeError:
                    block.extra_data_dict = {}
            else:
                block.extra_data_dict = {}

            # (MỚI) Gọi hàm parse_range để tạo list số câu hỏi
            block.question_numbers = parse_range(block.question_range)
    return render_template('reading_test.html', test=test)


@test_bp.route('/listening_page/<int:test_id>')  # URL sẽ là /listening_page/1
def listening_test_page(test_id):
    if 'email' not in session:
        flash("Bạn cần đăng nhập để làm test.", "error")
        return redirect(url_for('auth.login'))

    test = Test.query.options(
        db.joinedload(Test.passages).joinedload(Passage.question_blocks)
    ).get_or_404(test_id)

    if test.category != 'Listening':
        abort(404)

    # (SỬA) Gom câu hỏi từ TẤT CẢ passages (sections)
    all_question_blocks = []
    if test.passages:
        for passage in test.passages:
            all_question_blocks.extend(passage.question_blocks)

        # Sắp xếp lại toàn bộ danh sách
        all_question_blocks.sort(key=get_sort_key)

    # Xử lý JSON (bây giờ dùng all_question_blocks)
    for block in all_question_blocks:
        if block.extra_data:
            try:
                block.extra_data_dict = json.loads(block.extra_data)
            except json.JSONDecodeError:
                block.extra_data_dict = {}
        else:
            block.extra_data_dict = {}
   
    audio_url = test.audio_url if hasattr(test, 'audio_url') and test.audio_url else ""

    return render_template('listening_test.html',
                           test=test,
                           question_blocks=all_question_blocks,
                           audio_url=audio_url)


@test_bp.route('/submit_reading/<int:test_id>', methods=['POST'])
def submit_reading_answers(test_id):
    if 'email' not in session:
        flash("Bạn cần đăng nhập để nộp bài.", "error")
        return redirect(url_for('auth.login'))
    current_user = User.query.filter_by(email=session['email']).first()
    if not current_user:
        flash("Lỗi xác thực người dùng.", "error")
        return redirect(url_for('auth.login'))
    user_id = current_user.id

    user_answers_raw = request.form
    test = Test.query.options(
        db.joinedload(Test.passages).joinedload(Passage.question_blocks)
    ).get_or_404(test_id)

    # 3. Xây dựng bản đồ đáp án đúng
    correct_answers_map = {}
    total_questions_count = 0

    for passage in test.passages:
        for block in passage.question_blocks:
            extra_data_dict = json.loads(
                block.extra_data) if block.extra_data else {}

            # Case 1: Câu hỏi nhóm (Matching, v.v.)
            if 'sub_questions' in extra_data_dict:
                for i, sub_q in enumerate(extra_data_dict['sub_questions']):
                    correct_answers_map.setdefault(block.id, {})[
                        i] = sub_q['answer']
                    total_questions_count += 1

            # Case 2: (SỬA) Câu hỏi đơn (MC, Fill, T/F)
            else:
                # Chỉ có 1 câu trả lời, lưu ở sub_index = 0
                correct_answers_map.setdefault(block.id, {})[
                    0] = block.simple_answer
                total_questions_count += 1  # Chỉ đếm là 1 câu hỏi

    # 4. Chấm điểm và Chuẩn bị lưu
    score = 0
    answers_to_save = []

    new_test_result = UserTestResult(
        user_id=user_id,
        test_id=test_id,
        score=0,
        taken_at=datetime.utcnow()
    )
    db.session.add(new_test_result)
    db.session.flush()

    for key, user_ans_val in user_answers_raw.items():
        if key.startswith('answer_'):
            try:
                parts = key.split('_')
                block_id = int(parts[1])
                sub_index = int(parts[2])
            except (IndexError, ValueError):
                continue

            user_ans_val = user_ans_val.strip()

            correct_ans_val = correct_answers_map.get(
                block_id, {}).get(sub_index)

            is_correct = False
            if user_ans_val and correct_ans_val:
                # (SỬA) Logic so sánh
                # Nếu là câu hỏi đơn (Fill 1-5), đáp án đúng có thể là "ans1, ans2, ans3"
                # Logic này cần được cải thiện sau, tạm thời so sánh toàn bộ
                if user_ans_val.lower() == correct_ans_val.lower():
                    is_correct = True
                    score += 1

            new_answer = UserAnswer(
                user_test_result_id=new_test_result.id,
                question_block_id=block_id,
                sub_question_index=sub_index,
                user_answer=user_ans_val,
                is_correct=is_correct
            )
            answers_to_save.append(new_answer)

    # 5. Lưu vào Database
    db.session.add_all(answers_to_save)
    new_test_result.score = score
    db.session.commit()

    return redirect(url_for('test.show_test_result', result_id=new_test_result.id))


@test_bp.route('/submit_listening/<int:test_id>', methods=['POST'])
def submit_listening_answers(test_id):
    # Logic 1-5 giống hệt submit_reading_answers
    # 1. Xác thực người dùng
    if 'email' not in session:
        flash("Bạn cần đăng nhập để nộp bài.", "error")
        return redirect(url_for('auth.login'))
    current_user = User.query.filter_by(email=session['email']).first()
    if not current_user:
        flash("Lỗi xác thực người dùng.", "error")
        return redirect(url_for('auth.login'))
    user_id = current_user.id

    # 2. Lấy dữ liệu
    user_answers_raw = request.form
    test = Test.query.options(
        db.joinedload(Test.passages).joinedload(Passage.question_blocks)
    ).get_or_404(test_id)

    # 3. Xây dựng bản đồ đáp án đúng (Correct Answer Map)
    correct_answers_map = {}
    total_questions_count = 0

    # Logic lấy đáp án đúng là như nhau cho cả Reading và Listening
    for passage in test.passages:
        for block in passage.question_blocks:
            extra_data_dict = json.loads(
                block.extra_data) if block.extra_data else {}
            if 'sub_questions' in extra_data_dict:
                for i, sub_q in enumerate(extra_data_dict['sub_questions']):
                    correct_answers_map.setdefault(block.id, {})[
                        i] = sub_q['answer']
                    total_questions_count += 1
            else:
                correct_answers_map.setdefault(block.id, {})[
                    0] = block.simple_answer
                total_questions_count += 1

    # 4. Chấm điểm và Chuẩn bị lưu
    score = 0
    answers_to_save = []
    new_test_result = UserTestResult(
        user_id=user_id, test_id=test_id, score=0, taken_at=datetime.utcnow()
    )
    db.session.add(new_test_result)
    db.session.flush()

    for key, user_ans_val in user_answers_raw.items():
        if key.startswith('answer_'):
            try:
                parts = key.split('_')
                block_id = int(parts[1])
                sub_index = int(parts[2])
            except (IndexError, ValueError):
                continue
            user_ans_val = user_ans_val.strip()
            correct_ans_val = correct_answers_map.get(
                block_id, {}).get(sub_index)
            is_correct = False
            if user_ans_val and correct_ans_val:
                if user_ans_val.lower() == correct_ans_val.lower():
                    is_correct = True
                    score += 1
            new_answer = UserAnswer(
                user_test_result_id=new_test_result.id,
                question_block_id=block_id,
                sub_question_index=sub_index,
                user_answer=user_ans_val,
                is_correct=is_correct
            )
            answers_to_save.append(new_answer)

    # 5. Lưu vào Database
    db.session.add_all(answers_to_save)
    new_test_result.score = score
    db.session.commit()

    return redirect(url_for('test.show_test_result', result_id=new_test_result.id))
# -----------------------------------------------------------------
# (MỚI) ROUTE HIỂN THỊ KẾT QUẢ (ĐÃ SỬA)
# -----------------------------------------------------------------


@test_bp.route('/test_result/<int:result_id>')
def show_test_result(result_id):
    
    result = UserTestResult.query.get_or_404(result_id)

    current_user = User.query.filter_by(email=session['email']).first()
    if not current_user or (result.user_id != current_user.id and session.get('role') != 'admin'):
        return redirect(url_for('index'))

    # Xây dựng lại bản đồ đáp án đúng
    correct_answers_map = {}
    total_questions = 0
    test = result.test
    
    # Tạo một dict map block_id -> block để dễ tra cứu
    all_blocks = {} 
    
    for passage in test.passages:
        if passage.question_blocks:
             passage.question_blocks.sort(key=get_sort_key)
        for block in passage.question_blocks:
            all_blocks[block.id] = block # Thêm block vào map
            extra_data_dict = json.loads(block.extra_data) if block.extra_data else {}
            block.extra_data_dict = extra_data_dict # Gán lại để dùng sau
            
            if 'sub_questions' in extra_data_dict:
                for i, sub_q in enumerate(extra_data_dict['sub_questions']):
                    correct_answers_map.setdefault(block.id, {})[i] = sub_q['answer']
                    total_questions += 1
            else:
                correct_answers_map.setdefault(block.id, {})[0] = block.simple_answer
                total_questions += 1
    
    # Lấy câu trả lời chi tiết của user và sắp xếp
    answers_with_details = []
    # Lấy các câu trả lời của user cho lần làm bài này
    user_answers = UserAnswer.query.filter_by(user_test_result_id=result.id).all()
    
    # Sắp xếp câu trả lời của user DỰA TRÊN THỨ TỰ CỦA QUESTION BLOCK
    user_answers.sort(key=lambda ans: (
        get_sort_key(all_blocks.get(ans.question_block_id, ans)), # Sắp xếp theo block
        ans.sub_question_index # Sắp xếp theo câu con
    ))

    for answer in user_answers:
        block = all_blocks.get(answer.question_block_id)
        if not block:
            continue # Bỏ qua nếu không tìm thấy block (lỗi dữ liệu)
            
        block_id = answer.question_block_id
        sub_index = answer.sub_question_index
        correct_ans = correct_answers_map.get(block_id, {}).get(sub_index, "N/A")
        
        # (SỬA) Lấy thông tin chi tiết cho template
        query_label = f"Câu hỏi {block.question_range}" # Mặc định
        instruction = block.instruction_text
        options = []
        
        try:
            if 'sub_questions' in block.extra_data_dict:
                query_label = block.extra_data_dict['sub_questions'][sub_index]['query']
            elif block.question_type == 'multiple_choice':
                options = block.extra_data_dict.get('options', [])
                query_label = block.instruction_text # Câu hỏi MC là instruction
            else: # Fill, T/F
                query_label = f"Câu {parse_range(block.question_range)[sub_index]}"
        except Exception:
            pass 
        
        answers_with_details.append({
            'query_label': query_label, # Nhãn câu hỏi (Câu 1, 14. reference...)
            'instruction': instruction, # Hướng dẫn chung (Which section contains...)
            'question_type': block.question_type,
            'user_answer': answer.user_answer,
            'correct_answer': correct_ans,
            'is_correct': answer.is_correct
        })
    
    # Tính điểm Band (Logic đơn giản)
    score = result.score
    band_score = 1.0
    if total_questions == 40: 
        if score >= 39: band_score = 9.0
        elif score >= 37: band_score = 8.5
        elif score >= 35: band_score = 8.0
        elif score >= 32: band_score = 7.5
        elif score >= 30: band_score = 7.0
        elif score >= 26: band_score = 6.5
        elif score >= 23: band_score = 6.0
        elif score >= 19: band_score = 5.5
        elif score >= 15: band_score = 5.0
        elif score >= 13: band_score = 4.5
        elif score >= 10: band_score = 4.0
        else: band_score = 3.5 
    
    return render_template('test_result.html', 
                           result=result, 
                           answers=answers_with_details, # Gửi dữ liệu chi tiết
                           total_questions=total_questions,
                           band_score=band_score)
