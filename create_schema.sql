-- DROP DB if exists, create fresh DB
DROP DATABASE IF EXISTS medicine_db;
CREATE DATABASE medicine_db;
USE medicine_db;

-- Composition
CREATE TABLE Composition (
  composition_id INT AUTO_INCREMENT PRIMARY KEY,
  salt_name VARCHAR(100) NOT NULL,
  strength VARCHAR(50),
  form VARCHAR(50)
);

-- Medicine Category
CREATE TABLE Medicine_Category (
  category_id INT AUTO_INCREMENT PRIMARY KEY,
  category_name VARCHAR(100) NOT NULL
);

-- Manufacturer
CREATE TABLE Manufacturer (
  manufacturer_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  address VARCHAR(250)
);

-- Medicine_Generic
CREATE TABLE Medicine_Generic (
  generic_id INT AUTO_INCREMENT PRIMARY KEY,
  generic_name VARCHAR(150) NOT NULL,
  composition_id INT,
  price DECIMAL(10,2),
  manufacturer_id INT,
  category_id INT,
  FOREIGN KEY (composition_id) REFERENCES Composition(composition_id),
  FOREIGN KEY (manufacturer_id) REFERENCES Manufacturer(manufacturer_id),
  FOREIGN KEY (category_id) REFERENCES Medicine_Category(category_id)
);

-- Medicine_Brand
CREATE TABLE Medicine_Brand (
  brand_id INT AUTO_INCREMENT PRIMARY KEY,
  brand_name VARCHAR(150) NOT NULL,
  composition_id INT,
  price DECIMAL(10,2),
  manufacturer_id INT,
  category_id INT,
  FOREIGN KEY (composition_id) REFERENCES Composition(composition_id),
  FOREIGN KEY (manufacturer_id) REFERENCES Manufacturer(manufacturer_id),
  FOREIGN KEY (category_id) REFERENCES Medicine_Category(category_id)
);

-- Brand_Generic_Map
CREATE TABLE Brand_Generic_Map (
  map_id INT AUTO_INCREMENT PRIMARY KEY,
  brand_id INT,
  generic_id INT,
  price_diff_percentage DECIMAL(5,2),
  FOREIGN KEY (brand_id) REFERENCES Medicine_Brand(brand_id),
  FOREIGN KEY (generic_id) REFERENCES Medicine_Generic(generic_id)
);

-- Pharmacy
CREATE TABLE Pharmacy (
  pharmacy_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150),
  location VARCHAR(200),
  type VARCHAR(20)
);

-- Supplier
CREATE TABLE Supplier (
  supplier_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150),
  contact VARCHAR(100)
);

-- Batch
CREATE TABLE Batch (
  batch_id INT AUTO_INCREMENT PRIMARY KEY,
  medicine_type ENUM('brand','generic'),
  medicine_id INT,
  manufacture_date DATE,
  expiry_date DATE,
  batch_no VARCHAR(60)
);

-- Inventory
CREATE TABLE Inventory (
  inventory_id INT AUTO_INCREMENT PRIMARY KEY,
  pharmacy_id INT,
  medicine_type ENUM('brand','generic'),
  medicine_id INT,
  batch_id INT,
  stock_quantity INT,
  expiry_date DATE,
  FOREIGN KEY (pharmacy_id) REFERENCES Pharmacy(pharmacy_id),
  FOREIGN KEY (batch_id) REFERENCES Batch(batch_id)
);

-- Supply_Log
CREATE TABLE Supply_Log (
  supply_id INT AUTO_INCREMENT PRIMARY KEY,
  supplier_id INT,
  pharmacy_id INT,
  medicine_type ENUM('brand','generic'),
  medicine_id INT,
  quantity INT,
  supply_date DATE,
  FOREIGN KEY (supplier_id) REFERENCES Supplier(supplier_id),
  FOREIGN KEY (pharmacy_id) REFERENCES Pharmacy(pharmacy_id)
);

-- Price_History
CREATE TABLE Price_History (
  price_id INT AUTO_INCREMENT PRIMARY KEY,
  medicine_type ENUM('brand','generic'),
  medicine_id INT,
  old_price DECIMAL(10,2),
  new_price DECIMAL(10,2),
  change_date DATE
);

-- Sales_Log
CREATE TABLE Sales_Log (
  sale_id INT AUTO_INCREMENT PRIMARY KEY,
  pharmacy_id INT,
  medicine_type ENUM('brand','generic'),
  medicine_id INT,
  quantity INT,
  sale_date DATE,
  FOREIGN KEY (pharmacy_id) REFERENCES Pharmacy(pharmacy_id)
);

-- Govt_Subsidy
CREATE TABLE Govt_Subsidy (
  subsidy_id INT AUTO_INCREMENT PRIMARY KEY,
  generic_id INT,
  scheme_name VARCHAR(150),
  subsidy_percentage DECIMAL(5,2),
  FOREIGN KEY (generic_id) REFERENCES Medicine_Generic(generic_id)
);

-- SideEffects
CREATE TABLE SideEffects (
  side_effect_id INT AUTO_INCREMENT PRIMARY KEY,
  medicine_type ENUM('brand','generic'),
  medicine_id INT,
  description TEXT
);

-- Index suggestions (optional)
CREATE INDEX idx_batch_medicine ON Batch(medicine_type, medicine_id);
CREATE INDEX idx_inventory_pharmacy ON Inventory(pharmacy_id);
