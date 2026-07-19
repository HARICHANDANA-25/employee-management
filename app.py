from flask import Flask, request, redirect, url_for, render_template_string, Response
import sqlite3
import csv
import io

app = Flask(__name__)

DB = 'employee.db'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS employee
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  department TEXT,
                  position TEXT,
                  email TEXT,
                  phone TEXT,
                  salary REAL,
                  join_date TEXT,
                  status TEXT DEFAULT 'Active')''')
    conn.commit()
    conn.close()


init_db()

# Columns allowed for sorting (whitelist to avoid SQL injection via order-by)
SORTABLE_COLUMNS = {
    "id": "id",
    "name": "name",
    "department": "department",
    "position": "position",
    "salary": "salary",
    "join_date": "join_date",
    "status": "status",
}

# ---------------------------------------------------------------------------
# Shared layout
# ---------------------------------------------------------------------------

BASE_HEAD = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
<style>
  body { background:#111318; }
  .card, .table { background:#181b21; }
  .navbar-brand { font-weight:600; }
  .status-active { color:#4ade80; }
  .status-inactive { color:#f87171; }
  a.btn-sm { margin-right:2px; }
</style>
"""

NAVBAR = """
<nav class="navbar navbar-expand-lg navbar-dark bg-black mb-4">
  <div class="container-fluid">
    <a class="navbar-brand" href="/list">🏢 Employee Manager</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav me-auto">
        <li class="nav-item"><a class="nav-link" href="/list">All Employees</a></li>
        <li class="nav-item"><a class="nav-link" href="/add">Add Employee</a></li>
        <li class="nav-item"><a class="nav-link" href="/export">Export CSV</a></li>
      </ul>
    </div>
  </div>
</nav>
"""

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return redirect(url_for("list_employees"))


@app.route("/list")
def list_employees():
    search = request.args.get("q", "").strip()
    dept_filter = request.args.get("department", "").strip()
    status_filter = request.args.get("status", "").strip()
    sort = request.args.get("sort", "id")
    direction = request.args.get("dir", "asc")

    if sort not in SORTABLE_COLUMNS:
        sort = "id"
    direction = "DESC" if direction.lower() == "desc" else "ASC"

    conn = get_conn()
    c = conn.cursor()

    query = "SELECT * FROM employee WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE ? OR email LIKE ? OR position LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like]

    if dept_filter:
        query += " AND department = ?"
        params.append(dept_filter)

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    query += f" ORDER BY {SORTABLE_COLUMNS[sort]} {direction}"

    c.execute(query, params)
    rows = c.fetchall()

    c.execute("SELECT DISTINCT department FROM employee WHERE department IS NOT NULL AND department != '' ORDER BY department")
    departments = [r[0] for r in c.fetchall()]

    c.execute("SELECT COUNT(*) FROM employee")
    total_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM employee WHERE status='Active'")
    active_count = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT department) FROM employee")
    dept_count = c.fetchone()[0]

    conn.close()

    def sort_link(col, label):
        new_dir = "desc" if (sort == col and direction == "ASC") else "asc"
        arrow = ""
        if sort == col:
            arrow = " ▲" if direction == "ASC" else " ▼"
        args = request.args.to_dict()
        args["sort"] = col
        args["dir"] = new_dir
        qs = "&".join(f"{k}={v}" for k, v in args.items())
        return f'<a class="text-white text-decoration-none" href="/list?{qs}">{label}{arrow}</a>'

    html = """
    <!DOCTYPE html>
    <html><head><title>Employee Management</title>""" + BASE_HEAD + """</head>
    <body class="text-white">
    """ + NAVBAR + """
    <div class="container">
      <div class="row mb-4">
        <div class="col-md-4">
          <div class="card p-3 text-center"><h6 class="text-secondary">Total Employees</h6><h3>{{ total_count }}</h3></div>
        </div>
        <div class="col-md-4">
          <div class="card p-3 text-center"><h6 class="text-secondary">Active</h6><h3>{{ active_count }}</h3></div>
        </div>
        <div class="col-md-4">
          <div class="card p-3 text-center"><h6 class="text-secondary">Departments</h6><h3>{{ dept_count }}</h3></div>
        </div>
      </div>

      <form method="GET" action="/list" class="row g-2 mb-4">
        <div class="col-md-4">
          <input type="text" name="q" value="{{ search }}" class="form-control" placeholder="Search name, email, position...">
        </div>
        <div class="col-md-3">
          <select name="department" class="form-select">
            <option value="">All Departments</option>
            {% for d in departments %}
            <option value="{{d}}" {% if d==dept_filter %}selected{% endif %}>{{d}}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-3">
          <select name="status" class="form-select">
            <option value="">All Statuses</option>
            <option value="Active" {% if status_filter=="Active" %}selected{% endif %}>Active</option>
            <option value="Inactive" {% if status_filter=="Inactive" %}selected{% endif %}>Inactive</option>
          </select>
        </div>
        <div class="col-md-2 d-grid">
          <button type="submit" class="btn btn-primary">🔍 Filter</button>
        </div>
      </form>

      <table class="table table-dark table-hover table-bordered align-middle">
        <thead class="table-light text-dark">
          <tr>
            <th>{{ sort_link('id', 'ID')|safe }}</th>
            <th>{{ sort_link('name', 'Name')|safe }}</th>
            <th>{{ sort_link('department', 'Department')|safe }}</th>
            <th>{{ sort_link('position', 'Position')|safe }}</th>
            <th>{{ sort_link('salary', 'Salary')|safe }}</th>
            <th>{{ sort_link('join_date', 'Join Date')|safe }}</th>
            <th>{{ sort_link('status', 'Status')|safe }}</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {% for row in rows %}
          <tr>
            <td>{{row['id']}}</td>
            <td>{{row['name']}}</td>
            <td>{{row['department']}}</td>
            <td>{{row['position']}}</td>
            <td>{{ '%.2f'|format(row['salary']) if row['salary'] else '-' }}</td>
            <td>{{row['join_date'] or '-'}}</td>
            <td class="{{ 'status-active' if row['status']=='Active' else 'status-inactive' }}">{{row['status']}}</td>
            <td>
              <a href='/view/{{row["id"]}}' class="btn btn-sm btn-info">👁 View</a>
              <a href='/edit/{{row["id"]}}' class="btn btn-sm btn-warning">✏️ Edit</a>
              <a href='/delete/{{row["id"]}}' class="btn btn-sm btn-danger"
                 onclick="return confirm('Delete {{row[\"name\"]}}? This cannot be undone.');">🗑️ Delete</a>
            </td>
          </tr>
          {% else %}
          <tr><td colspan="8" class="text-center text-secondary">No employees found.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    </body></html>
    """
    return render_template_string(
        html, rows=rows, departments=departments, search=search,
        dept_filter=dept_filter, status_filter=status_filter,
        sort_link=sort_link, total_count=total_count,
        active_count=active_count, dept_count=dept_count
    )


@app.route("/view/<int:emp_id>")
def view_employee(emp_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM employee WHERE id=?", (emp_id,))
    emp = c.fetchone()
    conn.close()

    if emp is None:
        return redirect(url_for("list_employees"))

    html = """
    <!DOCTYPE html>
    <html><head><title>Employee Details</title>""" + BASE_HEAD + """</head>
    <body class="text-white">
    """ + NAVBAR + """
    <div class="container">
      <div class="card p-4">
        <h3>{{emp['name']}}</h3>
        <span class="{{ 'status-active' if emp['status']=='Active' else 'status-inactive' }}">● {{emp['status']}}</span>
        <hr>
        <dl class="row mt-3">
          <dt class="col-sm-3">Department</dt><dd class="col-sm-9">{{emp['department'] or '-'}}</dd>
          <dt class="col-sm-3">Position</dt><dd class="col-sm-9">{{emp['position'] or '-'}}</dd>
          <dt class="col-sm-3">Email</dt><dd class="col-sm-9">{{emp['email'] or '-'}}</dd>
          <dt class="col-sm-3">Phone</dt><dd class="col-sm-9">{{emp['phone'] or '-'}}</dd>
          <dt class="col-sm-3">Salary</dt><dd class="col-sm-9">{{ '%.2f'|format(emp['salary']) if emp['salary'] else '-' }}</dd>
          <dt class="col-sm-3">Join Date</dt><dd class="col-sm-9">{{emp['join_date'] or '-'}}</dd>
        </dl>
        <a href="/edit/{{emp['id']}}" class="btn btn-warning">✏️ Edit</a>
        <a href="/list" class="btn btn-secondary">⬅ Back</a>
      </div>
    </div>
    </body></html>
    """
    return render_template_string(html, emp=emp)


@app.route("/add", methods=["GET", "POST"])
def add_employee():
    if request.method == "POST":
        name = request.form["name"]
        dept = request.form.get("department", "")
        position = request.form.get("position", "")
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")
        salary = request.form.get("salary") or None
        join_date = request.form.get("join_date", "")
        status = request.form.get("status", "Active")

        conn = get_conn()
        c = conn.cursor()
        c.execute(
            """INSERT INTO employee (name, department, position, email, phone, salary, join_date, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, dept, position, email, phone, salary, join_date, status),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("list_employees"))

    html = """
    <!DOCTYPE html>
    <html><head><title>Add Employee</title>""" + BASE_HEAD + """</head>
    <body class="text-white">
    """ + NAVBAR + """
    <div class="container">
      <div class="card p-4">
        <h4 class="mb-3">Add Employee</h4>
        <form method="POST">
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label">Name *</label>
              <input type="text" name="name" class="form-control" required>
            </div>
            <div class="col-md-6">
              <label class="form-label">Department</label>
              <input type="text" name="department" class="form-control">
            </div>
            <div class="col-md-6">
              <label class="form-label">Position</label>
              <input type="text" name="position" class="form-control">
            </div>
            <div class="col-md-6">
              <label class="form-label">Status</label>
              <select name="status" class="form-select">
                <option value="Active">Active</option>
                <option value="Inactive">Inactive</option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label">Email</label>
              <input type="email" name="email" class="form-control">
            </div>
            <div class="col-md-6">
              <label class="form-label">Phone</label>
              <input type="text" name="phone" class="form-control">
            </div>
            <div class="col-md-6">
              <label class="form-label">Salary</label>
              <input type="number" step="0.01" name="salary" class="form-control">
            </div>
            <div class="col-md-6">
              <label class="form-label">Join Date</label>
              <input type="date" name="join_date" class="form-control">
            </div>
          </div>
          <div class="mt-4">
            <button type="submit" class="btn btn-success">➕ Add Employee</button>
            <a href="/list" class="btn btn-secondary">⬅ Back</a>
          </div>
        </form>
      </div>
    </div>
    </body></html>
    """
    return render_template_string(html)


@app.route("/edit/<int:emp_id>", methods=["GET", "POST"])
def edit_employee(emp_id):
    conn = get_conn()
    c = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        dept = request.form.get("department", "")
        position = request.form.get("position", "")
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")
        salary = request.form.get("salary") or None
        join_date = request.form.get("join_date", "")
        status = request.form.get("status", "Active")

        c.execute(
            """UPDATE employee SET name=?, department=?, position=?, email=?,
               phone=?, salary=?, join_date=?, status=? WHERE id=?""",
            (name, dept, position, email, phone, salary, join_date, status, emp_id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("list_employees"))

    c.execute("SELECT * FROM employee WHERE id=?", (emp_id,))
    emp = c.fetchone()
    conn.close()

    if emp is None:
        return redirect(url_for("list_employees"))

    html = """
    <!DOCTYPE html>
    <html><head><title>Edit Employee</title>""" + BASE_HEAD + """</head>
    <body class="text-white">
    """ + NAVBAR + """
    <div class="container">
      <div class="card p-4">
        <h4 class="mb-3">Edit Employee</h4>
        <form method="POST">
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label">Name *</label>
              <input type="text" name="name" value="{{emp['name']}}" class="form-control" required>
            </div>
            <div class="col-md-6">
              <label class="form-label">Department</label>
              <input type="text" name="department" value="{{emp['department'] or ''}}" class="form-control">
            </div>
            <div class="col-md-6">
              <label class="form-label">Position</label>
              <input type="text" name="position" value="{{emp['position'] or ''}}" class="form-control">
            </div>
            <div class="col-md-6">
              <label class="form-label">Status</label>
              <select name="status" class="form-select">
                <option value="Active" {% if emp['status']=='Active' %}selected{% endif %}>Active</option>
                <option value="Inactive" {% if emp['status']=='Inactive' %}selected{% endif %}>Inactive</option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label">Email</label>
              <input type="email" name="email" value="{{emp['email'] or ''}}" class="form-control">
            </div>
            <div class="col-md-6">
              <label class="form-label">Phone</label>
              <input type="text" name="phone" value="{{emp['phone'] or ''}}" class="form-control">
            </div>
            <div class="col-md-6">
              <label class="form-label">Salary</label>
              <input type="number" step="0.01" name="salary" value="{{emp['salary'] or ''}}" class="form-control">
            </div>
            <div class="col-md-6">
              <label class="form-label">Join Date</label>
              <input type="date" name="join_date" value="{{emp['join_date'] or ''}}" class="form-control">
            </div>
          </div>
          <div class="mt-4">
            <button type="submit" class="btn btn-warning">💾 Update Employee</button>
            <a href="/list" class="btn btn-secondary">⬅ Back</a>
          </div>
        </form>
      </div>
    </div>
    </body></html>
    """
    return render_template_string(html, emp=emp)


@app.route("/delete/<int:emp_id>")
def delete_employee(emp_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM employee WHERE id=?", (emp_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("list_employees"))


@app.route("/export")
def export_csv():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM employee")
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Department", "Position", "Email", "Phone", "Salary", "Join Date", "Status"])
    for row in rows:
        writer.writerow([row["id"], row["name"], row["department"], row["position"],
                          row["email"], row["phone"], row["salary"], row["join_date"], row["status"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=employees.csv"},
    )


if __name__ == "__main__":
    app.run(debug=True)
