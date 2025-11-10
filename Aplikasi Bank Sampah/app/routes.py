from flask import (Blueprint, render_template, request, redirect, url_for, flash, abort
)
from flask_login import login_required, current_user
from .auth import role_required
from datetime import date  # <--- TAMBAHKAN BARIS INI

from . import service, repo


# --- Blueprint ---
main_bp = Blueprint('main', __name__, url_prefix='/')


# --- Rute Utama dan Dasbor ---

@main_bp.route('/')
def index():
    """Halaman utama, redirect ke dasbor jika sudah login"""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
        
    if current_user.is_admin:
        return redirect(url_for('main.dashboard_admin'))
    elif current_user.is_pengepul:
        return redirect(url_for('main.dashboard_pengepul'))
    else:
        return redirect(url_for('main.dashboard_pengguna'))

@main_bp.route('/dashboard/pengguna')
@login_required
@role_required('pengguna')
def dashboard_pengguna():
    """Dasbor untuk Pengguna (User), sesuai screenshot"""
    # Ambil data riwayat transaksi
    transactions = repo.get_transactions_by_user(current_user.id)
    return render_template(
        'dashboard_pengguna.html', 
        user=current_user,
        transactions=transactions
    )

@main_bp.route('/dashboard/pengepul')
@login_required
@role_required('pengepul')
def dashboard_pengepul():
    """Dasbor untuk Pengepul"""
    # Ambil tugas (pickup yang masih 'diminta')
    tasks = repo.get_pickups_by_status('diminta')
    # Ambil daftar jenis sampah untuk form input
    sampah_types = repo.get_sampah_types()
    
    tasks_with_user = []
    for task in tasks:
        user = repo.get_user_by_id(task['userId'])
        task['namaPengguna'] = user['nama'] if user else 'Pengguna Dihapus'
        tasks_with_user.append(task)
        
    return render_template(
        'dashboard_pengepul.html', 
        tasks=tasks_with_user, 
        sampah_types=sampah_types
    )

@main_bp.route('/dashboard/admin')
@login_required
@role_required('admin')
def dashboard_admin():
    """Dasbor untuk Admin"""
    users = repo.get_all_users()
    rewards = repo.get_rewards()
    sampah_types = repo.get_sampah_types()
    
    return render_template(
        'dashboard_admin.html',
        all_users=users,
        all_rewards=rewards,
        all_sampah=sampah_types
    )

# --- Rute Fitur Pengguna ---

@main_bp.route('/pickup/new', methods=('GET', 'POST'))
@login_required
@role_required('pengguna')
def new_pickup():
    if request.method == 'POST':
        tanggal = request.form['tanggal']
        waktu = request.form['waktu']
        lokasi = request.form.get('lokasi', current_user.alamat)
        try:
            service.schedule_pickup(
            user_id=current_user.id,
            tanggal=tanggal,
            waktu=waktu,
            lokasi=lokasi
            )
            flash('Penjemputan berhasil dijadwalkan!', 'success')
            return redirect(url_for('main.dashboard_pengguna'))
        except Exception as e:
            flash(f'Terjadi kesalahan: {e}', 'error')

    today = date.today()
    today_string = today.strftime('%Y-%m-%d')
    return render_template('pickup_form.html', default_tanggal=today_string)
@main_bp.route('/rewards')
@login_required
@role_required('pengguna')
def reward_catalog():
    """Menampilkan katalog reward, sesuai screenshot"""
    rewards = repo.get_rewards()
    # Mengambil data user terbaru (terutama totalPoin)
    user_data = repo.get_user_by_id(current_user.id)
    user_poin = user_data.get('totalPoin', 0)
    
    return render_template(
        'reward_catalog.html', 
        rewards=rewards, 
        user_poin=user_poin
    )

@main_bp.route('/rewards/redeem/<string:reward_id>', methods=('POST',))
@login_required
@role_required('pengguna')
def redeem_reward(reward_id):
    """Memproses permintaan penukaran reward"""
    try:
        success, message = service.redeem_reward(current_user.id, reward_id)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
    except Exception as e:
        flash(f'Terjadi kesalahan: {e}', 'error')
        
    return redirect(url_for('main.reward_catalog'))

@main_bp.route('/map')
@login_required
def map_placeholder():
    """Halaman placeholder untuk fitur Peta Bank Sampah"""
    return render_template('map_placeholder.html')

# --- Rute Fitur Pengepul ---

@main_bp.route('/pickup/confirm/<string:pickup_id>', methods=('POST',))
@login_required
@role_required('pengepul')
def confirm_pickup(pickup_id):
    """Memproses konfirmasi pickup dan input sampah oleh pengepul"""
    
    waste_details = {}
    for key, value in request.form.items():
        if key.startswith('kg-'):
            sampah_id = key.split('-')[1]
            if value:
                waste_details[sampah_id] = value
                
    if not waste_details:
        flash('Input berat sampah tidak boleh kosong.', 'error')
        return redirect(url_for('main.dashboard_pengepul'))

    try:
        tx = service.confirm_pickup(
            pickup_id=pickup_id,
            pengepul_id=current_user.id,
            waste_details=waste_details
        )
        flash(f"Pickup berhasil dikonfirmasi! {tx['totalPoin']} poin ditambahkan ke pengguna.", 'success')
    except ValueError as e:
        flash(f'Gagal konfirmasi: {e}', 'error')
    except Exception as e:
        flash(f'Terjadi kesalahan sistem: {e}', 'error')

    return redirect(url_for('main.dashboard_pengepul'))