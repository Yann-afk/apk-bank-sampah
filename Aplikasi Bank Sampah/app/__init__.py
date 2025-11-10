import os
import json
from flask import Flask, redirect, url_for
from flask_login import LoginManager, UserMixin, current_user
from .repository import JsonRepository
from .services import WasteBankService

# --- Inisialisasi Layer ---
# Tentukan path absolut ke database.json di root proyek
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database.json'))

# Inisialisasi satu instance dari Repository dan Service
try:
    repo = JsonRepository(db_path)
except FileNotFoundError:
    print(f"ERROR: database.json not found at {db_path}")
    # Buat file kosong jika tidak ada
    with open(db_path, 'w') as f:
        json.dump({
            "users": {},
            "sampah": {},
            "rewards": {},
            "pickups": {},
            "transactions": {}
        }, f, indent=2)
    repo = JsonRepository(db_path)
    print("Created empty database.json.")

service = WasteBankService(repo)
login_manager = LoginManager()

# --- Model User untuk Flask-Login ---
class User(UserMixin):
    """
    Wrapper class untuk data user dari JSON agar kompatibel dengan Flask-Login
    """
    def __init__(self, user_dict):
        self._user = user_dict
        self.id = user_dict.get('id')
        self.nama = user_dict.get('nama')
        self.email = user_dict.get('email')
        self.role = user_dict.get('role')
        self.alamat = user_dict.get('alamat')
        self.totalPoin = user_dict.get('totalPoin', 0)

    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_pengepul(self):
        return self.role == 'pengepul'

    @property
    def is_pengguna(self):
        return self.role == 'pengguna'


@login_manager.user_loader
def load_user(user_id):
    """Callback untuk Flask-Login untuk me-load user dari sesi"""
    user_dict = repo.get_user_by_id(user_id)
    if user_dict:
        return User(user_dict)
    return None

@login_manager.unauthorized_handler
def unauthorized():
    """Redirect user yang belum login ke halaman login"""
    return redirect(url_for('auth.login'))

# --- App Factory ---
def create_app(config_object=None):
    """
    Factory function untuk membuat instance aplikasi Flask.
    """
    app = Flask(__name__, instance_relative_config=False)
    
    # Konfigurasi dasar
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-super-aman')
    )

    # Inisialisasi ekstensi
    login_manager.init_app(app)

    with app.app_context():
        # Import blueprints
        from . import auth
        from . import routes

        # Register blueprints
        app.register_blueprint(auth.auth_bp)
        app.register_blueprint(routes.main_bp)

        # Setel halaman login
        login_manager.login_view = 'auth.login'
        
        # Injeksi service dan repo ke app context (opsional, tapi bisa berguna)
        app.service = service
        app.repo = repo

    return app