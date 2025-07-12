from flask import Blueprint, render_template, redirect, session, url_for
home_bp = Blueprint('home', __name__)


def require_login(role=None):
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    if role and session.get('role', '').lower() != role:
        return redirect(url_for('auth.login'))
    return None

@home_bp.route('/')
def index():
    return render_template('index.html')

@home_bp.route('/home')
def home():
    if redirect_resp := require_login():
        return redirect_resp
    is_admin = session.get('role', '').lower() == 'responsable'
    return render_template('home.html', is_admin=is_admin)
