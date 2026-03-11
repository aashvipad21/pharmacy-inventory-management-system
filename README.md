# Pharmacy Inventory Management System

A database-driven system designed to manage pharmacy inventory, suppliers, medicines, and sales operations.

## Project Overview

This project implements a fully normalized relational database along with a Python CLI backend application for managing pharmacy operations.

## Technologies Used

MySQL  
Python  
SQLAlchemy  
Pandas  

## Key Features

• Normalized relational database with 15+ tables  
• Inventory tracking with batch and expiry management  
• Role-based authentication system (Admin / User)  
• Medicine search and generic alternative recommendation  
• Sales analytics and inventory reports  

## Database Design

The database includes entities such as:

Medicine_Brand  
Medicine_Generic  
Supplier  
Inventory  
Sales_Log  
Batch  
Manufacturer  

The schema follows normalization principles up to **3NF / BCNF**.

## Backend System

A Python CLI backend was developed using **SQLAlchemy** to interact with the MySQL database.

Features include:

• Medicine search  
• Inventory management  
• Sales recording  
• Analytical reports  

## Project Structure

database/ – SQL schema  
backend/ – Python CLI application  
diagrams/ – ER diagram  
screenshots/ – system preview
