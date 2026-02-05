"""
This microservice handles order management.
Port 9003
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
db_name = "orders.db"
sql_file = "orders.sql"
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

@app.route('/order', methods=['POST'])
def order():
    # Get the JWT from the HTTP header
    jwt_token = request.headers.get('Authorization')
    if not jwt_token:
        return json.dumps({"status": 2, "cost": "NULL"})
    
    # Verify the JWT with the user management microservice
    URL = "http://user:5000/verify"
    PARAMS = {'jwt': jwt_token}
    r = requests.get(url=URL, params=PARAMS)
    user_data = r.json()
    if user_data["status"] == 2:
        return json.dumps({"status": 2, "cost": "NULL"})
    
    # Parse the JSON payload and extract the 'order' parameter
    order_raw = request.form.get('order')
    if not order_raw:
        return json.dumps({"status": 3, "cost": "NULL"})
    
    try:
        order_list = json.loads(order_raw)
    except Exception as e:
        return json.dumps({"status": 3, "cost": "NULL"})
    
    if not isinstance(order_list, list) or len(order_list) == 0:
        return json.dumps({"status": 3, "cost": "NULL"})
    
    total_cost = 0.0
    # Process each product in the order
    for item in order_list:
        product_name = item["product"]
        quantity = item["quantity"]
        if product_name is None or quantity is None:
            return json.dumps({"status": 3, "cost": "NULL"})
        
        # Verify product with the product management microservice
        URL = "http://products:5000/product"
        PARAMS = {"product_name": product_name}
        r = requests.get(url=URL, params=PARAMS)
        product = r.json()

        if not product or product["status"] == 2 or product["products"] == "NULL":
            return json.dumps({"status": 3, "cost": "NULL"})
        
        prod_data = product["products"]
        prod_data = prod_data[0]
        price = prod_data["price"]
        
        if price is None:
            return json.dumps({"status": 3, "cost": "NULL"})
        
        total_cost += price * quantity

    # Log the event
    URL = "http://logs:5000/log"
    PARAMS = {"event": "order", "user": user_data["user"], "name": "NULL"}
    log = requests.post(url=URL, data=PARAMS)
    log = log.json()

    total_cost = format(total_cost, '.2f')
    return json.dumps({"status": 1, "cost": total_cost})