# app_backend_connect.py
"""
Quick connection & auth-check script.
Saves as: C:\DBMS\DBMSPROJECT\app_backend_connect.py
Run: python app_backend_connect.py
What it does:
 - asks for MySQL root password
 - connects to medicine_db and user_management
 - ensures users table exists in user_management
 - if no admin user exists, prompts you to create one (password is hashed)
"""

import getpass
import hashlib
import sys
from sqlalchemy import create_engine, text
import pandas as pd

DB_USER = "root"
DB_HOST = "127.0.0.1"
DB_PORT = "3306"
DB_MED = "medicine_db"
DB_AUTH = "user_management"

def hash_password(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()

def make_engine(dbname: str):
    return create_engine(f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{dbname}", echo=False)

def run_nonselect(engine, sql: str):
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()

def run_select_df(engine, sql: str):
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)

if __name__ == "__main__":
    DB_PASS = getpass.getpass(prompt=f"Enter MySQL password for {DB_USER}: ")

    # 1) Test connection to server & medicine_db
    try:
        eng_med = make_engine(DB_MED)
        with eng_med.connect() as c:
            c.execute(text("SELECT 1"))
        print(f"[OK] Connected to database: {DB_MED}")
    except Exception as e:
        print(f"[ERROR] Cannot connect to {DB_MED}. Check MySQL server and password.")
        print(e)
        sys.exit(1)

    # 2) Ensure auth DB exists and connect
    try:
        eng_root = make_engine("")  # connect without DB to create DB if needed
        # create user_management database if missing
        with eng_root.connect() as c:
            c.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_AUTH};"))
        eng_auth = make_engine(DB_AUTH)
        with eng_auth.connect() as c:
            c.execute(text("SELECT 1"))
        print(f"[OK] Connected to (or created) database: {DB_AUTH}")
    except Exception as e:
        print(f"[ERROR] Cannot create/connect to {DB_AUTH}.")
        print(e)
        sys.exit(1)

    # 3) Ensure users table exists (role ENUM 'admin'|'user')
    users_table_sql = f"""
    CREATE TABLE IF NOT EXISTS users (
       user_id INT AUTO_INCREMENT PRIMARY KEY,
       username VARCHAR(100) UNIQUE NOT NULL,
       password_hash VARCHAR(256) NOT NULL,
       role ENUM('admin','user') NOT NULL DEFAULT 'user',
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    run_nonselect(eng_auth, users_table_sql)
    print("[OK] Ensured table `users` exists in user_management.")

    # 4) Check if any admin exists
    try:
        df = run_select_df(eng_auth, "SELECT COUNT(*) AS c FROM users WHERE role='admin';")
        admin_count = int(df['c'].iloc[0])
    except Exception as e:
        print("[ERROR] Could not check admin users.")
        print(e)
        sys.exit(1)

    if admin_count == 0:
        print("\nNo admin account found. Let's create one now.")
        while True:
            admin_user = input("Enter admin username (e.g. admin): ").strip()
            if not admin_user:
                print("Please enter a username.")
                continue
            admin_pass = getpass.getpass("Enter admin password: ")
            admin_pass2 = getpass.getpass("Repeat admin password: ")
            if admin_pass != admin_pass2:
                print("Passwords do not match. Try again.")
                continue
            pw_hash = hash_password(admin_pass)
            try:
                run_nonselect(eng_auth, f"INSERT INTO users (username, password_hash, role) VALUES ('{admin_user}', '{pw_hash}', 'admin');")
                print(f"[OK] Admin user '{admin_user}' created.")
                break
            except Exception as e:
                print("[ERROR] Could not create admin user. Maybe username exists or SQL error.")
                print(e)
                # ask again
    else:
        print(f"[OK] Admin user(s) already present: {admin_count} found.")

    print("\nAll checks done. If you want, run the full backend next.")
