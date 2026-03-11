# ================================================================
#                 PHARMACY INVENTORY MANAGEMENT SYSTEM
# ================================================================
# Backend (CLI) - MySQL + SQLAlchemy + Pandas
# File   : app_backend.py
# Run    : python app_backend.py
# Notes  : - NO getpass (no IDLE echo warning)
#          - MySQL password hard-coded (DB_PASS = "1234")
#          - Admin/User menus with renamed items:
#              * "Brand Medicine" / "Generic Medicine"
#              * "Advanced Functions" (composition-driven)
#              * User area uses "Functions" (not Queries)
#          - Removed: Low Stock (threshold), Price Trend
#          - Defensive input validation to avoid FK errors
# ================================================================

import sys
import hashlib
from typing import Optional, Dict, Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# -------------------- CONFIGURATION --------------------
DB_USER = "root"
DB_HOST = "127.0.0.1"
DB_PORT = "3306"
MAIN_DB = "medicine_db"
AUTH_DB = "user_management"

# Hard-coded MySQL password (per your request)
DB_PASS = "1234"

# Admin signup code (case-insensitive check)
ADMIN_SIGNUP_CODE = "ADM-2025-OK"

# Pretty title width
LINE_WIDTH = 63

# -------------------- SIMPLE INPUT HELPERS --------------------
def read_password(prompt: str) -> str:
    """Plain input for passwords (no getpass => no IDLE warnings)."""
    return input(prompt)

def hash_password(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()

def prompt_int(msg: str, default: Optional[int] = None) -> Optional[int]:
    s = input(msg).strip()
    if s == "" and default is not None:
        return int(default)
    try:
        return int(s)
    except ValueError:
        print("Please enter a valid integer.")
        return None

def prompt_float(msg: str, default: Optional[float] = None) -> Optional[float]:
    s = input(msg).strip()
    if s == "" and default is not None:
        return float(default)
    try:
        return float(s)
    except ValueError:
        print("Please enter a valid amount.")
        return None

def show_table(df: pd.DataFrame, max_rows: int = 20):
    if df is None or df.empty:
        print("\n[No records found]\n")
    else:
        print("\n" + df.head(max_rows).to_string(index=False) + "\n")

def normalize_type(label: str) -> Optional[str]:
    s = label.strip().lower()
    if s in ("brand", "medicine brand", "brand medicine", "b"):
        return "brand"
    if s in ("generic", "generic medicine", "generic medicine brand", "g"):
        return "generic"
    return None

def pp_title(text: str):
    print("=" * LINE_WIDTH)
    print(text.center(LINE_WIDTH))
    print("=" * LINE_WIDTH)

# -------------------- DATABASE HELPERS --------------------
def make_engine(db_name: str, pwd: str):
    url = f"mysql+mysqlconnector://{DB_USER}:{pwd}@{DB_HOST}:{DB_PORT}/{db_name}"
    return create_engine(url, echo=False, future=True)

def run_select_df(engine, sql: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)

def run_exec(engine, sql: str, params: Optional[Dict[str, Any]] = None):
    """Execute write with all numeric params coerced to native Python types."""
    safe_params = {}
    if params:
        for k, v in params.items():
            if isinstance(v, (pd.Int64Dtype,)):
                v = int(v)
            # Coerce NumPy / pandas numeric scalars to native Python
            try:
                import numpy as np
                if isinstance(v, (np.integer,)):
                    v = int(v)
                if isinstance(v, (np.floating,)):
                    v = float(v)
            except Exception:
                pass
            safe_params[k] = v
    with engine.begin() as conn:
        conn.execute(text(sql), safe_params)

# -------------------- AUTH DATABASE (user_management) --------------------
def ensure_auth_schema(eng_auth):
    run_exec(eng_auth, """
        CREATE TABLE IF NOT EXISTS users(
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(256) NOT NULL,
            role ENUM('admin','user') NOT NULL
        )
    """)

def get_user_record(eng_auth, username: str) -> Optional[Dict[str, Any]]:
    df = run_select_df(eng_auth, "SELECT * FROM users WHERE username=:u", {"u": username})
    return None if df.empty else df.iloc[0].to_dict()

def create_user(eng_auth, username: str, plain_pw: str, role: str):
    run_exec(eng_auth,
             "INSERT INTO users(username, password_hash, role) VALUES(:u,:p,:r)",
             {"u": username, "p": hash_password(plain_pw), "r": role})
    print(f"\n✅ User '{username}' created as '{role}'.\n")

# -------------------- STARTUP --------------------
pp_title("PHARMACY INVENTORY MANAGEMENT SYSTEM")
print("\nStarting backend...\n")

try:
    eng_main = make_engine(MAIN_DB, DB_PASS)
    eng_auth = make_engine(AUTH_DB, DB_PASS)
    run_select_df(eng_main, "SELECT 1;")
    run_select_df(eng_auth, "SELECT 1;")
except SQLAlchemyError as e:
    print("❌ Database connection failed. Please check MySQL settings.")
    print(str(e))
    sys.exit(1)

print(f"[OK] Connected to {MAIN_DB} and {AUTH_DB} .\n")
ensure_auth_schema(eng_auth)

# Create first admin if not exists
adm = run_select_df(eng_auth, "SELECT COUNT(*) AS c FROM users WHERE role='admin'")
if int(adm.iloc[0]["c"]) == 0:
    print("No admin found. Creating first admin...\n")
    while True:
        u = input("Admin username: ").strip()
        pw = read_password("Admin password: ")
        pw2 = read_password("Repeat password: ")
        if not u or not pw:
            print("Username/password cannot be empty.")
            continue
        if pw != pw2:
            print("❌ Passwords didn't match. Try again.")
            continue
        create_user(eng_auth, u, pw, "admin")
        break

# -------------------- COMMON LOOKUPS / VALIDATION --------------------
def next_id(table: str, id_col: str) -> int:
    df = run_select_df(eng_main, f"SELECT COALESCE(MAX({id_col}),0)+1 AS nid FROM {table}")
    # force native int (avoid numpy.int64)
    return int(df.iloc[0]["nid"])

def choose_composition_by_name() -> Optional[int]:
    """Ask for composition (medicine) name fragment and return chosen composition_id."""
    frag = input("Enter medicine (composition) name fragment: ").strip()
    if not frag:
        print("Please enter a valid name.")
        return None
    df = run_select_df(eng_main, """
        SELECT composition_id, salt_name, strength, form
        FROM Composition
        WHERE salt_name LIKE :x
        ORDER BY salt_name
        LIMIT 25
    """, {"x": f"%{frag}%"})
    if df.empty:
        print("No match found.")
        return None
    show_table(df, 25)
    cid = prompt_int("Enter composition_id: ")
    if cid is None:
        return None
    # verify exists
    chk = run_select_df(eng_main, "SELECT 1 FROM Composition WHERE composition_id=:i", {"i": int(cid)})
    if chk.empty:
        print("❌ composition_id not found.")
        return None
    return int(cid)

def pharmacy_exists(pid: int) -> bool:
    df = run_select_df(eng_main, "SELECT pharmacy_id FROM Pharmacy WHERE pharmacy_id=:p", {"p": int(pid)})
    return not df.empty

def brand_exists(bid: int) -> bool:
    df = run_select_df(eng_main, "SELECT brand_id FROM Medicine_Brand WHERE brand_id=:i", {"i": int(bid)})
    return not df.empty

def generic_exists(gid: int) -> bool:
    df = run_select_df(eng_main, "SELECT generic_id FROM Medicine_Generic WHERE generic_id=:i", {"i": int(gid)})
    return not df.empty

# -------------------- ADMIN: CATALOG --------------------
def add_composition():
    print("\nAdd Composition")
    name = input("Salt name: ").strip()
    strength = input("Strength (e.g., 500 mg): ").strip()
    form = input("Form (tablet/capsule/syrup/injection): ").strip()
    if not name:
        print("Name required.")
        return
    nid = int(next_id("Composition", "composition_id"))
    run_exec(eng_main, """
        INSERT INTO Composition(composition_id, salt_name, strength, form)
        VALUES(:i,:n,:s,:f)
    """, {"i": int(nid), "n": name, "s": strength, "f": form})
    print("✅ Composition added.\n")

def add_manufacturer():
    print("\nAdd Manufacturer")
    nm = input("Manufacturer name: ").strip()
    addr = input("Address: ").strip()
    if not nm:
        print("Name required.")
        return
    mid = int(next_id("Manufacturer", "manufacturer_id"))
    run_exec(eng_main, """
        INSERT INTO Manufacturer(manufacturer_id, name, address)
        VALUES(:i,:n,:a)
    """, {"i": int(mid), "n": nm, "a": addr})
    print("✅ Manufacturer added.\n")

def add_brand():
    print("\nAdd Brand Medicine")
    name = input("Brand name: ").strip()
    composition_id = prompt_int("composition_id: ")
    price = prompt_float("price: ")
    manufacturer_id = prompt_int("manufacturer_id: ")
    category_id = prompt_int("category_id: ")
    if not all([name, composition_id, price, manufacturer_id, category_id]):
        print("All fields required.")
        return
    chk = run_select_df(eng_main, "SELECT 1 FROM Composition WHERE composition_id=:i", {"i": int(composition_id)})
    if chk.empty:
        print("❌ composition_id not found.")
        return
    bid = int(next_id("Medicine_Brand", "brand_id"))
    run_exec(eng_main, """
        INSERT INTO Medicine_Brand(brand_id, brand_name, composition_id, price, manufacturer_id, category_id)
        VALUES(:i,:n,:c,:p,:m,:k)
    """, {"i": int(bid), "n": name, "c": int(composition_id), "p": float(price),
          "m": int(manufacturer_id), "k": int(category_id)})
    print("✅ Brand Medicine added.\n")

def add_generic():
    print("\nAdd Generic Medicine")
    name = input("Generic name: ").strip()
    composition_id = prompt_int("composition_id: ")
    price = prompt_float("price: ")
    manufacturer_id = prompt_int("manufacturer_id: ")
    category_id = prompt_int("category_id: ")
    if not all([name, composition_id, price, manufacturer_id, category_id]):
        print("All fields required.")
        return
    chk = run_select_df(eng_main, "SELECT 1 FROM Composition WHERE composition_id=:i", {"i": int(composition_id)})
    if chk.empty:
        print("❌ composition_id not found.")
        return
    gid = int(next_id("Medicine_Generic", "generic_id"))
    run_exec(eng_main, """
        INSERT INTO Medicine_Generic(generic_id, generic_name, composition_id, price, manufacturer_id, category_id)
        VALUES(:i,:n,:c,:p,:m,:k)
    """, {"i": int(gid), "n": name, "c": int(composition_id), "p": float(price),
          "m": int(manufacturer_id), "k": int(category_id)})
    print("✅ Generic Medicine added.\n")

def update_price_brand():
    bid = prompt_int("Brand Medicine ID: ")
    if bid is None or not brand_exists(int(bid)):
        print("❌ Invalid Brand Medicine ID.")
        return
    newp = prompt_float("New price: ")
    if newp is None:
        return
    run_exec(eng_main, "UPDATE Medicine_Brand SET price=:p WHERE brand_id=:i",
             {"p": float(newp), "i": int(bid)})
    print("✅ Brand Medicine price updated.\n")

def update_price_generic():
    gid = prompt_int("Generic Medicine ID: ")
    if gid is None or not generic_exists(int(gid)):
        print("❌ Invalid Generic Medicine ID.")
        return
    newp = prompt_float("New price: ")
    if newp is None:
        return
    run_exec(eng_main, "UPDATE Medicine_Generic SET price=:p WHERE generic_id=:i",
             {"p": float(newp), "i": int(gid)})
    print("✅ Generic Medicine price updated.\n")

def delete_brand():
    bid = prompt_int("Brand Medicine ID to delete: ")
    if bid is None:
        return
    run_exec(eng_main, "DELETE FROM Medicine_Brand WHERE brand_id=:i", {"i": int(bid)})
    print("✅ Brand Medicine deleted (if existed).\n")

def delete_generic():
    gid = prompt_int("Generic Medicine ID to delete: ")
    if gid is None:
        return
    run_exec(eng_main, "DELETE FROM Medicine_Generic WHERE generic_id=:i", {"i": int(gid)})
    print("✅ Generic Medicine deleted (if existed).\n")

def admin_catalog_menu():
    while True:
        print("\n================= ADMIN → CATALOG =================")
        print("1) Add Composition")
        print("2) Add Manufacturer")
        print("3) Add Brand Medicine")
        print("4) Add Generic Medicine")
        print("5) Update price (Brand Medicine)")
        print("6) Update price (Generic Medicine)")
        print("7) Delete Brand Medicine")
        print("8) Delete Generic Medicine")
        print("0) Back")
        c = input("Choice: ").strip()
        if   c == "1": add_composition()
        elif c == "2": add_manufacturer()
        elif c == "3": add_brand()
        elif c == "4": add_generic()
        elif c == "5": update_price_brand()
        elif c == "6": update_price_generic()
        elif c == "7": delete_brand()
        elif c == "8": delete_generic()
        elif c == "0": break
        else:
            print("Invalid option.\n")

# -------------------- ADMIN: INVENTORY / SALES --------------------
def view_inventory():
    sql = """
    SELECT i.inventory_id, i.pharmacy_id, p.name AS pharmacy_name,
           i.medicine_type, i.medicine_id, i.stock_quantity, i.expiry_date
    FROM Inventory i
    LEFT JOIN Pharmacy p ON p.pharmacy_id = i.pharmacy_id
    ORDER BY i.stock_quantity DESC, i.expiry_date ASC
    LIMIT 60;
    """
    df = run_select_df(eng_main, sql)
    show_table(df, 60)

def record_supply():
    print("\nRecord Supply")
    pid = prompt_int("Pharmacy ID: ")
    if pid is None or not pharmacy_exists(int(pid)):
        print("❌ Invalid pharmacy id.")
        return
    mtype = input("Medicine type ('medicine brand' / 'generic medicine brand'): ").strip()
    mtype_norm = normalize_type(mtype)
    if not mtype_norm:
        print("❌ Invalid medicine type.")
        return
    mid = prompt_int("Medicine ID (integer): ")
    if mid is None:
        return
    if mtype_norm == "brand" and not brand_exists(int(mid)):
        print("❌ Brand Medicine ID not found.")
        return
    if mtype_norm == "generic" and not generic_exists(int(mid)):
        print("❌ Generic Medicine ID not found.")
        return
    qty = prompt_int("Quantity: ")
    if qty is None or int(qty) <= 0:
        print("❌ Quantity must be positive.")
        return

    supply_id = int(next_id("Supply_Log", "supply_id"))
    run_exec(eng_main, """
        INSERT INTO Supply_Log(supply_id, pharmacy_id, medicine_type, medicine_id, quantity, supply_date)
        VALUES(:i,:p,:t,:m,:q,CURDATE())
    """, {"i": int(supply_id), "p": int(pid), "t": mtype_norm, "m": int(mid), "q": int(qty)})

    # Pick any batch for same med (or create)
    row = run_select_df(eng_main, """
        SELECT batch_id, expiry_date
        FROM Batch
        WHERE medicine_type=:t AND medicine_id=:m
        ORDER BY manufacture_date DESC
        LIMIT 1
    """, {"t": mtype_norm, "m": int(mid)})
    if row.empty:
        batch_id = int(next_id("Batch", "batch_id"))
        run_exec(eng_main, """
            INSERT INTO Batch(batch_id, medicine_type, medicine_id, manufacture_date, expiry_date, batch_no)
            VALUES(:b,:t,:m,CURDATE(),DATE_ADD(CURDATE(), INTERVAL 730 DAY), CONCAT('AUTO-',:b))
        """, {"b": int(batch_id), "t": mtype_norm, "m": int(mid)})
        expiry_date = run_select_df(eng_main, "SELECT expiry_date FROM Batch WHERE batch_id=:b", {"b": int(batch_id)}).iloc[0]["expiry_date"]
    else:
        batch_id = int(row.iloc[0]["batch_id"])
        expiry_date = row.iloc[0]["expiry_date"]

    invrow = run_select_df(eng_main, """
        SELECT inventory_id, stock_quantity
        FROM Inventory
        WHERE pharmacy_id=:p AND medicine_type=:t AND medicine_id=:m AND batch_id=:b
        LIMIT 1
    """, {"p": int(pid), "t": mtype_norm, "m": int(mid), "b": int(batch_id)})

    if invrow.empty:
        inv_id = int(next_id("Inventory", "inventory_id"))
        run_exec(eng_main, """
            INSERT INTO Inventory(inventory_id, pharmacy_id, medicine_type, medicine_id, batch_id, stock_quantity, expiry_date)
            VALUES(:i,:p,:t,:m,:b,:q,:e)
        """, {"i": int(inv_id), "p": int(pid), "t": mtype_norm, "m": int(mid),
              "b": int(batch_id), "q": int(qty), "e": expiry_date})
    else:
        inv_id = int(invrow.iloc[0]["inventory_id"])
        oldq = int(invrow.iloc[0]["stock_quantity"])
        run_exec(eng_main, "UPDATE Inventory SET stock_quantity=:x WHERE inventory_id=:i",
                 {"x": int(oldq) + int(qty), "i": int(inv_id)})

    print("✅ Supply recorded and inventory updated.\n")

def record_sale():
    print("\nRecord Sale")
    pid = prompt_int("Pharmacy ID: ")
    if pid is None or not pharmacy_exists(int(pid)):
        print("❌ Invalid pharmacy id.")
        return
    mtype = input("Medicine type ('medicine brand' / 'generic medicine brand'): ").strip()
    mtype_norm = normalize_type(mtype)
    if not mtype_norm:
        print("❌ Invalid medicine type. Enter 'medicine brand' or 'generic medicine brand'.")
        return
    mid = prompt_int("Medicine ID (integer): ")
    if mid is None:
        return
    if mtype_norm == "brand" and not brand_exists(int(mid)):
        print("❌ Brand Medicine ID not found.")
        return
    if mtype_norm == "generic" and not generic_exists(int(mid)):
        print("❌ Generic Medicine ID not found.")
        return
    qty = prompt_int("Quantity: ")
    if qty is None or int(qty) <= 0:
        print("❌ Quantity must be positive.")
        return

    sale_id = int(next_id("Sales_Log", "sale_id"))
    # First, try to deduct inventory (oldest expiry first)
    inv = run_select_df(eng_main, """
        SELECT inventory_id, stock_quantity
        FROM Inventory
        WHERE pharmacy_id=:p AND medicine_type=:t AND medicine_id=:m AND stock_quantity>0
        ORDER BY expiry_date ASC
        LIMIT 1
    """, {"p": int(pid), "t": mtype_norm, "m": int(mid)})
    if inv.empty:
        print("⚠ No inventory found for that medicine in this pharmacy. Recording sale anyway.")
    else:
        inv_id = int(inv.iloc[0]["inventory_id"])
        stock = int(inv.iloc[0]["stock_quantity"])
        new_stock = stock - int(qty)
        run_exec(eng_main, "UPDATE Inventory SET stock_quantity=:s WHERE inventory_id=:i",
                 {"s": int(new_stock), "i": int(inv_id)})

    run_exec(eng_main, """
        INSERT INTO Sales_Log(sale_id, pharmacy_id, medicine_type, medicine_id, quantity, sale_date)
        VALUES(:i,:p,:t,:m,:q,CURDATE())
    """, {"i": int(sale_id), "p": int(pid), "t": mtype_norm, "m": int(mid), "q": int(qty)})

    print("✅ Sale recorded successfully.\n")

def admin_inventory_menu():
    while True:
        print("\n================ ADMIN → INVENTORY/SALES ================")
        print("1) Record Supply")
        print("2) Record Sale")
        print("3) View Inventory")
        print("0) Back")
        c = input("Choice: ").strip()
        if   c == "1": record_supply()
        elif c == "2": record_sale()
        elif c == "3": view_inventory()
        elif c == "0": break
        else:
            print("Invalid option.\n")

# -------------------- REPORTS (Admin & User shared where relevant) --------------------
def report_counts():
    df = run_select_df(eng_main, """
    SELECT 
      (SELECT COUNT(*) FROM Composition) AS composition,
      (SELECT COUNT(*) FROM Medicine_Category) AS medicine_category,
      (SELECT COUNT(*) FROM Manufacturer) AS manufacturer,
      (SELECT COUNT(*) FROM Medicine_Generic) AS medicine_generic,
      (SELECT COUNT(*) FROM Medicine_Brand) AS medicine_brand,
      (SELECT COUNT(*) FROM Brand_Generic_Map) AS brand_generic_map,
      (SELECT COUNT(*) FROM Pharmacy) AS pharmacy,
      (SELECT COUNT(*) FROM Supplier) AS supplier,
      (SELECT COUNT(*) FROM Batch) AS batch,
      (SELECT COUNT(*) FROM Inventory) AS inventory,
      (SELECT COUNT(*) FROM Supply_Log) AS supply_log,
      (SELECT COUNT(*) FROM Sales_Log) AS sales_log,
      (SELECT COUNT(*) FROM Price_History) AS price_history,
      (SELECT COUNT(*) FROM Govt_Subsidy) AS govt_subsidy,
      (SELECT COUNT(*) FROM SideEffects) AS sideeffects;
    """)
    row = df.iloc[0].to_dict()
    print("\n=== TABLE COUNTS ===")
    for k in ["composition","medicine_category","manufacturer","medicine_generic",
              "medicine_brand","brand_generic_map","pharmacy","supplier","batch",
              "inventory","supply_log","sales_log","price_history","govt_subsidy","sideeffects"]:
        print(f"{k:20s} : {int(row[k])}")
    print()

def report_top_sellers(limit: int = 10):
    df = run_select_df(eng_main, f"""
        SELECT medicine_type, medicine_id, SUM(quantity) AS total_sold
        FROM Sales_Log
        GROUP BY medicine_type, medicine_id
        ORDER BY total_sold DESC
        LIMIT {int(limit)};
    """)
    show_table(df, int(limit))

def report_near_expiry(days: int = 90):
    df = run_select_df(eng_main, f"""
        SELECT batch_id, medicine_type, medicine_id, expiry_date
        FROM Batch
        WHERE expiry_date <= DATE_ADD(CURDATE(), INTERVAL {int(days)} DAY)
        ORDER BY expiry_date ASC
        LIMIT 50;
    """)
    show_table(df, 50)

def report_category_popularity(limit: int = 25):
    # Example aggregate with joins
    df = run_select_df(eng_main, """
        SELECT mc.category_name, SUM(s.quantity) AS total_sold
        FROM Sales_Log s
        JOIN (
            SELECT brand_id AS id, category_id, 'brand' AS t FROM Medicine_Brand
            UNION ALL
            SELECT generic_id AS id, category_id, 'generic' AS t FROM Medicine_Generic
        ) AS x ON x.id = s.medicine_id AND x.t = s.medicine_type
        JOIN Medicine_Category mc ON mc.category_id = x.category_id
        GROUP BY mc.category_name
        ORDER BY total_sold DESC
        LIMIT 25;
    """)
    show_table(df, limit)

def report_suppliers_for_med(mtype: str, mid: int):
    # Suppliers that supplied this medicine (join Supply_Log -> Supplier)
    mtype = normalize_type(mtype)
    if not mtype:
        print("Invalid type.")
        return
    df = run_select_df(eng_main, """
        SELECT su.supplier_id, su.name AS supplier_name, su.contact
        FROM Supply_Log sl
        JOIN Supplier su ON su.supplier_id = sl.supplier_id
        WHERE sl.medicine_type = :t AND sl.medicine_id = :m
        GROUP BY su.supplier_id, su.name, su.contact
        ORDER BY su.supplier_id
        LIMIT 20;
    """, {"t": mtype, "m": int(mid)})
    show_table(df, 20)

def admin_reports_menu():
    while True:
        print("\n===================== ADMIN → REPORTS =====================")
        print("1) Table Counts")
        print("2) Top Sellers")
        print("3) Near Expiry (<=90 days)")
        print("4) Category Popularity (sales by category)")
        print("5) Suppliers for a Medicine")
        print("0) Back")
        c = input("Choice: ").strip()
        if   c == "1": report_counts()
        elif c == "2": report_top_sellers()
        elif c == "3": report_near_expiry()
        elif c == "4": report_category_popularity()
        elif c == "5":
            t = input("Medicine type ('medicine brand' / 'generic medicine brand'): ")
            t = normalize_type(t)
            if not t:
                print("Invalid type.")
                continue
            mid = prompt_int("Medicine ID: ")
            if mid is None:
                continue
            report_suppliers_for_med(t, int(mid))
        elif c == "0": break
        else:
            print("Invalid.\n")

# -------------------- ADVANCED FUNCTIONS (composition-driven) --------------------
def fn_cheapest_generics_for_composition():
    cid = choose_composition_by_name()
    if not cid:
        return
    df = run_select_df(eng_main, """
        SELECT 'generic' AS type, g.generic_id AS id, g.generic_name AS name, g.price
        FROM Medicine_Generic g
        WHERE g.composition_id = :c
        ORDER BY g.price ASC
        LIMIT 20;
    """, {"c": int(cid)})
    show_table(df, 20)

def fn_brand_generic_alternatives_for_composition():
    cid = choose_composition_by_name()
    if not cid:
        return
    # Compare each brand with generics of same composition and price diff
    df = run_select_df(eng_main, """
        SELECT 
            'brand' AS src_type,
            b.brand_id AS src_id,
            b.brand_name AS src_name,
            b.price AS src_price,
            'generic' AS alt_type,
            g.generic_id AS alt_id,
            g.generic_name AS alt_name,
            g.price AS alt_price,
            ROUND( (b.price - g.price) / NULLIF(g.price,0) * 100, 2) AS price_diff_pct
        FROM Medicine_Brand b
        JOIN Medicine_Generic g ON g.composition_id = b.composition_id
        WHERE b.composition_id = :c
        ORDER BY price_diff_pct DESC
        LIMIT 25;
    """, {"c": int(cid)})
    show_table(df, 25)

def fn_availability_by_pharmacy_for_composition():
    cid = choose_composition_by_name()
    if not cid:
        return
    # Any brand/generic with same composition
    df = run_select_df(eng_main, """
        SELECT i.pharmacy_id, p.name AS pharmacy_name, p.location,
               SUM(i.stock_quantity) AS total_qty,
               MIN(i.expiry_date) AS earliest_expiry
        FROM Inventory i
        JOIN Pharmacy p ON p.pharmacy_id = i.pharmacy_id
        LEFT JOIN Medicine_Brand  b ON (i.medicine_type='brand'   AND b.brand_id=i.medicine_id)
        LEFT JOIN Medicine_Generic g ON (i.medicine_type='generic' AND g.generic_id=i.medicine_id)
        WHERE ( (i.medicine_type='brand'   AND b.composition_id=:c)
             OR (i.medicine_type='generic' AND g.composition_id=:c) )
        GROUP BY i.pharmacy_id, p.name, p.location
        HAVING total_qty > 0
        ORDER BY total_qty DESC
        LIMIT 25;
    """, {"c": int(cid)})
    show_table(df, 25)

def admin_advanced_menu():
    while True:
        print("\n================= ADMIN → ADVANCED FUNCTIONS =================")
        print("1) Cheapest alternatives (Generic) for a Composition")
        print("2) Brand ↔ Generic alternatives for a Composition (with % diff)")
        print("3) Availability by pharmacy (for a Composition)")
        print("0) Back")
        c = input("Choice: ").strip()
        if   c == "1": fn_cheapest_generics_for_composition()
        elif c == "2": fn_brand_generic_alternatives_for_composition()
        elif c == "3": fn_availability_by_pharmacy_for_composition()
        elif c == "0": break
        else:
            print("Invalid.\n")

# -------------------- USER AREA --------------------
def user_search_by_medicine_name():
    """User search: input medicine name (we interpret as composition salt_name fragment)."""
    frag = input("Enter medicine name (composition) fragment: ").strip()
    if not frag:
        print("Please type something.")
        return
    # Show matching compositions first
    comps = run_select_df(eng_main, """
        SELECT composition_id, salt_name, strength, form
        FROM Composition
        WHERE salt_name LIKE :x
        ORDER BY salt_name
        LIMIT 20;
    """, {"x": f"%{frag}%"})
    if comps.empty:
        print("No matching compositions.")
        return
    show_table(comps, 20)
    cid = prompt_int("Pick composition_id to see brands and generics: ")
    if cid is None:
        return
    chk = run_select_df(eng_main, "SELECT 1 FROM Composition WHERE composition_id=:i", {"i": int(cid)})
    if chk.empty:
        print("Invalid composition_id.")
        return
    # Show brands & generics for that composition
    df = run_select_df(eng_main, """
        SELECT 'brand' AS type, b.brand_id AS id, b.brand_name AS name, b.price,
               b.manufacturer_id, b.composition_id, b.category_id
        FROM Medicine_Brand b
        WHERE b.composition_id=:c
        UNION ALL
        SELECT 'generic' AS type, g.generic_id AS id, g.generic_name AS name, g.price,
               g.manufacturer_id, g.composition_id, g.category_id
        FROM Medicine_Generic g
        WHERE g.composition_id=:c
        ORDER BY type, price ASC
        LIMIT 40;
    """, {"c": int(cid)})
    show_table(df, 40)

def user_cheapest_generics_for_composition():
    fn_cheapest_generics_for_composition()

def user_brand_generic_alternatives_for_composition():
    fn_brand_generic_alternatives_for_composition()

def user_availability_by_pharmacy_for_composition():
    fn_availability_by_pharmacy_for_composition()

def user_reports_menu():
    while True:
        print("\n====================== USER → REPORTS ======================")
        print("1) Top Sellers")
        print("2) Near Expiry (<=90 days)")
        print("0) Back")
        c = input("Choice: ").strip()
        if   c == "1": report_top_sellers()
        elif c == "2": report_near_expiry()
        elif c == "0": break
        else:
            print("Invalid.\n")

def user_functions_menu():
    while True:
        print("\n====================== USER → FUNCTIONS ======================")
        print("1) Search Medicines")
        print("2) Cheapest alternatives (Generic) for a Composition")
        print("3) Brand ↔ Generic alternatives for a Composition (with % diff)")
        print("4) Availability by pharmacy (for a Composition)")
        print("0) Back")
        c = input("Choice: ").strip()
        if   c == "1": user_search_by_medicine_name()
        elif c == "2": user_cheapest_generics_for_composition()
        elif c == "3": user_brand_generic_alternatives_for_composition()
        elif c == "4": user_availability_by_pharmacy_for_composition()
        elif c == "0": break
        else:
            print("Invalid.\n")

# -------------------- AUTH FLOWS --------------------
def admin_dashboard():
    while True:
        print("\nADMIN DASHBOARD")
        print("1) Catalog")
        print("2) Inventory / Sales")
        print("3) Reports")
        print("4) Advanced Functions")
        print("0) Logout")
        c = input("Choice: ").strip()
        if   c == "1": admin_catalog_menu()
        elif c == "2": admin_inventory_menu()
        elif c == "3": admin_reports_menu()
        elif c == "4": admin_advanced_menu()
        elif c == "0": break
        else:
            print("Invalid.\n")

def admin_login_flow():
    u = input("Username: ").strip()
    p = read_password("Password: ")
    rec = get_user_record(eng_auth, u)
    if not rec or rec["role"] != "admin":
        print("Invalid admin credentials.")
        return
    if hash_password(p) != rec["password_hash"]:
        print("Invalid admin credentials.")
        return
    print(f"Welcome, {u} (admin)")
    admin_dashboard()

def admin_signup_flow():
    print("\n(Signup requires admin code)")
    code = input("Enter admin signup code (ask supervisor): ").strip()
    if code.lower() != ADMIN_SIGNUP_CODE.lower():
        print("Invalid admin code.")
        return
    u = input("Choose admin username: ").strip()
    if get_user_record(eng_auth, u):
        print("Username exists.")
        return
    p = read_password("Password: ")
    p2 = read_password("Repeat: ")
    if p != p2:
        print("Password mismatch.")
        return
    create_user(eng_auth, u, p, "admin")

def user_login_flow():
    u = input("Username: ").strip()
    p = read_password("Password: ")
    rec = get_user_record(eng_auth, u)
    if not rec or rec["role"] != "user":
        print("Invalid user credentials.")
        return
    if hash_password(p) != rec["password_hash"]:
        print("Invalid user credentials.")
        return
    print(f"Welcome, {u} (user)")
    # user dashboard
    while True:
        print("\nUSER DASHBOARD")
        print("1) Reports")
        print("2) Functions")
        print("0) Logout")
        c = input("Choice: ").strip()
        if   c == "1": user_reports_menu()
        elif c == "2": user_functions_menu()
        elif c == "0":
            print("Goodbye.")
            break
        else:
            print("Invalid.\n")

def user_signup_flow():
    u = input("Choose username: ").strip()
    if get_user_record(eng_auth, u):
        print("Username exists.")
        return
    p = read_password("Password: ")
    p2 = read_password("Repeat: ")
    if p != p2:
        print("Password mismatch.")
        return
    create_user(eng_auth, u, p, "user")

# -------------------- MAIN MENUS --------------------
def admin_entry_menu():
    while True:
        print("\nADMIN")
        print("1) Login")
        print("2) Signup (requires admin code)")
        print("0) Back")
        c = input("Choice: ").strip()
        if   c == "1": admin_login_flow()
        elif c == "2": admin_signup_flow()
        elif c == "0": break
        else:
            print("Invalid.\n")

def main():
    while True:
        print("\n=== Medicine DB CLI ===")
        print("1) Admin")
        print("2) User")
        print("0) Exit")
        c = input("Choice: ").strip()
        if   c == "1": admin_entry_menu()
        elif c == "2":
            print("\nUSER")
            print("1) Login")
            print("2) Signup")
            print("0) Back")
            cc = input("Choice: ").strip()
            if   cc == "1": user_login_flow()
            elif cc == "2": user_signup_flow()
            elif cc == "0": continue
            else:
                print("Invalid.\n")
        elif c == "0":
            print("Exiting.")
            break
        else:
            print("Invalid.\n")

# -------------------- ENTRY --------------------
if __name__ == "__main__":
    main()
