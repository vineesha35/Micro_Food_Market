"""
This microservice handles search functionality for products.
It uses a SQLite database to store product information.
Port 9002
"""

import sqlite3
import os
from flask import Flask, request
import json
import hashlib
import re
import base64
import hmac
import requests

app = Flask(__name__)
db_name = "search.db"
sql_file = "search.sql"
db_flag = False

# def create_db():
# 	conn = sqlite3.connect(db_name)
# 	with open(sql_file, 'r') as sql_startup:
# 		init_db = sql_startup.read()
# 	cursor = conn.cursor()
# 	cursor.executescript(init_db)
# 	conn.execute("PRAGMA foreign_keys = ON")
# 	conn.commit()
# 	conn.close()
# 	global db_flag
# 	db_flag = True
# 	return conn

# def get_db():
# 	if not db_flag:
# 		create_db()
# 	conn = sqlite3.connect(db_name)
# 	return conn

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

@app.route('/search', methods=['GET'])
def search():
	# Check JWT in Authorization header
	jwt_token = request.headers.get('Authorization')
	if not jwt_token:
		return json.dumps({"status": 2, "data": "NULL"})
	
	# Verify if user exists
	URL = "http://user:5000/verify"
	PARAMS = {'jwt': jwt_token}
	r = requests.get(url=URL, params=PARAMS)
	user_data = r.json()
	if user_data["status"] == 2:
		return json.dumps({"status": 2, "data": "NULL"})

	# Extract query parameters from URL args (GET request)
	product_name = request.args.get('product_name')
	category = request.args.get('category')
	products = []

	# Depending on the parameter, call the Product Management microservice
	try:
		if not product_name and not category:
			return json.dumps({"status": 3, "data": "NULL"})
		
		elif product_name:
			URL = "http://products:5000/product"
			PARAMS = {"product_name": product_name}
			r = requests.get(url=URL, params=PARAMS)
			prod_data = r.json()

			if prod_data["status"] == 2 or prod_data["products"] == "NULL":
				return json.dumps({"status": 3, "data": "NULL"})
			
			# Translate result: unwrap the product list
			products = prod_data["products"]

		elif category:
			URL = "http://products:5000/product"
			PARAMS = {"category": category}
			r = requests.get(url=URL, params=PARAMS)
			prod_data = r.json()

			if prod_data["status"] == 2 or prod_data["products"] == "NULL":
				return json.dumps({"status": 3, "data": "NULL"})
			
			# Translate result: unwrap the product list
			products = prod_data["products"]
		
	except Exception:
		return json.dumps({"status": 3, "data": "NULL"})
	
	# For each product, get last modifier info from the Logging microservice
	results = []
	for prod in products:
		try:
			name = prod["product_name"]
			URL = "http://logs:5000/last_mod"
			PARAMS = {"product_name": name}
			r = requests.get(url=URL, params=PARAMS)
			log_data = r.json()
			if log_data["status"] == 2:
				return json.dumps({"status": 3, "data": "NULL"})
			last_mod = log_data["last_mod"]
		except Exception:
			return json.dumps({"status": 3, "data": "NULL"})
		prod["last_mod"] = last_mod
		results.append(prod)

	if product_name:
		# Log the event for product search
		URL = "http://logs:5000/log"
		PARAMS = {"event": "search", "user": user_data["user"], "name": product_name}
		log = requests.post(url=URL, data=PARAMS)
	if category:
		# Log the event for category search
		URL = "http://logs:5000/log"
		PARAMS = {"event": "search", "user": user_data["user"], "name": category}
		log = requests.post(url=URL, data=PARAMS)

	return json.dumps({"status": 1, "data": results})