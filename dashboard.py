from flask import Blueprint, session, redirect, send_file, request, current_app, render_template_string, flash
import pandas as pd
import io
from werkzeug.security import check_password_hash, generate_password_hash

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

@dashboard_bp.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect('/admin-login')
    db = get_db()
    cred_db = get_cred_db()
    teachers = list(cred_db.execute('SELECT id, username FROM teachers'))
    classes = list(db.execute('SELECT DISTINCT class FROM reports'))
    student_classes = list(db.execute('SELECT DISTINCT class FROM students'))
    staff_count = cred_db.execute('SELECT COUNT(*) FROM staffs').fetchone()[0]

    report_teacher = None
    report_class = None
    report_student = None
    student_teacher = None
    student_class = None
    student_name = None
    if request.method == 'POST':
        filter_type = request.form.get('filter_type')
        if filter_type == 'reports':
            report_teacher = request.form.get('teacher')
            report_class = request.form.get('class')
            report_student = request.form.get('student_name')
        elif filter_type == 'students':
            student_teacher = request.form.get('teacher')
            student_class = request.form.get('class')
            student_name = request.form.get('student_name')

    # Build teacher dictionary for fast lookup
    teacher_dict = {t['id']: t['username'] for t in teachers}

    # Build the reports query with filters
    query = 'SELECT * FROM reports'
    params = []
    filters = []
    if report_teacher:
        filters.append('teacher_id=?')
        params.append(report_teacher)
    if report_class:
        filters.append('class=?')
        params.append(report_class)
    if report_student:
        filters.append('student_name LIKE ?')
        params.append(f"%{report_student}%")
    if filters:
        query += ' WHERE ' + ' AND '.join(filters)
    query += ' ORDER BY id DESC'

    reports = db.execute(query, params).fetchall()
    student_query = 'SELECT * FROM students'
    student_params = []
    student_filters = []
    if student_teacher:
        student_filters.append('teacher_id=?')
        student_params.append(student_teacher)
    if student_class:
        student_filters.append('class=?')
        student_params.append(student_class)
    if student_name:
        student_filters.append('name LIKE ?')
        student_params.append(f"%{student_name}%")
    if student_filters:
        student_query += ' WHERE ' + ' AND '.join(student_filters)
    student_query += ' ORDER BY id DESC'
    students = db.execute(student_query, student_params).fetchall()

    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Admin Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
    <div class="container-fluid">
      <div class="row">
        <!-- Sidebar -->
        <nav class="col-12 col-md-2 sidebar d-flex flex-column">
          <div class="brand">LearnWell</div>
          <a href="/admin" class="active">Dashboards</a>
          <a href="/export">Export</a>
          <a href="/admin/add-user">Add User</a>
          <a href="/admin/invoices">Invoices</a>
          <a href="/admin/teachers">Teachers</a>
          <a href="/admin/staffs">Staffs</a>
          <a href="/admin/students">Students</a>
          {clear_db_link}
          <div class="mt-auto">
            <a href="/admin-logout" class="logout">Logout</a>
          </div>
        </nav>
        <!-- Main -->
        <main class="col-12 col-md-10 ms-sm-auto px-4">
          <div class="topbar">
            <div class="left">
              <h3 style="margin:0;">Project overview</h3>
            </div>
            <div style="display:flex; gap:10px; align-items:center;">
              <input class="form-control search" placeholder="Search" />
            </div>
          </div>

          <!-- Summary cards row -->
          <div class="row mb-4">
            <div class="col-md-2 col-6 mb-3">
              <div class="card">
                <div class="card-body text-center">
                  <div class="stat">Students</div>
                  <div class="stat-value">{student_count}</div>
                </div>
              </div>
            </div>
            <div class="col-md-2 col-6 mb-3">
              <div class="card">
                <div class="card-body text-center">
                  <div class="stat">Teachers</div>
                  <div class="stat-value">{teacher_count}</div>
                </div>
              </div>
            </div>
            <div class="col-md-2 col-6 mb-3">
              <div class="card">
                <div class="card-body text-center">
                  <div class="stat">Staff</div>
                  <div class="stat-value">{staff_count}</div>
                </div>
              </div>
            </div>
            <div class="col-md-2 col-6 mb-3">
              <div class="card">
                <div class="card-body text-center">
                  <div class="stat">Classes</div>
                  <div class="stat-value">{class_count}</div>
                </div>
              </div>
            </div>
            <div class="col-md-2 col-6 mb-3">
              <div class="card">
                <div class="card-body text-center">
                  <div class="stat">Reports</div>
                  <div class="stat-value">{report_count}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Reports Table -->
          <div class="card shadow-sm">
            <div class="card-body">
              <h5 class="card-title">Reports Table</h5>
              <form method="post" class="row g-3 mb-3" data-auto-submit="true">
                <input type="hidden" name="filter_type" value="reports">
                <div class="col-md-4">
                  <label class="form-label">View Teacher</label>
                  <select name="teacher" class="form-select">
                    <option value="">All</option>
    '''.format(
        student_count=db.execute('SELECT COUNT(*) FROM students').fetchone()[0],
        teacher_count=len(teachers),
        staff_count=cred_db.execute('SELECT COUNT(*) FROM staffs').fetchone()[0],
        class_count=len(classes),
        report_count=db.execute('SELECT COUNT(*) FROM reports').fetchone()[0],
        clear_db_link=('<a href="/admin/clear-database-confirm" class="clear-db">Clear Database</a>' if current_app.debug else '')
    )

    for t in teachers:
        sel = 'selected' if report_teacher and str(t['id']) == str(report_teacher) else ''
        html += f'<option value="{t["id"]}" {sel}>{t["username"]}</option>'
    html += f'''
                  </select>
                </div>
                <div class="col-md-4">
                  <label class="form-label">View by Class</label>
                  <select name="class" class="form-select">
                    <option value="">All</option>
    '''
    for c in classes:
        sel = 'selected' if report_class and c['class'] == report_class else ''
        html += f'<option value="{c["class"]}" {sel}>{c["class"]}</option>'
    html += f'''
                  </select>
                </div>
                <div class="col-md-4">
                  <label class="form-label">Student Name</label>
                  <input name="student_name" class="form-control" placeholder="Search by name" value="{report_student or ''}">
                </div>
                <div class="col-12">
                  <button type="submit" class="btn btn-primary">Filter</button>
                </div>
              </form>
              <div class="table-responsive">
                <table class="table align-middle table-hover">
                  <thead>
                    <tr>
                      <th>Teacher</th>
                      <th>Class</th>
                      <th>Grade</th>
                      <th>Student Name</th>
                      <th>Score</th>
                      <th>Comment</th>
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
        </tr>
        '''
    html += '''
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div class="card shadow-sm mt-4">
            <div class="card-body">
              <h5 class="card-title">Student Data Table</h5>
              <form method="post" class="row g-3 mb-3" data-auto-submit="true">
                <input type="hidden" name="filter_type" value="students">
                <div class="col-md-4">
                  <label class="form-label">View Teacher</label>
                  <select name="teacher" class="form-select">
                    <option value="">All</option>
    '''
    for t in teachers:
        sel = 'selected' if student_teacher and str(t['id']) == str(student_teacher) else ''
        html += f'<option value="{t["id"]}" {sel}>{t["username"]}</option>'
    html += '''
                  </select>
                </div>
                <div class="col-md-4">
                  <label class="form-label">View by Class</label>
                  <select name="class" class="form-select">
                    <option value="">All</option>
    '''
    for c in student_classes:
        sel = 'selected' if student_class and c['class'] == student_class else ''
        html += f'<option value="{c["class"]}" {sel}>{c["class"]}</option>'
    html += f'''
                  </select>
                </div>
                <div class="col-md-4">
                  <label class="form-label">Student Name</label>
                  <input name="student_name" class="form-control" placeholder="Search by name" value="{student_name or ''}">
                </div>
                <div class="col-12">
                  <button type="submit" class="btn btn-primary">Filter</button>
                </div>
              </form>
              <div class="table-responsive">
                <table class="table align-middle table-hover">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Class</th>
                      <th>Grade</th>
                      <th>Teacher</th>
                    </tr>
                  </thead>
                  <tbody>
    '''
    for row in students:
        teacher_name = teacher_dict.get(row["teacher_id"], "Unknown")
        html += f'''
        <tr>
            <td>{row["name"]}</td>
            <td>{row["class"]}</td>
            <td>{row["grade"]}</td>
            <td>{teacher_name}</td>
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
    <script>
      (function () {
        var forms = document.querySelectorAll('form[data-auto-submit="true"]');
        forms.forEach(function (form) {
          var timeoutId;
          var inputs = form.querySelectorAll('input[type="text"], input[type="search"]');
          inputs.forEach(function (input) {
            input.addEventListener('input', function () {
              clearTimeout(timeoutId);
              timeoutId = setTimeout(function () {
                form.submit();
              }, 400);
            });
          });
          var selects = form.querySelectorAll('select');
          selects.forEach(function (select) {
            select.addEventListener('change', function () {
              form.submit();
            });
          });
        });
      })();
    </script>
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
        if admin and verify_and_upgrade_password(cred_db, 'admins', admin['id'], admin['password'], password):
            return redirect('/admin/clear-database')
        else:
            flash("Incorrect password. Database NOT cleared.", "danger")
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Confirm Clear Database</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
    <div class="container-fluid">
      <div class="row">
        <nav class="col-12 col-md-2 sidebar d-flex flex-column">
          <div class="brand">LearnWell</div>
          <a href="/admin">Dashboards</a>
          <a href="/export">Export</a>
          <a href="/admin/add-user">Add User</a>
          <a href="/admin/invoices">Invoices</a>
          <a href="/admin/teachers">Teachers</a>
          <a href="/admin/staffs">Staffs</a>
          <a href="/admin/students">Students</a>
          <a href="/admin/clear-database-confirm" class="active">Clear Database</a>
          <div class="mt-auto">
            <a href="/admin-logout" class="logout">Logout</a>
          </div>
        </nav>
        <main class="col-12 col-md-10 ms-sm-auto px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h2>Confirm Clear Database</h2>
          </div>
          <div class="card shadow-sm">
            <div class="card-body">
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
                <a href="/admin" class="btn btn-light">Cancel</a>
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
          </div>
        </main>
      </div>
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
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
    <div class="container-fluid">
      <div class="row">
        <nav class="col-12 col-md-2 sidebar d-flex flex-column">
          <div class="brand">LearnWell</div>
          <a href="/admin">Dashboards</a>
          <a href="/export">Export</a>
          <a href="/admin/add-user">Add User</a>
          <a href="/admin/invoices" class="active">Invoices</a>
          <a href="/admin/teachers">Teachers</a>
          <a href="/admin/staffs">Staffs</a>
          <a href="/admin/students">Students</a>
          <div class="mt-auto">
            <a href="/admin-logout" class="logout">Logout</a>
          </div>
        </nav>
        <main class="col-12 col-md-10 ms-sm-auto px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h2>Invoice List</h2>
          </div>
          <div class="card shadow-sm">
            <div class="card-body">
              <div class="table-responsive">
                <table class="table align-middle table-hover">
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
            </div>
          </div>
        </main>
      </div>
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
    teachers = cred_db.execute('SELECT id, username, status FROM teachers').fetchall()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Teacher List</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
    <div class="container-fluid">
      <div class="row">
        <nav class="col-12 col-md-2 sidebar d-flex flex-column">
          <div class="brand">LearnWell</div>
          <a href="/admin">Dashboards</a>
          <a href="/export">Export</a>
          <a href="/admin/add-user">Add User</a>
          <a href="/admin/invoices">Invoices</a>
          <a href="/admin/teachers" class="active">Teachers</a>
          <a href="/admin/staffs">Staffs</a>
          <a href="/admin/students">Students</a>
          <div class="mt-auto">
            <a href="/admin-logout" class="logout">Logout</a>
          </div>
        </nav>
        <main class="col-12 col-md-10 ms-sm-auto px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h2>Teacher List</h2>
          </div>
          <div class="card shadow-sm">
            <div class="card-body">
              <div class="table-responsive">
                <table class="table align-middle table-hover mb-0">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Username</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                  {% for t in teachers %}
                    <tr>
                      <td>{{ t['id'] }}</td>
                      <td>{{ t['username'] }}</td>
                      <td>
                        {% if t['status'] == 'standby' %}
                          <span class="badge bg-warning text-dark">Standby</span>
                        {% else %}
                          <span class="badge bg-success">Active</span>
                        {% endif %}
                      </td>
                      <td class="d-flex gap-2">
                        <form method="post" action="/admin/teacher/{{ t['id'] }}/toggle">
                          <button type="submit" class="btn btn-sm btn-outline-primary">
                            {% if t['status'] == 'standby' %}Activate{% else %}Standby{% endif %}
                          </button>
                        </form>
                        <form method="post" action="/admin/teacher/{{ t['id'] }}/remove" onsubmit="return confirm('Remove this teacher?');">
                          <button type="submit" class="btn btn-sm btn-outline-danger">Remove</button>
                        </form>
                      </td>
                    </tr>
                  {% endfor %}
                  </tbody>
                </table>
              </div>
              <a href="/admin" class="btn btn-light mt-3">Back to Dashboard</a>
            </div>
          </div>
        </main>
      </div>
    </div>
    </body>
    </html>
    ''', teachers=teachers)

@dashboard_bp.route('/admin/staffs')
def admin_staffs():
    cred_db = get_cred_db()
    staffs = cred_db.execute('SELECT id, username, gender, status FROM staffs').fetchall()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Staff List</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
    <div class="container-fluid">
      <div class="row">
        <nav class="col-12 col-md-2 sidebar d-flex flex-column">
          <div class="brand">LearnWell</div>
          <a href="/admin">Dashboards</a>
          <a href="/export">Export</a>
          <a href="/admin/add-user">Add User</a>
          <a href="/admin/invoices">Invoices</a>
          <a href="/admin/teachers">Teachers</a>
          <a href="/admin/staffs" class="active">Staffs</a>
          <a href="/admin/students">Students</a>
          <div class="mt-auto">
            <a href="/admin-logout" class="logout">Logout</a>
          </div>
        </nav>
        <main class="col-12 col-md-10 ms-sm-auto px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h2>Staff List</h2>
          </div>
          <div class="card shadow-sm">
            <div class="card-body">
              <div class="table-responsive">
                <table class="table align-middle table-hover mb-0">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Username</th>
                      <th>Gender</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                  {% for s in staffs %}
                    <tr>
                      <td>{{ s['id'] }}</td>
                      <td>{{ s['username'] }}</td>
                      <td>{{ s['gender'] or '' }}</td>
                      <td>
                        {% if s['status'] == 'standby' %}
                          <span class="badge bg-warning text-dark">Standby</span>
                        {% else %}
                          <span class="badge bg-success">Active</span>
                        {% endif %}
                      </td>
                      <td class="d-flex gap-2">
                        <form method="post" action="/admin/staff/{{ s['id'] }}/toggle">
                          <button type="submit" class="btn btn-sm btn-outline-primary">
                            {% if s['status'] == 'standby' %}Activate{% else %}Standby{% endif %}
                          </button>
                        </form>
                        <form method="post" action="/admin/staff/{{ s['id'] }}/remove" onsubmit="return confirm('Remove this staff member?');">
                          <button type="submit" class="btn btn-sm btn-outline-danger">Remove</button>
                        </form>
                      </td>
                    </tr>
                  {% endfor %}
                  </tbody>
                </table>
              </div>
              <a href="/admin" class="btn btn-light mt-3">Back to Dashboard</a>
            </div>
          </div>
        </main>
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
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
    <div class="container-fluid">
      <div class="row">
        <nav class="col-12 col-md-2 sidebar d-flex flex-column">
          <div class="brand">LearnWell</div>
          <a href="/admin">Dashboards</a>
          <a href="/export">Export</a>
          <a href="/admin/add-user">Add User</a>
          <a href="/admin/invoices">Invoices</a>
          <a href="/admin/teachers">Teachers</a>
          <a href="/admin/staffs">Staffs</a>
          <a href="/admin/students" class="active">Students</a>
          <div class="mt-auto">
            <a href="/admin-logout" class="logout">Logout</a>
          </div>
        </nav>
        <main class="col-12 col-md-10 ms-sm-auto px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h2>Student List</h2>
          </div>
          <div class="card shadow-sm">
            <div class="card-body">
              <div class="table-responsive">
                <table class="table align-middle table-hover mb-0">
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
              <a href="/admin" class="btn btn-light mt-3">Back to Dashboard</a>
            </div>
          </div>
        </main>
      </div>
    </div>
    </body>
    </html>
    ''', students=students, teachers=teachers)

@dashboard_bp.route('/admin/teacher/<int:teacher_id>/toggle', methods=['POST'])
def admin_toggle_teacher(teacher_id):
    if not session.get('admin_logged_in'):
        return redirect('/admin-login')
    cred_db = get_cred_db()
    teacher = cred_db.execute('SELECT status FROM teachers WHERE id=?', (teacher_id,)).fetchone()
    if teacher:
        new_status = 'active' if teacher['status'] == 'standby' else 'standby'
        cred_db.execute('UPDATE teachers SET status=? WHERE id=?', (new_status, teacher_id))
        cred_db.commit()
    return redirect('/admin/teachers')

@dashboard_bp.route('/admin/teacher/<int:teacher_id>/remove', methods=['POST'])
def admin_remove_teacher(teacher_id):
    if not session.get('admin_logged_in'):
        return redirect('/admin-login')
    cred_db = get_cred_db()
    cred_db.execute('DELETE FROM teachers WHERE id=?', (teacher_id,))
    cred_db.commit()
    db = get_db()
    db.execute('UPDATE students SET teacher_id=NULL WHERE teacher_id=?', (teacher_id,))
    db.commit()
    return redirect('/admin/teachers')

@dashboard_bp.route('/admin/staff/<int:staff_id>/toggle', methods=['POST'])
def admin_toggle_staff(staff_id):
    if not session.get('admin_logged_in'):
        return redirect('/admin-login')
    cred_db = get_cred_db()
    staff = cred_db.execute('SELECT status FROM staffs WHERE id=?', (staff_id,)).fetchone()
    if staff:
        new_status = 'active' if staff['status'] == 'standby' else 'standby'
        cred_db.execute('UPDATE staffs SET status=? WHERE id=?', (new_status, staff_id))
        cred_db.commit()
    return redirect('/admin/staffs')

@dashboard_bp.route('/admin/staff/<int:staff_id>/remove', methods=['POST'])
def admin_remove_staff(staff_id):
    if not session.get('admin_logged_in'):
        return redirect('/admin-login')
    cred_db = get_cred_db()
    cred_db.execute('DELETE FROM staffs WHERE id=?', (staff_id,))
    cred_db.commit()
    return redirect('/admin/staffs')
