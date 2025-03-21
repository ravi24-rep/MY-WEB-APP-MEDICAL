from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_mail import Mail, Message
import mysql.connector
from config import db_config, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a strong secret key in production

# File upload configuration
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'png'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Mail configuration
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
mail = Mail(app)

# Function to get a database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Function to log user activity
def log_user_activity(user_id, activity_type, activity_description):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO user_activity_logs (user_id, activity_type, activity_description, activity_timestamp) VALUES (%s, %s, %s, %s)',
        (user_id, activity_type, activity_description, datetime.now())
    )
    conn.commit()
    conn.close()

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route for viewing users (Admin only)
@app.route('/admin/users')
def view_users():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id, username, email, role FROM users')
    users = cursor.fetchall()
    conn.close()

    return render_template('view_users.html', users=users)

# Route for login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email=%s AND password=%s', (email, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['email'] = user['email']  # Store email for notifications
            # Log the login activity
            log_user_activity(user['id'], 'login', f"{user['username']} logged in")
            flash('Login successful!', 'success')
            conn.close()
            return redirect(url_for('admin_dashboard' if user['role'] == 'admin' else 'user_dashboard'))
        else:
            flash('Invalid login credentials', 'danger')
        conn.close()
    return render_template('index.html')

# Route for user registration
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check if username or email already exists
    cursor.execute('SELECT * FROM users WHERE username=%s OR email=%s', (username, email))
    existing_user = cursor.fetchone()
    
    if existing_user:
        conn.close()
        if existing_user['username'] == username:
            flash('Username already exists. Please choose a different username.', 'danger')
        else:
            flash('Email already exists. Please use a different email.', 'danger')
        return redirect(url_for('login'))
    
    # If no duplicates, proceed with registration
    try:
        cursor.execute('INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, "user")', (username, email, password))
        conn.commit()
        flash('Registration successful. Please log in.', 'success')
    except mysql.connector.Error as err:
        flash(f'Registration failed: {err}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('login'))

# Route for logout
@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    username = session.get('username')
    if user_id and username:
        log_user_activity(user_id, 'logout', f"{username} logged out")
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# Route for user dashboard
@app.route('/user_dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch user's own requests
    cursor.execute('SELECT id, title, description, funding_goal, raised, status, created_at FROM fund_requests WHERE user_id=%s', (session['user_id'],))
    user_requests = cursor.fetchall()
    
    # Fetch approved requests from other users for donation
    cursor.execute('SELECT fr.id, fr.title, fr.description, fr.funding_goal, fr.raised, u.username FROM fund_requests fr JOIN users u ON fr.user_id = u.id WHERE fr.status="approved" AND fr.user_id != %s', (session['user_id'],))
    approved_requests = cursor.fetchall()
    
    # Fetch user's donation history
    cursor.execute('SELECT d.amount, d.donation_message, d.donated_at, fr.title, u.username AS recipient FROM donations d JOIN fund_requests fr ON d.request_id = fr.id JOIN users u ON fr.user_id = u.id WHERE d.donor_id=%s', (session['user_id'],))
    donation_history = cursor.fetchall()
    
    conn.close()

    return render_template('dashboard_user.html', username=session['username'], requests=user_requests, approved_requests=approved_requests, donation_history=donation_history)

# Route for admin dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT fr.*, u.username FROM fund_requests fr JOIN users u ON fr.user_id = u.id')
    requests = cursor.fetchall()
    conn.close()

    return render_template('dashboard_admin.html', requests=requests)

# Route to post fund request (User)
@app.route('/post_request', methods=['POST'])
def post_request():
    if session.get('role') != 'user':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    title = request.form['title']
    description = request.form['description']
    funding_goal = float(request.form['funding_goal'])
    user_id = session['user_id']

    # Handle file upload
    if 'documents' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('user_dashboard'))

    files = request.files.getlist('documents')
    filenames = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filenames.append(filename)

    # Save request to database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO fund_requests (user_id, title, description, funding_goal, raised, status) VALUES (%s, %s, %s, %s, %s, "pending")',
        (user_id, title, description, funding_goal, 0.0)
    )
    request_id = cursor.lastrowid

    # Save uploaded files
    for filename in filenames:
        cursor.execute('INSERT INTO request_documents (request_id, filename) VALUES (%s, %s)', (request_id, filename))
    
    # Fetch the created_at timestamp for the notification
    cursor.execute('SELECT created_at FROM fund_requests WHERE id=%s', (request_id,))
    created_at = cursor.fetchone()[0]
    
    # Log the fund request activity
    log_user_activity(user_id, 'fund_request', f"{session['username']} submitted fund request: {title}")
    
    conn.commit()
    conn.close()

    # Send email notification to user
    msg = Message('Fund Request Submitted', sender=MAIL_USERNAME, recipients=[session.get('email', 'user@example.com')])
    msg.body = f'Your fund request "{title}" was submitted on {created_at}. It is pending approval.'
    mail.send(msg)

    flash('Fund request posted successfully.', 'success')
    return redirect(url_for('user_dashboard'))

# Route to donate to a fund request (User)
@app.route('/donate/<int:request_id>', methods=['POST'])
def donate(request_id):
    if session.get('role') != 'user':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    amount = float(request.form['amount'])
    donation_message = request.form.get('donation_message', '')  # Get the donation message (optional)
    donor_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify the request exists and is approved
    cursor.execute('SELECT * FROM fund_requests WHERE id=%s AND status="approved"', (request_id,))
    fund_request = cursor.fetchone()
    if not fund_request:
        flash('Invalid or unapproved fund request.', 'danger')
        conn.close()
        return redirect(url_for('user_dashboard'))

    # Insert the donation
    cursor.execute('INSERT INTO donations (request_id, donor_id, amount, donation_message) VALUES (%s, %s, %s, %s)', (request_id, donor_id, amount, donation_message))

    # Update the raised amount in fund_requests
    cursor.execute('UPDATE fund_requests SET raised = raised + %s WHERE id=%s', (amount, request_id))

    # Fetch the recipient's email and fund request title for notification
    cursor.execute('SELECT u.email, fr.title FROM fund_requests fr JOIN users u ON fr.user_id = u.id WHERE fr.id=%s', (request_id,))
    result = cursor.fetchone()
    recipient_email = result[0]
    request_title = result[1]

    # Log the donation activity
    log_user_activity(donor_id, 'donation', f"{session['username']} donated ${amount} to {request_title}")

    conn.commit()
    conn.close()

    # Send email notification to the recipient
    msg = Message('New Donation Received', sender=MAIL_USERNAME, recipients=[recipient_email])
    msg.body = f'You received a donation of ${amount} for your fund request "{request_title}" from {session["username"]}.'
    if donation_message:
        msg.body += f'\nMessage from donor: {donation_message}'
    mail.send(msg)

    flash(f'Successfully donated ${amount} to the fund request.', 'success')
    return redirect(url_for('user_dashboard'))

# Route to view documents (Admin)
@app.route('/view_documents/<int:request_id>')
def view_documents(request_id):
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT filename FROM request_documents WHERE request_id=%s', (request_id,))
    files = cursor.fetchall()
    conn.close()

    return render_template('view_documents.html', request_id=request_id, files=files)

# Route to update fund request status (Admin)
@app.route('/update_request/<int:request_id>/<string:action>')
def update_request(request_id, action):
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    status = 'approved' if action == 'approve' else 'rejected'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE fund_requests SET status=%s WHERE id=%s', (status, request_id))
    conn.commit()

    # Fetch user email and created_at for notification
    cursor.execute('SELECT u.email, fr.created_at FROM fund_requests fr JOIN users u ON fr.user_id = u.id WHERE fr.id=%s', (request_id,))
    result = cursor.fetchone()
    user_email = result[0]
    created_at = result[1]
    conn.close()

    # Send email notification
    msg = Message('Fund Request Status Update', sender=MAIL_USERNAME, recipients=[user_email])
    msg.body = f'Your fund request #{request_id}, submitted on {created_at}, has been {status}.'
    mail.send(msg)

    flash(f'Request #{request_id} {status}.', 'info')
    return redirect(url_for('admin_dashboard'))

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)