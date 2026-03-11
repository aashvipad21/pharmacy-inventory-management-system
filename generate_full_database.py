# generate_full_database.py
"""
Full generation script:
 - Creates database `medicine_db` (drops if exists)
 - Creates 15 tables
 - Generates realistic data for each table to target counts
 - Inserts data into MySQL using SQLAlchemy (mysql-connector)
How to run:
  cd "C:\DBMS\DBMSPROJECT"
  python generate_full_database.py
It will ask for MySQL root password.
"""

import random
from faker import Faker
import pandas as pd
from sqlalchemy import create_engine, text
import getpass
from datetime import timedelta, date

# -------------------------
# CONFIG: targets (you approved these)
# -------------------------
TARGETS = {
    "composition": 60,
    "medicine_category": 25,
    "manufacturer": 200,
    "medicine_generic": 2500,
    "medicine_brand": 2000,
    "brand_generic_map": 1500,
    "pharmacy": 200,
    "supplier": 200,
    "batch": 3500,
    "inventory": 3000,
    "supply_log": 1500,
    "sales_log": 3000,
    "price_history": 1000,
    "govt_subsidy": 250,
    "sideeffects": 800
}

# -------------------------
# DB connection info
# -------------------------
DB_USER = "root"
DB_HOST = "127.0.0.1"
DB_PORT = "3306"
DB_NAME = "medicine_db"

# prompt password securely
DB_PASS = getpass.getpass(prompt=f"Enter MySQL password for {DB_USER}: ")

# engine for server-level ops (no database)
engine_root = create_engine(f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/", echo=False)
# engine for DB-level ops will be created after DB is created
engine = None

fake = Faker()
random.seed(42)
Faker.seed(42)

# -------------------------
# SQL: schema creation (explicit)
# -------------------------
SCHEMA_SQL = """
CREATE DATABASE IF NOT EXISTS medicine_db;
USE medicine_db;

CREATE TABLE IF NOT EXISTS Composition (
  composition_id INT PRIMARY KEY,
  salt_name VARCHAR(100) NOT NULL,
  strength VARCHAR(50),
  form VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS Medicine_Category (
  category_id INT PRIMARY KEY,
  category_name VARCHAR(150) NOT NULL
);

CREATE TABLE IF NOT EXISTS Manufacturer (
  manufacturer_id INT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  address VARCHAR(300)
);

CREATE TABLE IF NOT EXISTS Medicine_Generic (
  generic_id INT PRIMARY KEY,
  generic_name VARCHAR(200) NOT NULL,
  composition_id INT,
  price DECIMAL(10,2),
  manufacturer_id INT,
  category_id INT,
  FOREIGN KEY (composition_id) REFERENCES Composition(composition_id),
  FOREIGN KEY (manufacturer_id) REFERENCES Manufacturer(manufacturer_id),
  FOREIGN KEY (category_id) REFERENCES Medicine_Category(category_id)
);

CREATE TABLE IF NOT EXISTS Medicine_Brand (
  brand_id INT PRIMARY KEY,
  brand_name VARCHAR(200) NOT NULL,
  composition_id INT,
  price DECIMAL(10,2),
  manufacturer_id INT,
  category_id INT,
  FOREIGN KEY (composition_id) REFERENCES Composition(composition_id),
  FOREIGN KEY (manufacturer_id) REFERENCES Manufacturer(manufacturer_id),
  FOREIGN KEY (category_id) REFERENCES Medicine_Category(category_id)
);

CREATE TABLE IF NOT EXISTS Brand_Generic_Map (
  map_id INT PRIMARY KEY,
  brand_id INT,
  generic_id INT,
  price_diff_percentage DECIMAL(5,2),
  FOREIGN KEY (brand_id) REFERENCES Medicine_Brand(brand_id),
  FOREIGN KEY (generic_id) REFERENCES Medicine_Generic(generic_id)
);

CREATE TABLE IF NOT EXISTS Pharmacy (
  pharmacy_id INT PRIMARY KEY,
  name VARCHAR(200),
  location VARCHAR(200),
  type VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS Supplier (
  supplier_id INT PRIMARY KEY,
  name VARCHAR(200),
  contact VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS Batch (
  batch_id INT PRIMARY KEY,
  medicine_type ENUM('brand','generic'),
  medicine_id INT,
  manufacture_date DATE,
  expiry_date DATE,
  batch_no VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS Inventory (
  inventory_id INT PRIMARY KEY,
  pharmacy_id INT,
  medicine_type ENUM('brand','generic'),
  medicine_id INT,
  batch_id INT,
  stock_quantity INT,
  expiry_date DATE,
  FOREIGN KEY (pharmacy_id) REFERENCES Pharmacy(pharmacy_id),
  FOREIGN KEY (batch_id) REFERENCES Batch(batch_id)
);

CREATE TABLE IF NOT EXISTS Supply_Log (
  supply_id INT PRIMARY KEY,
  supplier_id INT,
  pharmacy_id INT,
  medicine_type ENUM('brand','generic'),
  medicine_id INT,
  quantity INT,
  supply_date DATE,
  FOREIGN KEY (supplier_id) REFERENCES Supplier(supplier_id),
  FOREIGN KEY (pharmacy_id) REFERENCES Pharmacy(pharmacy_id)
);

CREATE TABLE IF NOT EXISTS Price_History (
  price_id INT PRIMARY KEY,
  medicine_type ENUM('brand','generic'),
  medicine_id INT,
  old_price DECIMAL(10,2),
  new_price DECIMAL(10,2),
  change_date DATE
);

CREATE TABLE IF NOT EXISTS Sales_Log (
  sale_id INT PRIMARY KEY,
  pharmacy_id INT,
  medicine_type ENUM('brand','generic'),
  medicine_id INT,
  quantity INT,
  sale_date DATE,
  FOREIGN KEY (pharmacy_id) REFERENCES Pharmacy(pharmacy_id)
);

CREATE TABLE IF NOT EXISTS Govt_Subsidy (
  subsidy_id INT PRIMARY KEY,
  generic_id INT,
  scheme_name VARCHAR(200),
  subsidy_percentage DECIMAL(5,2),
  FOREIGN KEY (generic_id) REFERENCES Medicine_Generic(generic_id)
);

CREATE TABLE IF NOT EXISTS SideEffects (
  side_effect_id INT PRIMARY KEY,
  medicine_type ENUM('brand','generic'),
  medicine_id INT,
  description TEXT
);
"""

# -------------------------
# Helpers for counts and ids
# -------------------------
def execute_root(sql_text: str):
    with engine_root.connect() as conn:
        conn.execute(text(sql_text))
        conn.commit()

def get_count(table_name: str) -> int:
    with engine.connect() as conn:
        r = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        return int(r or 0)

def get_max_id(table_name: str, id_col: str) -> int:
    with engine.connect() as conn:
        r = conn.execute(text(f"SELECT IFNULL(MAX({id_col}),0) FROM {table_name}")).scalar()
        return int(r or 0)

def insert_df(df, table_name):
    if df is None or df.empty:
        return 0
    # to_sql handles bulk insert
    df.to_sql(name=table_name, con=engine, if_exists="append", index=False)
    return len(df)

# -------------------------
# Data generation functions
# -------------------------
def gen_compositions(start, n):
    rows = []
    for i in range(n):
        rows.append({
            "composition_id": start + i,
            "salt_name": fake.word().capitalize() + ("" if random.random() < 0.6 else "ol"),
            "strength": random.choice(["250 mg","500 mg","5 mg/ml","10 mg"]),
            "form": random.choice(["tablet","capsule","syrup","injection"])
        })
    return pd.DataFrame(rows)

def gen_categories(start, n):
    base = ["Antibiotic","Painkiller","Antacid","Vitamin","Antihistamine","Antidepressant","Antidiabetic","Dermatological","Cardiac"]
    rows = []
    for i in range(n):
        rows.append({"category_id": start + i, "category_name": base[i % len(base)] + ("" if i < len(base) else f" {i}")})
    return pd.DataFrame(rows)

def gen_manufacturers(start, n):
    rows=[]
    for i in range(n):
        rows.append({"manufacturer_id": start + i, "name": fake.company(), "address": fake.address().replace("\n",", ")})
    return pd.DataFrame(rows)

def gen_generics(start, n, max_comp, max_mfr, max_cat):
    rows=[]
    for i in range(n):
        rows.append({
            "generic_id": start + i,
            "generic_name": fake.word().capitalize() + f"gen{start + i}",
            "composition_id": random.randint(1, max_comp) if max_comp>0 else 1,
            "price": round(random.uniform(10, 500),2),
            "manufacturer_id": random.randint(1, max_mfr) if max_mfr>0 else 1,
            "category_id": random.randint(1, max_cat) if max_cat>0 else 1
        })
    return pd.DataFrame(rows)

def gen_brands(start, n, max_comp, max_mfr, max_cat):
    rows=[]
    for i in range(n):
        rows.append({
            "brand_id": start + i,
            "brand_name": fake.word().capitalize() + " " + random.choice(["Pharma","Labs","Healthcare"]),
            "composition_id": random.randint(1, max_comp) if max_comp>0 else 1,
            "price": round(random.uniform(20,800),2),
            "manufacturer_id": random.randint(1, max_mfr) if max_mfr>0 else 1,
            "category_id": random.randint(1, max_cat) if max_cat>0 else 1
        })
    return pd.DataFrame(rows)

def gen_brand_generic_map(start, n, max_brand, max_generic):
    rows=[]
    for i in range(n):
        rows.append({
            "map_id": start + i,
            "brand_id": random.randint(1, max_brand) if max_brand>0 else 1,
            "generic_id": random.randint(1, max_generic) if max_generic>0 else 1,
            "price_diff_percentage": round(random.uniform(-30,40),2)
        })
    return pd.DataFrame(rows)

def gen_pharmacies(start, n):
    rows=[]
    for i in range(n):
        rows.append({"pharmacy_id": start + i, "name": fake.company() + " Pharmacy", "location": fake.city(), "type": random.choice(["private","govt"])})
    return pd.DataFrame(rows)

def gen_suppliers(start, n):
    rows=[]
    for i in range(n):
        rows.append({"supplier_id": start + i, "name": fake.company(), "contact": fake.phone_number()})
    return pd.DataFrame(rows)

def gen_batches(start, n, max_brand, max_generic):
    rows=[]
    for i in range(n):
        med_type = random.choice(["brand","generic"])
        med_id = random.randint(1, max_brand) if med_type=="brand" and max_brand>0 else random.randint(1, max_generic) if max_generic>0 else 1
        mfg = fake.date_between(start_date="-3y", end_date="today")
        exp = mfg + timedelta(days=random.randint(180,1200))
        rows.append({"batch_id": start + i, "medicine_type": med_type, "medicine_id": med_id, "manufacture_date": mfg, "expiry_date": exp, "batch_no": f"BATCH-{mfg.year}-{start + i}"})
    return pd.DataFrame(rows)

def gen_inventory(start, pharmacies_count, batches_df, target_rows):
    rows=[]
    inv_id = start
    pharmacy_ids = list(range(1, pharmacies_count+1)) if pharmacies_count>0 else [1]
    batch_rows = batches_df.to_dict(orient="records") if batches_df is not None else []
    if not batch_rows:
        for i in range(target_rows):
            rows.append({"inventory_id": inv_id, "pharmacy_id": pharmacy_ids[i % len(pharmacy_ids)], "medicine_type": random.choice(["brand","generic"]), "medicine_id":1, "batch_id":1, "stock_quantity": random.randint(1,200), "expiry_date": fake.date_between(start_date="today", end_date="+2y")})
            inv_id+=1
        return pd.DataFrame(rows)
    while len(rows) < target_rows:
        pharmacy_id = random.choice(pharmacy_ids)
        batch = random.choice(batch_rows)
        rows.append({"inventory_id": inv_id, "pharmacy_id": pharmacy_id, "medicine_type": batch["medicine_type"], "medicine_id": int(batch["medicine_id"]), "batch_id": int(batch["batch_id"]), "stock_quantity": random.randint(1,200), "expiry_date": batch["expiry_date"]})
        inv_id += 1
    return pd.DataFrame(rows)

def gen_supply_log(start, n, max_supplier, max_pharmacy, max_brand, max_generic):
    rows=[]
    for i in range(n):
        med_type = random.choice(["brand","generic"])
        med_id = random.randint(1, max_brand) if med_type=="brand" and max_brand>0 else random.randint(1, max_generic) if max_generic>0 else 1
        rows.append({"supply_id": start + i, "supplier_id": random.randint(1, max_supplier) if max_supplier>0 else 1, "pharmacy_id": random.randint(1, max_pharmacy) if max_pharmacy>0 else 1, "medicine_type": med_type, "medicine_id": med_id, "quantity": random.randint(5,800), "supply_date": fake.date_between(start_date="-2y", end_date="today")})
    return pd.DataFrame(rows)

def gen_sales_log(start, n, max_pharmacy, max_brand, max_generic):
    rows=[]
    for i in range(n):
        med_type = random.choice(["brand","generic"])
        med_id = random.randint(1, max_brand) if med_type=="brand" and max_brand>0 else random.randint(1, max_generic) if max_generic>0 else 1
        rows.append({"sale_id": start + i, "pharmacy_id": random.randint(1, max_pharmacy) if max_pharmacy>0 else 1, "medicine_type": med_type, "medicine_id": med_id, "quantity": random.randint(1,50), "sale_date": fake.date_between(start_date="-2y", end_date="today")})
    return pd.DataFrame(rows)

def gen_price_history(start, n, max_brand, max_generic):
    rows=[]
    for i in range(n):
        med_type = random.choice(["brand","generic"])
        med_id = random.randint(1, max_brand) if med_type=="brand" and max_brand>0 else random.randint(1, max_generic) if max_generic>0 else 1
        old_p = round(random.uniform(10,500),2)
        new_p = round(old_p * (1 + random.uniform(-0.25,0.4)),2)
        rows.append({"price_id": start + i, "medicine_type": med_type, "medicine_id": med_id, "old_price": old_p, "new_price": new_p, "change_date": fake.date_between(start_date="-3y", end_date="today")})
    return pd.DataFrame(rows)

def gen_govt_subsidy(start, n, max_generic):
    rows=[]
    for i in range(n):
        rows.append({"subsidy_id": start + i, "generic_id": random.randint(1, max_generic) if max_generic>0 else 1, "scheme_name": random.choice(["HealthAssist A","HealthAssist B","MedicCare"]), "subsidy_percentage": round(random.uniform(5,60),2)})
    return pd.DataFrame(rows)

def gen_sideeffects(start, n, max_brand, max_generic):
    rows=[]
    for i in range(n):
        med_type = random.choice(["brand","generic"])
        med_id = random.randint(1, max_brand) if med_type=="brand" and max_brand>0 else random.randint(1, max_generic) if max_generic>0 else 1
        rows.append({"side_effect_id": start + i, "medicine_type": med_type, "medicine_id": med_id, "description": fake.sentence(nb_words=8)})
    return pd.DataFrame(rows)

# -------------------------
# MAIN
# -------------------------
def main():
    global engine
    print("1) Creating database and schema...")
    # drop/create DB
    execute_root = engine_root.connect().execution_options(isolation_level="AUTOCOMMIT").execute
    execute_root(text("DROP DATABASE IF EXISTS medicine_db;"))
    execute_root(text("CREATE DATABASE medicine_db;"))
    print("  database created.")
    # create new engine for medicine_db
    engine = create_engine(f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}", echo=False)
    # create schema/tables
    with engine.connect() as conn:
        for stmt in SCHEMA_SQL.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s + ";"))
        conn.commit()
    print("  schema created.")

    # get current counts (should be 0)
    current = {t: get_count(t) for t in TARGETS.keys()}
    print("\n2) Current counts (before insert):")
    for k,v in current.items():
        print(f"  {k}: {v}")

    # compute deficits
    to_add = {t: max(0, TARGETS[t] - current.get(t,0)) for t in TARGETS.keys()}
    print("\n3) Will add rows (per table):")
    for k,v in to_add.items():
        print(f"  {k}: {v}")

    # helper maxes
    max_brand = get_max_id("medicine_brand","brand_id")
    max_generic = get_max_id("medicine_generic","generic_id")
    max_batch = get_max_id("batch","batch_id")
    max_inventory = get_max_id("inventory","inventory_id")
    max_map = get_max_id("brand_generic_map","map_id")
    max_supply = get_max_id("supply_log","supply_id")
    max_sale = get_max_id("sales_log","sale_id")
    max_price = get_max_id("price_history","price_id")
    max_subsidy = get_max_id("govt_subsidy","subsidy_id")
    max_side = get_max_id("sideeffects","side_effect_id")

    # 1: masters / catalog
    if to_add["composition"]>0:
        n = to_add["composition"]
        df = gen_compositions(get_max_id("Composition","composition_id")+1, n)
        insert_df(df, "Composition")
    if to_add["medicine_category"]>0:
        n=to_add["medicine_category"]
        df = gen_categories(get_max_id("Medicine_Category","category_id")+1, n)
        insert_df(df, "Medicine_Category")
    if to_add["manufacturer"]>0:
        n=to_add["manufacturer"]
        df = gen_manufacturers(get_max_id("Manufacturer","manufacturer_id")+1, n)
        insert_df(df, "Manufacturer")

    # refresh supporting ids
    max_comp = get_max_id("Composition","composition_id")
    max_mfr = get_max_id("Manufacturer","manufacturer_id")
    max_cat = get_max_id("Medicine_Category","category_id")

    # generics & brands
    if to_add["medicine_generic"]>0:
        n = to_add["medicine_generic"]
        df = gen_generics(get_max_id("Medicine_Generic","generic_id")+1, n, max_comp, max_mfr, max_cat)
        insert_df(df, "Medicine_Generic")
    if to_add["medicine_brand"]>0:
        n = to_add["medicine_brand"]
        df = gen_brands(get_max_id("Medicine_Brand","brand_id")+1, n, max_comp, max_mfr, max_cat)
        insert_df(df, "Medicine_Brand")

    # brand_generic_map
    if to_add["brand_generic_map"]>0:
        n = to_add["brand_generic_map"]
        df = gen_brand_generic_map(get_max_id("Brand_Generic_Map","map_id")+1, n, get_max_id("Medicine_Brand","brand_id"), get_max_id("Medicine_Generic","generic_id"))
        insert_df(df, "Brand_Generic_Map")

    # pharmacies & suppliers
    if to_add["pharmacy"]>0:
        n=to_add["pharmacy"]
        df = gen_pharmacies(get_max_id("Pharmacy","pharmacy_id")+1, n)
        insert_df(df, "Pharmacy")
    if to_add["supplier"]>0:
        n=to_add["supplier"]
        df = gen_suppliers(get_max_id("Supplier","supplier_id")+1, n)
        insert_df(df, "Supplier")

    # batches
    if to_add["batch"]>0:
        n=to_add["batch"]
        df = gen_batches(get_max_id("Batch","batch_id")+1, n, get_max_id("Medicine_Brand","brand_id"), get_max_id("Medicine_Generic","generic_id"))
        insert_df(df, "Batch")

    # inventory (needs batches and pharmacies)
    if to_add["inventory"]>0:
        batches_df = None
        with engine.connect() as conn:
            batches_df = pd.read_sql(text("SELECT batch_id, medicine_type, medicine_id, expiry_date FROM Batch"), conn)
        df = gen_inventory(get_max_id("Inventory","inventory_id")+1, get_max_id("Pharmacy","pharmacy_id"), batches_df, to_add["inventory"])
        insert_df(df, "Inventory")

    # supply_log
    if to_add["supply_log"]>0:
        n=to_add["supply_log"]
        df = gen_supply_log(get_max_id("Supply_Log","supply_id")+1, n, get_max_id("Supplier","supplier_id"), get_max_id("Pharmacy","pharmacy_id"), get_max_id("Medicine_Brand","brand_id"), get_max_id("Medicine_Generic","generic_id"))
        insert_df(df, "Supply_Log")

    # sales_log
    if to_add["sales_log"]>0:
        n=to_add["sales_log"]
        df = gen_sales_log(get_max_id("Sales_Log","sale_id")+1, n, get_max_id("Pharmacy","pharmacy_id"), get_max_id("Medicine_Brand","brand_id"), get_max_id("Medicine_Generic","generic_id"))
        insert_df(df, "Sales_Log")

    # price_history
    if to_add["price_history"]>0:
        n=to_add["price_history"]
        df = gen_price_history(get_max_id("Price_History","price_id")+1, n, get_max_id("Medicine_Brand","brand_id"), get_max_id("Medicine_Generic","generic_id"))
        insert_df(df, "Price_History")

    # govt_subsidy
    if to_add["govt_subsidy"]>0:
        n=to_add["govt_subsidy"]
        df = gen_govt_subsidy(get_max_id("Govt_Subsidy","subsidy_id")+1, n, get_max_id("Medicine_Generic","generic_id"))
        insert_df(df, "Govt_Subsidy")

    # sideeffects
    if to_add["sideeffects"]>0:
        n=to_add["sideeffects"]
        df = gen_sideeffects(get_max_id("SideEffects","side_effect_id")+1, n, get_max_id("Medicine_Brand","brand_id"), get_max_id("Medicine_Generic","generic_id"))
        insert_df(df, "SideEffects")

    # final counts
    final = {t: get_count(t) for t in TARGETS.keys()}
    total = sum(final.values())
    print("\nFinal counts:")
    for k,v in final.items():
        print(f"  {k}: {v}")
    print(f"\nTotal rows in DB now: {total}")
    print("\nScript finished.")

if __name__ == "__main__":
    main()
