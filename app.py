from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import hashlib
from datetime import datetime, timedelta

# IMPORTS
from mt5_signal import get_signal, get_trade_history, manual_close_trade

app = Flask(__name__)
app.secret_key = "secret123"

# ================= HASH =================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ================= DB CONNECT =================
def get_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# ================= INIT DB =================
def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        lastname TEXT,
        mobile TEXT,
        email TEXT,
        username TEXT,
        password TEXT,
        status TEXT,
        role TEXT,
        expiry_date TEXT,
        payment_status TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ================= ADMIN CREATE =================
def create_admin():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("""
        INSERT INTO users 
        (name, lastname, mobile, email, username, password, status, role, expiry_date, payment_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("Admin", "User", "9999999999", "admin@gmail.com", "admin",
         hash_password("admin123"),
         "approved", "admin", "2099-12-31", "paid"))

    conn.commit()
    conn.close()

create_admin()

# ================= ROUTES =================
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

# ================= REGISTER =================
@app.route('/register_user', methods=['POST'])
def register_user():
    data = request.form
    expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=?", (data['username'],))
    if c.fetchone():
        return "❌ Username already exists"

    c.execute("""
    INSERT INTO users 
    (name, lastname, mobile, email, username, password, status, role, expiry_date, payment_status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        data['name'],
        data['lastname'],
        data['mobile'],
        data['email'],
        data['username'],
        hash_password(data['password']),
        "pending",
        "user",
        expiry,
        "pending"
    ))

    conn.commit()
    conn.close()

    session['temp_user'] = data['username']
    return redirect('/payment')

# ================= LOGIN =================
@app.route('/login_user', methods=['POST'])
def login_user():
    username = request.form['username']
    password = hash_password(request.form['password'])

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()

    if not user:
        return "❌ Invalid Login"

    if user["status"] == "pending":
        session['temp_user'] = user["username"]
        return redirect('/payment')

    if user["status"] == "rejected":
        return "❌ Account Rejected"

    if user["expiry_date"] and datetime.now() > datetime.strptime(user["expiry_date"], "%Y-%m-%d"):
        return "❌ Subscription Expired"

    session['user'] = user["username"]
    session['role'] = user["role"]

    return redirect('/admin' if user["role"] == "admin" else '/dashboard')

# ================= PAYMENT =================
@app.route('/payment')
def payment():
    if 'temp_user' not in session:
        return redirect('/')
    return render_template('payment.html')

@app.route('/payment_success', methods=['POST'])
def payment_success():
    username = session.get('temp_user')

    conn = get_db()
    c = conn.cursor()

    expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    c.execute("""
        UPDATE users 
        SET payment_status='paid',
            status='pending',
            expiry_date=?
        WHERE username=?
    """, (expiry, username))

    conn.commit()
    conn.close()

    session.pop('temp_user', None)

    return "✅ Payment successful! Waiting for admin approval"

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('dashboard.html', user=session['user'])

# ================= ADMIN =================
@app.route('/admin')
def admin():
    if 'user' not in session or session.get('role') != "admin":
        return "Access Denied"

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()

    return render_template('admin.html', users=users)

# ================= SIGNAL API (FIXED) =================
@app.route('/get_signal')
def signal_api():
    if 'user' not in session:
        return jsonify({"error": "unauthorized"})

    data = get_signal()

    # 🔥 FORCE REQUIRED FIELDS (VERY IMPORTANT)
    data["confidence"] = data.get("confidence", 0)
    data["trade_type"] = data.get("trade_type", "NONE")
    data["timeframes"] = data.get("timeframes", {})

    return jsonify(data)

# ================= CLOSE TRADE (FIXED) =================
@app.route('/close_trade')
def close_trade_route():
    if 'user' not in session:
        return jsonify({"error": "unauthorized"})

    data = get_signal()

    if not data.get("trade"):
        return jsonify({"msg": "no trade"})

    price = data.get("price", 0)
    result = manual_close_trade(price)

    return jsonify({"closed": result})

# ================= HISTORY =================
@app.route('/api/history')
def api_history():
    if 'user' not in session:
        return jsonify([])
    return jsonify(get_trade_history())

@app.route('/trade_history')
def trade_history():
    if 'user' not in session:
        return redirect('/')
    return render_template('trade_history.html')

# ================= PROFILE =================
@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect('/')

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (session['user'],))
    user = c.fetchone()
    conn.close()

    return render_template('profile.html', user=user)

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)