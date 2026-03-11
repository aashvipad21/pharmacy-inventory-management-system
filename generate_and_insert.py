# generate_and_insert.py
"""
This script generates realistic fake data for the medicine database
and inserts it into the MySQL database `medicine_db`.

How to run:
  1. Open Command Prompt in folder C:\DBMS\DBMSPROJECT
  2. Run: python generate_and_insert.py
  3. Enter MySQL root password when prompted.

Author: Your Name (replace this in final submission)
"""

import random
from faker import Faker
import pandas as pd
from sqlalchemy import create_engine
from datetime import timedelta
import getpass

# ----------------------------
# Database connection settings
# ----------------------------
DB_USER = "root"
DB_HOST = "127.0.0.1"
DB_PORT = "3306"
DB_NAME = "medicine_db"

# Ask for password at runtime (safer)
DB_PASSWORD = getpass.getpass(prompt=f"Enter MySQL password for {DB_USER}: ")

# SQLAlchemy engine string (do not change unless your MySQL settings differ)
engine = create_engine(
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    echo=False
)

faker = Faker()

# ----------------------------
# Dataset sizes (changeable)
# ----------------------------
NUM_COMPOSITIONS = 30
NUM_CATEGORIES = 6
NUM_MANUFACTURERS = 12
NUM_GENERICS = 180
NUM_BRANDS = 250
NUM_PHARMACIES = 25
NUM_SUPPLIERS = 12
NUM_BATCHES = 800
NUM_SALES = 1200
NUM_SUPPLIES = 800
NUM_PRICE_RECORDS = 400
NUM_SIDE_EFFECTS = 300

# ----------------------------
# Helper function to write DataFrame to DB
# ----------------------------
def insert_dataframe_to_table(df: pd.DataFrame, table_name: str):
    """Insert a pandas DataFrame into a MySQL table using SQLAlchemy."""
    if df is None or df.empty:
        print(f"[WARN] Nothing to insert into {table_name} (empty dataframe).")
        return
    df.to_sql(name=table_name, con=engine, if_exists="append", index=False)
    print(f"[OK] Inserted {len(df)} rows into `{table_name}`")

# ----------------------------
# Data generation functions
# ----------------------------
def generate_compositions(n: int):
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "composition_id": i,
            "salt_name": faker.word().capitalize() + ("" if random.random() < 0.6 else "ol"),
            "strength": random.choice(["250 mg", "500 mg", "5 mg/ml", "10 mg"]),
            "form": random.choice(["tablet", "capsule", "syrup", "injection"])
        })
    return pd.DataFrame(rows)

def generate_categories(n: int):
    sample = ["Antibiotic", "Painkiller", "Antacid", "Vitamin", "Antihistamine", "Antidepressant"]
    rows = [{"category_id": i+1, "category_name": sample[i % len(sample)]} for i in range(n)]
    return pd.DataFrame(rows)

def generate_manufacturers(n: int):
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "manufacturer_id": i,
            "name": faker.company(),
            "address": faker.address().replace("\n", ", ")
        })
    return pd.DataFrame(rows)

def generate_generics(n: int, max_composition: int, max_manufacturer: int, max_category: int):
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "generic_id": i,
            "generic_name": faker.word().capitalize() + "gen",
            "composition_id": random.randint(1, max_composition),
            "price": round(random.uniform(20, 300), 2),
            "manufacturer_id": random.randint(1, max_manufacturer),
            "category_id": random.randint(1, max_category)
        })
    return pd.DataFrame(rows)

def generate_brands(n: int, max_composition: int, max_manufacturer: int, max_category: int):
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "brand_id": i,
            "brand_name": faker.word().capitalize() + " " + random.choice(["Pharma", "Labs", "Healthcare"]),
            "composition_id": random.randint(1, max_composition),
            "price": round(random.uniform(30, 800), 2),
            "manufacturer_id": random.randint(1, max_manufacturer),
            "category_id": random.randint(1, max_category)
        })
    return pd.DataFrame(rows)

def generate_pharmacies(n: int):
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "pharmacy_id": i,
            "name": faker.company() + " Pharmacy",
            "location": faker.city(),
            "type": random.choice(["private", "govt"])
        })
    return pd.DataFrame(rows)

def generate_suppliers(n: int):
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "supplier_id": i,
            "name": faker.company(),
            "contact": faker.phone_number()
        })
    return pd.DataFrame(rows)

def generate_batches(n: int, max_brand_id: int, max_generic_id: int):
    rows = []
    for i in range(1, n + 1):
        med_type = random.choice(["brand", "generic"])
        med_id = random.randint(1, max_brand_id) if med_type == "brand" else random.randint(1, max_generic_id)
        manufacture_date = faker.date_between(start_date="-3y", end_date="today")
        expiry_date = manufacture_date + timedelta(days=random.randint(180, 1200))
        rows.append({
            "batch_id": i,
            "medicine_type": med_type,
            "medicine_id": med_id,
            "manufacture_date": manufacture_date,
            "expiry_date": expiry_date,
            "batch_no": f"BATCH{100000 + i}"
        })
    return pd.DataFrame(rows)

def generate_inventory(pharmacies_df: pd.DataFrame, batches_df: pd.DataFrame):
    rows = []
    inv_id = 1
    for pharmacy_id in pharmacies_df["pharmacy_id"].tolist():
        # each pharmacy holds 10-30 batch entries
        for _ in range(random.randint(10, 25)):
            batch = batches_df.sample(1).iloc[0]
            rows.append({
                "inventory_id": inv_id,
                "pharmacy_id": pharmacy_id,
                "medicine_type": batch["medicine_type"],
                "medicine_id": int(batch["medicine_id"]),
                "batch_id": int(batch["batch_id"]),
                "stock_quantity": random.randint(1, 200),
                "expiry_date": batch["expiry_date"]
            })
            inv_id += 1
    return pd.DataFrame(rows)

def main():
    # Seed for reproducibility during demo
    Faker.seed(42)
    random.seed(42)

    print("[1/9] Generating compositions...")
    compositions_df = generate_compositions(NUM_COMPOSITIONS)
    insert_dataframe_to_table(compositions_df, "Composition")

    print("[2/9] Generating categories...")
    categories_df = generate_categories(NUM_CATEGORIES)
    insert_dataframe_to_table(categories_df, "Medicine_Category")

    print("[3/9] Generating manufacturers...")
    manufacturers_df = generate_manufacturers(NUM_MANUFACTURERS)
    insert_dataframe_to_table(manufacturers_df, "Manufacturer")

    print("[4/9] Generating generic medicines...")
    generics_df = generate_generics(NUM_GENERICS, NUM_COMPOSITIONS, NUM_MANUFACTURERS, NUM_CATEGORIES)
    insert_dataframe_to_table(generics_df, "Medicine_Generic")

    print("[5/9] Generating branded medicines...")
    brands_df = generate_brands(NUM_BRANDS, NUM_COMPOSITIONS, NUM_MANUFACTURERS, NUM_CATEGORIES)
    insert_dataframe_to_table(brands_df, "Medicine_Brand")

    print("[6/9] Generating pharmacies and suppliers...")
    pharmacies_df = generate_pharmacies(NUM_PHARMACIES)
    insert_dataframe_to_table(pharmacies_df, "Pharmacy")

    suppliers_df = generate_suppliers(NUM_SUPPLIERS)
    insert_dataframe_to_table(suppliers_df, "Supplier")

    print("[7/9] Generating batches...")
    batches_df = generate_batches(NUM_BATCHES, NUM_BRANDS, NUM_GENERICS)
    insert_dataframe_to_table(batches_df, "Batch")

    print("[8/9] Generating inventory (pharmacy stock)...")
    inventory_df = generate_inventory(pharmacies_df, batches_df)
    insert_dataframe_to_table(inventory_df, "Inventory")

    # Note: For time/space, I am not auto-generating Supply_Log, Sales_Log, Price_History,
    # Govt_Subsidy, SideEffects here. You can add them similarly following these examples.

    print("\n[DONE] Basic data inserted. If you want, I can now:")
    print(" - Add Supply_Log, Sales_Log, Price_History, Govt_Subsidy, SideEffects generation")
    print(" - Or run smaller test (faster) with fewer rows")
    print("Tell me: reply 'SAVED PY' after you save this file and I will give the NEXT step to run it.")
    
if __name__ == "__main__":
    main()
