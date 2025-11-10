
# Proyek Bank Sampah Digital

Proyek ini adalah aplikasi web "Bank Sampah Digital & Daur Ulang" yang dibangun menggunakan Flask, berdasarkan proposal yang telah disusun.

Fitur Utama

- 3 Peran Pengguna: Pengguna (Rumah Tangga), Pengepul, dan Admin.

- Manajemen Sampah: Pengguna dapat menjadwalkan penjemputan sampah terpilah.

- Sistem Poin: Pengepul mengonfirmasi penjemputan dan menginput berat sampah, yang dikonversi menjadi poin untuk Pengguna.

- Katalog Reward: Pengguna dapat menukarkan poin dengan reward.

- Panel Admin: Admin dapat mengelola pengguna, data master (jenis sampah, reward), dan memonitor transaksi.

Arsitektur

Aplikasi ini menerapkan Layered Architecture:

1. Presentation Layer (routes.py, auth.py, templates/): Menangani rute HTTP, permintaan/respons, dan rendering template HTML (menggunakan Tailwind CSS).

2. Business Logic Layer (services.py): Berisi logika bisnis inti, seperti kalkulasi poin, validasi penukaran reward, dan proses bisnis lainnya.

3. Data Access Layer (repository.py): Bertanggung jawab untuk membaca dan menulis data dari/ke sumber data (database.json).

Struktur Proyek

```
proyek_bank_sampah/
├── app/
│ ├── __init__.py
│ ├── auth.py
│ ├── repository.py
│ ├── routes.py
│ ├── services.py
│ └── templates/
│ ├── base.html
│ ├── dashboard_admin.html
│ ├── dashboard_pengepul.html
│ ├── dashboard_pengguna.html
│ ├── login.html
│ ├── map_placeholder.html
│ ├── pickup_form.html
│ ├── register.html
│ ├── reward_catalog.html
│ ├── admin_manage_users.html
│ ├── admin_manage_master_data.html
│ └── admin_monitor_transactions.html
│
├── database.json
├── README.md
├── README_UseCase.md
└── run.py
```

Cara Menjalankan

1. Pastikan Python 3 terinstal.

2. Buat virtual environment (direkomendasikan):

```
python -m venv venv
source venv/bin/activate  # Di Windows: venv\Scripts\activate
```

3. Instal dependensi yang diperlukan:

```
pip install Flask flask-login werkzeug
```

4. Jalankan aplikasi:

```
python run.py
```

5. Buka aplikasi di browser:
Akses http://127.0.0.1:5000

Akun Contoh (dari database.json)

- Admin: admin@example.com (password: admin123)

- Pengepul: pengepul@example.com (password: pengepul123)

- Pengguna: pengguna@example.com (password: pengguna123)

cat: untuk menambahkan akun, kalian hanya perlu registrasi akun
```