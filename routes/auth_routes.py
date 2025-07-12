from flask import render_template, request, redirect, session, url_for
from models import db, User


auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('home.home'))
        else:
            message = "Nom d'utilisateur ou mot de passe incorrect."
    return render_template('login.html', message=message)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role'].lower().strip()
        if User.query.filter_by(username=username).first():
            return "Ce nom d'utilisateur existe déjà."
        db.session.add(User(username=username, password=password, role=role))
        db.session.commit()
        return redirect(url_for('auth.login'))
    return render_template('signup.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home.index'))
