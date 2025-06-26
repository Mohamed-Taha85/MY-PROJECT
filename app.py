import os
from io import BytesIO, StringIO
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, send_file
)
from flask_sqlalchemy import SQLAlchemy
from xhtml2pdf import pisa
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
app.secret_key = 'your_secret_key'

# Context processor to inject current datetime
@app.context_processor
def inject_now():
    return {'now': datetime.now}

# Callback to resolve static asset paths for xhtml2pdf
def link_callback(uri, rel):
    if uri.startswith('/'):
        # Convert URI to relative path within static folder
        path = os.path.join(app.root_path, uri.lstrip('/'))
    else:
        path = os.path.join(os.path.dirname(__file__), uri)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Asset not found: {path}")
    return path

# --- Models ---

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employe')

class Checklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    created_by = db.Column(db.String(80), nullable=False)
    items = db.relationship('ChecklistItem', backref='checklist', lazy=True)

class ChecklistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('checklist.id'), nullable=False)
    item_text = db.Column(db.Text, nullable=False)
    answer = db.Column(db.String(10), nullable=False)
    comment = db.Column(db.Text)

class ChecklistTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    items = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

with app.app_context():
    db.create_all()

# --- Helper to enforce login and role ---

def require_login(role=None):
    if 'username' not in session:
        return redirect(url_for('login'))
    if role and session.get('role', '').lower() != role:
        return redirect(url_for('login'))
    return None

# --- Routes ---

@app.route('/')
def index():
    users = User.query.all()
    return render_template('index.html', users=users)

@app.route('/home')
def home():
    if redirect_resp := require_login():
        return redirect_resp
    is_admin = session.get('role', '').lower() == 'responsable'
    return render_template('home.html', is_admin=is_admin)

@app.route('/creer_modele', methods=['GET', 'POST'])
def creer_modele():
    if redirect_resp := require_login(role='responsable'):
        return redirect_resp
    message = ''
    if request.method == 'POST':
        title = request.form.get('title')
        items = request.form.get('items')
        if title and items:
            tpl = ChecklistTemplate(
                title=title,
                items=items,
                created_by=session['username']
            )
            db.session.add(tpl)
            db.session.commit()
            message = 'Modèle enregistré avec succès.'
        else:
            message = 'Veuillez remplir tous les champs.'
    return render_template('creer_module.html', message=message)

@app.route('/remplir_checklist', methods=['GET', 'POST'])
def remplir_checklist():
    if redirect_resp := require_login():
        return redirect_resp
    templates = ChecklistTemplate.query.all()
    message = ''
    selected_template = None
    items = []
    if request.method == 'POST':
        selected_id = request.form.get('template_id', type=int)
        if 'load_template' in request.form and selected_id:
            selected_template = ChecklistTemplate.query.get(selected_id)
            items = [l.strip() for l in selected_template.items.splitlines() if l.strip()]
        elif 'submit_checklist' in request.form and selected_id:
            tpl = ChecklistTemplate.query.get(selected_id)
            if tpl:
                items = [l.strip() for l in tpl.items.splitlines() if l.strip()]
                checklist = Checklist(
                    title=tpl.title,
                    date=datetime.today().date(),
                    status='Complétée',
                    created_by=session['username']
                )
                db.session.add(checklist)
                db.session.flush()
                for idx, item in enumerate(items):
                    answer = request.form.get(f'item_{idx}')
                    comment = request.form.get(f'comment_{idx}', '').strip()
                    db.session.add(ChecklistItem(
                        checklist_id=checklist.id,
                        item_text=item,
                        answer=answer,
                        comment=comment
                    ))
                db.session.commit()
                message = 'Check‑list enregistrée avec succès.'
    return render_template(
        'remplir_checklist.html',
        templates=templates,
        selected_template=selected_template,
        items=items,
        message=message
    )

@app.route('/voir_details/<int:checklist_id>')
def voir_details(checklist_id):
    if redirect_resp := require_login():
        return redirect_resp
    checklist = Checklist.query.get_or_404(checklist_id)
    items = ChecklistItem.query.filter_by(checklist_id=checklist_id).all()
    return render_template('details.html', checklist=checklist, items=items)

@app.route('/historique')
def historique():
    if redirect_resp := require_login():
        return redirect_resp
    frm = request.args.get('from_date')
    to = request.args.get('to_date')
    user_filter = request.args.get('user')
    q = Checklist.query
    if frm and to:
        q = q.filter(Checklist.date.between(frm, to))
    if user_filter:
        q = q.filter_by(created_by=user_filter)
    checklists = q.filter_by(status='Complétée').order_by(Checklist.date.desc()).all()
    users = [u.username for u in User.query.all()]
    return render_template(
        'historique.html',
        checklists=checklists,
        users=users,
        from_date=frm,
        to_date=to,
        user_filter=user_filter
    )

@app.route('/non_conformites')
def non_conformites():
    if redirect_resp := require_login():
        return redirect_resp
    non_conform_items = ChecklistItem.query.filter_by(answer='Non').all()
    return render_template('non_conformites.html', non_conform_items=non_conform_items)

@app.route('/generer_rapport', methods=['GET', 'POST'])
def generer_rapport():
    # Si non connecté, renvoyer vers login
    if 'username' not in session:
        return redirect(url_for('login'))

    # Si connecté mais pas responsable, renvoyer vers home
    if session.get('role', '').lower() != 'responsable':
        return redirect(url_for('home'))

    # À ce stade, c'est un responsable
    report_data = []
    from_date = to_date = ''
    if request.method == 'POST':
        from_date = request.form.get('from_date')
        to_date   = request.form.get('to_date')
        if from_date and to_date:
            report_data = Checklist.query.filter(
                Checklist.date.between(from_date, to_date),
                Checklist.status == 'Complétée'
            ).order_by(Checklist.date).all()

    return render_template(
        'generer_rapport.html',
        report_data=report_data,
        from_date=from_date,
        to_date=to_date
    )


@app.route('/generer_rapport/pdf', methods=['POST'])
def export_rapport_pdf():
    if redirect_resp := require_login(role='responsable'):
        return redirect_resp
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    if not from_date or not to_date:
        return 'Dates invalides', 400
    checklists = Checklist.query.filter(
        Checklist.date.between(from_date, to_date),
        Checklist.status=='Complétée'
    ).order_by(Checklist.date).all()
    html = render_template(
        'rapport_pdf.html',
        checklists=checklists,
        from_date=from_date,
        to_date=to_date
    )
    result = BytesIO()
    pisa_status = pisa.CreatePDF(
        StringIO(html),
        dest=result,
        link_callback=link_callback
    )
    if pisa_status.err:
        app.logger.error(f'PDF gen error: {pisa_status.err}')
        return 'Erreur lors de la génération du PDF', 500
    result.seek(0)
    return send_file(
        result,
        download_name='rapport_checklists.pdf',
        as_attachment=True,
        mimetype='application/pdf'
    )

@app.route('/export_non_conformites_pdf')
def export_non_conformites_pdf():
    if redirect_resp := require_login():
        return redirect_resp
    # Debug print query result in console
    non_conform_items = ChecklistItem.query.filter_by(answer='Non').all()
    print("Non-conformites query:", non_conform_items)  # Added debug print

    html = render_template(
        'non_conformites_pdf.html',
        non_conform_items=non_conform_items,
        debug=True  # Pass debug flag to template
    )
    result = BytesIO()
    pisa_status = pisa.CreatePDF(
        StringIO(html),
        dest=result,
        link_callback=link_callback
    )
    if pisa_status.err:
        app.logger.error(f'Non‑conformités PDF error: {pisa_status.err}')
        return 'Erreur lors de la génération du PDF', 500
    result.seek(0)
    return send_file(
        result,
        download_name='non_conformites.pdf',
        as_attachment=True,
        mimetype='application/pdf'
    )

@app.route('/login', methods=['GET', 'POST'])
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
            return redirect(url_for('home'))
        else:
            message = "Nom d'utilisateur ou mot de passe incorrect."
    return render_template('login.html', message=message)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role'].lower().strip()
        if User.query.filter_by(username=username).first():
            return "Ce nom d'utilisateur existe déjà."
        db.session.add(User(username=username, password=password, role=role))
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

