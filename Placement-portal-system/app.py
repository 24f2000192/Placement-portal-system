from flask import render_template, request, redirect, url_for, session, flash
from flask import Flask          # Flask is the main class that creates our app
from models import db, User, CompanyProfile, StudentProfile, PlacementDrive, Application, Placement
import os           # os lets us work with file paths
from jinja2 import Template
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from fileinput import filename
from datetime import datetime
from sqlalchemy import or_

# FUNCTION: create_app() 
def create_app():
    # Creates the Flask application object
    # __name__ tells Flask where your app file is located
    app = Flask(__name__)

    # CONFIGURATION 
    # SECRET_KEY: Used to encrypt session data (cookie security)
    # Sessions store who is logged in — they need to be encrypted
    app.config['SECRET_KEY'] = 'chitranjan'

    # This is the path to SQLite database file
    # sqlite:/// means "SQLite file in the instance/ folder"
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'

    # A disables a feature we don't need (reduces memory usage)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Path where uploaded resumes will be saved
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'uploads')

    # DATABASE SETUP 
    # Connect the database object (db) to this app
    db.init_app(app)

    @app.route('/')
    def home():
        return render_template('index.html')  

    def seed_admin():
    # Check if admin already exists — we don't want duplicates
        admin = User.query.filter_by(role='admin').first()
        if not admin:
        # Create admin object
            admin = User(name='chitranjan', email='admin@placement.com', role='admin')
        # Hash the password (never store plain text passwords!)
            admin.set_password('admin123')
        # Add to database session (like a staging area)
            db.session.add(admin)
        # Actually save/commit to the database file
            db.session.commit()

    
    # --- CREATE TABLES + SEED ADMIN ----
    # app_context() means "run this inside the Flask app environment"
    with app.app_context():
        # Creates all tables in the database (if they don't exist yet)
        db.create_all()
        # Create the admin user in the database
        seed_admin()

    return app

# ----- RUN THE APP -----
# This creates the app and assigns it to a variable called 'app'
app = create_app()

@app.route('/student_register', methods=['GET','POST'])
def student_register():

    if request.method == 'POST':

        # form data
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        branch = request.form.get('branch')
        cgpa = request.form.get('cgpa')

        # check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered", "danger")
            return redirect(url_for('student_register'))

        # create user first
        user = User(
            name=name,
            email=email,
            role='student'
        )
        user.set_password(password)

        db.session.add(user)
        db.session.flush()  # gives user.id before commit

        # file upload
        resume = request.files.get('resume')
        resume_path = None

        if resume and resume.filename != "":
            filename = secure_filename(resume.filename)

            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            resume.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            resume_path = filename

        # create student profile
        student = StudentProfile(
            name=name,
            Email=email,
            user_id=user.id,
            branch=branch,
            cgpa=cgpa,
            resume_path=resume_path
        )

        db.session.add(student)
        db.session.commit()

        flash("Student registered successfully", "success")

        return redirect(url_for('login'))

    return render_template('student_register.html')


# ---- HOME PAGE ----
@app.route('/')
def index():
    # if already logged in 
    if session.get('user_id'):
        role = session.get('user_role')
        if role == 'admin': return redirect(url_for('admin.dashboard'))
        if role == 'company': return redirect(url_for('company.dashboard'))
        return redirect(url_for('student.dashboard'))
    return render_template('index.html')

# - LOGIN -
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Try to find user by email
        user = User.query.filter_by(email=email).first()

        # Case 1: User not found or wrong password
        if not user or not user.check_password(password):
            flash('Invalid email or password', 'danger')
            return render_template('login.html')

        # Case 2: User is deactivated
        if not user.is_active:
            flash('Your account has been deactivated by admin.', 'danger')
            return render_template('login.html')
        
        # Case 3: User is blacklisted
        if user.is_blacklisted:
            flash('Your account has been blacklisted. Contact admin.', 'danger')
            return render_template('login.html')

        # Case 4: User is blacklisted
        if user.is_blacklisted:
            flash('Your account has been blacklisted. Contact admin.', 'danger')
            return render_template('login.html')

        # Case 5: Company not yet approved
        if user.role == 'company':
            if user.company_profile.approval_status == 'pending':
                flash('Your company registration is pending admin approval.', 'warning')
                return render_template('login.html')
            if user.company_profile.approval_status == 'rejected':
                flash('Your company registration was rejected.', 'danger')
                return render_template('login.html')

        # SUCCESS: Set session and redirect to dashboard
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['user_name'] = user.name
        flash(f'Welcome back, {user.name}!', 'success')

        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'company':
            session['company_id'] = user.company_profile.id  
            return redirect(url_for('company_dashboard'))

        else:
            session['student_id'] = user.student_profile.id

            return redirect(url_for('student_dashboard'))

    return render_template('login.html')


@app.route('/company/register', methods=['GET', 'POST'])
def company_register():

    if request.method == 'POST':

        name = request.form.get('name')   # must exist in form
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password)
        company_name = request.form.get('company_name')
        hr_contact = request.form.get('hr_contact')
        website = request.form.get('website')
        description = request.form.get('description')
        

        # check duplicate email
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already registered", "danger")
            return redirect(url_for('company_register'))

        # create user
        user = User(
            name=name,
            email=email,
            password_hash=hashed_password,
            role='company'
        )


        db.session.add(user)
        db.session.flush()

        # create company profile
        company = CompanyProfile(
            user_id=user.id,
            company_name=request.form.get("company_name"),
            hr_contact=request.form.get("hr_contact"),
            website=request.form.get("website"),
            description=request.form.get("description"),
            approval_status='pending'
        )

        db.session.add(company)
        db.session.commit()

        flash("Company registered successfully", "success")
        return redirect(url_for('login'))

    return render_template('company_register.html')

# ---- LOGOUT ----
@app.route('/logout')
def logout():
    session.clear()  # Remove all session data = logged out
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))




# Full URL = /admin + /dashboard = /admin/dashboard
@app.route('/admin/dashboard')
def admin_dashboard():

    if not session.get('user_id') or session.get('user_role') != 'admin':
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('login'))
    
    
    company_search = request.args.get("company_search")
    # Company search
    companies_query = CompanyProfile.query

    if company_search:
        companies_query = companies_query.filter(
            CompanyProfile.company_name.ilike(f"%{company_search}%")
        )


    student_search = request.args.get("student_search")
    # Student search
    students_query = StudentProfile.query.join(User)

    if student_search:
        students_query = students_query.filter(
            or_(
                StudentProfile.name.ilike(f"%{student_search}%"),
                StudentProfile.id.ilike(f"%{student_search}%"),
                User.email.ilike(f"%{student_search}%"),
                
            )
        )

    students = StudentProfile.query.all()
    companies = CompanyProfile.query.all()
    company_search_count = companies_query.count()
    student_search_count = students_query.count()
    drives = PlacementDrive.query.all()
    placement_count = Application.query.filter_by(status='placed').count()
    application_count = Application.query.count()
    company_count = CompanyProfile.query.count()
    student_count = StudentProfile.query.count()
    drives_count = PlacementDrive.query.count()
    return render_template(
        'admin/dashboard.html',
        students=students,
        companies=companies,
        company_search=company_search,
        company_search_count=company_search_count,
        student_search_count=student_search_count,
        drives=drives,
        placement_count=placement_count,
        application_count=application_count,
        company_count = company_count,
        student_count = student_count,
        drives_count = drives_count
    )

@app.route('/approved_companies/<int:company_id>')
def approved_companies(company_id):
    # Implementation for approved companies
    company = CompanyProfile.query.get_or_404(company_id)
    company.approval_status = 'approved'
    db.session.commit()
    flash(f'Company {company.company_name} approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/rejected_companies/<int:company_id>')
def rejected_companies(company_id):
    # Implementation for rejected companies
    company = CompanyProfile.query.get_or_404(company_id)
    company.approval_status = 'rejected'
    db.session.commit()
    flash(f'Company {company.company_name} rejected ', 'warning')
    return redirect(url_for('admin_dashboard'))

@app.route('/approve_drive/<int:drive_id>')
def approve_drive(drive_id):
    # Implementation for approving placement drives
    if not session.get('user_id') or session.get('user_role') != 'admin':
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('login'))
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'active'
    db.session.commit()
    flash(f'Placement drive {drive.job_title} approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/reject_drive/<int:drive_id>')
def reject_drive(drive_id):
    # Implementation for rejecting placement drives
    if not session.get('user_id') or session.get('user_role') != 'admin':
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('login'))
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'closed'
    db.session.commit()
    flash(f'Placement drive {drive.job_title} rejected!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_view_applications/<int:drive_id>')
def admin_view_applications(drive_id):
    if not session.get('user_id') or session.get('user_role') != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    drive = PlacementDrive.query.get_or_404(drive_id)
    applications = Application.query.filter_by(drive_id=drive_id).all()
    return render_template('admin_view_applications.html', drive=drive, applications=applications)


@app.route('/deactivate_student/<int:student_id>')
def deactivate_student(student_id):
    student = StudentProfile.query.get_or_404(student_id)
    student.user.is_active = False
    db.session.commit()
    flash(f'Student {student.name} deactivated', 'warning')
    return redirect(url_for('admin_dashboard'))

@app.route('/deactivate_company/<int:company_id>')
def deactivate_company(company_id):
    company = CompanyProfile.query.get_or_404(company_id)
    company.is_active = False
    db.session.commit()
    flash(f'Company {company.company_name} deactivated', 'warning')
    return redirect(url_for('admin_dashboard'))

@app.route('/activate_student/<int:student_id>')
def activate_student(student_id):
    student = StudentProfile.query.get_or_404(student_id)
    student.user.is_active = True
    db.session.commit()
    flash(f'Student {student.name} activated', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/activate_company/<int:company_id>')
def activate_company(company_id):
    company = CompanyProfile.query.get_or_404(company_id)
    company.is_active = True
    db.session.commit()
    flash(f'Company {company.company_name} activated', 'success')
    return redirect(url_for('admin_dashboard'))

#####################
#                   #
# COMPANY DASHBOARD ##############################################################################################
#                   #
#####################
@app.route('/company/dashboard')
def company_dashboard():
    if "company_id" not in session:
        flash("Please login first", "danger")
        return redirect(url_for('login'))
    
    company = db.session.get(CompanyProfile, session['company_id'])
    if not company or company.approval_status != 'approved':
        flash("Your company registration is pending admin approval.", "warning")
        return redirect(url_for('login'))
    
    drives = PlacementDrive.query.filter_by(company_id=company.id).all()

    return render_template('company/dashboard.html', company=company, drives=drives)


#ADD PLACEMENT DRIVE

@app.route('/add_drive', methods=['GET', 'POST'])
def add_drive():

    if "company_id" not in session:
        flash("Please login first", "danger")
        return redirect(url_for('login'))

    company = db.session.get(CompanyProfile, session['company_id'])

    if company.approval_status != "approved":
        flash("Your company is not approved by admin. You cannot create drives.", "danger")
        return redirect(url_for('company_dashboard'))
    
    if not company.is_active:
        flash("Your company is deactivated by admin. Contact admin.", "danger")
        return redirect(url_for('company_dashboard'))


    if request.method == 'POST':

        job_title = request.form.get('job_title')
        job_description = request.form.get('job_description')
        location = request.form.get('location')
        deadline_str = request.form.get('deadline')

        deadline = None
        if deadline_str:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d")

        new_drive = PlacementDrive(
            company_id=company.id,
            job_title=job_title,
            job_description=job_description,
            location=location,
            deadline=deadline,
            status="pending"
        )

        db.session.add(new_drive)
        db.session.commit()

        flash("Drive created successfully", "success")

        return redirect(url_for('company_dashboard'))

    return render_template('company/add_drive.html')


#END DRIVE when deadline is reached or company wants to end it manually.
@app.route('/end_drive/<int:drive_id>')
def end_drive(drive_id):
    drive = db.session.get(PlacementDrive, drive_id)
    drive.status = "closed"
    db.session.commit()
    flash(f"Placement drive {drive.job_title} has been closed.", "info")
    return redirect(url_for('company_dashboard'))

@app.route('/activate_drive/<int:drive_id>')
def activate_drive(drive_id):
    if "company_id" not in session:
        flash("Please log in to access the company dashboard.", "danger")
        return redirect(url_for('login'))
    drive = db.session.get(PlacementDrive, drive_id)
    drive.status = "active"
    db.session.commit()
    flash(f"Placement drive {drive.job_title} has been activated.", "info")
    return redirect(url_for('company_dashboard'))

@app.route('/view_applications/<int:drive_id>')
def view_applications(drive_id):
    if "company_id" not in session:
        flash("Please log in to access the company dashboard.", "danger")
        return redirect(url_for('login'))
    drive = db.session.get(PlacementDrive, drive_id)
    applications = Application.query.filter_by(drive_id=drive_id).all()
    return render_template('company/view_applications.html', drive=drive, applications=applications)

@app.route('/update_application/<int:application_id>/<string:new_status>')
def update_application(application_id, new_status):
    application = db.session.get(Application, application_id)
    application.status = new_status

    if new_status =="selected":
        existing = Placement.query.filter_by(student_id=application.student_id, drive_id=application.drive_id).first()
        if not existing:
            placement = Placement(
                student_id=application.student_id,
                company_id=application.drive.company_id,
                drive_id=application.drive_id,
                status='placed'
            )
            db.session.add(placement)

    db.session.commit()
    flash(f"Application status updated to {new_status}.", "success")
    return redirect(url_for('view_applications', drive_id=application.drive_id))

@app.route('/shortlist_student/<int:application_id>')
def shortlist_student(drive_id):
    Placement = Placement.query.filter_by(student_id=application.student_id, drive_id=application.drive_id).first()
    application = db.session.get(Application, drive_id)
    application.status = "shortlisted"
    db.session.commit()
    flash("Student shortlisted successfully!", "success")
    return redirect(url_for('company.view_applications', drive_id=application.drive_id))

UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Ensure the upload folder exists

# Create the uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

#####################
#                   #
# student dashboard #########################################################################
#                   #
#####################
@app.route('/student/dashboard')
def student_dashboard():
    if "student_id" not in session:
        flash("Please log in first", "danger")
        return redirect(url_for('login'))
    approved_drives = PlacementDrive.query.filter_by(status="active").all()
    # student's applications
    my_applications = Application.query.filter_by(student_id=session['student_id']).all()
    applied_drive_ids = [app.drive_id for app in my_applications]
    return render_template('student/dashboard.html',
                           approved_drives=approved_drives,
                           my_applications=my_applications,
                           applied_drive_ids=applied_drive_ids)

@app.route('/resume_upload', methods=['POST'])
def resume_upload():
    if "student_id" not in session:
        flash("Please log in to upload your resume.", "danger")
        return redirect(url_for('login'))
    
    file = request.files['resume']
    if file and file.filename != "":
        filename = secure_filename(file.filename)
        file.save(os.path.join("static/resumes", filename))
        student_profile = StudentProfile.query.get(session['student_id'])
        student_profile.resume_filename = filename
        db.session.commit()
    # Handle resume upload logic here
    flash("Resume uploaded successfully!", "success")
    return redirect(url_for('student_dashboard'))

@app.route('/view_drives')
def view_drives():
    if "student_id" not in session:
        flash("Please log in to view placement drives.", "danger")
        return redirect(url_for('login'))
    drives = PlacementDrive.query.filter_by(status="active").all()
    applications = Application.query.filter_by(student_id=session['student_id']).all()
    applied_drives = [app.drive_id for app in applications]
    return render_template(
        'student/view_drives.html',
        drives=drives,
        applied_drives=applied_drives
    )

@app.route('/apply/<int:drive_id>')
def apply(drive_id):
    if "student_id" not in session:
        flash("Please log in to apply for placement drives.", "danger")
        return redirect(url_for('login'))
    
    existing = Application.query.filter_by(student_id=session['student_id'], drive_id=drive_id).first()
    if existing:
        flash("You have already applied for this drive.", "warning")
        return redirect(url_for('view_drives'))

    new_application = Application(
        student_id=session['student_id'],
        drive_id=drive_id,
        status='applied'
    )
    db.session.add(new_application)
    db.session.commit()
    flash("Applied to drive successfully!", "success")
    return redirect(url_for('view_drives'))

@app.route('/profile_update', methods=['GET', 'POST'])
def profile_update():
    student_profile = StudentProfile.query.filter_by(user_id=session['user_id']).first()
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.name = request.form.get('name') 
        user.email = request.form.get('email') 
        student_profile.branch = request.form.get('branch') 
        student_profile.cgpa = request.form.get('cgpa') 

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile_update'))
    return render_template('student/profile_update.html', student=student_profile, user=user)

@app.route('/search_jobs', methods=['POST'])
def search_jobs():
    query = request.form['query']
    results = PlacementDrive.query.join(CompanyProfile).filter(
        (PlacementDrive.name.contains(query)) |
        (PlacementDrive.role.contains(query)) |
        (PlacementDrive.location.contains(query)) |
        (CompanyProfile.company_name.contains(query))
    )

    
    return render_template('student/view_drives.html', drives=results ,search_query=query)

@app.route('/my_applications')
def my_applications():
    if "student_id" not in session:
        flash("Please log in to view your applications.", "danger")
        return redirect(url_for('login'))

    applications = Application.query.filter_by(student_id=session['student_id']).all()
    return render_template('student/my_applications.html', applications=applications)

# This means: "If you run THIS file directly (python app.py), start the server"
if __name__ == '__main__':
    app.run(debug=True)    # debug=True shows errors clearly in browser