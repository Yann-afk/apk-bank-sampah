import os
from flask import Flask
from flask_login import LoginManager
from app.repository import UserRepository

# Inisialisasi LoginManager untuk mengelola sesi pengguna
login_manager = LoginManager()

def create_app():
    """
    Factory Function untuk membuat instance aplikasi Flask.
    Ini memungkinkan konfigurasi dan setup yang fleksibel.
    """
    
    # Membuat instance aplikasi Flask
    app = Flask(__name__)
    
    # Mengatur secret key untuk keamanan sesi.
    # Di produksi, ini harus berupa nilai acak yang kompleks dan
    # diambil dari environment variable.
    app.config['SECRET_KEY'] = 'kunci-rahasia-yang-sangat-aman-ganti-di-produksi'

    # Inisialisasi LoginManager dengan aplikasi
    login_manager.init_app(app)
    
    # Menentukan view (route) untuk halaman login.
    # Jika pengguna yang belum login mencoba mengakses halaman yang dilindungi,
    # mereka akan dialihkan ke view ini.
    login_manager.login_view = 'auth.login'
    
    # Pesan yang ditampilkan saat pengguna dialihkan ke halaman login.
    login_manager.login_message = 'Silakan login untuk mengakses halaman ini.'
    login_manager.login_message_category = 'warning'

    # Menggunakan 'with app.app_context()' untuk memastikan
    # kita berada dalam konteks aplikasi saat mendaftarkan blueprint.
    with app.app_context():
        # Mendaftarkan Blueprint untuk rute otentikasi (login, register, logout)
        from . import auth
        app.register_blueprint(auth.auth_bp, url_prefix='/auth')

        # Mendaftarkan Blueprint untuk rute utama aplikasi
        from . import routes
        app.register_blueprint(routes.main_bp)

    return app

@login_manager.user_loader
def load_user(user_id):
    """
    Callback yang digunakan oleh Flask-Login untuk me-reload objek pengguna
    dari sesi berdasarkan user ID yang tersimpan.
    """
    # Menggunakan UserRepository untuk mengambil data pengguna dari 'database.json'
    repo = UserRepository()
    user_data = repo.get_user_by_id(user_id)
    
    if user_data:
        # Jika pengguna ditemukan, buat instance dari User class
        # (didefinisikan di auth.py)
        from .auth import User
        return User(user_data)
    
    # Jika pengguna tidak ditemukan, kembalikan None
    return None