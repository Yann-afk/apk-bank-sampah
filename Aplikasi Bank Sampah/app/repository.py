import json
import os
import threading

class JsonRepository:
    """
    Data Access Layer (DAL) untuk mengelola data dalam file JSON.
    Semua operasi baca/tulis ke database.json HARUS melalui kelas ini.
    """
    _lock = threading.Lock() # Lock untuk menangani file I/O yang thread-safe

    def __init__(self, db_path):
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"File database tidak ditemukan di: {db_path}")
        self.db_path = db_path

    def _read_db(self):
        """Membaca seluruh data dari file JSON dengan thread-safe."""
        with self._lock:
            try:
                with open(self.db_path, 'r') as f:
                    # Periksa apakah file kosong
                    content = f.read()
                    if not content:
                        return self._get_empty_db_structure()
                    return json.loads(content)
            except (IOError, json.JSONDecodeError) as e:
                print(f"Error reading DB: {e}. Returning empty structure.")
                return self._get_empty_db_structure()
                
    def _get_empty_db_structure(self):
        """Mengembalikan struktur DB kosong jika file rusak atau kosong."""
        return {
            "users": {},
            "sampah": {},
            "rewards": {},
            "pickups": {},
            "transactions": {}
        }

    def _write_db(self, data):
        """Menulis seluruh data ke file JSON dengan thread-safe."""
        with self._lock:
            try:
                with open(self.db_path, 'w') as f:
                    json.dump(data, f, indent=2)
            except IOError as e:
                print(f"Error writing to DB: {e}")

    # --- User Methods ---
    
    def get_all_users(self):
        data = self._read_db()
        return list(data.get('users', {}).values())

    def get_user_by_id(self, user_id):
        data = self._read_db()
        return data.get('users', {}).get(user_id)

    def get_user_by_email(self, email):
        data = self._read_db()
        for user in data.get('users', {}).values():
            if user['email'] == email:
                return user
        return None

    def add_user(self, user_data):
        data = self._read_db()
        if user_data['id'] in data['users']:
            raise ValueError("User ID sudah ada")
        data['users'][user_data['id']] = user_data
        self._write_db(data)
        return user_data
        
    def update_user(self, user_id, updates):
        data = self._read_db()
        if user_id not in data['users']:
            return None
        data['users'][user_id].update(updates)
        self._write_db(data)
        return data['users'][user_id]

    # --- Sampah (Waste) Methods ---
    
    def get_sampah_types(self):
        data = self._read_db()
        return list(data.get('sampah', {}).values())
        
    def get_sampah_by_id(self, sampah_id):
        data = self._read_db()
        return data.get('sampah', {}).get(sampah_id)

    # --- Reward Methods ---
    
    def get_rewards(self):
        data = self._read_db()
        return list(data.get('rewards', {}).values())
        
    def get_reward_by_id(self, reward_id):
        data = self._read_db()
        return data.get('rewards', {}).get(reward_id)

    # --- Pickup Methods ---
    
    def get_pickups_by_user(self, user_id):
        data = self._read_db()
        pickups = []
        for pickup in data.get('pickups', {}).values():
            if pickup['userId'] == user_id:
                pickups.append(pickup)
        # Urutkan berdasarkan tanggal, terbaru dulu
        return sorted(pickups, key=lambda p: p['tanggal'], reverse=True)
        
    def get_pickups_by_status(self, status):
        data = self._read_db()
        pickups = []
        for pickup in data.get('pickups', {}).values():
            if pickup['status'] == status:
                pickups.append(pickup)
        return sorted(pickups, key=lambda p: p['tanggal'])

    def get_pickup_by_id(self, pickup_id):
        data = self._read_db()
        return data.get('pickups', {}).get(pickup_id)
        
    def add_pickup(self, pickup_data):
        data = self._read_db()
        if pickup_data['id'] in data['pickups']:
            raise ValueError("Pickup ID sudah ada")
        data['pickups'][pickup_data['id']] = pickup_data
        self._write_db(data)
        return pickup_data

    def update_pickup(self, pickup_id, updates):
        data = self._read_db()
        if pickup_id not in data['pickups']:
            return None
        data['pickups'][pickup_id].update(updates)
        self._write_db(data)
        return data['pickups'][pickup_id]

    # --- Transaction Methods ---
    
    def add_transaction(self, tx_data):
        data = self._read_db()
        if tx_data['id'] in data['transactions']:
            raise ValueError("Transaction ID sudah ada")
        data['transactions'][tx_data['id']] = tx_data
        self._write_db(data)
        return tx_data
        
    def get_transactions_by_user(self, user_id):
        data = self._read_db()
        txs = []
        for tx in data.get('transactions', {}).values():
            if tx['userId'] == user_id:
                txs.append(tx)
        return sorted(txs, key=lambda t: t['tanggal'], reverse=True)