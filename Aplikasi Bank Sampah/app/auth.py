import uuid
from functools import wraps
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
# Hapus import 'check_password_hash'
# from werkzeug.security import check_password_hash

# Impor service dan User model dari __init__.py
from . import service, User, repo

# --- Blueprint ---
auth_bp = Blueprint('auth', __name__, url_prefix='/')

# --- Role Decorator ---
def role_required(role_name):
    """Decorator untuk membatasi akses berdasarkan role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role_name:
                flash(f"Akses ditolak. Anda harus login sebagai {role_name}.", 'error')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --- Rute Autentikasi ---

@auth_bp.route('/login', methods=('GET', 'POST'))
def login():
    """Menangani proses login user, sesuai screenshot"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Redirect jika sudah login

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # --- HAPUS SEMUA DEBUGGING PRINT ---
        
        # Ambil data user dari repository
        user_dict = repo.get_user_by_email(email)
        
        if user_dict:
            
            try:
                # Ganti 'check_password_hash' dengan perbandingan string biasa
                is_password_correct = (user_dict['password'] == password)
                
                if is_password_correct:
                    user_obj = User(user_dict)
                    login_user(user_obj)
                    flash(f"Selamat datang kembali, {user_obj.nama}!", 'success')
                    
                    if user_obj.is_admin:
                        return redirect(url_for('main.dashboard_admin'))
                    elif user_obj.is_pengepul:
                        return redirect(url_for('main.dashboard_pengepul'))
                    else:
                        return redirect(url_for('main.dashboard_pengguna'))
                else:
                    # print("Login GAGAL: Password tidak cocok.") <-- Dihapus
                    flash('Email atau password salah.', 'error')
            except Exception as e:
                # print(f"ERROR saat perbandingan: {e}") <-- Dihapus
                flash(f'Terjadi error: {e}', 'error')
        
        else:
            # print("Login GAGAL: User TIDAK DITEMUKAN.") <-- Dihapus
            flash('Email atau password salah.', 'error')
            
        # print("--- AKHIR DEBUGGING ---\n") <-- Dihapus

    return render_template('login.html')

@auth_bp.route('/register', methods=('GET', 'POST'))
def register():
    """Menangani proses registrasi user baru, sesuai screenshot"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        nama = request.form['nama']
        email = request.form['email']
        password = request.form['password']
        alamat = request.form['alamat']
        role = request.form.get('role', 'pengguna') 
        
        try:
            # Panggil service untuk registrasi
            new_user = service.register_user(
                id=str(uuid.uuid4()),
                nama=nama,
                email=email,
                password=password,
                role=role,
                alamat=alamat
            )
            if new_user:
                flash('Registrasi berhasil! Silakan login.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Email sudah terdaftar.', 'error')
        except Exception as e:
            flash(f'Terjadi kesalahan: {e}', 'error')

    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Menangani proses logout user"""
    logout_user()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('auth.login'))