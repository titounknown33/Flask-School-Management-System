from flask import Blueprint, render_template_string, request, redirect, session
import sqlite3
from flask import send_file
import io
import datetime
import os

staff_bp = Blueprint('staff', __name__)

def get_db():
    conn = sqlite3.connect('school.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_cred_db():
    conn = sqlite3.connect('credential.db')
    conn.row_factory = sqlite3.Row
    return conn

@staff_bp.route('/staff-dashboard', methods=['GET', 'POST'])
def staff_dashboard():
    if 'staff_id' not in session:
        return redirect('/staff-login')
    db = get_db()
    students = db.execute('SELECT * FROM students').fetchall()
    # Get teachers from credential.db
    cred_db = get_cred_db()
    teachers = {row['id']: row['username'] for row in cred_db.execute('SELECT id, username FROM teachers')}
    teacher_list = list(cred_db.execute('SELECT id, username FROM teachers'))
    student_count = len(students)
    class_count = len(set(s['class'] for s in students))
    grade_count = len(set(s['grade'] for s in students))

    selected_teacher = None
    selected_class = None
    selected_student = None
    if request.method == 'POST':
        selected_teacher = request.form.get('teacher')
        selected_class = request.form.get('class')
        selected_student = request.form.get('student_name')

    report_classes = list(db.execute('SELECT DISTINCT class FROM reports'))
    query = 'SELECT * FROM reports'
    params = []
    filters = []
    if selected_teacher:
        filters.append('teacher_id=?')
        params.append(selected_teacher)
    if selected_class:
        filters.append('class=?')
        params.append(selected_class)
    if selected_student:
        filters.append('student_name LIKE ?')
        params.append(f"%{selected_student}%")
    if filters:
        query += ' WHERE ' + ' AND '.join(filters)
    query += ' ORDER BY id DESC'
    reports = db.execute(query, params).fetchall()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Staff Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
    <div class="container-fluid">
      <div class="row">
        <!-- Sidebar -->
        <nav class="col-md-2 d-none d-md-flex sidebar py-4 flex-column">
          <div class="text-center mb-4">
            <h4>Staff Panel</h4>
          </div>
          <a href="/staff-dashboard" class="active">Dashboard</a>
          <a href="/staff/register-student">Register Student</a>
          <a href="/staff/manage-payments">Manage Payments</a>
                    <div class="mt-auto">
            <a href="/staff-logout" class="logout">Logout</a>
          </div>
        </nav>
        <!-- Main -->
        <main class="col-md-10 ms-sm-auto px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h2>Welcome Back, Staff!</h2>
          </div>
          <!-- Cards -->
          <div class="row mb-4">
            <div class="col-md-4">
              <div class="card p-3 shadow-sm">
                <div class="text-muted">Total Students</div>
                <h4>{{ student_count }}</h4>
              </div>
            </div>
            <div class="col-md-4">
              <div class="card p-3 shadow-sm">
                <div class="text-muted">Total Classes</div>
                <h4>{{ class_count }}</h4>
              </div>
            </div>
            <div class="col-md-4">
              <div class="card p-3 shadow-sm">
                <div class="text-muted">Total Grades</div>
                <h4>{{ grade_count }}</h4>
              </div>
            </div>
          </div>
          <!-- Data Table -->
          <div class="card shadow-sm">
            <div class="card-body">
              <h5 class="card-title">Student Data Table</h5>
              <div class="table-responsive">
                <table class="table align-middle table-hover">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Gender</th>
                      <th>Date of Birth</th>
                      <th>Emergency Contact</th>
                      <th>Class</th>
                      <th>Grade</th>
                      <th>Teacher</th>
                      <th>Edit</th>
                      <th>Delete</th>
                    </tr>
                  </thead>
                  <tbody>
                  {% for student in students %}
                    <tr>
                      <td>{{ student['name'] }}</td>
                      <td>{{ student['gender'] or '' }}</td>
                      <td>{{ student['dob'] or '' }}</td>
                      <td>{{ student['emergency_contact'] or '' }}</td>
                      <td>{{ student['class'] }}</td>
                      <td>{{ student['grade'] }}</td>
                      <td>{{ teachers[student['teacher_id']] if student['teacher_id'] in teachers else 'Unknown' }}</td>
                      <td>
                        <a href="/staff/edit-student/{{ student['id'] }}" class="btn btn-sm btn-primary">Edit</a>
                      </td>
                      <td>
                        <form method="post" action="/staff/delete-student/{{ student['id'] }}" onsubmit="return confirm('Delete this student?');">
                          <button type="submit" class="btn btn-sm btn-danger">Delete</button>
                        </form>
                      </td>
                    </tr>
                  {% endfor %}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div class="card shadow-sm mt-4">
            <div class="card-body">
              <h5 class="card-title">Reports Table</h5>
              <form method="post" class="row g-3 mb-3" data-auto-submit="true">
                <div class="col-md-4">
                  <label class="form-label">View Teacher</label>
                  <select name="teacher" class="form-select">
                    <option value="">All</option>
                    {% for t in teacher_list %}
                      <option value="{{ t['id'] }}" {% if selected_teacher and t['id']|string == selected_teacher|string %}selected{% endif %}>
                        {{ t['username'] }}
                      </option>
                    {% endfor %}
                  </select>
                </div>
                <div class="col-md-4">
                  <label class="form-label">View by Class</label>
                  <select name="class" class="form-select">
                    <option value="">All</option>
                    {% for c in report_classes %}
                      <option value="{{ c['class'] }}" {% if selected_class == c['class'] %}selected{% endif %}>
                        {{ c['class'] }}
                      </option>
                    {% endfor %}
                  </select>
                </div>
                <div class="col-md-4">
                  <label class="form-label">Student Name</label>
                  <input name="student_name" class="form-control" placeholder="Search by name" value="{{ selected_student or '' }}">
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
                  {% for row in reports %}
                    <tr>
                      <td>{{ teachers.get(row['teacher_id'], 'Unknown') }}</td>
                      <td>{{ row['class'] }}</td>
                      <td>{{ row['grade'] }}</td>
                      <td>{{ row['student_name'] }}</td>
                      <td>{{ row['student_score'] }}</td>
                      <td>{{ row['teacher_comment'] }}</td>
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
    ''', students=students, student_count=student_count, class_count=class_count, grade_count=grade_count, teachers=teachers, reports=reports, report_classes=report_classes, teacher_list=teacher_list, selected_teacher=selected_teacher, selected_class=selected_class, selected_student=selected_student)

@staff_bp.route('/staff/register-student', methods=['GET', 'POST'])
def register_student():
    if 'staff_id' not in session:
        return redirect('/staff-login')
    db = get_db()
    cred_db = get_cred_db()
    teachers = list(cred_db.execute('SELECT id, username FROM teachers'))
    if request.method == 'POST':
        name = request.form['name']
        class_ = request.form['class']
        grade = request.form['grade']
        gender = request.form['gender']
        dob = request.form['dob']
        emergency_contact = request.form['emergency_contact']
        teacher_id = request.form['teacher_id']
        db = get_db()
        db.execute(
            'INSERT INTO students (name, class, grade, gender, dob, emergency_contact, teacher_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (name, class_, grade, gender, dob, emergency_contact, teacher_id)
        )
        db.commit()
        return redirect('/staff-dashboard')
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Register Student</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
    <div class="container-fluid">
      <div class="row">
        <!-- Sidebar -->
        <nav class="col-md-2 d-none d-md-flex sidebar py-4 flex-column">
          <div class="text-center mb-4">
            <h4>Staff Panel</h4>
          </div>
          <a href="/staff-dashboard">Dashboard</a>
          <a href="/staff/register-student" class="active">Register Student</a>
          <a href="/staff/manage-payments">Manage Payments</a>
                    <div class="mt-auto">
            <a href="/staff-logout" class="logout">Logout</a>
          </div>
        </nav>
        <!-- Main -->
        <main class="col-md-10 ms-sm-auto px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h2>Register Student</h2>
          </div>
          <div class="card shadow-sm">
            <div class="card-body">
              <form method="post">
                <div class="row g-3">
                  <div class="col-md-6">
                    <label class="form-label">Class</label>
                    <input name="class" class="form-control" placeholder="e.g., 5A" required>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Grade</label>
                    <input name="grade" class="form-control" placeholder="e.g., Grade 5" required>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Student Name</label>
                    <input name="name" class="form-control" placeholder="Student full name" required>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Gender</label>
                    <select name="gender" class="form-control" required>
                      <option value="">Select</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Teacher</label>
                    <select name="teacher_id" class="form-control" required>
                      {% for t in teachers %}
                        <option value="{{ t['id'] }}">{{ t['username'] }}</option>
                      {% endfor %}
                    </select>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Date of Birth</label>
                    <input name="dob" type="date" class="form-control" required>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Emergency Contact</label>
                    <input name="emergency_contact" type="text" class="form-control" placeholder="Phone number" required>
                  </div>
                  <div class="col-12 d-flex gap-2">
                    <button type="submit" class="btn btn-primary">Register</button>
                    <a href="/staff-dashboard" class="btn btn-light">Back</a>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </main>
      </div>
    </div>
    </body>
    </html>
    ''', teachers=teachers)

@staff_bp.route('/staff/manage-payments', methods=['GET', 'POST'])
def manage_payments():
    if 'staff_id' not in session:
        return redirect('/staff-login')
    db = get_db()

    # Handle payment update/add
    if request.method == 'POST':
        student_id = request.form['student_id']
        amount = request.form['amount']
        pay_date = request.form['pay_date']
        next_pay_date = request.form['next_pay_date']
        status = request.form['status']
        discount = float(request.form.get('discount', 0.15))
        khr_rate = int(request.form.get('khr_rate', 4100))
        payment = db.execute('SELECT * FROM payments WHERE student_id=?', (student_id,)).fetchone()
        if payment:
            db.execute('UPDATE payments SET amount=?, pay_date=?, next_pay_date=?, status=?, discount=?, khr_rate=? WHERE student_id=?',
                       (amount, pay_date, next_pay_date, status, discount, khr_rate, student_id))
        else:
            db.execute('INSERT INTO payments (student_id, amount, pay_date, next_pay_date, status, discount, khr_rate) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (student_id, amount, pay_date, next_pay_date, status, discount, khr_rate))
        db.commit()

    students = db.execute('SELECT * FROM students').fetchall()
    payments = {p['student_id']: p for p in db.execute('SELECT * FROM payments').fetchall()}

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Manage Payments</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/dashboard.css">
    </head>
    <body>
    <div class="container-fluid">
      <div class="row">
        <!-- Sidebar -->
        <nav class="col-md-2 d-none d-md-flex sidebar py-4 flex-column">
          <div class="text-center mb-4">
            <h4>Staff Panel</h4>
          </div>
          <a href="/staff-dashboard">Dashboard</a>
          <a href="/staff/register-student">Register Student</a>
          <a href="/staff/manage-payments" class="active">Manage Payments</a>
                    <div class="mt-auto">
            <a href="/staff-logout" class="logout">Logout</a>
          </div>
        </nav>
        <!-- Main -->
        <main class="col-md-10 ms-sm-auto px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h2>Manage Payments</h2>
          </div>
          <div class="card shadow-sm">
            <div class="card-body">
              <div class="table-responsive">
                <table class="table align-middle table-hover">
                  <thead>
                    <tr>
                      <th>Student Name</th>
                      <th>Amount</th>
                      <th>Pay Date</th>
                      <th>Next Pay Date</th>
                      <th>Status</th>
                      <th>Discount</th>
                      <th>USD-KHR</th>
                      <th>Action</th>
                      <th>Print</th>
                    </tr>
                  </thead>
                  <tbody>
                  {% for student in students %}
                    <tr>
                      <form method="post">
                        <td>{{ student['name'] }}</td>
                        <td>
                          <input type="number" step="0.01" name="amount" class="form-control"
                                 value="{{ payments[student['id']]['amount'] if student['id'] in payments else '' }}">
                        </td>
                        <td>
                          <input type="date" name="pay_date" class="form-control"
                                 value="{{ payments[student['id']]['pay_date'] if student['id'] in payments else '' }}">
                        </td>
                        <td>
                          <input type="date" name="next_pay_date" class="form-control"
                                 value="{{ payments[student['id']]['next_pay_date'] if student['id'] in payments else '' }}">
                        </td>
                        <td>
                          <select name="status" class="form-control">
                            <option value="Paid" {% if student['id'] in payments and payments[student['id']]['status'] == 'Paid' %}selected{% endif %}>Paid</option>
                            <option value="Not Paid" {% if student['id'] in payments and payments[student['id']]['status'] == 'Not Paid' %}selected{% endif %}>Not Paid</option>
                          </select>
                        </td>
                        <td>
                          <select name="discount" class="form-control">
                            {% set d = payments[student['id']]['discount'] if student['id'] in payments and payments[student['id']]['discount'] is not none else 0.15 %}
                            <option value="0.05" {% if d == 0.05 %}selected{% endif %}>5%</option>
                            <option value="0.10" {% if d == 0.10 %}selected{% endif %}>10%</option>
                            <option value="0.15" {% if d == 0.15 %}selected{% endif %}>15%</option>
                            <option value="0.20" {% if d == 0.20 %}selected{% endif %}>20%</option>
                          </select>
                        </td>
                        <td>
                          <select name="khr_rate" class="form-control">
                            {% set k = payments[student['id']]['khr_rate'] if student['id'] in payments and payments[student['id']]['khr_rate'] is not none else 4100 %}
                            <option value="4000" {% if k == 4000 %}selected{% endif %}>4000</option>
                            <option value="4100" {% if k == 4100 %}selected{% endif %}>4100</option>
                            <option value="4200" {% if k == 4200 %}selected{% endif %}>4200</option>
                          </select>
                        </td>
                        <td>
                          <input type="hidden" name="student_id" value="{{ student['id'] }}">
                          <button type="submit" class="btn btn-sm btn-primary">Save</button>
                        </td>
                        <td>
                          <a href="/staff/print-invoice/{{ student['id'] }}" class="btn btn-sm btn-success" target="_blank">Print Invoice</a>
                        </td>
                      </form>
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
    ''', students=students, payments=payments)

@staff_bp.route('/staff/delete-student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    if 'staff_id' not in session:
        return redirect('/staff-login')
    db = get_db()
    db.execute('DELETE FROM payments WHERE student_id=?', (student_id,))
    db.execute('DELETE FROM invoices WHERE student_id=?', (student_id,))
    db.execute('DELETE FROM students WHERE id=?', (student_id,))
    db.commit()
    return redirect('/staff-dashboard')

@staff_bp.route('/staff/print-invoice/<int:student_id>')
def print_invoice(student_id):
    if 'staff_id' not in session:
        return redirect('/staff-login')
    db = get_db()
    cred_db = get_cred_db()
    student = db.execute('SELECT * FROM students WHERE id=?', (student_id,)).fetchone()
    payment = db.execute('SELECT * FROM payments WHERE student_id=?', (student_id,)).fetchone()
    teacher = cred_db.execute('SELECT username FROM teachers WHERE id=?', (student['teacher_id'],)).fetchone()
    teacher_name = teacher['username'] if teacher else 'Unknown'

    invoice_no = f"Inv-{student_id:04d}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    invoice_date = payment['pay_date'] if payment and payment['pay_date'] else datetime.date.today().strftime('%d %b %Y')
    amount = float(payment['amount']) if payment and payment['amount'] else 0.0
    discount = float(payment['discount']) if payment and payment['discount'] is not None else 0.15
    khr_rate = int(payment['khr_rate']) if payment and payment['khr_rate'] is not None else 4100
    discount_amount = amount * discount
    total = amount - discount_amount
    total_khr = int(total * khr_rate)

    # Render invoice HTML (no PDF)
    return render_template_string(
        '''<!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Invoice</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body { font-family: 'Khmer OS', Arial, sans-serif; }
                .invoice-box { max-width: 900px; margin: auto; padding: 30px; border: 1px solid #eee; }
                .table th, .table td { vertical-align: middle; }
                .total-row { font-weight: bold; }
            </style>
        </head>
        <body>
        <div class="invoice-box">
            <div class="row mb-4">
                <div class="col-6">
                    <img src="/static/chrome.png" style="height:60px;">
                    <h5>LearnWell Academy of Phnom Penh</h5>
                </div>
                <div class="col-6 text-end">
                    <b>Invoice No:</b> {{ invoice_no }}<br>
                    <b>Date:</b> {{ invoice_date }}
                </div>
            </div>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Student Name</th>
                        <th>Class</th>
                        <th>Grade</th>
                        <th>Teacher</th>
                        <th>Amount</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>1</td>
                        <td>{{ student['name'] }}</td>
                        <td>{{ student['class'] }}</td>
                        <td>{{ student['grade'] }}</td>
                        <td>{{ teacher_name }}</td>
                        <td>${{ "{:.2f}".format(amount) }}</td>
                    </tr>
                </tbody>
            </table>
            <div class="row">
                <div class="col-6"></div>
                <div class="col-6">
                    <table class="table">
                        <tr>
                            <td>Subtotal</td>
                            <td>${{ "{:.2f}".format(amount) }}</td>
                        </tr>
                        <tr>
                            <td>Discount ({{ int(discount*100) }}%)</td>
                            <td>${{ "{:.2f}".format(discount_amount) }}</td>
                        </tr>
                        <tr class="total-row">
                            <td>Total</td>
                            <td>${{ "{:.2f}".format(total) }}</td>
                        </tr>
                        <tr>
                            <td>Total (KHR)</td>
                            <td>{{ "{:,}".format(total_khr) }} ៛</td>
                        </tr>
                    </table>
                </div>
            </div>
            <!-- Print Button -->
            <div class="text-center mt-4">
                <button class="btn btn-primary" onclick="window.print()">Print Invoice</button>
            </div>
        </div>
        </body>
        </html>
        ''',
        student=student,
        teacher_name=teacher_name,
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        amount=amount,
        discount=discount,
        discount_amount=discount_amount,
        total=total,
        total_khr=total_khr,
        int=int
    )

@staff_bp.route('/staff-logout')
def staff_logout():
    session.pop('staff_id', None)
    return redirect('/staff-login')
