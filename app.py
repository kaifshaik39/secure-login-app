import os
import re
import sqlite3
from datetime import timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['DATABASE'] = os.path.join(app.root_path, 'users.db')

MAX_LOGIN_ATTEMPTS = 5


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(app.config['DATABASE'])
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            failed_attempts INTEGER DEFAULT 0,
            locked INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def is_valid_email(email):
    return bool(EMAIL_RE.match(email))


def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped_view


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        error = None
        if not username or not email or not password:
            error = 'All fields are required.'
        elif not is_valid_email(email):
            error = 'Please enter a valid email address.'
        elif not is_strong_password(password):
            error = ('Password must be at least 8 characters and include an '
                      'uppercase letter, a lowercase letter, a number, and a '
                      'special character.')
        elif password != confirm_password:
            error = 'Passwords do not match.'

        db = get_db()
        if error is None:
            existing = db.execute(
                'SELECT id FROM users WHERE username = ? OR email = ?',
                (username, email)
            ).fetchone()
            if existing:
                error = 'Username or email is already registered.'

        if error:
            flash(error, 'danger')
            return render_template('register.html', username=username, email=email)

        password_hash = generate_password_hash(password)
        db.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash)
        )
        db.commit()
        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ? OR email = ?',
            (identifier, identifier.lower())
        ).fetchone()

        if user is None:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')

        if user['locked']:
            flash('This account is locked due to too many failed login attempts. '
                  'Please reset your password or contact support.', 'danger')
            return render_template('login.html')

        if check_password_hash(user['password_hash'], password):
            db.execute(
                'UPDATE users SET failed_attempts = 0 WHERE id = ?', (user['id'],)
            )
            db.commit()
            session.clear()
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f"Welcome back, {user['username']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            attempts = user['failed_attempts'] + 1
            locked = 1 if attempts >= MAX_LOGIN_ATTEMPTS else 0
            db.execute(
                'UPDATE users SET failed_attempts = ?, locked = ? WHERE id = ?',
                (attempts, locked, user['id'])
            )
            db.commit()
            if locked:
                flash('Too many failed attempts. Account has been locked.', 'danger')
            else:
                remaining = MAX_LOGIN_ATTEMPTS - attempts
                flash(f'Invalid username or password. {remaining} attempt(s) remaining.', 'danger')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    user = db.execute(
        'SELECT username, email, created_at FROM users WHERE id = ?',
        (session['user_id'],)
    ).fetchone()
    return render_template('dashboard.html', user=user)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
init_db()

if __name__ == '__main__':
    app.run(debug=True)
