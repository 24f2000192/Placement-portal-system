# application/student.py

from flask import Blueprint, render_template

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard')
def dashboard():
    return render_template('student/dashboard.html')


@student_bp.route('/profile')
def profile():
    return render_template('student/profile.html')

@student_bp.route('/history')
def history():
    return render_template('student/history.html')