try:
    from flask import Flask, render_template, request, redirect, url_for, session  # type: ignore[import]
except ImportError as e:
    raise ImportError("Flask is not installed. Please install it using: pip install flask") from e

import sqlite3
try:
    from werkzeug.security import generate_password_hash, check_password_hash  # type: ignore[import]
except Exception:
    # Fallback if werkzeug is not installed: use plain-text (insecure) as a last resort.
    def generate_password_hash(password: str) -> str:
        return password

    def check_password_hash(hashed: str, password: str) -> bool:
        return hashed == password
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "placement_secret_key"
app.permanent_session_lifetime = timedelta(days=7)

DATABASE = "database.db"


def create_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        password TEXT NOT NULL,
        college TEXT,
        branch TEXT,
        year TEXT,
        cgpa REAL,
        role TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS progress(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    aptitude INTEGER DEFAULT 0,
    coding INTEGER DEFAULT 0,
    resume INTEGER DEFAULT 0
    )
    """)   
    cur.execute("""
CREATE TABLE IF NOT EXISTS companies(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    package TEXT NOT NULL,
    role TEXT,
    eligibility REAL
)
""")
    cur.execute("""
CREATE TABLE IF NOT EXISTS progress(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    aptitude INTEGER DEFAULT 0,
    coding INTEGER DEFAULT 0,
    resume INTEGER DEFAULT 0,

    aptitude_attempted INTEGER DEFAULT 0,
    aptitude_correct INTEGER DEFAULT 0,

    coding_solved INTEGER DEFAULT 0,

    resume_completed INTEGER DEFAULT 0
)
""")
    cur.execute("""
CREATE TABLE IF NOT EXISTS aptitude_questions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT,
    option1 TEXT,
    option2 TEXT,
    option3 TEXT,
    option4 TEXT,
    answer TEXT,
    topic TEXT
)
""")

    conn.commit()
    conn.close()


create_table()



@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        college = request.form['college']
        branch = request.form['branch']
        year = request.form['year']
        cgpa = request.form['cgpa']


        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()

        hashed_pw = generate_password_hash(password)
        cur.execute("""
        INSERT INTO users
        (name,email,phone,password,college,branch,year,cgpa,role)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (name, email, phone, hashed_pw, college, branch, year, cgpa, "user"))
        cur.execute("SELECT id FROM users WHERE email=?", (email,))
        user_id = cur.fetchone()[0]
        session['user_id'] = user_id 
        session['user_name'] = name
        cur.execute("""
        INSERT INTO progress (user_id, aptitude, coding, resume)
            VALUES (?, 0, 0, 0)
            """, (user_id,))
        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[4], password):

            session['user_id'] = user[0]
            session['user_name'] = user[1]

            return redirect(url_for('dashboard'))

        return "Invalid Login"

    # ✅ THIS MUST ALWAYS BE OUTSIDE POST BLOCK
    return render_template('login.html')


@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
    SELECT aptitude, coding, resume
    FROM progress
    WHERE user_id=?
""", (session['user_id'],))

    data = cur.fetchone()

    cur.execute("""
    SELECT name,email,phone,college,branch,year,cgpa
    FROM users
    WHERE id=?
""", (session['user_id'],))

    user = cur.fetchone()

    conn.close()

    if not data:
        aptitude = coding = resume = 0
    else:
        aptitude, coding, resume = data

    placement_score = int(
        (aptitude * 0.4) +
        (coding * 0.4) +
        (resume * 0.2)
    )
   

    name = session.get('user_name', '').strip()

    if not name:
        name = "User" 
    return render_template(
        'dashboard.html',
        user= user,
        name=session['user_name'],
        profile_letter=session['user_name'][0].upper() if session.get('user_name') else "U",
        aptitude=aptitude,
        coding=coding,
        resume=resume,
        placement_score=placement_score
    )
    



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():

    if request.method == 'POST':

        email = request.form['email']

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        )

        user = cur.fetchone()

        conn.close()

        if user:
            return "Account Found"

        return "Email Not Registered"

    return render_template(
        'forgot.html'
    )
@app.route('/profile', methods=['GET', 'POST'])
def profile():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    try:
        if request.method == 'POST':

            name = request.form['name']
            phone = request.form['phone']
            college = request.form['college']
            branch = request.form['branch']
            year = request.form['year']
            cgpa = request.form['cgpa']

            cur.execute("""
            UPDATE users
            SET name=?, phone=?, college=?, branch=?, year=?, cgpa=?
            WHERE id=?
            """, (
                name, phone, college, branch, year, cgpa,
                session['user_id']
            ))

            conn.commit()
            session['user_name'] = name

        cur.execute("""
        SELECT name, email, phone, college, branch, year, cgpa, role
        FROM users
        WHERE id=?
        """, (session['user_id'],))

        user = cur.fetchone()

    finally:
        conn.close()

    return render_template("profile.html", user=user)
   
@app.route('/update_aptitude', methods=['POST'])
def update_aptitude():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    value = request.form['aptitude']

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
    UPDATE progress
    SET aptitude=?
    WHERE user_id=?
    """, (value, session['user_id']))

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


@app.route('/update_coding', methods=['POST'])
def update_coding():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    value = request.form['coding']

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
    UPDATE progress
    SET coding=?
    WHERE user_id=?
    """, (value, session['user_id']))

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


@app.route('/update_resume', methods=['POST'])
def update_resume():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    value = request.form['resume']

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
    UPDATE progress
    SET resume=?
    WHERE user_id=?
    """, (value, session['user_id']))

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))



@app.route('/coding')
def coding():
    return "<h1>Coding Section Coming Soon</h1>"


@app.route('/resume')
def resume():
    return render_template('resume.html')


@app.route('/companies')
def companies():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
    SELECT company_name, package, role, eligibility
    FROM companies
    """)

    companies = cur.fetchall()

    conn.close()

    return render_template(
        'companies.html',
        companies=companies
    )

@app.route('/admin')
def admin():

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("SELECT * FROM users")

    users = cur.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        users=users
    )
@app.route('/add_company', methods=['GET', 'POST'])
def add_company():

    if request.method == 'POST':

        company = request.form['company']
        package = request.form['package']
        role = request.form['role']
        cgpa = request.form['cgpa']

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO companies
        (company_name, package, role, eligibility)
        VALUES (?,?,?,?)
        """, (company, package, role, cgpa))

        conn.commit()
        conn.close()

        return redirect(url_for('companies'))

    return render_template('add_company.html')
@app.route('/aptitude')
def aptitude():

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
    SELECT aptitude
    FROM progress
    WHERE user_id=?
    """, (session['user_id'],))

    score = cur.fetchone()[0]

    conn.close()

    return render_template(
        'aptitude_home.html',
        score=score
    )
@app.route('/submit_aptitude', methods=['POST'])
def submit_aptitude():

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
    SELECT id, answer
    FROM aptitude_questions
    """)

    questions = cur.fetchall()

    correct = 0

    for q in questions:

        qid = q[0]
        answer = q[1]

        user_answer = request.form.get(
            f"q{qid}"
        )

        if user_answer == answer:
            correct += 1

    score = int((correct / len(questions)) * 100)

    cur.execute("""
    UPDATE progress
    SET aptitude=?
    WHERE user_id=?
    """, (score, session['user_id']))

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))
@app.route('/aptitude_test')
def aptitude_test():

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
    SELECT *
    FROM aptitude_questions
    ORDER BY RANDOM()
    LIMIT 20
    """)

    questions = cur.fetchall()

    conn.close()

    return render_template(
        'aptitude.html',
        questions=questions
    )
if __name__ == '__main__':
    app.run(debug=True)