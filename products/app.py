"""
This microservice handles product management, including creating and editing products.
It uses a SQLite database to store product information.
It also returns product details based on product name or category.
Port 9001
"""

import sqlite3
import os
from flask import Flask, request
import json
import requests

app = Flask(__name__)
db_name = "products.db"
sql_file = "products.sql"
db_flag = False

def create_db():
	conn = sqlite3.connect(db_name)
	with open(sql_file, 'r') as sql_startup:
		init_db = sql_startup.read()
	cursor = conn.cursor()
	cursor.executescript(init_db)
	conn.execute("PRAGMA foreign_keys = ON")
	conn.commit()
	conn.close()
	global db_flag
	db_flag = True
	return conn

def get_db():
	if not db_flag:
		create_db()
	conn = sqlite3.connect(db_name)
	return conn

@app.route('/clear', methods=['GET'])
def clear():
	if os.path.exists(db_name):
		try:
			os.remove(db_name)
		except Exception as e:
			return f"Error clearing database: {e}"
	global db_flag
	db_flag = False
	return "Database Cleared"

@app.route('/', methods=(['GET']))
def index():
	conn = get_db()
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM products;")
	result = cursor.fetchall()
	conn.close()

	return result

@app.route('/create_product', methods=['POST'])
def create_product():
	# Extract form data from the request.
	jwt_token = request.headers.get('Authorization')
	name = request.form.get('name')
	price = request.form.get('price')
	category = request.form.get('category')

	# Validate the data
	if not jwt_token:
		return json.dumps({"status": 2})

	if not name:
		return json.dumps({"status": 2})
	
	if not price:
		return json.dumps({"status": 2})
	
	if not category:
		return json.dumps({"status": 2})
	
	# Check if the user is an employee by calling the users microservice.
	URL = "http://user:5000/verify"
	PARAMS = {'jwt': jwt_token}
	r = requests.get(url=URL, params=PARAMS)
	user_data = r.json()

	if user_data["employee"] == "NULL" or user_data["employee"] == "False":
		return json.dumps({"status": 2})
	
	# Check if the product name already exists
	conn = get_db()
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM products WHERE name = ?", (name,))
	if cursor.fetchone() is not None:
		conn.close()
		return json.dumps({"status": 2})
	
	# Insert the new product record into the products table.
	cursor.execute(
		"INSERT INTO products (name, price, category) VALUES (?, ?, ?)",
		(name, price, category)
	)
	conn.commit()
	conn.close()

	# Log the event
	URL = "http://logs:5000/log"
	PARAMS = {"event": "product_creation", "user": user_data["user"], "name": name}
	log = requests.post(url=URL, data=PARAMS)
	log = log.json()

	return json.dumps({"status": 1})
	
@app.route('/edit_product', methods=['POST'])
def edit_product():
	jwt_token = request.headers.get('Authorization')
	product_name = request.form.get('name')
	new_price = request.form.get('new_price')
	new_category = request.form.get('new_category')
	
	# Check if the user is an employee.
	URL = "http://user:5000/verify"
	PARAMS = {'jwt': jwt_token}
	r = requests.get(url=URL, params=PARAMS)
	user_data = r.json()
	
	if user_data["status"] == 2:
		return json.dumps({"status": 2})
	if user_data["employee"] == "False":
		return json.dumps({"status": 3})
	
	# Connect to database and update the product.
	conn = get_db()
	cursor = conn.cursor()
	
	if new_price:
		# Updating price: replace the current value with the new one.
		cursor.execute("UPDATE products SET price = ? WHERE name = ?", (new_price, product_name))
	elif new_category:
		# Updating category: replace the current category with the new one.
		cursor.execute("UPDATE products SET category = ? WHERE name = ?", (new_category, product_name))

	conn.commit()
	conn.close()

	# Log the event
	URL = "http://logs:5000/log"
	PARAMS = {"event": "product_edit", "user": user_data["user"], "name": product_name}
	log = requests.post(url=URL, data=PARAMS)
	log = log.json()

	return json.dumps({"status": 1})

@app.route('/product', methods=['GET'])
def product():
	product_name = request.args.get('product_name')
	category = request.args.get('category')
	
	if product_name:
		# Connect to the database and retrieve the product price.
		conn = get_db()
		cursor = conn.cursor()
		cursor.execute("SELECT price, category FROM products WHERE name = ?", (product_name,))
		product = cursor.fetchone()
		conn.close()
		
		if not product:
			return json.dumps({"status": 2, "products": "NULL"})
		
		product_list = [{"product_name": product_name, "price": product[0], "category": product[1]}]
		
		return json.dumps({"status": 1, "products": product_list})
	
	if category:
		# Connect to the database and retrieve all products in the specified category.
		conn = get_db()
		cursor = conn.cursor()
		cursor.execute("SELECT name, price FROM products WHERE category = ?", (category,))
		products = cursor.fetchall()
		conn.close()
		
		if not products:
			return json.dumps({"status": 2, "products": "NULL"})
		
		product_list = [{"product_name": prod[0], "price": prod[1], "category": category} for prod in products]
		return json.dumps({"status": 1, "products": product_list})
	
	return json.dumps({"status": 2, "products": "NULL"})
