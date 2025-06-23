# db.py
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",        # DBホスト（ローカルならlocalhost）
        user="root",             # あなたのMySQLユーザー名
        password="",# パスワード
        database="shift_app_db", # 作成したMySQLのDB名
        charset='utf8mb4'
    )
    

# テスト実行
try:
    conn = get_connection()
    print("MySQLに接続成功！")
    conn.close()
except mysql.connector.Error as err:
    print(f"接続エラー: {err}")
