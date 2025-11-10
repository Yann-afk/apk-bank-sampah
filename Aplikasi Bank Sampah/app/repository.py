import json
import os
import uuid # Untuk generate ID unik

# Menentukan path ke file database JSON
# Menggunakan os.path untuk membuatnya kompatibel antar sistem operasi
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, '..', 'database.json')

# PENTING: Dalam aplikasi nyata, menggunakan file JSON tunggal untuk database
# akan menyebabkan masalah besar (race conditions, performa buruk).
# Ini hanya untuk tujuan demo sesuai permintaan.
# Di produksi, gunakan database seperti PostgreSQL, MySQL, atau Firestore.

class BaseRepository:
    """
    Kelas dasar untuk repositori yang menangani pembacaan dan penulisan
    ke file database JSON.
    """
    def _load_data(self):
        """
        Metode internal untuk membaca seluruh data dari database.json.
        """
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Jika file tidak ada, kembalikan struktur data kosong
            return {"users": {}, "waste_types": {}, "rewards": {}, "pickups": {}, "transactions": {}}
        except json.JSONDecodeError:
            # Jika file korup, kembalikan struktur data kosong
            return {"users": {}, "waste_types": {}, "rewards": {}, "pickups": {}, "transactions": {}}

    def _save_data(self, data):
        """
        Metode internal untuk menulis seluruh data kembali ke database.json.
        """
        try:
            with open(DB_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            # Menangani error jika tidak bisa menulis file
            print(f"Error saving data: {e}")

class UserRepository(BaseRepository):
    """
    Repositori untuk mengelola data pengguna (users).
    """
    def get_all_users(self):
        data = self._load_data()
        return list(data.get('users', {}).values())

    def get_user_by_id(self, user_id):
        data = self._load_data()
        return data.get('users', {}).get(user_id)

    def get_user_by_email(self, email):
        data = self._load_data()
        for user in data.get('users', {}).values():
            if user['email'] == email:
                return user
        return None

    def save_user(self, user_data):
        data = self._load_data()
        
        # Jika 'id' belum ada, buat ID baru
        if 'id' not in user_data or not user_data['id']:
            user_data['id'] = f"u{uuid.uuid4().hex[:6]}" # ID unik singkat
        
        if 'users' not in data:
            data['users'] = {}
            
        data['users'][user_data['id']] = user_data
        self._save_data(data)
        return user_data

class DataRepository(BaseRepository):
    """
    Repositori untuk mengelola data master (sampah, reward)
    dan data transaksional (penjemputan, transaksi).
    """

    # --- Master Data ---
    
    def get_all_waste_types(self):
        data = self._load_data()
        return list(data.get('waste_types', {}).values())

    def get_all_rewards(self):
        data = self._load_data()
        return list(data.get('rewards', {}).values())

    def save_waste_type(self, waste_data):
        data = self._load_data()
        if 'id' not in waste_data:
            waste_data['id'] = f"wt{uuid.uuid4().hex[:4]}"
        if 'waste_types' not in data:
            data['waste_types'] = {}
        data['waste_types'][waste_data['id']] = waste_data
        self._save_data(data)
        return waste_data

    def save_reward(self, reward_data):
        data = self._load_data()
        if 'id' not in reward_data:
            reward_data['id'] = f"r{uuid.uuid4().hex[:4]}"
        if 'rewards' not in data:
            data['rewards'] = {}
        data['rewards'][reward_data['id']] = reward_data
        self._save_data(data)
        return reward_data

    def get_reward_by_id(self, reward_id):
        """Mengambil data reward tunggal berdasarkan ID."""
        data = self._load_data()
        return data.get('rewards', {}).get(reward_id)

    # --- Transactional Data ---

    def get_all_pickups(self):
        data = self._load_data()
        return list(data.get('pickups', {}).values())

    def get_pickups_by_user_id(self, user_id):
        data = self._load_data()
        pickups = []
        for pickup in data.get('pickups', {}).values():
            if pickup['user_id'] == user_id:
                pickups.append(pickup)
        return pickups

    def get_pickups_by_collector_id(self, collector_id):
        data = self._load_data()
        tasks = []
        for pickup in data.get('pickups', {}).values():
            # Menampilkan tugas yang ditugaskan atau yang masih 'menunggu'
            if pickup.get('pengepul_id') == collector_id or pickup['status'] == 'menunggu':
                tasks.append(pickup)
        return tasks
        
    def get_pickup_by_id(self, pickup_id):
        data = self._load_data()
        return data.get('pickups', {}).get(pickup_id)

    def save_pickup(self, pickup_data):
        data = self._load_data()
        if 'id' not in pickup_data:
            pickup_data['id'] = f"p{uuid.uuid4().hex[:6]}"
        if 'pickups' not in data:
            data['pickups'] = {}
        data['pickups'][pickup_data['id']] = pickup_data
        self._save_data(data)
        return pickup_data

    def get_all_transactions(self):
        data = self._load_data()
        return list(data.get('transactions', {}).values())

    def save_transaction(self, trans_data):
        data = self._load_data()
        if 'id' not in trans_data:
            trans_data['id'] = f"t{uuid.uuid4().hex[:6]}"
        if 'transactions' not in data:
            data['transactions'] = {}
        data['transactions'][trans_data['id']] = trans_data
        self._save_data(data)
        return trans_data

    # --- Metode Update Kompleks ---
    
    def update_user_points_and_save(self, user_id, new_total_points):
        """
        Metode ini mengupdate poin pengguna secara spesifik.
        Ini adalah bagian dari "transaksi" file JSON.
        """
        data = self._load_data()
        if user_id in data.get('users', {}):
            data['users'][user_id]['total_poin'] = new_total_points
            self._save_data(data)
            return True
        return False
        
    def confirm_pickup_transaction(self, pickup_data, transaction_data, user_data):
        """
        Menyimpan beberapa update data sekaligus (pseudo-transaksi).
        1. Update pickup
        2. Buat transaksi baru
        3. Update poin pengguna
        """
        data = self._load_data()
        
        # 1. Update pickup
        if 'pickups' not in data: data['pickups'] = {}
        data['pickups'][pickup_data['id']] = pickup_data
        
        # 2. Buat transaksi baru
        if 'id' not in transaction_data:
            transaction_data['id'] = f"t{uuid.uuid4().hex[:6]}"
        if 'transactions' not in data: data['transactions'] = {}
        data['transactions'][transaction_data['id']] = transaction_data
        
        # 3. Update poin pengguna
        if 'users' not in data: data['users'] = {}
        data['users'][user_data['id']] = user_data
        
        self._save_data(data)
        return True

    def redeem_reward_transaction(self, user_data, transaction_data):
        """
        Menyimpan update data untuk redeem reward (pseudo-transaksi).
        1. Buat transaksi baru
        2. Update poin pengguna
        """
        data = self._load_data()
        
        # 1. Buat transaksi baru
        if 'id' not in transaction_data:
            transaction_data['id'] = f"t{uuid.uuid4().hex[:6]}"
        if 'transactions' not in data: data['transactions'] = {}
        data['transactions'][transaction_data['id']] = transaction_data
        
        # 2. Update poin pengguna
        if 'users' not in data: data['users'] = {}
        data['users'][user_data['id']] = user_data
        
        self._save_data(data)
        return True