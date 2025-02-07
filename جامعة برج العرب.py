from flask import Flask, jsonify, request, render_template, send_from_directory, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///university_organizer.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# نموذج المستخدم مع إضافة دور
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    academic_id = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")

# نموذج للمواد الدراسية
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    professor = db.Column(db.String(100), nullable=True)

# نموذج للمحاضرات
class Lecture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(200), nullable=True)

# نموذج للواجبات
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    due_date = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(200), nullable=True)

# نموذج للنتائج
class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(10), nullable=False)

# نموذج سجل النشاط
class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

with app.app_context():
    db.create_all()

# وظيفة التحقق من امتداد الملفات
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# تسجيل المستخدم
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        academic_id = request.form['academic_id']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password)

        if User.query.filter_by(academic_id=academic_id).first():
            flash("المستخدم موجود بالفعل!", "danger")
            return redirect(url_for('register'))

        new_user = User(academic_id=academic_id, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash("تم التسجيل بنجاح، يمكنك الآن تسجيل الدخول", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

# تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        academic_id = request.form['academic_id']
        password = request.form['password']
        user = User.query.filter_by(academic_id=academic_id).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            log = ActivityLog(user_id=user.id, action='تسجيل الدخول')
            db.session.add(log)
            db.session.commit()
            flash("تم تسجيل الدخول بنجاح", "success")
            return redirect(url_for('dashboard'))
        flash("خطأ في تسجيل الدخول", "danger")
    return render_template('login.html')

# تسجيل الخروج
@app.route('/logout')
def logout():
    if 'user_id' in session:
        log = ActivityLog(user_id=session['user_id'], action='تسجيل الخروج')
        db.session.add(log)
        db.session.commit()
    session.pop('user_id', None)
    session.pop('role', None)
    flash("تم تسجيل الخروج", "info")
    return redirect(url_for('login'))

# لوحة التحكم حسب الدور
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("يجب تسجيل الدخول أولاً", "warning")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role == "student":
        return render_template('student_dashboard.html')
    elif user.role == "professor":
        return render_template('professor_dashboard.html')
    elif user.role == "admin":
        return render_template('admin_dashboard.html')
    
    flash("خطأ في تحديد الدور", "danger")
    return redirect(url_for('logout'))

# رفع الملفات (محاضرات أو جداول أو نتائج)
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash("لم يتم اختيار أي ملف", "danger")
        return redirect(url_for('dashboard'))
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        flash("يرجى اختيار ملف بصيغة صحيحة (PDF أو DOCX)", "danger")
        return redirect(url_for('dashboard'))
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    log = ActivityLog(user_id=session['user_id'], action=f'رفع ملف: {filename}')
    db.session.add(log)
    db.session.commit()
    flash("تم رفع الملف بنجاح", "success")
    return redirect(url_for('dashboard'))

# تنزيل الملفات
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# واجهة المستخدم
@app.route('/')
def index():
    return redirect(url_for('login'))