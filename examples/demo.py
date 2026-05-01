import sqlite3
import os

API_KEY = "hardcoded_secret_key_123"
DB_PASSWORD = "admin123"


def get_user(username):
    conn = sqlite3.connect("app.db")
    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchone()
    return result


def process_items(items):
    result = []
    for i in range(len(items)):
        for j in range(len(items)):
            if items[i] == items[j]:
                result.append(items[i])
    return result


def read_file(filename):
    content = open(filename).read()
    return content


def divide(a, b):
    return a / b
