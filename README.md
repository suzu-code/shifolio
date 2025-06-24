# Shifolio -シフト管理アプリ-

## 🔍 概要
従業員のシフト管理を効率化するWebアプリです。管理者はシフトを簡単に入力・編集でき、1週間・1ヶ月・1日単位で表示。CSV出力やメール送信も可能でシフト管理の手間を減らします。

## 🌐 URL
[https://shifolio.vercel.app](https://shifolio.vercel.app)

## 🎯 開発背景
私の昔勤めていたアルバイト先では店長がExcelでシフトを管理しており手間が多そうに見えたので、もし使って貰えるとしたらと考え効率化を目指して開発しました。

## 🧩 主な機能
- ユーザー登録・ログイン
  ![企業登録](/images/company_registration.png)
  ![企業ログイン](/images/company_login.png)
- 1週間・1ヶ月・1日表示でのシフト管理（作成・更新・削除）  
  ![1週間表示](/images/popup_week_view.png)
  ![1ヶ月表示](/images/month_view.png)
  ![一日表示](/images/day_view.png)
- スタッフの追加、削除、非表示  
  ![スタッフ追加](/images/add_staff.png)
  ![スタッフ削除・非表示](/images/staff_list.png)  
- シフト表のCSV出力  
  ![CSV出力画面](/images/export_csv.png)  
- 従業員への確定シフトメール送信（ResendAPI利用）  
  ![メール送信画面](/images/send_shift.png)  

## 🔧 使用技術
- フロントエンド：HTML / CSS / JavaScript  
- バックエンド：Python (Flask)  
- データベース：PostgreSQL（[Neon](https://neon.tech/)）    
- メール送信：ResendAPI  
- インフラ：Vercel

## 🛠 工夫、挑戦した点
- ログイン機能の実装  
- 操作しやすいUI設計とポップアップによる編集機能  
- CSVエクスポートやメール送信など実務に役立つ機能の開発

## 📈 今後の改善点
- 従業員による希望シフトの提出機能追加  
- 勤務日数超過アラートや自動集計の実装  
- スマホ対応のレスポンシブ強化

## ✍️ 自己PR
設計から実装・デプロイまで一貫して行い、実践的なWebアプリ開発力と課題解決力を身につけることができたと思います。



## 🗃️ データベース設定（Neon 使用）

このアプリでは Neon（PostgreSQL）を使用しています。

### 1. Neon アカウントを作成し、プロジェクトを作成

- [https://neon.tech](https://neon.tech) で無料アカウントを作成
- プロジェクト作成後、「Connection string」を取得してください（例：`postgresql://username:password@host/dbname`）

### 2. `.env` の設定（環境変数）

プロジェクトのルートに `.env` ファイルを作成し、以下を記述：

```env
DATABASE_URL=postgresql://username:password@your-neon-db.neon.tech/dbname
RESEND_API_KEY=your-resend-api-key
SECRET_KEY=your-secret-key
```

### 3. テーブルの初期化

次のコマンドでテーブルを作成します：

```bash
python db.py
```


## ▶️ ローカル開発手順

### 1. リポジトリをクローン：

   ```
   git clone https://github.com/suzu-code/shifolio.git
   cd shifolio
   ```

### 2. 仮想環境を作成・有効化（Unix/macOS の場合）：

   ```
   python -m venv venv
   source venv/bin/activate
   ```

   Windows の場合：

   ```
   python -m venv venv
   venv\Scripts\activate
   ```

### 3. 必要パッケージをインストール：

   ```
   pip install -r requirements.txt
   ```

### 4. `.env` ファイルをプロジェクトのルートに作成し、必要な環境変数を記述（次項参照）

### 5. アプリを起動：

   ```
   flask run
   ```

## ✉️ メール送信機能のセットアップ
### 1. Resend に登録し、APIキーを取得します（[公式サイト](https://resend.com/)）。

### 2. `.env` に以下を記述します：

   ```
   RESEND_API_KEY=your-resend-api-key
   ```

### 3. `resend_config.py` を編集し、APIキーを `.env` に記述した値に合わせてください

```python
resend.api_key = os.getenv("RESEND_API_KEY")
```
