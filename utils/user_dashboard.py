from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from utils.extensions import db
from utils.data_manage import User, Test, UserTestResult, UserAnswer, QuestionBlock
from sqlalchemy import func
from datetime import datetime, date
import calendar
import json

dashboard_bp = Blueprint('dashboard', __name__,
                         template_folder='templates',
                         url_prefix='/dashboard')  # Đặt tiền tố /dashboard cho tất cả route

# Hàm helper để chuẩn bị dữ liệu lịch


def get_calendar_data(submission_dates_set, year, month):
    """Tạo dữ liệu cho 1 tháng: (ngày, có_làm_bài, là_ngày_hôm_nay)"""
    cal = calendar.Calendar()
    month_days = []
    today = date.today()

    for day in cal.itermonthdates(year, month):
        if day.month != month:
            month_days.append(None)  # Ngày thuộc tháng khác
        else:
            date_str = day.strftime('%Y-%m-%d')
            is_today = (day == today)
            has_submission = (date_str in submission_dates_set)
            month_days.append({
                'day': day.day,
                'has_submission': has_submission,
                'is_today': is_today
            })
    # Chia thành các tuần (7 ngày)
    weeks = [month_days[i:i + 7] for i in range(0, len(month_days), 7)]
    return weeks


@dashboard_bp.route('/')
def user_dashboard():
    """Hiển thị trang dashboard chính của người dùng"""
    # 1. Xác thực người dùng
    if 'email' not in session:
        flash("Bạn cần đăng nhập để xem trang này.", "error")
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=session['email']).first()
    if not user:
        flash("Lỗi xác thực người dùng.", "error")
        return redirect(url_for('auth.logout'))

    # 2. Lấy section từ URL (mặc định là 'history')
    section = request.args.get('section', 'history')

    # 3. Chuẩn bị dữ liệu
    all_results = None
    stats_data = {}
    calendar_data = {}

    # Lấy TẤT CẢ kết quả làm bài của user (dùng cho cả 2 section)
    all_results = UserTestResult.query.filter_by(
        user_id=user.id).order_by(UserTestResult.taken_at.desc()).all()

    if section == 'statistics':
        # --- 1. Lấy dữ liệu cho 2 Biểu đồ 5 bài gần nhất ---
        last_5_reading = UserTestResult.query.join(Test).filter(
            Test.category == 'Reading', UserTestResult.user_id == user.id
            # [::-1] để đảo ngược (cũ nhất trước)
        ).order_by(UserTestResult.taken_at.desc()).limit(5).all()[::-1]

        last_5_listening = UserTestResult.query.join(Test).filter(
            Test.category == 'Listening', UserTestResult.user_id == user.id
            # Đảo ngược
        ).order_by(UserTestResult.taken_at.desc()).limit(5).all()[::-1]

        # --- 2. Lấy dữ liệu Lịch (Calendar Heatmap) ---
        submission_dates_set = {result.taken_at.strftime(
            '%Y-%m-%d') for result in all_results}
        today = date.today()
        # Lấy tháng và năm hiện tại, có thể cho user chọn sau
        cal_year = request.args.get('year', today.year, type=int)
        cal_month = request.args.get('month', today.month, type=int)

        calendar_data = {
            'weeks': get_calendar_data(submission_dates_set, cal_year, cal_month),
            'month_name': calendar.month_name[cal_month],
            'year': cal_year
        }

        # --- 3. Lấy dữ liệu Thống kê câu sai theo loại ---
        # Query này lấy: (loại câu hỏi, có đúng không)
        type_results = db.session.query(
            QuestionBlock.question_type, UserAnswer.is_correct
        ).join(UserAnswer).join(UserTestResult).filter(
            UserTestResult.user_id == user.id
        ).all()

        question_type_stats = {}
        # Đếm tổng số câu đúng/sai cho từng loại
        for r in type_results:
            # 'fill_in_blank' -> 'Fill In Blank'
            q_type = r.question_type.replace("_", " ").title()
            if q_type not in question_type_stats:
                question_type_stats[q_type] = {'correct': 0, 'total': 0}

            if r.is_correct:
                question_type_stats[q_type]['correct'] += 1
            question_type_stats[q_type]['total'] += 1

        # Tính toán % và số câu sai
        stats_list = []
        for q_type, data in question_type_stats.items():
            if data['total'] > 0:
                data['wrong_count'] = data['total'] - data['correct']
                data['wrong_percent'] = round(
                    (data['wrong_count'] / data['total']) * 100)
                data['type_name'] = q_type
                stats_list.append(data)

        # Sắp xếp theo % sai nhiều nhất
        stats_list.sort(key=lambda x: x['wrong_percent'], reverse=True)

        # Đóng gói dữ liệu stats
        stats_data = {
            'last_5_reading_labels': json.dumps([r.test.title for r in last_5_reading]),
            'last_5_reading_scores': json.dumps([r.score for r in last_5_reading]),
            'last_5_listening_labels': json.dumps([r.test.title for r in last_5_listening]),
            'last_5_listening_scores': json.dumps([r.score for r in last_5_listening]),
            'question_type_stats': stats_list
        }

    return render_template('user.html',
                           section=section,
                           all_results=all_results,
                           stats_data=stats_data,
                           calendar_data=calendar_data
                           )
