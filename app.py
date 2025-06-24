import os
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta, date
from flask import Response
from resend_config import send_email
from db import get_connection
import psycopg2
import psycopg2.extras


app = Flask(__name__)
#セッションキー　安全のためにやったほうがいいらしい
app.secret_key = os.urandom(24)


#データベースを初期化
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # companyテーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS company (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL
        )
    """)

    # staffテーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            position VARCHAR(255),
            max_days INT,
            available_days TEXT,
            can_edit BOOLEAN,
            company_id INT,
            email VARCHAR(255),
            visible BOOLEAN DEFAULT TRUE,
            FOREIGN KEY(company_id) REFERENCES company(id)
        )
    """)

    # shiftテーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shift (
            id SERIAL PRIMARY KEY,
            staff_id INT,
            date DATE,
            start_time TIME,
            end_time TIME,
            FOREIGN KEY(staff_id) REFERENCES staff(id)
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

# 初期化実行
init_db()





#フォームの表示（GET）と送信（POST）
@app.route('/register_company', methods=["GET", "POST"])
def register_company():
    #フォームが送信された時
    if request.method == "POST":
        # 入力した企業名をフォームから取得
        name = request.form["name"]
        password = request.form["password"]

        conn = get_connection()
        # .cursor()でSQL実行用のカーソルオブジェクトを作成
        cur = conn.cursor()
        # cur.execute("INSERT INTO company (name, password) VALUES (%s, %s)", (name, password))
        # conn.commit()
        cur.execute("INSERT INTO company (name, password) VALUES (%s, %s) RETURNING id",(name, password))
        company_id = cur.fetchone()[0]  # 挿入された行のidを取得
        conn.commit()

        #SQLiteのlastrowid：SQLiteのカーソルオブジェクト(cursor)に用意されたプロパティ名。その接続で直前に追加された1件のIDを確実に返す。
        # company_id = cur.lastrowid
        conn.close()

        # fはf"..." の中に{}で変数や式を埋め込むことで、文字列の中に動的な値を簡単に入れられる機能
        flash(f"登録完了。控えてください → 企業ID: {company_id}")
        return redirect(url_for("login")) 
    return render_template("register_company_test.html")




@app.route('/login', methods=["GET", "POST"])
def login():
    # ユーザーがログインフォームを送信してきた時に実行
    if request.method == "POST":
        company_id = request.form["company_id"]
        password = request.form["password"]
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM company WHERE id=%s AND password=%s", (company_id, password))
        #cur.executeでSQLクエリを実行した後、SQLの結果から1行だけ取得
        company = cur.fetchone()
        conn.close()

        #companyに企業情報が入っていれば、ログイン情報が正しければ
        if company:
            # sessionはユーザーごとに情報を保持する辞書のようなもの。ログインした企業のIDと名前をセッションに保存して、ログイン状態を管理。
            session["company_id"] = company_id
            #企業名を保存
            session["company_name"] = company[1]  
            flash("ログイン成功")
            # return redirect(url_for("index"))　これ元のやつ
            
            # 今日の日付を取得し、文字列にしてリダイレクト
            today = datetime.today().strftime("%Y-%m-%d")
            # date=todayで今日を表示基準日に設定
            return redirect(url_for("week_view", date=today))
        else:
            flash("ログイン失敗。企業IDまたはパスワードが違います。")
    return render_template("login.html")




@app.route('/logout')
def logout():
    #セッション＝ログイン情報を全部クリア
    session.clear()
    return redirect(url_for('login'))




@app.route("/", methods=["GET", "POST"])
def index():
    if "company_id" not in session:
        return redirect(url_for("login"))

    #もしフォームを送信したなら
    if request.method == "POST":
        #ここで保存！前ページで選択した日付を先頭にするため。カレンダーで決めた日付（フォームで送った）をセッションに保存
        session["start_date"] = request.form["date"]
        # フォームからoriginを取得（省略された場合はweekをデフォルトに）　保存した直前にいた場所
        origin = request.form.get("origin", "week")
        if origin == "month":
            return redirect(url_for("month_view", date=request.form["date"]))
        else:
            return redirect(url_for("week_view", date=request.form["date"]))

    return render_template("index.html")




@app.route('/add_staff', methods=["GET", "POST"])
def add_staff():
    if "company_id" not in session:
        return redirect(url_for("login"))
    
    today = date.today().strftime('%Y-%m-%d')

    if request.method == "POST":
        name = request.form["name"]
        position = request.form["position"]
        email = request.form["email"] 
        max_days = request.form["max_days"]
        #フォームで送られてきた "available_days" という 複数選択可能なチェックボックスの値をリストとして取得。　",".join([...])=取得したリストをカンマ区切りの1つの文字列に変換
        available_days = ",".join(request.form.getlist("available_days"))
        #チェックボックスのon/offを判定して1or0を入力している
        # can_edit = 1 if request.form.get("can_edit") else 0
        #PostgreSQL の boolean 型は TRUE / FALSE（または true / false）であって、 1 / 0 では ない
        can_edit = bool(request.form.get("can_edit"))
        #現在ログイン中の企業のIDをセッションから取得。スタッフと企業の紐付けのため
        company_id = session["company_id"]

        conn = get_connection()
        cur = conn.cursor()
        #新しいスタッフを挿入
        cur.execute("""
            INSERT INTO staff (name, position, email, max_days, available_days, can_edit, company_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, position, email, max_days, available_days, can_edit, company_id))
        conn.commit()
        conn.close()
        
        #ここから下　リダイレクト先の制御　ここindexの内容を上につけたからいるやつ
        origin = request.form.get("origin", "index")
        start_date = request.form.get("start_date", "")

        if origin == "week" and start_date:
            return redirect(url_for("week_view", date=start_date))
        elif origin == "month" and start_date:
            return redirect(url_for("month_view", date=start_date))
        elif origin == "day":
            return redirect(url_for("one_day_view", date=start_date))
        else:
            return redirect(url_for("index"))

    #GETのときパラメータをテンプレートへ渡す
    origin = request.args.get("origin", "index")
    start_date = request.args.get("start_date", "")
    return render_template("add_staff.html", origin=origin, start_date=start_date ,today=today)



    
def trim_time_str(t):
    if isinstance(t, str):
        return t[:5]
    elif isinstance(t, timedelta):
        total_seconds = int(t.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    else:
        return t.strftime("%H:%M")


@app.route('/week/<date>')
def week_view(date):
    if "company_id" not in session:
        return redirect(url_for("login"))

    company_id = session["company_id"]
    #strptimeメソッド:文字列として表現された日付や時刻からdatetime型のオブジェクトを作成。%Y-%m-%dは年-月-日　
    #datetimeモジュールの中にあるstrptimeメゾット(引数のdateという文字列をdatetimeオブジェクトに変換)
    start_date = datetime.strptime(date, "%Y-%m-%d")
    
    # 曜日を漢字に変換するための辞書
    week_days_kanji = ['月', '火', '水', '木', '金', '土', '日']
    #[]でリストを作成
    #datetimeモジュールの中にあるクラスがtimedelta.時間の差の足し算引き算をする時に使う
    #daysはキーワード引数で上で定義しなくても関数やクラスの中で定義される名前
    week_dates = [(start_date + timedelta(days=i)) for i in range(7)]
    
    dates_with_kanji = [{"date": d, "weekday_kanji": week_days_kanji[d.weekday()]} for d in week_dates]
    
    dates_with_meta = [
    {
        "date": d,
        "kanji": week_days_kanji[d.weekday()],
        "cls": "saturday" if d.weekday() == 5 else "sunday" if d.weekday() == 6 else ""
    }
    for d in week_dates
]


    db = get_connection()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM staff WHERE company_id=%s AND visible=TRUE", (company_id,))
    staff = cursor.fetchall()

    query_shift = "SELECT start_time, end_time FROM shift WHERE staff_id=%s AND date=%s"
    
    #★ここ勉強し直す必要あり！！！！！！！！
    #スタッフごとのシフト情報を格納する辞書を初期化
    shifts = {}
    #スタッフの人数の分だけループ
    for s in staff:
        shifts[s[0]] = {}
        for d in week_dates:
            cursor.execute(query_shift, (s[0], d.strftime("%Y-%m-%d")))
            shift = cursor.fetchone()  # (start_time, end_time) または None
            if shift:
                # 秒をカットしてタプルに入れる
                start_trimmed = trim_time_str(shift[0])
                end_trimmed = trim_time_str(shift[1])
                shifts[s[0]][d.strftime("%Y-%m-%d")] = (start_trimmed, end_trimmed)
            else:
                shifts[s[0]][d.strftime("%Y-%m-%d")] = None

    db.close()
    return render_template("week_view.html", staff=staff, dates=week_dates, dates_with_kanji=dates_with_kanji, dates_with_meta=dates_with_meta, shifts=shifts, start_date=start_date.strftime("%Y-%m-%d"))




@app.route('/month/<date>', methods=['GET', 'POST'])  # ← POST を追加
def month_view(date):
    if "company_id" not in session:
        return redirect(url_for("login"))

    # POSTのとき、新しい日付が来たらリダイレクト
    if request.method == 'POST':
        new_date = request.form.get("date")
        if new_date:
            return redirect(url_for('month_view', date=new_date))

    # 表示開始日をセッションに常に保持
    session["start_date"] = date  

    company_id = session["company_id"]
    start_date = datetime.strptime(date, "%Y-%m-%d")
    month_dates = [(start_date + timedelta(days=i)) for i in range(30)]

    # 曜日を漢字に変換するための辞書
    month_days_kanji = ['月', '火', '水', '木', '金', '土', '日']

    dates_with_kanji = [{"date": d, "monthday_kanji": month_days_kanji[d.weekday()]} for d in month_dates]

    dates_with_meta = [
        {
            "date": d,
            "kanji": month_days_kanji[d.weekday()],
            "cls": "saturday" if d.weekday() == 5 else "sunday" if d.weekday() == 6 else ""
        }
        for d in month_dates
    ]

    conn = get_connection()
    cur = conn.cursor()

    # スタッフ一覧（ログイン企業のみ）
    # cur.execute("SELECT * FROM staff WHERE company_id=%s AND visible=1", (company_id,))
    cur.execute("SELECT * FROM staff WHERE company_id=%s AND visible=TRUE", (company_id,))

    staff = cur.fetchall()
    
    shifts = {}
    for s in staff:
        shifts[s[0]] = {}
        for d in month_dates:
            cur.execute("SELECT start_time, end_time FROM shift WHERE staff_id=%s AND date=%s", (s[0], d.strftime("%Y-%m-%d")))
            shift = cur.fetchone()  # (start_time, end_time) または None
            if shift:
                start_trimmed = trim_time_str(shift[0])
                end_trimmed = trim_time_str(shift[1])
                shifts[s[0]][d.strftime("%Y-%m-%d")] = (start_trimmed, end_trimmed)
            else:
                shifts[s[0]][d.strftime("%Y-%m-%d")] = None

    conn.close()
    return render_template(
        "month_view.html",
        staff=staff,
        dates=month_dates,
        dates_with_kanji=dates_with_kanji,
        dates_with_meta=dates_with_meta,
        shifts=shifts,
        start_date=start_date.strftime("%Y-%m-%d")
    )




@app.route('/add_shift', methods=["POST"])
def add_shift():
    if "company_id" not in session:
        return redirect(url_for("login"))

    staff_id = request.form["staff_id"]
    date = request.form["date"]
    start_time = request.form["start_time"]
    end_time = request.form["end_time"]
    origin = request.form.get("origin", "month")
    # ここが最初に選んだ日付を先頭のままにするためにいるやつ
    start_date = request.form.get("start_date", date)

    db = get_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM shift WHERE staff_id=%s AND date=%s", (staff_id, date))
    cursor.execute("""
        INSERT INTO shift (staff_id, date, start_time, end_time)
        VALUES (%s, %s, %s, %s)
    """, (staff_id, date, start_time, end_time))
    db.commit()
    db.close()

    # 元のページへリダイレクト
    if origin == "week":
        return redirect(url_for("week_view", date=start_date))
    elif origin == "day":
        return redirect(url_for("one_day_view", date=start_date))
    else:
        start_date = session.get("start_date", date)
        return redirect(url_for("month_view", date=start_date))




@app.route('/delete_shift', methods=["POST"])
def delete_shift():
    #ログインしていない時ログイン画面にリダイレクトする。セッションにcompany_idがない＝ログインしていない
    if "company_id" not in session:
        return redirect(url_for("login"))

    staff_id = request.form["staff_id"]
    date = request.form["date"]
    origin = request.form.get("origin", "month")
    #これが重要！　ゴミ箱ボタン押した時そこが先頭にならないために
    start_date = request.form.get("start_date", date)

    db = get_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM shift WHERE staff_id=%s AND date=%s", (staff_id, date))
    db.commit()
    db.close()

    flash("シフトを削除しました。")

    if origin == "week":
        return redirect(url_for("week_view", date=start_date))
    else:
        return redirect(url_for("month_view", date=start_date))
    
    


@app.route('/export_csv', methods=['GET', 'POST'])
def export_csv():
    if "company_id" not in session:
        return redirect(url_for("login"))
    
    
    if request.method == 'GET':
        #今日の日付をテンプレートに渡す
        today = datetime.today().strftime('%Y-%m-%d')
        return render_template('export_csv.html', today=today)

    #POSTのとき処理開始
    company_id = session["company_id"]
    start_date_str = request.form.get('export_start_date')
    end_date_str = request.form.get('export_end_date')

    #日付のバリデーション
    try:
        #フォームから開始日（文字列）を取得
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        #フォームから終了日（文字列）を取得
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        #開始日が終了日より後ならエラーメッセージを表示して再読み込み
        if start_date > end_date:
            flash("開始日は終了日より前の日付を指定してください。")
            return redirect(url_for('export_csv'))
        
    #日付の変換で例外が発生した場合（例：不正な形式）、エラーメッセージを表示して再読み込み
    except Exception:
        flash("日付の形式が正しくありません。")
        return redirect(url_for('export_csv'))

    #期間中の日付リスト作成
    #開始日から終了日までの期間（日数）を算出
    delta = (end_date - start_date).days + 1
    #その期間中の日付リストを生成（1日ずつ加算）
    date_list = [start_date + timedelta(days=i) for i in range(delta)]

    # DB接続してスタッフとシフトを取得
    conn = get_connection()
    cur = conn.cursor()

    # 企業のスタッフを取得
    cur.execute("SELECT id, name FROM staff WHERE company_id=%s", (company_id,))
    #取得したスタッフデータをリストとして保存。
    staff_list = cur.fetchall()

    # スタッフごとのシフトを取得
    shifts = {}
    for s in staff_list:
        #スタッフIDを取り出す
        staff_id = s[0]
        #シフト情報を初期化。
        shifts[staff_id] = {}
        # シフトを取得（期間中のもの）そのスタッフの指定期間内のシフト情報を取得
        cur.execute("""
            SELECT date, start_time, end_time FROM shift
            WHERE staff_id=%s AND date BETWEEN %s AND %s
        """, (staff_id, start_date_str, end_date_str))
        #結果をリストで取得
        shift_rows = cur.fetchall()
        #各シフト情報に対して… {日付: "開始時刻 - 終了時刻"} の形式で保存
        for row in shift_rows:
            shifts[staff_id][row[0]] = f"{row[1]} - {row[2]}"  #"09:00 - 17:00"形式

    conn.close()

    #CSVをメモリ上で生成
    #メモリ上に文字列データを書き込むためのバッファ(=一時的にデータを貯めておく場所)を作成（CSV出力用）
    output = io.StringIO()
    #CSVライターを作成
    writer = csv.writer(output)

    #ヘッダー行を作成（名前 + 各日付列） ヘッダーをCSVに書き込む
    header = ['名前'] + [d.strftime('%Y-%m-%d') for d in date_list]
    writer.writerow(header)

    #各スタッフのCSV行を生成
    for s in staff_list:
        #行の最初はスタッフ名
        row = [s[1]] 
        #各日付に対して…
        #日付を文字列に
        #シフト情報があれば書き込み、無ければ空欄
        for d in date_list:
            date_str = d.strftime('%Y-%m-%d')
            row.append(shifts.get(s[0], {}).get(date_str, ''))
        #そのスタッフの行をCSVに書き込む
        writer.writerow(row)

    #メモリ上のCSV内容を文字列として取得
    csv_data = output.getvalue()
    #バッファを閉じる
    output.close()

    # レスポンス作成（CSVダウンロード）
    #CSVファイルをHTTPレスポンスとして返す
    return Response(
        csv_data,
        #ファイル形式はCSV
        mimetype='text/csv',
        #ダウンロード用に適切なファイル名を設定（例：shift_2025-06-01_to_2025-06-07.csv）
        headers={"Content-Disposition": f"attachment; filename=shift_{start_date_str}_to_{end_date_str}.csv"}
    )
    
  
  
   
@app.route("/send_shift", methods=["GET", "POST"])
def send_shift():
    if request.method == "POST":
        #開始終了　範囲
        start = request.form["send_start_date"]
        end = request.form["send_end_date"]

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, name, email FROM staff")
        #取得した結果をstaff_listというリストに保存
        staff_list = c.fetchall()

        # そのスタッフのシフトデータを指定された期間取得　ORDER BY dateで日付順に並べru
        for staff_id, name, email in staff_list:
            c.execute("""
                SELECT date, start_time, end_time 
                FROM shift 
                WHERE staff_id = %s AND date BETWEEN %s AND %s 
                ORDER BY date
            """, (staff_id, start, end))
            #シフトデータをリストで受け取る
            shifts = c.fetchall()

            #シフトがなければスキップ
            if not shifts:
                continue  
            
            #形を整える
            shift_lines = [
                f"{date}: {start_time}～{end_time}"
                for date, start_time, end_time in shifts
            ]
            #メール本文の最初
            body = f"<p>{name}さん、以下が{start}〜{end}のシフトです。</p>"
            
            # 上で作成した shift_linesを<ul><li>...</li></ul>のHTMLリストに整形して本文に追加
            body += "<ul>" + "".join([f"<li>{line}</li>" for line in shift_lines]) + "</ul>"
            # メールの件名を作成
            subject = f"{name}さんの{start}〜{end}のシフト"
            # テスト用に自分のメールアドレスに送信
            send_email(email, subject, body)

        conn.close()
    # 今日の日付（例：2025-06-16）を取得し、テンプレートに渡す
    today = date.today().isoformat()
    # 今日の日付もテンプレートに渡してデフォルト日付として表示できるようにする
    return render_template("send_shift.html", today=today)






# @app.route('/staff')
# def staff_list():
#     conn = get_connection()
#     cur = conn.cursor(dictionary=True)  

#     cur.execute('SELECT * FROM staff')
   
#     staffs = cur.fetchall() 

#     conn.close()
 
#     start_date = datetime.today()
#     dates = [(start_date + timedelta(days=i)) for i in range(30)]
    
#     today = datetime.today().strftime('%Y-%m-%d')

#     return render_template('staff_list.html', staffs=staffs, dates=dates, today=today)




@app.route('/staff')
def staff_list():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)  # ← 辞書形式のカーソルを作成

    cur.execute('SELECT * FROM staff')
    # staffテーブルから全てのデータを取得し、staffsに格納　fetchall()で全行まとめて取り出してリスト
    staffs = cur.fetchall()  # これで staffs[0]['name'] のようにアクセス可能

    conn.close()
    # 今日から30日分の日付リストを作成
    start_date = datetime.today()
    dates = [(start_date + timedelta(days=i)) for i in range(30)]
    # 今日の日付を YYYY-MM-DD 形式の文字列で取得
    today = datetime.today().strftime('%Y-%m-%d')

    return render_template('staff_list.html', staffs=staffs, dates=dates, today=today)





@app.route('/staff/delete/<int:staff_id>', methods=['POST'])
def staff_delete(staff_id):
    conn = get_connection()
    cursor = conn.cursor()  
    # 該当するスタッフIDを持つ行をstaffテーブルから削除
    cursor.execute('DELETE FROM staff WHERE id = %s', (staff_id,))
    conn.commit()
    cursor.close()  
    conn.close()
    return redirect(url_for('staff_list'))




@app.route('/start_date_display', methods=['GET', 'POST'])
def start_date_display():
    start_date = None
    if request.method == 'POST':
        start_date = request.form.get('date')  
    return render_template('start_date_display.html', start_date=start_date)




@app.route('/day/<date>', methods=['GET', 'POST'])
def one_day_view(date):
    if "company_id" not in session:
        return redirect(url_for("login"))

    # POSTで別の日付が送られてきた場合、そちらにリダイレクト
    if request.method == 'POST':
        new_date = request.form.get("date")
        if new_date:
            return redirect(url_for("one_day_view", date=new_date))

    company_id = session["company_id"]
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id, name FROM staff WHERE company_id = %s AND visible = TRUE", (company_id,))
    
    staff = c.fetchall()
    shifts = {}
    for s in staff:
        c.execute("SELECT start_time, end_time FROM shift WHERE staff_id = %s AND date = %s", (s[0], date))
        row = c.fetchone()
        print(f"staff_id={s[0]}, date={date}, row={row}")
        if row:
            start_trimmed = trim_time_str(row[0])
            end_trimmed = trim_time_str(row[1])
            shifts[s[0]] = {"start": start_trimmed, "end": end_trimmed}
        else:
            shifts[s[0]] = None
    conn.close()
    
    dates = [datetime.strptime(date, "%Y-%m-%d")]


    return render_template("day_view.html", date=date, dates=dates, staff=staff, shifts=shifts)




@app.route('/staff/hide/<int:staff_id>', methods=['POST'])
def staff_hide(staff_id):
    conn = get_connection()
    cursor = conn.cursor()  
    cursor.execute('UPDATE staff SET visible=FALSE WHERE id=%s', (staff_id,))
    conn.commit()
    cursor.close() 
    conn.close()
    return redirect(url_for('staff_list'))




@app.route('/staff/show/<int:staff_id>', methods=['POST'])
def staff_show(staff_id):
    conn = get_connection()
    cursor = conn.cursor()  
    cursor.execute('UPDATE staff SET visible=TRUE WHERE id=%s', (staff_id,))
    conn.commit()
    cursor.close() 
    conn.close()
    return redirect(url_for('staff_list'))




@app.route('/staff/toggle_visibility/<int:staff_id>', methods=['POST'])
def toggle_visibility(staff_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT visible FROM staff WHERE id=%s', (staff_id,))
    row = c.fetchone()
    if row:
        current_visible = row[0]
        new_visible = 0 if current_visible == 1 else 1
        c.execute('UPDATE staff SET visible=%s WHERE id=%s', (new_visible, staff_id))
        conn.commit()
    c.close()  
    conn.close()
    return redirect(url_for('staff_list'))
