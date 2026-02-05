"""
This microservice handles logging functionality for user actions.
It uses a SQLite database to store logs.
Port 9004
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
db_name = "logs.db"
sql_file = "logs.sql"
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

@app.route('/', methods=(['GET']))
def index():
	conn = get_db()
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM logs;")
	result = cursor.fetchall()
	conn.close()

	return result

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

@app.route('/log', methods=['POST'])
def log():
	event = request.form.get('event')
	username = request.form.get('user')
	name = request.form.get('name')

	conn = get_db()
	cursor = conn.cursor()
	cursor.execute("INSERT INTO logs (event, username, name) VALUES (?, ?, ?)", (event, username, name))
	conn.commit()
	conn.close()

	return json.dumps({"status": 1})

@app.route('/view_log', methods=['GET'])
def view_logs():
	username = request.args.get('username')
	product = request.args.get('product')
	jwt_token = request.headers.get('Authorization')

	# Verify the user.
	URL = "http://user:5000/verify"
	PARAMS = {'jwt': jwt_token}
	r = requests.get(url=URL, params=PARAMS)
	user_data = r.json()

	# If the JWT is not valid, return NULL.
	if user_data["status"] == 2:
		return json.dumps({"status": 2, "data": "NULL"})

	if username:
		# If the user isn't requesting logs for themselves, return NULL.
		if (user_data["user"] != username):
			return json.dumps({"status": 3, "data": "NULL"})

		conn = get_db()
		cursor = conn.cursor()
		cursor.execute("SELECT event, username, name FROM logs WHERE username=? ORDER BY row_id", (username,))
		logs = cursor.fetchall()
		conn.close()

		logs_list = {}
		for i in range(1, len(logs)+1):
			logs_list[i] = {
				'event': logs[i-1][0],
				'user': logs[i-1][1],
				'name': logs[i-1][2],
			}

		ret_list = {"status": 1, "data": logs_list}
		return json.dumps(ret_list)

	if product:
		# If the user is not an employee and requesting logs for a product, return NULL.
		if user_data.get("employee") != "True":
			return json.dumps({"status": 3, "data": "NULL"})
		
		conn = get_db()
		cursor = conn.cursor()
		cursor.execute("SELECT event, username, name FROM logs WHERE name=? ORDER BY row_id", (product,))
		logs = cursor.fetchall()
		conn.close()

		logs_list = {}
		for i in range(1, len(logs)+1):
			logs_list[i] = {
				'event': logs[i-1][0],
				'user': logs[i-1][1],
				'name': logs[i-1][2],
			}

		ret_list = {"status": 1, "data": logs_list}
		return json.dumps(ret_list)
	
	return json.dumps({"status": 3, "data": "NULL"})

@app.route('/last_mod', methods=['GET'])
def last_mod():
	product_name = request.args.get('product_name')

	conn = get_db()
	cursor = conn.cursor()
	cursor.execute("SELECT username FROM logs WHERE name=? ORDER BY row_id DESC LIMIT 1", (product_name,))
	logs = cursor.fetchone()
	conn.close()
	last_mod = logs[0] if logs else None

	if last_mod:
		return json.dumps({"status": 1, "last_mod": last_mod})
	else:
		return json.dumps({"status": 2, "last_mod": "NULL"})