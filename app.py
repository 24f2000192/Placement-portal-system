# ── LINE 1-4: Import what we need ──────────────────────────
from flask import render_template, request, redirect, url_for, session
from flask import Flask          # Flask is the main class that creates our app
from models import db, User, CompanyProfile, StudentProfile, PlacementDrive, Application
import os           # os lets us work with file paths
from application.auth import auth_bp      
from application.student import student_bp   
from application.admin import admin_bp
from application.company import company_bp
from jinja2 import Template

# ── FUNCTION: create_app() ────────────────────────────────
def create_app():
    # Creates the Flask application object
    # __name__ tells Flask where your app file is located
    app = Flask(__name__)

    # ── CONFIGURATION ───────────────────────────────────────
    # SECRET_KEY: Used to encrypt session data (cookie security)
    # Sessions store who is logged in — they need to be encrypted
    app.config['SECRET_KEY'] = 'your-super-secret-key-change-this'

    # This is the path to your SQLite database file
    # sqlite:/// means "SQLite file in the instance/ folder"
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'

    # Set to False — disables a feature we don't need (reduces memory usage)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Path where uploaded resumes will be saved
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'uploads')

    # DATABASE SETUP 
    # Connect the database object (db) to this app
    db.init_app(app)

    
    
    # ── CREATE TABLES + SEED ADMIN ──────────────────────────
    # app_context() means "run this inside the Flask app environment"
    with app.app_context():
        # Creates all tables in the database (if they don't exist yet)
        db.create_all()
        # Create the admin user in the database
        seed_admin()

    return app

def seed_admin():
    # Check if admin already exists — we don't want duplicates
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        # Create admin object
        admin = User(name='Admin', email='admin@placement.com', role='admin')
        # Hash the password (never store plain text passwords!)
        admin.set_password('admin123')
        # Add to database session (like a staging area)
        db.session.add(admin)
        # Actually save/commit to the database file
        db.session.commit()



# ── RUN THE APP ─────────────────────────────────────────────
# This creates the app and assigns it to a variable called 'app'
app = create_app()

# register blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(company_bp, url_prefix='/company')
app.register_blueprint(student_bp, url_prefix='/student')

@app.route('/')
def home():
    return render_template('index.html')  


# ---- HOME PAGE ----
@auth_bp.route('/')
def index():
    # if already logged in 
    if session.get('user_id'):
        role = session.get('user_role')
        if role == 'admin': return redirect(url_for('admin.dashboard'))
        if role == 'company': return redirect(url_for('company.dashboard'))
        return redirect(url_for('student.dashboard'))
    return render_template('index.html')

# - LOGIN -
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Try to find user by email
        user = User.query.filter_by(email=email).first()

        # Case 1: User not found or wrong password
        if not user or not user.check_password(password):
            flash('Invalid email or password', 'danger')
            return render_template('auth/login.html')

        # Case 2: User is blacklisted
        if user.is_blacklisted:
            flash('Your account has been blacklisted. Contact admin.', 'danger')
            return render_template('auth/login.html')

        # Case 3: Company not yet approved
        if user.role == 'company':
            if user.company_profile.approval_status == 'pending':
                flash('Your company registration is pending admin approval.', 'warning')
                return render_template('auth/login.html')
            if user.company_profile.approval_status == 'rejected':
                flash('Your company registration was rejected.', 'danger')
                return render_template('auth/login.html')

        # SUCCESS: Set session and redirect to dashboard
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['user_name'] = user.name
        flash(f'Welcome back, {user.name}!', 'success')

        if user.role == 'admin': return redirect(url_for('admin.dashboard'))
        if user.role == 'company': return redirect(url_for('company.dashboard'))
        return redirect(url_for('student.dashboard'))

    return render_template('auth/login.html')

# ---- REGISTER ----
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form.get('name')
        email    = request.form.get('email')
        password = request.form.get('password')
        role     = request.form.get('role')

        # Check if email already registered
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html')

        # Create user object (not saved to DB yet)
        user = User(name=name, email=email, role=role)
        user.set_password(password)  # Hash the password!
        db.session.add(user)
        db.session.flush()  # flush gives us user.id without committing yet

        if role == 'student':
            profile = StudentProfile(
                user_id=user.id,
                student_id_number=request.form.get('student_id_number'),
                contact=request.form.get('contact')
            )
            db.session.add(profile)

        elif role == 'company':
            profile = CompanyProfile(
                user_id=user.id,
                company_name=request.form.get('company_name'),
                hr_contact=request.form.get('hr_contact'),
                website=request.form.get('website'),
                approval_status='pending'
            )
            db.session.add(profile)

        db.session.commit()  # NOW save everything to DB
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

# ---- LOGOUT ----
@auth_bp.route('/logout')
def logout():
    session.clear()  # Remove all session data = logged out
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

# Full URL = /admin + /dashboard = /admin/dashboard
@admin_bp.route('/dashboard')
def dashboard():
    
    return render_template('admin/dashboard.html')    

@company_bp.route('/dashboard')
def dashboard():
    return render_template('company/dashboard.html')  


# This means: "If you run THIS file directly (python app.py), start the server"
if __name__ == '__main__':
    app.run(debug=True)    # debug=True shows errors clearly in browser