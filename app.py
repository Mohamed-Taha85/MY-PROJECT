from flask import Flask
from config import Config
from models import db
from routes import auth_bp, home_bp, checklist_bp, export_bp
from datetime import datetime
import os

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = 'your_secret_key'
db.init_app(app)

# Register route blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(home_bp)
app.register_blueprint(checklist_bp)
app.register_blueprint(export_bp)

# Context processor for templates
@app.context_processor
def inject_now():
    return {'now': datetime.now}

# Used by xhtml2pdf for asset resolving
def link_callback(uri, rel):
    if uri.startswith('/'):
        return os.path.join(app.root_path, uri.lstrip('/'))
    return os.path.join(os.path.dirname(__file__), uri)

# Initialize database
with app.app_context():
    db.create_all()

# Start app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)


# cd "C:\Users\mtmme\OneDrive - Al Akhawayn University in Ifrane\Documents\my project\hse_app"
#git add . && git commit -m "Update project: modify files and enhance functionality" && git push origin main
