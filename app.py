import requests
from TelegramAPI   import setWebhook
from WordTest      import ExecTest
from flask         import Flask, request
from UsersData     import ProcessCommand, Settings, InitUsersData
from AppDB         import InitThemesData
from Notifications import InitNotifications, NotifCommandProcessing

app = Flask(__name__)

# ----------------------------------
# Приём входящих сообщений
# ----------------------------------
@app.route("/", methods=["GET", "POST"])
def receive_update():
    if request.method == "POST":
        # Получить chat_id и текст сообщения
        message = None
        if request.json.get("message") is None:
            root = request.json.get("callback_query")
        else:
            root    = request.json
            message = root["message"].get("text")
        chat_id = root["message"]["chat"]["id"]
        
        # Обработать основную команду
        ProcessCommand(chat_id, message)

        # Выполнить настройку
        Settings(chat_id, request)

        # Выполнение теста
        ExecTest(chat_id, request, message)

        # Обработать команду уведомления
        NotifCommandProcessing(chat_id, request)
    return {"ok": True}

# ----------------------------------
# Установка webhook'а
# ----------------------------------
@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    return setWebhook()

InitThemesData()
InitUsersData()
InitNotifications()
