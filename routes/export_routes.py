from flask import Blueprint, render_template, request, redirect, session, url_for, send_file
from io import BytesIO, StringIO
from datetime import datetime
from models import Checklist, ChecklistItem
from xhtml2pdf import pisa
import os

export_bp = Blueprint('export', __name__)

# Helper to enforce login
def require_login(role=None):
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    if role and session.get('role', '').lower() != role:
        return redirect(url_for('auth.login'))
    return None

# PDF assets link resolver
def link_callback(uri, rel):
    if uri.startswith('/'):
        return os.path.join(os.getcwd(), uri.lstrip('/'))
    return os.path.join(os.path.dirname(__file__), uri)

@export_bp.route('/generer_rapport', methods=['GET', 'POST'])
def generer_rapport():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    if session.get('role', '').lower() != 'responsable':
        return redirect(url_for('home.home'))

    report_data = []
    from_date = to_date = ''
    if request.method == 'POST':
        from_date = request.form.get('from_date')
        to_date = request.form.get('to_date')
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

@export_bp.route('/generer_rapport/pdf', methods=['POST'])
def export_rapport_pdf():
    if redirect_resp := require_login(role='responsable'):
        return redirect_resp
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    if not from_date or not to_date:
        return 'Dates invalides', 400
    checklists = Checklist.query.filter(
        Checklist.date.between(from_date, to_date),
        Checklist.status == 'Complétée'
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
        return 'Erreur lors de la génération du PDF', 500
    result.seek(0)
    return send_file(
        result,
        download_name='rapport_checklists.pdf',
        as_attachment=True,
        mimetype='application/pdf'
    )

@export_bp.route('/export_non_conformites_pdf')
def export_non_conformites_pdf():
    if redirect_resp := require_login():
        return redirect_resp
    non_conform_items = ChecklistItem.query.filter_by(answer='Non').all()
    html = render_template(
        'non_conformites_pdf.html',
        non_conform_items=non_conform_items
    )
    result = BytesIO()
    pisa_status = pisa.CreatePDF(
        StringIO(html),
        dest=result,
        link_callback=link_callback
    )
    if pisa_status.err:
        return 'Erreur lors de la génération du PDF', 500
    result.seek(0)
    return send_file(
        result,
        download_name='non_conformites.pdf',
        as_attachment=True,
        mimetype='application/pdf'
    )
