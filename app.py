from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from pymongo import MongoClient
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
from bson import ObjectId
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate a secure secret key

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['elearning_db']

# Collections
users = db['users']
courses = db['courses']
students = db['students']
assignments = db['assignments']
enrollments = db['enrollments']
grades = db['grades']
submissions = db['submissions']

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Teacher required decorator
def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'teacher':
            flash('Access denied. Teacher privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Student required decorator
def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'student':
            flash('Access denied. Student privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def clear_database():
    """Clear all collections in the database and uploads folder"""
    # Clear all collections
    users.delete_many({})
    courses.delete_many({})
    students.delete_many({})
    assignments.delete_many({})
    enrollments.delete_many({})
    grades.delete_many({})
    submissions.delete_many({})
    
    # Clear uploads folder
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f'Error deleting {file_path}: {e}')
    
    flash('Database and uploads folder cleared successfully!', 'success')

@app.route('/clear-db')
@teacher_required
def clear_db():
    clear_database()
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = users.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['email'] = user['email']
            session['role'] = user['role']
            
            # If user is a student, get or create student profile
            if user['role'] == 'student':
                student = students.find_one({'user_id': str(user['_id'])})
                if not student:
                    student_data = {
                        'user_id': str(user['_id']),
                        'email': user['email'],
                        'name': user.get('name', ''),
                        'created_at': datetime.utcnow()
                    }
                    students.insert_one(student_data)
            
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        name = request.form.get('name', '')
        
        if users.find_one({'email': email}):
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        
        user_data = {
            'email': email,
            'password': generate_password_hash(password),
            'role': role,
            'name': name,
            'created_at': datetime.utcnow()
        }
        result = users.insert_one(user_data)
        
        # If registering as a student, create student profile with additional details
        if role == 'student':
            student_data = {
                'user_id': str(result.inserted_id),
                'email': email,
                'first_name': request.form.get('first_name', ''),
                'last_name': request.form.get('last_name', ''),
                'roll_number': request.form.get('roll_number', ''),
                'department': request.form.get('department', ''),
                'semester': request.form.get('semester', ''),
                'created_at': datetime.utcnow()
            }
            students.insert_one(student_data)
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/courses')
@login_required
def list_courses():
    if session.get('role') == 'teacher':
        # Teachers see their own courses
        course_list = list(courses.find({'teacher_id': session['user_id']}))
    else:
        # Students see all courses
        course_list = list(courses.find())
    return render_template('courses.html', courses=course_list)

@app.route('/course/add', methods=['GET', 'POST'])
@teacher_required
def add_course():
    if request.method == 'POST':
        course_data = {
            'name': request.form['name'],
            'code': request.form['code'],
            'description': request.form['description'],
            'teacher_id': session['user_id'],
            'created_at': datetime.utcnow()
        }
        courses.insert_one(course_data)
        flash('Course added successfully!', 'success')
        return redirect(url_for('list_courses'))
    return render_template('add_course.html')

@app.route('/course/<course_id>/assignments')
@login_required
def course_assignments(course_id):
    # Check if user has access to this course
    course = courses.find_one({'_id': ObjectId(course_id)})
    if not course:
        abort(404)
    
    if session.get('role') == 'student':
        # Check if student is enrolled
        enrollment = enrollments.find_one({
            'student_id': session['user_id'],
            'course_id': course_id
        })
        if not enrollment:
            flash('You must enroll in this course to view assignments.', 'warning')
            return redirect(url_for('list_courses'))
    
    assignment_list = list(assignments.find({'course_id': course_id}))
    return render_template('assignments.html', 
                         assignments=assignment_list, 
                         course_id=course_id, 
                         course=course,
                         now=datetime.utcnow())

@app.route('/assignment/add/<course_id>', methods=['GET', 'POST'])
@teacher_required
def add_assignment(course_id):
    # Verify teacher owns this course
    course = courses.find_one({'_id': ObjectId(course_id), 'teacher_id': session['user_id']})
    if not course:
        flash('Access denied. You can only add assignments to your own courses.', 'danger')
        return redirect(url_for('list_courses'))
    
    if request.method == 'POST':
        assignment_data = {
            'course_id': course_id,
            'title': request.form['title'],
            'description': request.form['description'],
            'due_date': datetime.strptime(request.form['due_date'], '%Y-%m-%d'),
            'created_at': datetime.utcnow()
        }
        assignments.insert_one(assignment_data)
        flash('Assignment added successfully!', 'success')
        return redirect(url_for('course_assignments', course_id=course_id))
    return render_template('add_assignment.html', course_id=course_id)

@app.route('/enroll/<course_id>', methods=['POST'])
@student_required
def enroll_course(course_id):
    # Double check the role (extra security)
    if session.get('role') != 'student':
        flash('Only students can enroll in courses.', 'danger')
        return redirect(url_for('list_courses'))
    
    # Check if already enrolled
    existing_enrollment = enrollments.find_one({
        'student_id': session['user_id'],
        'course_id': course_id
    })
    if existing_enrollment:
        flash('You are already enrolled in this course.', 'info')
        return redirect(url_for('list_courses'))
    
    # Check if the course exists
    course = courses.find_one({'_id': ObjectId(course_id)})
    if not course:
        flash('Course not found.', 'danger')
        return redirect(url_for('list_courses'))
    
    enrollment_data = {
        'student_id': session['user_id'],
        'course_id': course_id,
        'enrolled_at': datetime.utcnow()
    }
    enrollments.insert_one(enrollment_data)
    flash('Successfully enrolled in the course!', 'success')
    return redirect(url_for('list_courses'))

@app.route('/assignment/<assignment_id>/submit', methods=['POST'])
@student_required
def submit_assignment(assignment_id):
    # Check if assignment exists and is not past due date
    assignment = assignments.find_one({'_id': ObjectId(assignment_id)})
    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('list_courses'))
    
    if assignment['due_date'] < datetime.utcnow():
        flash('Assignment is past due date.', 'danger')
        return redirect(url_for('list_courses'))
    
    # Check if student is enrolled in the course
    enrollment = enrollments.find_one({
        'student_id': session['user_id'],
        'course_id': assignment['course_id']
    })
    if not enrollment:
        flash('You must be enrolled in the course to submit assignments.', 'danger')
        return redirect(url_for('list_courses'))
    
    # Handle file upload
    if 'submission_file' not in request.files:
        flash('No file uploaded.', 'danger')
        return redirect(url_for('course_assignments', course_id=assignment['course_id']))
    
    file = request.files['submission_file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('course_assignments', course_id=assignment['course_id']))
    
    # Save file and create submission record
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    submission_data = {
        'assignment_id': assignment_id,
        'student_id': session['user_id'],
        'file_url': file_path,
        'comments': request.form.get('comments', ''),
        'submitted_at': datetime.utcnow()
    }
    
    submissions.insert_one(submission_data)
    flash('Assignment submitted successfully!', 'success')
    return redirect(url_for('course_assignments', course_id=assignment['course_id']))

@app.route('/student/<course_id>/<student_id>/progress')
@teacher_required
def view_student_progress(course_id, student_id):
    # Verify teacher owns the course
    course = courses.find_one({'_id': ObjectId(course_id), 'teacher_id': session['user_id']})
    if not course:
        flash('Access denied.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Get student information
    student = students.find_one({'user_id': student_id})
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Get all assignments for the course
    course_assignments = list(assignments.find({'course_id': course_id}))
    
    # Get student's submissions and grades
    for assignment in course_assignments:
        submission = submissions.find_one({
            'assignment_id': str(assignment['_id']),
            'student_id': student_id
        })
        grade = grades.find_one({
            'assignment_id': str(assignment['_id']),
            'student_id': student_id
        })
        
        assignment['submission'] = submission
        assignment['grade'] = grade['score'] if grade else None
        assignment['feedback'] = grade['feedback'] if grade else None
    
    # Calculate progress
    total_assignments = len(course_assignments)
    completed_assignments = len([a for a in course_assignments if a['submission']])
    overall_progress = (completed_assignments / total_assignments * 100) if total_assignments > 0 else 0
    
    # Calculate average grade
    grades_list = [a['grade'] for a in course_assignments if a['grade'] is not None]
    average_grade = sum(grades_list) / len(grades_list) if grades_list else None
    
    return render_template('student_progress.html',
                         student=student,
                         course=course,
                         assignments=course_assignments,
                         overall_progress=overall_progress,
                         completed_assignments=completed_assignments,
                         total_assignments=total_assignments,
                         average_grade=average_grade)

@app.route('/grade/<assignment_id>', methods=['GET', 'POST'])
@teacher_required
def update_grade(assignment_id):
    assignment = assignments.find_one({'_id': ObjectId(assignment_id)})
    if not assignment:
        abort(404)
    
    # Verify teacher owns the course
    course = courses.find_one({'_id': ObjectId(assignment['course_id']), 'teacher_id': session['user_id']})
    if not course:
        flash('Access denied. You can only grade assignments for your own courses.', 'danger')
        return redirect(url_for('list_courses'))
    
    if request.method == 'POST':
        # Get all enrolled students
        enrolled_students = list(enrollments.find({'course_id': assignment['course_id']}))
        student_ids = [e['student_id'] for e in enrolled_students]
        
        # Update grades for each student
        for student_id in student_ids:
            grade_key = f'grade_{student_id}'
            feedback_key = f'feedback_{student_id}'
            
            if grade_key in request.form and request.form[grade_key]:
                grade_data = {
                    'assignment_id': assignment_id,
                    'student_id': student_id,
                    'score': float(request.form[grade_key]),
                    'feedback': request.form.get(feedback_key, ''),
                    'updated_at': datetime.utcnow()
                }
                grades.update_one(
                    {'assignment_id': assignment_id, 'student_id': student_id},
                    {'$set': grade_data},
                    upsert=True
                )
        
        flash('Grades updated successfully!', 'success')
        return redirect(url_for('course_assignments', course_id=assignment['course_id']))
    
    # Get enrolled students and their submissions
    enrolled_students = list(enrollments.find({'course_id': assignment['course_id']}))
    student_ids = [e['student_id'] for e in enrolled_students]
    students_list = list(students.find({'user_id': {'$in': student_ids}}))
    
    # Add submission and grade information to each student
    for student in students_list:
        submission = submissions.find_one({
            'assignment_id': assignment_id,
            'student_id': student['user_id']
        })
        grade = grades.find_one({
            'assignment_id': assignment_id,
            'student_id': student['user_id']
        })
        
        student['submission'] = submission
        student['grade'] = grade['score'] if grade else None
        student['feedback'] = grade['feedback'] if grade else None
    
    return render_template('update_grade.html',
                         assignment_id=assignment_id,
                         assignment=assignment,
                         course_id=assignment['course_id'],
                         students=students_list)

@app.route('/student/dashboard')
@student_required
def student_dashboard():
    # Get student information
    student = students.find_one({'user_id': session['user_id']})
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('index'))
    
    # Get enrolled courses
    enrolled_courses = list(enrollments.find({'student_id': session['user_id']}))
    course_ids = [e['course_id'] for e in enrolled_courses]
    courses_list = list(courses.find({'_id': {'$in': [ObjectId(cid) for cid in course_ids]}}))
    
    # Calculate progress for each course
    for course in courses_list:
        course_assignments = list(assignments.find({'course_id': str(course['_id'])}))
        total_assignments = len(course_assignments)
        if total_assignments > 0:
            completed_assignments = len([a for a in course_assignments 
                                      if submissions.find_one({
                                          'assignment_id': str(a['_id']),
                                          'student_id': session['user_id']
                                      })])
            course['progress'] = (completed_assignments / total_assignments) * 100
        else:
            course['progress'] = 0
    
    # Get grades for all assignments
    grades_list = list(grades.find({'student_id': session['user_id']}))
    
    # Add course and assignment information to grades
    for grade in grades_list:
        assignment = assignments.find_one({'_id': ObjectId(grade['assignment_id'])})
        if assignment:
            grade['assignment_title'] = assignment['title']
            course = courses.find_one({'_id': ObjectId(assignment['course_id'])})
            if course:
                grade['course_name'] = course['name']
    
    return render_template('student_dashboard.html', 
                         student=student,
                         courses=courses_list,
                         grades=grades_list)

@app.route('/teacher/dashboard')
@teacher_required
def teacher_dashboard():
    # Get teacher's courses
    teacher_courses = list(courses.find({'teacher_id': session['user_id']}))
    
    # Get enrolled students for each course
    for course in teacher_courses:
        enrollments_list = list(enrollments.find({'course_id': str(course['_id'])}))
        student_ids = [e['student_id'] for e in enrollments_list]
        students_list = list(students.find({'user_id': {'$in': student_ids}}))
        
        # Add enrollment dates to student data
        for student in students_list:
            enrollment = next((e for e in enrollments_list if e['student_id'] == student['user_id']), None)
            if enrollment:
                student['enrolled_at'] = enrollment['enrolled_at']
        
        course['students'] = students_list
    
    # Calculate pending grades and upcoming due dates
    pending_grades = 0
    upcoming_due_dates = 0
    
    for course in teacher_courses:
        course_assignments = list(assignments.find({'course_id': str(course['_id'])}))
        for assignment in course_assignments:
            # Count pending grades
            submissions_count = submissions.count_documents({'assignment_id': str(assignment['_id'])})
            graded_count = grades.count_documents({'assignment_id': str(assignment['_id'])})
            pending_grades += max(0, submissions_count - graded_count)
            
            # Count upcoming due dates
            if assignment['due_date'] > datetime.utcnow():
                upcoming_due_dates += 1
    
    return render_template('teacher_dashboard.html', 
                         courses=teacher_courses,
                         pending_grades=pending_grades,
                         upcoming_due_dates=upcoming_due_dates)

@app.route('/submission/<submission_id>/view')
@teacher_required
def view_submission(submission_id):
    # Get submission details
    submission = submissions.find_one({'_id': ObjectId(submission_id)})
    if not submission:
        flash('Submission not found.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Get assignment and course details
    assignment = assignments.find_one({'_id': ObjectId(submission['assignment_id'])})
    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Verify teacher owns the course
    course = courses.find_one({'_id': ObjectId(assignment['course_id']), 'teacher_id': session['user_id']})
    if not course:
        flash('Access denied.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Get student details
    student = students.find_one({'user_id': submission['student_id']})
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Get grade if exists
    grade = grades.find_one({
        'assignment_id': submission['assignment_id'],
        'student_id': submission['student_id']
    })
    
    return render_template('view_submission.html',
                         submission=submission,
                         assignment=assignment,
                         course=course,
                         student=student,
                         grade=grade)

@app.route('/submission/<submission_id>/grade', methods=['POST'])
@teacher_required
def grade_submission(submission_id):
    # Get submission details
    submission = submissions.find_one({'_id': ObjectId(submission_id)})
    if not submission:
        flash('Submission not found.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Get assignment and course details
    assignment = assignments.find_one({'_id': ObjectId(submission['assignment_id'])})
    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Verify teacher owns the course
    course = courses.find_one({'_id': ObjectId(assignment['course_id']), 'teacher_id': session['user_id']})
    if not course:
        flash('Access denied.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Validate grade
    try:
        score = float(request.form.get('score', 0))
        if not 0 <= score <= 100:
            raise ValueError("Score must be between 0 and 100")
    except ValueError as e:
        flash(f'Invalid grade: {str(e)}', 'danger')
        return redirect(url_for('view_submission', submission_id=submission_id))
    
    # Update or create grade
    grade_data = {
        'assignment_id': submission['assignment_id'],
        'student_id': submission['student_id'],
        'score': score,
        'feedback': request.form.get('feedback', ''),
        'updated_at': datetime.utcnow()
    }
    
    grades.update_one(
        {'assignment_id': submission['assignment_id'], 'student_id': submission['student_id']},
        {'$set': grade_data},
        upsert=True
    )
    
    flash('Grade updated successfully!', 'success')
    return redirect(url_for('view_submission', submission_id=submission_id))

@app.route('/assignment/<assignment_id>/submissions')
@teacher_required
def view_submissions(assignment_id):
    # Get assignment details
    assignment = assignments.find_one({'_id': ObjectId(assignment_id)})
    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Verify teacher owns the course
    course = courses.find_one({'_id': ObjectId(assignment['course_id']), 'teacher_id': session['user_id']})
    if not course:
        flash('Access denied.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Get all submissions for this assignment
    submissions_list = list(submissions.find({'assignment_id': assignment_id}))
    
    # Add student and grade information to each submission
    for submission in submissions_list:
        student = students.find_one({'user_id': submission['student_id']})
        if student:
            submission['student'] = student
        
        grade = grades.find_one({
            'assignment_id': assignment_id,
            'student_id': submission['student_id']
        })
        if grade:
            submission['grade'] = grade
    
    return render_template('view_submissions.html',
                         assignment=assignment,
                         course=course,
                         submissions=submissions_list)

@app.route('/course/<course_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_course(course_id):
    course = courses.find_one({'_id': ObjectId(course_id)})
    if not course:
        flash('Course not found.', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    if course['teacher_id'] != session['user_id']:
        flash('You do not have permission to delete this course.', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    # Delete all assignments for this course
    assignments.delete_many({'course_id': course_id})
    
    # Delete all enrollments for this course
    enrollments.delete_many({'course_id': course_id})
    
    # Delete the course
    courses.delete_one({'_id': ObjectId(course_id)})
    
    flash('Course and all associated data have been deleted.', 'success')
    return redirect(url_for('teacher_dashboard'))

@app.route('/student/<student_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_student(student_id):
    student = students.find_one({'_id': ObjectId(student_id)})
    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    # Delete all enrollments for this student
    enrollments.delete_many({'student_id': student_id})
    
    # Delete all submissions for this student
    submissions.delete_many({'student_id': student_id})
    
    # Delete all grades for this student
    grades.delete_many({'student_id': student_id})
    
    # Delete the student
    students.delete_one({'_id': ObjectId(student_id)})
    
    flash('Student and all associated data have been deleted.', 'success')
    return redirect(url_for('teacher_dashboard'))

@app.route('/course/<course_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_course(course_id):
    course = courses.find_one({'_id': ObjectId(course_id)})
    if not course:
        flash('Course not found.', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    if course['teacher_id'] != session['user_id']:
        flash('You do not have permission to edit this course.', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        course_data = {
            'name': request.form['name'],
            'code': request.form['code'],
            'description': request.form['description'],
            'updated_at': datetime.utcnow()
        }
        courses.update_one(
            {'_id': ObjectId(course_id)},
            {'$set': course_data}
        )
        flash('Course updated successfully!', 'success')
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('edit_course.html', course=course)

@app.route('/student/<student_id>/view')
@login_required
@teacher_required
def view_student(student_id):
    # Get student information
    student = students.find_one({'user_id': student_id})
    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    # Get all enrollments for this student
    enrolled_courses = list(enrollments.find({'student_id': student_id}))
    course_ids = [e['course_id'] for e in enrolled_courses]
    courses_list = list(courses.find({'_id': {'$in': [ObjectId(cid) for cid in course_ids]}}))
    
    # Get all submissions and grades
    submissions_list = list(submissions.find({'student_id': student_id}))
    grades_list = list(grades.find({'student_id': student_id}))
    
    # Add course and assignment information to submissions and grades
    for submission in submissions_list:
        assignment = assignments.find_one({'_id': ObjectId(submission['assignment_id'])})
        if assignment:
            submission['assignment'] = assignment
            course = courses.find_one({'_id': ObjectId(assignment['course_id'])})
            if course:
                submission['course'] = course
    
    for grade in grades_list:
        assignment = assignments.find_one({'_id': ObjectId(grade['assignment_id'])})
        if assignment:
            grade['assignment'] = assignment
            course = courses.find_one({'_id': ObjectId(assignment['course_id'])})
            if course:
                grade['course'] = course
    
    # Calculate overall statistics
    total_submissions = len(submissions_list)
    total_grades = len(grades_list)
    average_grade = sum(g['score'] for g in grades_list) / len(grades_list) if grades_list else 0
    
    return render_template('view_student.html',
                         student=student,
                         courses=courses_list,
                         submissions=submissions_list,
                         grades=grades_list,
                         total_submissions=total_submissions,
                         total_grades=total_grades,
                         average_grade=average_grade)

if __name__ == '__main__':
    app.run(debug=True) 