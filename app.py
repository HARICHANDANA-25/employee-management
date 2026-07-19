from flask import Flask, request, redirect, url_for, render_template_string
import sqlite3

app = Flask(__name__)

# Initialize DB
def init_db():
    conn = sqlite3.connect('employee.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS employee
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  department TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    return redirect(url_for("list_employees"))

# List employees
@app.route("/list")
def list_employees():
    conn = sqlite3.connect('employee.db')
    c = conn.cursor()
    c.execute("SELECT * FROM employee")
    rows = c.fetchall()
    conn.close()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Employee Management</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    </head>
    <body class="bg-dark text-white">
        <nav class="navbar navbar-expand-lg navbar-dark bg-black">
            <div class="container-fluid">
                <a class="navbar-brand" href="/list">Employee Manager</a>
                <div class="collapse navbar-collapse">
                    <ul class="navbar-nav me-auto">
                        <li class="nav-item"><a class="nav-link" href="/add">Add Employee</a></li>
                    </ul>
                </div>
            </div>
        </nav>

        <div class="container mt-4">
            <h2 class="mb-4">👩‍💼 Employee Records</h2>
            <table class="table table-dark table-hover table-bordered">
                <thead class="table-light text-dark">
                    <tr><th>ID</th><th>Name</th><th>Department</th><th>Actions</th></tr>
                </thead>
                <tbody>
                    {% for row in rows %}
                    <tr>
                        <td>{{row[0]}}</td>
                        <td>{{row[1]}}</td>
                        <td>{{row[2]}}</td>
                        <td>
                            <a href='/edit/{{row[0]}}' class="btn btn-sm btn-warning">✏️ Edit</a>
                            <a href='/delete/{{row[0]}}' class="btn btn-sm btn-danger">🗑️ Delete</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, rows=rows)

# Add employee
@app.route("/add", methods=["GET", "POST"])
def add_employee():
    if request.method == "POST":
        name = request.form["name"]
        dept = request.form["department"]
        conn = sqlite3.connect('employee.db')
        c = conn.cursor()
        c.execute("INSERT INTO employee (name, department) VALUES (?, ?)", (name, dept))
        conn.commit()
        conn.close()
        return redirect(url_for("list_employees"))

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Add Employee</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    </head>
    <body class="bg-dark text-white">
        <nav class="navbar navbar-expand-lg navbar-dark bg-black">
            <div class="container-fluid">
                <a class="navbar-brand" href="/list">Employee Manager</a>
            </div>
        </nav>

        <div class="container mt-5">
            <div class="card shadow-sm bg-black text-white">
                <div class="card-header bg-black text-white">
                    <h4>Add Employee</h4>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="mb-3">
                            <label class="form-label">Name</label>
                            <input type="text" name="name" class="form-control" placeholder="Enter employee name">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Department</label>
                            <input type="text" name="department" class="form-control" placeholder="Enter department">
                        </div>
                        <button type="submit" class="btn btn-success">➕ Add Employee</button>
                        <a href="/list" class="btn btn-secondary">⬅ Back</a>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

# Edit employee
@app.route("/edit/<int:emp_id>", methods=["GET", "POST"])
def edit_employee(emp_id):
    conn = sqlite3.connect('employee.db')
    c = conn.cursor()
    if request.method == "POST":
        name = request.form["name"]
        dept = request.form["department"]
        c.execute("UPDATE employee SET name=?, department=? WHERE id=?", (name, dept, emp_id))
        conn.commit()
        conn.close()
        return redirect(url_for("list_employees"))

    c.execute("SELECT * FROM employee WHERE id=?", (emp_id,))
    emp = c.fetchone()
    conn.close()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Edit Employee</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    </head>
    <body class="bg-dark text-white">
        <nav class="navbar navbar-expand-lg navbar-dark bg-black">
            <div class="container-fluid">
                <a class="navbar-brand" href="/list">Employee Manager</a>
            </div>
        </nav>

        <div class="container mt-5">
            <div class="card shadow-sm bg-black text-white">
                <div class="card-header bg-black text-white">
                    <h4>Edit Employee</h4>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="mb-3">
                            <label class="form-label">Name</label>
                            <input type="text" name="name" value="{emp[1]}" class="form-control">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Department</label>
                            <input type="text" name="department" value="{emp[2]}" class="form-control">
                        </div>
                        <button type="submit" class="btn btn-warning">Update Employee</button>
                        <a href="/list" class="btn btn-secondary">⬅ Back</a>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

# Delete employee
@app.route("/delete/<int:emp_id>")
def delete_employee(emp_id):
    conn = sqlite3.connect('employee.db')
    c = conn.cursor()
    c.execute("DELETE FROM employee WHERE id=?", (emp_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("list_employees"))

if __name__ == "__main__":
    app.run(debug=True)
