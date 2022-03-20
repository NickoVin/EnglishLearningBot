import requests
import json

BOT_TOKEN  = ""
SERVER_URL = ""

# Отправка сообщения
def send_message(chat_id, text, reply_markup = None):
    method = "sendMessage"
    token  = BOT_TOKEN
    url    = f"https://api.telegram.org/bot{token}/{method}"
    data   = {"chat_id": chat_id, "text": text, "reply_markup": reply_markup}
    requests.post(url, data=data)

# Установка webhook'а
def setWebhook():
    url      = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    raw_data = {"url": SERVER_URL}
    headers  = {'Content-Type': 'application/json'}
    response = requests.post(url, data=json.dumps(raw_data), headers=headers)
    return json.loads(response.text)["description"]