# db.py
# import mysql.connector

# def get_connection():
#     return mysql.connector.connect(
#         host="localhost",       
#         user="root",            
#         password="",
#         database="shift_app_db", 
#         charset='utf8mb4'
#     )
    


# try:
#     conn = get_connection()
#     print("MySQLに接続成功！")
#     conn.close()
# except mysql.connector.Error as err:
#     print(f"接続エラー: {err}")



import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)


