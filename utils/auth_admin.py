from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
# (SỬA) Import model từ đúng file 'test_manage'
from utils.data_manage import Test, Passage, QuestionBlock, User
# Giả sử hàm này vẫn tồn tại để load user CSV
from utils.users_manage import load_data
import json
from utils.extensions import db
# Thêm import để xử lý tên file an toàn
from werkzeug.utils import secure_filename
import os  # Thêm import os
import json 
admin_bp = Blueprint(
    'admin', __name__, template_folder='templates', static_folder='static')

# --- Cấu hình cho Upload ---
ALLOWED_EXTENSIONS = {'mp3'}  # Chỉ cho phép mp3


def allowed_file(filename):
    """Kiểm tra xem file có đuôi mở rộng hợp lệ không."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -----------------------------------------------------------------
# HÀM HELPER: "PHÂN LOẠI CÂU HỎI VÀ LƯU TEST" (Đã cập nhật)
# -----------------------------------------------------------------


def parse_and_save_test(form_data, files_data):
    """
    Hàm này nhận request.form và request.files, phân loại, xác thực, xử lý file upload và lưu vào DB.
    Trả về (True, "Thông báo thành công") hoặc (False, "Thông báo lỗi").
    """
    # (Optional Debug Print)
    # print("\n--- DEBUG: Bắt đầu parse_and_save_test ---")
    # pprint.pprint({"form_data_keys": list(form_data.keys()), "files_data_keys": list(files_data.keys())})

    try:
        category = form_data.get('category')
        test_title = form_data.get('title')
        if not test_title or not category:
            return (False, "Lỗi: Thiếu Tên đề thi hoặc Loại.")

        saved_audio_url = None
        # --- Xử lý file upload NẾU là Listening ---
        if category == 'Listening':
            if 'audio_file' not in files_data or files_data['audio_file'].filename == '':
                return (False, "Lỗi: Vui lòng chọn file audio (.mp3) cho bài Listening.")
            file = files_data['audio_file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                save_path = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(save_path)
                    saved_audio_url = url_for(
                        'static', filename=f'audio/{filename}')
                except Exception as save_err:
                    # Log error properly in production
                    return (False, f"Lỗi nghiêm trọng khi lưu file audio: {save_err}")
            else:
                return (False, "Lỗi: Loại file audio không hợp lệ (chỉ chấp nhận .mp3).")
        # --- Kết thúc xử lý file upload ---

        # 1. Gom dữ liệu câu hỏi (Logic cũ)
        passages_data = {}
        for key, value in form_data.items():
            value_cleaned = value.strip() if isinstance(value, str) else value
            if not value_cleaned and 'passage' not in key and 'text' not in key:
                continue

            if key.startswith('passages['):
                try:
                    parts = key.replace(']', '').split('[')
                    p_id = parts[1]
                    if p_id not in passages_data:
                        passages_data[p_id] = {'questions': {}}

                    if len(parts) == 3 and parts[2] == 'text':
                        # Giữ nguyên whitespace
                        passages_data[p_id]['text'] = value
                        continue

                    if len(parts) >= 5 and parts[2] == 'questions':
                        q_id = parts[3]
                        if q_id not in passages_data[p_id]['questions']:
                            passages_data[p_id]['questions'][q_id] = {}

                        current_level = passages_data[p_id]['questions'][q_id]
                        for i, sub_part in enumerate(parts[4:-1]):
                            if sub_part not in current_level:
                                 current_level[sub_part] = {}
                            current_level = current_level[sub_part]
                        current_level[parts[-1]] = value_cleaned
                except (IndexError, KeyError) as e_parse:
                    # Log warning properly in production
                    pass

        # 2. Lọc và Xác thực dữ liệu đã gom (Logic cũ)
        valid_passages_with_questions = []
        total_valid_questions = 0
        MAX_QUESTIONS_PER_TEST = 40

        for p_id, p_data in passages_data.items():
            passage_text_value = p_data.get('text', '')
            passage_text_cleaned_for_check = passage_text_value.strip()

            if category == 'Reading' and not passage_text_cleaned_for_check:
                continue

            valid_question_blocks_in_passage = []
            for q_id, q_data in p_data.get('questions', {}).items():
                query_value = q_data.get('query')
                range_value = q_data.get('question_range')
                if query_value and range_value:
                    valid_question_blocks_in_passage.append(q_data)
                    total_valid_questions += 1

            if valid_question_blocks_in_passage:
                stored_passage_text = passage_text_value if category == 'Reading' else f"Listening Section {p_id} Data"
                valid_passages_with_questions.append(( {'text': stored_passage_text}, valid_question_blocks_in_passage) )

        # 3. Kiểm tra số lượng tổng (Logic cũ)
        if not valid_passages_with_questions:
            return (False, "Lỗi: Đề thi phải có ít nhất 1 Passage/Section chứa câu hỏi hợp lệ.")
        if total_valid_questions > MAX_QUESTIONS_PER_TEST:
            return (False, f"Lỗi: Tổng số câu hỏi hợp lệ ({total_valid_questions}) vượt quá giới hạn {MAX_QUESTIONS_PER_TEST}.")

        # 4. Lưu Test (ĐÃ SỬA)
        # Chỉ thêm audio_url nếu là Listening VÀ saved_audio_url có giá trị
        if category == 'Listening' and saved_audio_url:
            new_test = Test(title=test_title, category=category, audio_url=saved_audio_url)
        else:
            # Nếu là Reading hoặc Lưu Listening thất bại, không thêm audio_url
            new_test = Test(title=test_title, category=category)
    
        db.session.add(new_test)
        db.session.flush()  # Lấy ID

        # 5. Lặp qua các PASSAGE HỢP LỆ và câu hỏi của chúng để lưu (Logic cũ)
        for i, (passage_info, valid_blocks) in enumerate(valid_passages_with_questions):
            new_passage = Passage(
                passage_text=passage_info['text'],
                test_id=new_test.id
            )
            db.session.add(new_passage)
            db.session.flush()  # Lấy ID

            for j, block_data in enumerate(valid_blocks):
                q_type = block_data.get('type')
                extra_data_dict = {}

                # Xử lý extra_data (logic cũ)
                if q_type == 'multiple_choice':
                    options_dict = block_data.get('options', {})
                    valid_options = [opt for opt in options_dict.values() if opt]
                    if valid_options:
                        extra_data_dict['options'] = valid_options
                elif q_type == 'matching':
                    items_text = block_data.get('matching_items', '')
                    items_list = [item.strip() for item in items_text.splitlines() if item.strip()]
                    if items_list:
                        extra_data_dict['matching_items'] = items_list
                    sub_q_dict = block_data.get('sub_questions', {})
                    valid_sub_q = [sq for sq in sub_q_dict.values() if sq.get('query') and sq.get('answer')]
                    if valid_sub_q:
                        extra_data_dict['sub_questions'] = valid_sub_q

                new_block = QuestionBlock(
                    passage_id=new_passage.id,
                    question_type=q_type,
                    question_range=block_data.get('question_range'),
                    instruction_text=block_data.get('query'),
                    simple_answer=block_data.get('answer'),
                    extra_data=json.dumps(extra_data_dict) if extra_data_dict else None
                )
                db.session.add(new_block)

        # 6. Lưu tất cả vào DB (Logic cũ)
        db.session.commit()
        success_message = f"Đã thêm đề thi '{new_test.title}' với {len(valid_passages_with_questions)} passage/section và tổng cộng {total_valid_questions} câu hỏi!"
        return (True, success_message)

    except Exception as e:
        db.session.rollback()
        # Log lỗi hoặc in traceback để debug
        # traceback.print_exc()
        error_msg = f"Có lỗi xảy ra trong quá trình xử lý: {str(e)[:150]}..."
        return (False, error_msg)

@admin_bp.route('/delete_test/<int:test_id>', methods=['GET'])
def delete_test(test_id):
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập trang này.", 'error')
        return redirect(url_for('index'))

    test_to_delete = Test.query.get(test_id)
    if not test_to_delete:
        flash("Đề thi không tồn tại.", 'error')
        return redirect(url_for('admin.admin_panel', section='view_tests'))

    try:
        db.session.delete(test_to_delete)
        db.session.commit()
        flash(f"Đã xóa đề thi '{test_to_delete.title}'.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Lỗi khi xóa đề thi: {str(e)}", 'error')

    return redirect(url_for('admin.admin_panel', section='view_tests'))


@admin_bp.app_context_processor
def inject_utils():
    """Đưa các hàm/module tiện ích vào template Jinja2."""
    # Hàm này cho phép bạn gọi 'json.loads(text)' bên trong file HTML
    return dict(json=json)


@admin_bp.route('/view_test/<int:test_id>')
def view_test(test_id):
    """Hiển thị trang xem lại (read-only) một đề thi."""
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập trang này.", 'error')
        return redirect(url_for('index'))

    test = Test.query.get(test_id)
    if not test:
        flash("Đề thi không tồn tại.", 'error')
        return redirect(url_for('admin.admin_panel', section='view_tests'))

    # Sắp xếp các passage và question theo ID để đảm bảo thứ tự
    # (Phòng trường hợp database trả về không theo thứ tự)
    try:
        sorted_passages = sorted(test.passages, key=lambda p: p.id)
        for p in sorted_passages:
            # Gán danh sách đã sắp xếp vào một thuộc tính mới
            p.sorted_questions = sorted(p.question_blocks, key=lambda q: q.id)
    except Exception:
        # Fallback nếu ID không phải lúc nào cũng là số (ví dụ: khi test)
        sorted_passages = test.passages
        for p in sorted_passages:
            p.sorted_questions = p.question_blocks

    return render_template('view_test.html', test=test, sorted_passages=sorted_passages)


@admin_bp.route('/', methods=['GET', 'POST'])
def admin_panel():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập trang này.", 'error')
        return redirect(url_for('index'))

    if request.method == 'POST' and request.form.get('form_type') == 'add_test':
        success, message = parse_and_save_test(request.form, request.files)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
        return redirect(url_for('admin.admin_panel', section='add_test'))

    # Logic GET không đổi
    list_users = []
    list_tests = []
    section = request.args.get('section', 'users')
    if section == 'users':
        list_users = load_data()
    elif section == 'view_tests':
        list_tests = Test.query.order_by(Test.id.desc()).all()
    
    
    return render_template('admin.html', users=list_users, section=section, tests=list_tests)
