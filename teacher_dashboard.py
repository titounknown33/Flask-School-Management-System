from flask import Flask, request, redirect, session, Blueprint
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

teacher_bp = Blueprint('teacher', __name__)

def get_db():
    conn = sqlite3.connect('school.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_cred_db():
    conn = sqlite3.connect('credential.db')
    conn.row_factory = sqlite3.Row
    return conn

@teacher_bp.route('/teacher-dashboard')
def teacher_dashboard():
    if 'teacher_id' not in session:
        return redirect('/')
    db = get_db()
    students = db.execute('SELECT * FROM students WHERE teacher_id=?', (session['teacher_id'],)).fetchall()
    reports = db.execute(
        'SELECT * FROM reports WHERE teacher_id=? ORDER BY id DESC',
        (session['teacher_id'],)
    ).fetchall()

    # Stats for cards
    class_count = len(set(row["class"] for row in students))
    student_count = len(students)
    grade_count = len(set(row["grade"] for row in students))

    cred_db = get_cred_db()
    teachers = cred_db.execute('SELECT username FROM teachers WHERE id=?', (session['teacher_id'],)).fetchone()
    teachers_name = teachers['username'] if teachers else 'Unknown'

    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Teacher Dashboard</title>
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
  <h4>Teacher Panel</h4>
    <p>Welcome, {teachers_name}</p>
</div>
          <a href="/teacher-dashboard" class="active">Dashboard</a>
          <a href="/input">Add New Report</a>
                    <div class="mt-auto">
            <a href="/teacher-logout" class="logout">Logout</a>
          </div>
        </nav>
        <!-- Main -->
        <main class="col-md-10 ms-sm-auto px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h2>Your Students</h2>
          </div>
          <!-- Cards -->
          <div class="row mb-4">
            <div class="col-md-4">
              <div class="card p-3 shadow-sm">
                <div class="text-muted">Total Students</div>
                <h4>{student_count}</h4>
              </div>
            </div>
            <div class="col-md-4">
              <div class="card p-3 shadow-sm">
                <div class="text-muted">Total Classes</div>
                <h4>{class_count}</h4>
              </div>
            </div>
            <div class="col-md-4">
              <div class="card p-3 shadow-sm">
                <div class="text-muted">Total Grades</div>
                <h4>{grade_count}</h4>
              </div>
            </div>
          </div>
          <!-- Students Table -->
          <div class="card shadow-sm">
            <div class="card-body">
              <h5 class="card-title">Student Data Table</h5>
              <div class="table-responsive">
                <table class="table align-middle table-hover">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Class</th>
                      <th>Grade</th>
                    </tr>
                  </thead>
                  <tbody>
    '''
    for row in students:
        html += (
            f"<tr>"
            f"<td>{row['name']}</td>"
            f"<td>{row['class']}</td>"
            f"<td>{row['grade']}</td>"
            f"</tr>"
        )
    html += '''
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <!-- Reports Table -->
          <div class="card shadow-sm mt-4">
            <div class="card-body">
              <h5 class="card-title">My Reports</h5>
              <div class="table-responsive">
                <table class="table align-middle table-hover">
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Class</th>
                      <th>Grade</th>
                      <th>Score</th>
                      <th>Comment</th>
                      <th>Edit</th>
                    </tr>
                  </thead>
                  <tbody>
    '''
    for row in reports:
        html += (
            f"<tr>"
            f"<td>{row['student_name']}</td>"
            f"<td>{row['class']}</td>"
            f"<td>{row['grade']}</td>"
            f"<td>{row['student_score']}</td>"
            f"<td>{row['teacher_comment']}</td>"
            f"<td><a href=\"/edit-report/{row['id']}\" class=\"btn btn-sm btn-outline-primary\">Edit</a></td>"
            f"</tr>"
        )
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
    return html.format(teachers_name = teachers_name, student_count=student_count, class_count=class_count, grade_count=grade_count)

@teacher_bp.route('/edit-report/<int:report_id>', methods=['GET', 'POST'])
def edit_report(report_id):
    if 'teacher_id' not in session:
        return redirect('/')
    db = get_db()
    report = db.execute(
        'SELECT * FROM reports WHERE id=? AND teacher_id=?', (report_id, session['teacher_id'])
    ).fetchone()
    if not report:
        return "Report not found or access denied."
    if request.method == 'POST':
        student_score = request.form['student_score']
        teacher_comment = request.form['teacher_comment']
        db.execute(
            'UPDATE reports SET student_score=?, teacher_comment=? WHERE id=?',
            (student_score, teacher_comment, report_id)
        )
        db.commit()
        return redirect('/teacher-dashboard')
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Edit Report</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="/static/editreport.css">
    </head>
    <body>
        <div class="edit-container">
            <div class="edit-card">
                <h2>Edit Report for {report["student_name"]}</h2>
                <form method="post">
                    <div class="mb-3">
                        <label class="form-label">Student Score</label>
                        <input name="student_score" type="number" class="form-control" value="{report["student_score"]}" required min="0" max="100">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Teacher Comment</label>
                        <input name="teacher_comment" class="form-control" value="{report["teacher_comment"]}" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Update</button>
                </form>
                <div class="text-center mt-3">
                    <a href="/teacher-dashboard">Back to Dashboard</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/delete-report/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    if 'teacher_id' not in session:
        return redirect('/')
    db = get_db()
    db.execute(
        'DELETE FROM reports WHERE id=? AND teacher_id=?', (report_id, session['teacher_id'])
    )
    db.commit()
    return redirect('/teacher-dashboard')

@teacher_bp.route('/teacher-logout')
def teacher_logout():
    session.pop('teacher_id', None)
    return redirect('/')

@teacher_bp.route('/input', methods=['GET', 'POST'])
def input_report():
    if 'teacher_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        class_ = request.form['class']
        grade = request.form['grade']
        student_name = request.form['student_name']
        student_score = request.form['student_score']
        teacher_comment = request.form['teacher_comment']
        db = get_db()
        db.execute('''
            INSERT INTO reports (teacher_id, class, grade, student_name, student_score, teacher_comment)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['teacher_id'], class_, grade, student_name, student_score, teacher_comment))
        db.commit()
        return redirect('/teacher-dashboard')
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Add New Report</title>
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
            <h4>Teacher Panel</h4>
          </div>
          <a href="/teacher-dashboard">Dashboard</a>
          <a href="/input" class="active">Add New Report</a>
                    <div class="mt-auto">
            <a href="/teacher-logout" class="logout">Logout</a>
          </div>
        </nav>
        <!-- Main -->
        <main class="col-md-10 ms-sm-auto px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h2>Add New Report</h2>
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
                    <input name="student_name" class="form-control" placeholder="Student full name" required>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Student Score</label>
                    <input name="student_score" type="number" class="form-control" placeholder="0-100" required min="0" max="100">
                  </div>
                  <div class="col-12">
                    <label class="form-label">Teacher Comment</label>
                    <input name="teacher_comment" class="form-control" placeholder="Short feedback for the student" required>
                  </div>
                  <div class="col-12 d-flex gap-2">
                    <button type="submit" class="btn btn-primary">Add Report</button>
                    <a href="/teacher-dashboard" class="btn btn-light">Back</a>
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
    '''
