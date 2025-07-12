from flask import Blueprint, render_template, request, redirect, session, url_for
from datetime import datetime
from models import db, Checklist, ChecklistItem, ChecklistTemplate, User

checklist_bp = Blueprint('checklist', __name__)

# Helper to enforce login
def require_login(role=None):
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    if role and session.get('role', '').lower() != role:
        return redirect(url_for('auth.login'))
    return None

@checklist_bp.route('/creer_modele', methods=['GET', 'POST'])
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

@checklist_bp.route('/remplir_checklist', methods=['GET', 'POST'])
def remplir_checklist():
    if redirect_resp := require_login():
        return redirect_resp

    templates = ChecklistTemplate.query.all()
    message = ''
    selected_template = None
    items = []

    if request.method == 'POST':
        selected_id = request.form.get('template_id', type=int)
        
        # Load the selected template to display the checklist form
        if 'load_template' in request.form and selected_id:
            selected_template = ChecklistTemplate.query.get(selected_id)
            if selected_template:
                items = [line.strip() for line in selected_template.items.splitlines() if line.strip()]

        # Submit the filled checklist
        elif 'submit_checklist' in request.form and selected_id:
            tpl = ChecklistTemplate.query.get(selected_id)
            if tpl:
                items = [line.strip() for line in tpl.items.splitlines() if line.strip()]

                # Create new checklist record
                checklist = Checklist(
                    title=tpl.title,
                    date=datetime.today().date(),
                    status='Complétée',
                    created_by=session['username']
                )
                db.session.add(checklist)
                db.session.flush()  # to get checklist.id before commit

                # Add checklist items (answers + optional comments)
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
                # Reset after submit to show empty form
                selected_template = None
                items = []

    return render_template(
        'remplir_checklist.html',
        templates=templates,
        selected_template=selected_template,
        items=items,
        message=message
    )


@checklist_bp.route('/voir_details/<int:checklist_id>')
def voir_details(checklist_id):
    if redirect_resp := require_login():
        return redirect_resp
    checklist = Checklist.query.get_or_404(checklist_id)
    items = ChecklistItem.query.filter_by(checklist_id=checklist_id).all()
    return render_template('details.html', checklist=checklist, items=items)

@checklist_bp.route('/historique')
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

@checklist_bp.route('/non_conformites')
def non_conformites():
    if redirect_resp := require_login():
        return redirect_resp
    non_conform_items = ChecklistItem.query.filter_by(answer='Non').all()
    return render_template('non_conformites.html', non_conform_items=non_conform_items)
