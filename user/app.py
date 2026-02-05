"""
This microservice handles user management, including creating and logging in users.
It uses a SQLite database to store user information and generates JWT tokens for authentication.
It also checks if a user is an employee based on the JWT token.
Port 9000
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
db_name = "users.db"
sql_file = "users.sql"
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

def valid_password(username, first_name, last_name, pw, salt=""):
	if pw is None or len(pw) < 8:
		return False
	if not re.search(r'[0-9]', pw):
		return False
	if not re.search(r'[A-Z]', pw):
		return False
	if not re.search(r'[a-z]', pw):
		return False
	if username and username.lower() in pw.lower():
		return False
	if first_name and first_name.lower() in pw.lower():
		return False
	if last_name and last_name.lower() in pw.lower():
		return False
	return True

def generate_jwt(username):
	# Read key from file "key.txt" in the outermost directory
	try:
		with open("key.txt", "r") as key_file:
			key = key_file.readline().strip()
	except Exception as e:
		raise Exception("JWT key file not found or unreadable.")
	
	header = {"alg": "HS256", "typ": "JWT"}
	payload = {"username": username}
	
	# Convert header and payload to JSON
	header_json = json.dumps(header)
	payload_json = json.dumps(payload)
	
	# Base64 URL safe encode.
	header_b64 = base64.urlsafe_b64encode(header_json.encode('utf-8')).decode('utf-8')
	payload_b64 = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8')
	
	signing_input = f"{header_b64}.{payload_b64}"
	
	# Compute HMAC using the key and SHA256.
	signature = hmac.new(key.encode('utf-8'), signing_input.encode('utf-8'), hashlib.sha256).hexdigest()
	
	token = f"{header_b64}.{payload_b64}.{signature}"
	return token

def verify_jwt(token):
	try:
		parts = token.split('.')
		if len(parts) != 3:
			return None
		header_b64, payload_b64, sig = parts
		# Recompute the signature using the header and payload.
		try:
			with open("key.txt", "r") as key_file:
				key = key_file.readline().strip()
		except Exception as e:
			return None
		signing_input = f"{header_b64}.{payload_b64}"
		computed_signature = hmac.new(key.encode('utf-8'), signing_input.encode('utf-8'), hashlib.sha256).hexdigest()
		if not hmac.compare_digest(computed_signature, sig):
			return None
		payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode('utf-8'))
		return payload
	except Exception:
		return None
	
@app.route('/', methods=(['GET']))
def index():
	conn = get_db()
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM users;")
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

@app.route('/create_user', methods=['POST'])
def create_user():
	# Extract form data from the request.
	first_name = request.form.get('first_name')
	last_name = request.form.get('last_name')
	username = request.form.get('username')
	email_address = request.form.get('email_address')
	employee = "True" if request.form.get('employee') in [True, "true", "True", "1"] else "False"
	password = request.form.get('password')
	salt = request.form.get('salt')

	# Validate the password with required complexity and uniqueness.
	if not valid_password(username, first_name, last_name, password, salt):
		return json.dumps({"status": 4, "pass_hash": "NULL"})
	
	# Generate a SHA256 hash of the password concatenated with the salt.
	pass_hash = hashlib.sha256((password + salt).encode()).hexdigest()
	
	# Connect to the database.
	conn = get_db()
	cursor = conn.cursor()
	
	# Check if username is NULL
	if not username:
		conn.close()
		return json.dumps({"status": 2, "pass_hash": "NULL"})
	
	# Check if email address is NULL
	if not email_address:
		conn.close()
		return json.dumps({"status": 3, "pass_hash": "NULL"})

	# Check if the username already exists
	cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
	if cursor.fetchone() is not None:
		conn.close()
		return json.dumps({"status": 2, "pass_hash": "NULL"})
	
	# Check if the email address is already registered
	cursor.execute("SELECT * FROM users WHERE email_address = ?", (email_address,))
	if cursor.fetchone() is not None:
		conn.close()
		return json.dumps({"status": 3, "pass_hash": "NULL"})
	
	# Insert the new user record into the users table.
	cursor.execute(
		"INSERT INTO users (first_name, last_name, username, email_address, employee, password, salt) VALUES (?, ?, ?, ?, ?, ?, ?)",
		(first_name, last_name, username, email_address, employee, pass_hash, salt)
	)
	
	# Commit the transaction and close the database connection.
	conn.commit()
	conn.close()

	# Log the event
	URL = "http://logs:5000/log"
	PARAMS = {"event": "user_creation", "user": username, "name": "NULL"}
	log = requests.post(url=URL, data=PARAMS)
	log = log.json()
	
	# Return success response along with the password hash.
	return json.dumps({"status": 1, "pass_hash": pass_hash})

@app.route('/login', methods=['POST'])
def login():
	username = request.form.get('username')
	password = request.form.get('password')

	conn = get_db()
	cursor = conn.cursor()
	cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
	row = cursor.fetchone()
	if row is None:
		return json.dumps({"status": 2, "jwt": "NULL"})
	stored_hash = row[0]

	# Fetch the salt from the users table.
	cursor.execute("SELECT salt FROM users WHERE username = ?", (username,))
	row = cursor.fetchone()
	if row is None:
		return json.dumps({"status": 2, "jwt": "NULL"})
	salt = row[0]
	conn.close()
		
	computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
	if computed_hash != stored_hash:
		return json.dumps({"status": 2, "jwt": "NULL"})
	
	# If login is successful, generate a JWT.
	try:
		token = generate_jwt(username)
	except Exception as e:
		return json.dumps({"status": 3, "jwt": "NULL", "error": str(e)})
	
	# Log the event
	URL = "http://logs:5000/log"
	PARAMS = {"event": "login", "user": username, "name": "NULL"}
	log = requests.post(url=URL, data=PARAMS)
	log = log.json()
	
	return json.dumps({"status": 1, "jwt": token})

@app.route('/verify', methods=['GET'])
def verify():
	token = request.args.get('jwt')
	payload = verify_jwt(token)

	if payload is None:
		return json.dumps({"status": 2, "user": "NULL", "employee": "NULL"})
	
	username = payload["username"]
	conn = get_db()
	cursor = conn.cursor()
	cursor.execute("SELECT employee FROM users WHERE username = ?", (username,))
	row = cursor.fetchone()
	conn.close()

	if row is None:
		return json.dumps({"status": 2, "user": "NULL", "employee": "NULL"})
	employee = row[0]
	return json.dumps({"status": 1, "user": username, "employee": employee})