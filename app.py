from flask import Flask, request, redirect, session, send_file
import sqlite3
import pandas as pd
import io
from staff_dashboard import staff_bp
from teacher_dashboard import teacher_bp
from dashboard import dashboard_bp
from werkzeug.security import generate_password_hash, check_password_hash

# --- Database helpers ---

def get_db():
    conn = sqlite3.connect('school.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_cred_db():
    conn = sqlite3.connect('credential.db')
    conn.row_factory = sqlite3.Row
    return conn

def is_hashed(password):
    return isinstance(password, str) and password.startswith(("pbkdf2:", "scrypt:", "argon2:"))

def verify_and_upgrade_password(db, table, user_id, stored_password, provided_password):
    if not stored_password:
        return False
    if is_hashed(stored_password):
        return check_password_hash(stored_password, provided_password)
    if stored_password == provided_password:
        new_hash = generate_password_hash(provided_password)
        db.execute(f"UPDATE {table} SET password=? WHERE id=?", (new_hash, user_id))
        db.commit()
        return True
    return False

# --- Initialize DBs ---

def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY,
                teacher_id INTEGER,
                class TEXT,
                grade TEXT,
                student_name TEXT,
                student_score INTEGER,
                teacher_comment TEXT
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                class TEXT NOT NULL,
                grade TEXT NOT NULL,
                gender TEXT,
                dob TEXT,
                emergency_contact TEXT,
                teacher_id INTEGER
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                amount REAL,
                pay_date TEXT,
                next_pay_date TEXT,
                status TEXT,
                discount REAL DEFAULT 0.15,
                khr_rate INTEGER DEFAULT 4100,
                FOREIGN KEY(student_id) REFERENCES students(id)
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                invoice_no TEXT,
                file_path TEXT,
                created_at TEXT,
                FOREIGN KEY(student_id) REFERENCES students(id)
            )
        ''')
    with get_cred_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                gender TEXT,
                status TEXT DEFAULT 'active'
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS staffs (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                gender TEXT,
                status TEXT DEFAULT 'active'
            )
        ''')
        for table in ("teachers", "staffs"):
            columns = [row["name"] for row in db.execute(f"PRAGMA table_info({table})")]
            if "status" not in columns:
                db.execute(f"ALTER TABLE {table} ADD COLUMN status TEXT DEFAULT 'active'")
                db.execute(f"UPDATE {table} SET status='active' WHERE status IS NULL")

# --- Flask App Setup ---

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.register_blueprint(staff_bp)
app.register_blueprint(teacher_bp)
app.register_blueprint(dashboard_bp)

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_cred_db()
        teacher = db.execute(
            'SELECT * FROM teachers WHERE username=? AND status=?',
            (username, 'active')
        ).fetchone()
        if teacher and verify_and_upgrade_password(db, 'teachers', teacher['id'], teacher['password'], password):
            session['teacher_id'] = teacher['id']
            return redirect('/teacher-dashboard')
        else:
            message = 'Invalid username or password.'
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>LearnWell</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/login.css">
    </head>
    <body>
        <div class="login-container">
            <div class="login-card">
                <h2>LearnWell Academy</h2>
                <form method="post">
                    <div class="mb-3">
                        <label class="form-label">Teacher Name</label>
                        <input name="username" class="form-control" placeholder="Enter your username" autocomplete="username" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Password</label>
                        <input name="password" type="password" class="form-control" placeholder="Enter your password" autocomplete="current-password" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Sign in</button>
                </form>
                <div class="form-message {'show' if message else ''}" role="alert">{message}</div>
                <div class="switch-admin">
                    <form action="/staff-login" method="get">
                        <button type="submit">Switch to Staff</button>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_cred_db()
        admin = db.execute('SELECT * FROM admins WHERE username=?', (username,)).fetchone()
        if admin and verify_and_upgrade_password(db, 'admins', admin['id'], admin['password'], password):
            session['admin_logged_in'] = True
            return redirect('/admin')
        else:
            message = 'Invalid admin username or password.'
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Admin Login</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/login.css">
    </head>
    <body>
        <div class="login-container">
            <div class="login-card">
                <h2>Admin Login</h2>
                <form method="post">
                    <div class="mb-3">
                        <label class="form-label">Admin Username</label>
                        <input name="username" class="form-control" placeholder="Enter admin username" autocomplete="username" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Admin Password</label>
                        <input name="password" type="password" class="form-control" placeholder="Enter admin password" autocomplete="current-password" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Sign in</button>
                </form>
                <div class="form-message {'show' if message else ''}" role="alert">{message}</div>
                <div class="switch-admin">
                    <form action="/" method="get">
                        <button type="submit">Switch to Teacher</button>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/export')
def export_excel():
    db = get_db()
    cred_db = get_cred_db()
    teachers = {row['id']: row['username'] for row in cred_db.execute('SELECT id, username FROM teachers')}
    df = pd.read_sql_query('SELECT * FROM reports', db)
    df['teacher'] = df['teacher_id'].map(teachers)
    df = df[['teacher', 'class', 'grade', 'student_name', 'student_score', 'teacher_comment']]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="report.xlsx", as_attachment=True)

@app.route('/staff-login', methods=['GET', 'POST'])
def staff_login():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_cred_db()
        staff = db.execute(
            'SELECT * FROM staffs WHERE username=? AND status=?',
            (username, 'active')
        ).fetchone()
        if staff and verify_and_upgrade_password(db, 'staffs', staff['id'], staff['password'], password):
            session['staff_id'] = staff['id']
            return redirect('/staff-dashboard')
        else:
            message = 'Invalid staff username or password.'
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Staff Login</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/login.css">
    </head>
    <body>
        <div class="login-container">
            <div class="login-card">
                <h2>Staff Login</h2>
                <form method="post">
                    <div class="mb-3">
                        <label class="form-label">Staff Username</label>
                        <input name="username" class="form-control" placeholder="Enter staff username" autocomplete="username" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Staff Password</label>
                        <input name="password" type="password" class="form-control" placeholder="Enter staff password" autocomplete="current-password" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Sign in</button>
                </form>
                <div class="form-message {'show' if message else ''}" role="alert">{message}</div>
                <div class="switch-admin">
                    <form action="/" method="get">
                        <button type="submit">Switch to Teacher</button>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/admin/add-user', methods=['GET', 'POST'])
def admin_add_user():
    if not session.get('admin_logged_in'):
        return redirect('/admin-login')
    message = ''
    if request.method == 'POST':
        user_type = request.form['user_type']
        username = request.form['username']
        password = request.form['password']
        gender = request.form.get('gender')
        if user_type not in ['admin', 'teacher', 'staff']:
            message = "Please select a valid user type."
        elif not username or not password:
            message = "Username and password cannot be empty."
        elif user_type in ['teacher', 'staff'] and not gender:
            message = "Gender is required for teacher and staff."
        else:
            try:
                db = get_cred_db()
                password_hash = generate_password_hash(password)
                if user_type in ['teacher', 'staff']:
                    db.execute(
                        f"INSERT INTO {user_type}s (username, password, gender) VALUES (?, ?, ?)",
                        (username, password_hash, gender)
                    )
                else:
                    db.execute(
                        f"INSERT INTO {user_type}s (username, password) VALUES (?, ?)",
                        (username, password_hash)
                    )
                db.commit()
                message = f"{user_type.capitalize()} added successfully!"
            except Exception as e:
                message = f"Database Error: {str(e)}"
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Add User</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/dashboard.css">
        <script>
        function toggleGender() {{
            var userType = document.getElementsByName('user_type')[0].value;
            var genderRow = document.getElementById('gender_row');
            if (userType === 'teacher' || userType === 'staff') {{
                genderRow.style.display = '';
            }} else {{
                genderRow.style.display = 'none';
            }}
        }}
        </script>
    </head>
    <body onload="toggleGender()">
    <div class="container-fluid">
      <div class="row">
        <nav class="col-12 col-md-2 sidebar d-flex flex-column">
          <div class="brand">LearnWell</div>
          <a href="/admin">Dashboards</a>
          <a href="/export">Export</a>
          <a href="/admin/add-user" class="active">Add User</a>
          <a href="/admin/invoices">Invoices</a>
          <a href="/admin/teachers">Teachers</a>
          <a href="/admin/staffs">Staffs</a>
          <a href="/admin/students">Students</a>
          <div class="mt-auto">
            <a href="/admin-logout" class="logout">Logout</a>
          </div>
        </nav>
        <main class="col-12 col-md-10 ms-sm-auto px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h2>Add User</h2>
          </div>
          <div class="card shadow-sm">
            <div class="card-body">
              <form method="post">
                <div class="row g-3">
                  <div class="col-md-6">
                    <label class="form-label">User Type</label>
                    <select name="user_type" class="form-control" onchange="toggleGender()" required>
                      <option value="">Select</option>
                      <option value="admin">Admin</option>
                      <option value="teacher">Teacher</option>
                      <option value="staff">Staff</option>
                    </select>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Username</label>
                    <input name="username" class="form-control" placeholder="Create a username" required>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Password</label>
                    <input name="password" type="password" class="form-control" placeholder="Create a password" required>
                  </div>
                  <div class="col-md-6" id="gender_row" style="display:none;">
                    <label class="form-label">Gender</label>
                    <select name="gender" class="form-control">
                      <option value="">Select</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                  <div class="col-12 d-flex gap-2">
                    <button type="submit" class="btn btn-primary">Add User</button>
                    <a href="/admin" class="btn btn-light">Back</a>
                  </div>
                </div>
              </form>
              <div class="mt-3">
                <span class="text-warning fw-semibold">{message}</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    init_db()
    app.run(debug = True, host='0.0.0.0', port=8001)
