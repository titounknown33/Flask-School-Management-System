from flask import Blueprint, session, redirect, send_file, request, current_app, render_template_string, flash
import pandas as pd
import io
from werkzeug.security import check_password_hash

dashboard_bp = Blueprint('dashboard', __name__)

def get_db():
    import sqlite3
    conn = sqlite3.connect('school.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_cred_db():
    import sqlite3
    conn = sqlite3.connect('credential.db')
    conn.row_factory = sqlite3.Row
    return conn

@dashboard_bp.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect('/admin-login')
    db = get_db()
    cred_db = get_cred_db()
    teachers = list(cred_db.execute('SELECT id, username FROM teachers'))
    classes = list(db.execute('SELECT DISTINCT class FROM reports'))
    staff_count = cred_db.execute('SELECT COUNT(*) FROM staffs').fetchone()[0]

    selected_teacher = None
    selected_class = None
    if request.method == 'POST':
        selected_teacher = request.form.get('teacher')
        selected_class = request.form.get('class')
    else:
        selected_teacher = session.get('admin_filter_teacher')
        selected_class = session.get('admin_filter_class')

    # Build teacher dictionary for fast lookup
    teacher_dict = {t['id']: t['username'] for t in teachers}

    # Build the reports query with filters
    query = 'SELECT * FROM reports'
    params = []
    filters = []
    if selected_teacher:
        filters.append('teacher_id=?')
        params.append(selected_teacher)
    if selected_class:
        filters.append('class=?')
        params.append(selected_class)
    if filters:
        query += ' WHERE ' + ' AND '.join(filters)
    query += ' ORDER BY id DESC'

    reports = db.execute(query, params).fetchall()

    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Admin Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
    <div class="container-fluid">
      <div class="row">
        <!-- Sidebar -->
        <nav class="col-md-2 d-none d-md-block sidebar py-4 d-flex flex-column" style="min-height: 100vh;">
          <div class="flex-grow-1">
            <div class="text-center mb-4">
              <h4>School Admin</h4>
            </div>
            <a href="/admin" class="active">Dashboard</a>
            <a href="/export">Export</a>
            <a href="/admin/add-user">Add User</a>
            <a href="/admin/invoices">Invoices</a>
            <a href="/admin/teachers">Teachers</a>
            <a href="/admin/staffs">Staffs</a>
            <a href="/admin/students">Students</a>
            {clear_db_link}
          </div>
          <a href="/admin-logout" class="mb-2">Logout</a>
        </nav>
        <!-- Main -->
        <main class="col-md-10 ms-sm-auto px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h2>Welcome Back, Admin!</h2>
          </div>
          <!-- Cards -->
          <div class="row mb-4">
            <div class="col-md-3">
              <div class="card p-3 shadow-sm">
                <div class="text-muted">Total Students</div>
                <h4>{student_count}</h4>
              </div>
            </div>
            <div class="col-md-3">
              <div class="card p-3 shadow-sm">
                <div class="text-muted">Total Teachers</div>
                <h4>{teacher_count}</h4>
              </div>
            </div>
            <div class="col-md-3">
              <div class="card p-3 shadow-sm">
                <div class="text-muted">Total Staff</div>
                <h4>{staff_count}</h4>
              </div>
            </div>
            <div class="col-md-3">
              <div class="card p-3 shadow-sm">
                <div class="text-muted">Total Classes</div>
                <h4>{class_count}</h4>
              </div>
            </div>
            <div class="col-md-3">
              <div class="card p-3 shadow-sm">
                <div class="text-muted">Reports</div>
                <h4>{report_count}</h4>
              </div>
            </div>
          </div>
          <!-- Filters -->
          <form method="post" class="row g-3 mb-4">
            <div class="col-md-4">
              <label class="form-label">View Teacher</label>
              <select name="teacher" class="form-select">
                <option value="">All</option>
    '''.format(
        student_count=db.execute('SELECT COUNT(*) FROM reports').fetchone()[0],
        teacher_count=len(teachers),
        staff_count=cred_db.execute('SELECT COUNT(*) FROM staffs').fetchone()[0],
        class_count=len(classes),
        report_count=db.execute('SELECT COUNT(*) FROM reports').fetchone()[0],
        clear_db_link=('<a href="/admin/clear-database-confirm" style="color:red;">Clear Database</a>' if current_app.debug else '')
    )

    for t in teachers:
        sel = 'selected' if selected_teacher and str(t['id']) == str(selected_teacher) else ''
        html += f'<option value="{t["id"]}" {sel}>{t["username"]}</option>'
    html += '''
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label">View by Class</label>
              <select name="class" class="form-select">
                <option value="">All</option>
    '''
    for c in classes:
        sel = 'selected' if selected_class and c['class'] == selected_class else ''
        html += f'<option value="{c["class"]}" {sel}>{c["class"]}</option>'
    html += '''
              </select>
            </div>
            <div class="col-md-4 d-flex align-items-end">
              <button type="submit" class="btn btn-primary w-100">Filter</button>
            </div>
          </form>
          <!-- Data Table -->
          <div class="card shadow-sm">
            <div class="card-body">
              <h5 class="card-title">Student Data Table</h5>
              <div class="table-responsive">
                <table class="table align-middle">
                  <thead>
                    <tr>
                      <th>Teacher</th>
                      <th>Class</th>
                      <th>Grade</th>
                      <th>Student Name</th>
                      <th>Student Score</th>
                      <th>Teacher Comment</th>
                      <th>Edit</th>
                      <th>Delete</th>
                    </tr>
                  </thead>
                  <tbody>
    '''
    for row in reports:
        teacher_name = teacher_dict.get(row["teacher_id"], "Unknown")
        html += f'''
        <tr>
            <td>{teacher_name}</td>
            <td>{row["class"]}</td>
            <td>{row["grade"]}</td>
            <td>{row["student_name"]}</td>
            <td>{row["student_score"]}</td>
            <td>{row["teacher_comment"]}</td>
            <td><a href="/admin-edit/{row["id"]}" class="btn btn-sm btn-outline-primary">Edit</a></td>
            <td><a href="/admin-delete/{row["id"]}" class="btn btn-sm btn-outline-danger" onclick="return confirm('Are you sure?')">Delete</a></td>
        </tr>
        '''
    html += '''
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
    </body>
    </html>
    '''
    return html

@dashboard_bp.route('/export')
def export_excel():
    db = get_db()
    cred_db = get_cred_db()
    teachers = {row['id']: row['username'] for row in cred_db.execute('SELECT id, username FROM teachers')}

    # Get filters from session
    selected_teacher = session.get('admin_filter_teacher')
    selected_class = session.get('admin_filter_class')

    query = 'SELECT * FROM reports'
    params = []
    filters = []
    if selected_teacher:
        filters.append('teacher_id=?')
        params.append(selected_teacher)
    if selected_class:
        filters.append('class=?')
        params.append(selected_class)
    if filters:
        query += ' WHERE ' + ' AND '.join(filters)

    df = pd.read_sql_query(query, db, params=params)
    df['teacher'] = df['teacher_id'].map(teachers)
    df = df[['teacher', 'class', 'grade', 'student_name', 'student_score', 'teacher_comment']]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="report.xlsx", as_attachment=True)

@dashboard_bp.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin-login')

@dashboard_bp.route('/admin/clear-database')
def clear_database():
    if not current_app.debug:
        return "Not allowed.", 403
    db = get_db()
    db.execute("DELETE FROM reports")
    db.execute("DELETE FROM students")
    db.execute("DELETE FROM payments")
    db.commit()
    cred_db = get_cred_db()
    cred_db.execute("DELETE FROM teachers")
    cred_db.execute("DELETE FROM admins")
    cred_db.execute("DELETE FROM staffs")
    cred_db.commit()
    return "Database cleared."

@dashboard_bp.route('/admin/clear-database-confirm', methods=['GET', 'POST'])
def clear_database_confirm():
    if not current_app.debug:
        return "Not allowed.", 403
    if request.method == 'POST':
        password = request.form.get('password')
        cred_db = get_cred_db()
        admin = cred_db.execute("SELECT * FROM admins WHERE username = ?", (session.get('admin_username'),)).fetchone()
        if admin and admin['password'] == password:
            return redirect('/admin/clear-database')
        else:
            flash("Incorrect password. Database NOT cleared.", "danger")
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Confirm Clear Database</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
    <div class="container mt-5">
      <div class="alert alert-danger">
        <h4>Are you sure you want to clear the entire database?</h4>
        <p>This action cannot be undone. Please re-enter your admin password to confirm.</p>
      </div>
      <form method="post">
        <div class="mb-3">
          <label for="password" class="form-label">Admin Password</label>
          <input type="password" class="form-control" id="password" name="password" required>
        </div>
        <button type="submit" class="btn btn-danger">Yes, Clear Database</button>
        <a href="/admin" class="btn btn-secondary">Cancel</a>
      </form>
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          <div class="mt-3">
            {% for category, message in messages %}
              <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}
    </div>
    </body>
    </html>
    ''')
@dashboard_bp.route('/admin/invoices')
def admin_invoices():
    db = get_db()
    cred_db = get_cred_db()
    invoices = db.execute('''
        SELECT invoices.*, students.name AS student_name
        FROM invoices
        JOIN students ON invoices.student_id = students.id
        ORDER BY invoices.created_at DESC
    ''').fetchall()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Invoice List</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
    <div class="container mt-4">
        <h2>Invoice List</h2>
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Invoice No</th>
                    <th>Student Name</th>
                    <th>Date</th>
                    <th>View</th>
                    <th>Download</th>
                </tr>
            </thead>
            <tbody>
            {% for inv in invoices %}
                <tr>
                    <td>{{ inv['invoice_no'] }}</td>
                    <td>{{ inv['student_name'] }}</td>
                    <td>{{ inv['created_at'][:19].replace('T', ' ') }}</td>
                    <td>
                        <a href="/admin/view-invoice/{{ inv['id'] }}" class="btn btn-sm btn-info" target="_blank">View</a>
                    </td>
                    <td>
                        <a href="/admin/download-invoice/{{ inv['id'] }}" class="btn btn-sm btn-success">Download</a>
                    </td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
    </body>
    </html>
    ''', invoices=invoices)

@dashboard_bp.route('/admin/view-invoice/<int:invoice_id>')
def view_invoice(invoice_id):
    db = get_db()
    invoice = db.execute('SELECT * FROM invoices WHERE id=?', (invoice_id,)).fetchone()
    if not invoice:
        return "Invoice not found", 404
    with open(invoice['file_path'], 'r', encoding='utf-8') as f:
        html = f.read()
    return html

@dashboard_bp.route('/admin/download-invoice/<int:invoice_id>')
def download_invoice(invoice_id):
    db = get_db()
    invoice = db.execute('SELECT * FROM invoices WHERE id=?', (invoice_id,)).fetchone()
    if not invoice:
        return "Invoice not found", 404
    return send_file(invoice['file_path'], as_attachment=True)

@dashboard_bp.route('/admin/teachers')
def admin_teachers():
    cred_db = get_cred_db()
    teachers = cred_db.execute('SELECT id, username FROM teachers').fetchall()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Teacher List</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
    <div class="container mt-4">
      <div class="card shadow-sm">
        <div class="card-body">
          <h5 class="card-title">Teacher List</h5>
          <div class="table-responsive">
            <table class="table table-bordered table-striped align-middle mb-0">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                    </tr>
                </thead>
                <tbody>
                {% for t in teachers %}
                    <tr>
                        <td>{{ t['id'] }}</td>
                        <td>{{ t['username'] }}</td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
          </div>
          <a href="/admin" class="btn btn-secondary mt-3">Back to Dashboard</a>
        </div>
      </div>
    </div>
    </body>
    </html>
    ''', teachers=teachers)

@dashboard_bp.route('/admin/staffs')
def admin_staffs():
    cred_db = get_cred_db()
    staffs = cred_db.execute('SELECT id, username, gender FROM staffs').fetchall()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Staff List</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
    <div class="container mt-4">
      <div class="card shadow-sm">
        <div class="card-body">
          <h5 class="card-title">Staff List</h5>
          <div class="table-responsive">
            <table class="table table-bordered table-striped align-middle mb-0">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                        <th>Gender</th>
                    </tr>
                </thead>
                <tbody>
                {% for s in staffs %}
                    <tr>
                        <td>{{ s['id'] }}</td>
                        <td>{{ s['username'] }}</td>
                        <td>{{ s['gender'] or '' }}</td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
          </div>
          <a href="/admin" class="btn btn-secondary mt-3">Back to Dashboard</a>
        </div>
      </div>
    </div>
    </body>
    </html>
    ''', staffs=staffs)

@dashboard_bp.route('/admin/students')
def admin_students():
    db = get_db()
    students = db.execute('SELECT id, name, class, grade, teacher_id FROM students').fetchall()
    # Get teacher names for display
    cred_db = get_cred_db()
    teachers = {row['id']: row['username'] for row in cred_db.execute('SELECT id, username FROM teachers')}
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Student List</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
    <div class="container mt-4">
      <div class="card shadow-sm">
        <div class="card-body">
          <h5 class="card-title">Student List</h5>
          <div class="table-responsive">
            <table class="table table-bordered table-striped align-middle mb-0">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Class</th>
                        <th>Grade</th>
                        <th>Teacher</th>
                    </tr>
                </thead>
                <tbody>
                {% for s in students %}
                    <tr>
                        <td>{{ s['id'] }}</td>
                        <td>{{ s['name'] }}</td>
                        <td>{{ s['class'] }}</td>
                        <td>{{ s['grade'] }}</td>
                        <td>{{ teachers.get(s['teacher_id'], 'Unknown') }}</td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
          </div>
          <a href="/admin" class="btn btn-secondary mt-3">Back to Dashboard</a>
        </div>
      </div>
    </div>
    </body>
    </html>
    ''', students=students, teachers=teachers)
