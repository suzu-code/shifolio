import os
from dotenv import load_dotenv
import resend

# .env ファイルから環境変数を読み込む
load_dotenv()

# 環境変数からAPIキーを取得
resend.api_key = os.getenv("RESEND_API_KEY")


def send_email(to, subject, html_content):
    return resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": to,
        "subject": subject,
        "html": html_content
    })
