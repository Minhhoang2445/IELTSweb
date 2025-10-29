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
import traceback  # Thêm import để in traceback lỗi

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
    print("\n--- DEBUG: Bắt đầu parse_and_save_test ---")
    print.print({"form_data_keys": list(form_data.keys()),
                  "files_data_keys": list(files_data.keys())})

    try:
        category = form_data.get('category')
        saved_audio_url = None  # Biến để lưu URL file audio

        # --- Xử lý file upload NẾU là Listening ---
        if category == 'Listening':
            print("--- DEBUG: Xử lý upload cho Listening ---")
            if 'audio_file' not in files_data or files_data['audio_file'].filename == '':
                print("!!! DEBUG ERROR: Thiếu file audio hoặc chưa chọn file.")
                return (False, "Lỗi: Vui lòng chọn file audio (.mp3) cho bài Listening.")

            file = files_data['audio_file']
            print(f"DEBUG: Tên file upload: {file.filename}")

            if file and allowed_file(file.filename):
                # Tạo tên file an toàn
                filename = secure_filename(file.filename)
                # Tạo đường dẫn lưu file đầy đủ trong thư mục UPLOAD_FOLDER đã cấu hình
                save_path = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], filename)

                # Lưu file (sẽ ghi đè nếu file đã tồn tại)
                try:
                    file.save(save_path)
                    print(f"DEBUG: Đã lưu file audio vào: {save_path}")
                    # Tạo URL tương đối dạng /static/audio/ten_file.mp3
                    saved_audio_url = url_for(
                        'static', filename=f'audio/{filename}')
                    print(
                        f"DEBUG: URL file audio được lưu vào DB: {saved_audio_url}")
                except Exception as save_err:
                    print(
                        f"!!! DEBUG ERROR: Không thể lưu file audio: {save_err}")
                    return (False, f"Lỗi nghiêm trọng khi lưu file audio: {save_err}")
            else:
                print(
                    f"!!! DEBUG ERROR: Loại file không hợp lệ: {file.filename}")
                return (False, "Lỗi: Loại file audio không hợp lệ (chỉ chấp nhận .mp3).")
        # --- Kết thúc xử lý file upload ---

        # 1. Gom dữ liệu câu hỏi
        print("--- DEBUG: Bắt đầu gom dữ liệu câu hỏi ---")
        questions_data = {}
        # ... (code gom questions_data y hệt phiên bản debug trước) ...
        for key, value in form_data.items():
            if key.startswith('questions['):
                try:
                    parts = key.replace(']', '').split('[')
                    q_id = parts[1]
                    if q_id not in questions_data:
                        questions_data[q_id] = {}
                    current_level = questions_data[q_id]
                    for i, part in enumerate(parts[2:-1]):
                        if part not in current_level:
                            if part.isdigit():
                                part = int(part)
                            current_level[part] = {}
                        current_level = current_level[part]
                    last_part = parts[-1]
                    if last_part.isdigit():
                        last_part = int(last_part)
                    current_level[last_part] = value.strip(
                    ) if isinstance(value, str) else value
                except IndexError:
                    print(f"!!! DEBUG WARNING: Không thể phân tích key: {key}")
                except Exception as e_parse:
                    print(
                        f"!!! DEBUG WARNING: Lỗi khi phân tích key {key}: {e_parse}")
        print(f"--- DEBUG: Gom xong, có {len(questions_data)} khối thô ---")
        # pprint.pprint(questions_data) # Bỏ comment nếu cần xem chi tiết

        # 2. Lọc câu hỏi hợp lệ
        print("--- DEBUG: Bắt đầu lọc câu hỏi hợp lệ ---")
        valid_question_blocks = []
        for q_id, q_data in questions_data.items():
            query_value = q_data.get('query')
            range_value = q_data.get('question_range')
            print(
                f"  [*] Lọc khối ID={q_id}: query={repr(query_value)}, range={repr(range_value)}")
            if query_value and range_value:  # Kiểm tra cả 2 không rỗng
                print("      ==> HỢP LỆ.")
                valid_question_blocks.append(q_data)
            else:
                print("      ==> KHÔNG HỢP LỆ.")
        print(
            f"--- DEBUG: Lọc xong, có {len(valid_question_blocks)} khối hợp lệ ---")

        # 3. Kiểm tra số lượng
        if not valid_question_blocks:
            return (False, "Lỗi: Đề thi phải có ít nhất 1 khối câu hỏi hợp lệ (đã điền Instruction và Range).")

        # 4. Lưu Test và Passage (Đã cập nhật)
        print("--- DEBUG: Chuẩn bị lưu Test và Passage ---")
        new_test = Test(title=form_data.get('title'),
                        category=category,
                        # Lưu URL audio (sẽ là None nếu là Reading)
                        audio_url=saved_audio_url)

        db.session.add(new_test)
        print(f"DEBUG: Đã thêm Test '{new_test.title}' vào session.")

        # Chỉ tạo passage nếu là Reading
        new_passage = None
        if category == 'Reading':
            passage_text = form_data.get('passage_text')
            if not passage_text or not passage_text.strip():
                print("!!! DEBUG ERROR: Reading test thiếu passage text.")
                db.session.rollback()  # Hủy test đã add
                return (False, "Lỗi: Bài Reading phải có nội dung đoạn văn.")
            new_passage = Passage(passage_text=passage_text, test=new_test)
            db.session.add(new_passage)
            print(f"DEBUG: Đã thêm Passage cho Reading test vào session.")
        # Nếu là Listening, new_passage sẽ là None ban đầu

        # 5. Lặp qua các khối câu hỏi hợp lệ (Đã cập nhật)
        print(
            f"--- DEBUG: Bắt đầu xử lý {len(valid_question_blocks)} khối câu hỏi hợp lệ ---")
        virtual_listening_passage = None  # Biến lưu passage ảo cho Listening
        for i, block_data in enumerate(valid_question_blocks):
            q_type = block_data.get('type')
            print(
                f"  [*] Xử lý khối {i+1}: type={q_type}, range={block_data.get('question_range')}")
            extra_data_dict = {}

            # Xử lý extra_data (logic cũ)
            if q_type == 'multiple_choice':
                options_dict = block_data.get('options', {})
                valid_options = [opt for opt in options_dict.values() if opt]
                if valid_options:
                    extra_data_dict['options'] = valid_options
            elif q_type == 'matching':
                items_text = block_data.get('matching_items', '')
                items_list = [item.strip()
                              for item in items_text.splitlines() if item.strip()]
                if items_list:
                    extra_data_dict['matching_items'] = items_list
                sub_q_dict = block_data.get('sub_questions', {})
                valid_sub_q = [sq for sq in sub_q_dict.values(
                ) if sq.get('query') and sq.get('answer')]
                if valid_sub_q:
                    extra_data_dict['sub_questions'] = valid_sub_q

            # Tạo đối tượng QuestionBlock
            new_block = QuestionBlock(
                question_type=q_type,
                question_range=block_data.get('question_range'),
                instruction_text=block_data.get('query'),
                simple_answer=block_data.get('answer'),
                extra_data=json.dumps(
                    extra_data_dict) if extra_data_dict else None
            )

            # Liên kết QuestionBlock với Passage/Test
            if category == 'Reading':
                new_block.passage = new_passage  # Gán vào passage thật
            elif category == 'Listening':
                # Nếu là khối đầu tiên của Listening test, tạo passage ảo
                if virtual_listening_passage is None:
                    # Tạo passage ảo chỉ MỘT LẦN cho mỗi Listening test
                    virtual_listening_passage = Passage(
                        passage_text=f"Listening Sections for Test ID {new_test.id}", test=new_test)
                    db.session.add(virtual_listening_passage)
                    # Quan trọng: flush để passage ảo có ID trước khi gán cho block
                    # db.session.flush() # Có thể không cần thiết nếu relationship xử lý tốt
                    print(
                        f"DEBUG: Đã tạo virtual_listening_passage cho Test ID {new_test.id}")
                new_block.passage = virtual_listening_passage  # Gán vào passage ảo

            db.session.add(new_block)
            print(f"      ==> Đã thêm QuestionBlock vào session.")

        # 6. Lưu tất cả vào DB
        print("--- DEBUG: Chuẩn bị gọi db.session.commit() ---")
        db.session.commit()
        print("--- DEBUG: db.session.commit() đã hoàn thành! ---")
        success_message = f"Đã thêm đề thi '{new_test.title}' với {len(valid_question_blocks)} khối câu hỏi!"
        return (True, success_message)

    except Exception as e:
        db.session.rollback()
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!!!!!!!!!!!!! EXCEPTION OCCURRED !!!!!!!!!!!!!!!")
        print(f"Lỗi khi thêm đề: {e}")
        print("--- Traceback chi tiết ---")
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        # Cung cấp thông báo lỗi rõ ràng hơn
        # Giới hạn độ dài lỗi
        error_msg = f"Có lỗi xảy ra trong quá trình xử lý: {str(e)[:100]}..."
        return (False, error_msg)


# -----------------------------------------------------------------
# ROUTE 'admin_panel' (Đã cập nhật để truyền files_data)
# -----------------------------------------------------------------
@admin_bp.route('/', methods=['GET', 'POST'])
def admin_panel():
    if session.get('role') != 'admin':
        flash("Bạn không có quyền truy cập trang này.", 'error')
        return redirect(url_for('index'))

    if request.method == 'POST' and request.form.get('form_type') == 'add_test':
        # Truyền cả request.form và request.files
        success, message = parse_and_save_test(request.form, request.files)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
        # Redirect về section add_test để xem thông báo
        return redirect(url_for('admin.admin_panel', section='add_test'))

    # Logic GET không đổi
    list_users = []
    list_tests = []
    section = request.args.get('section', 'users')
    if section == 'users':
        list_users = load_data()
    elif section == 'view_tests':
        list_tests = Test.query.order_by(
            Test.id.desc()).all()  # Sắp xếp theo ID giảm dần
    return render_template('admin.html', users=list_users, section=section, tests=list_tests)
