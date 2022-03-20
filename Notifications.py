import json
import datetime
from TelegramAPI import *
from UsersData   import *
from threading   import Thread
from WordTest    import ExecTest
from time        import sleep

delay    = 1
interval = 10

# Поток оповещения
class NotifThread():
    # Конструктор
    def __init__(self, target, userID):
        self.needStop   = False
        self.needResetTimer = False
        self.counter = 0
        self.thread  = Thread(target=target, args=[userID, self])

    # Запустить тред
    def start(self):
        if not self.thread.is_alive():
            self.thread.start()
        else:
            print("Thread is alive.")

    # Проверка активности потока
    def is_alive(self):
        return self.thread.is_alive()

    # Сбросить таймер
    def resetTimer(self):
        self.needResetTimer = True

    # Остановить поток
    def stop(self):
        self.needStop = True;
        self = None

# Авто проверка необходимости отправки уведомления
def AutoCheck():
    while True:
        sleep(delay)
        for userID in data: # для каждого пользователя из локального словаря данных
            # Инициализация данных
            userData     = GetUserData(userID)
            lastTestDate = userData.get("lastTestDate")
            today        = datetime.datetime.today()
            difference   = (today - lastTestDate).seconds
            
            # Отправить уведомление
            # print(str(difference) + " / " + str(not userData["test"]["repeat"]) + " / " + str(userData["th_notification"] is None)) 
            if difference > interval:
                # Запустить таймер для отправки повторного уведомления
                repeate     = userData["test"]["repeat"]
                threadExist = userData["th_notification"]
                notifMode   = userData.get("notifications")
                state       = userData.get("localBotState")
                if not repeate and threadExist is None and state != States.TEST and notifMode:
                    userData["th_notification"] = NotifThread(Timer, userID)
                    userData["th_notification"].start()
                else:
                    break

                # Сформировать кнопки управления
                reply_markup = { "inline_keyboard": [[],[],[]] }
                reply_markup["inline_keyboard"][0].append({
                    "text": "Начать повтор",
                    "callback_data": "repeat"
                })
                reply_markup["inline_keyboard"][1].append({
                    "text": "Напомнить позже",
                    "callback_data": "later"
                })
                reply_markup["inline_keyboard"][2].append({
                    "text": "Отключить напоминание",
                    "callback_data": "disable"
                })

                # Отправить уведомление
                send_message(   
                                userID,
                                "Самое время повторить изученные слова!",
                                json.dumps(reply_markup)
                            )

# Таймер ожидания необходимости повторной отправки уведомления
def Timer(userID, th_parent):
# ----------------------------------
#   Входные параметры:
#       userID    - идентификатор пользователя
#       th_parent - родительский поток
# ----------------------------------
    global data
    # Основной отсчёт
    i = 0
    while i < interval:
        # Подождать секунду
        sleep(1)

        # Остановить таймер потока
        if th_parent.needStop:
            break

        # Сбросить таймер
        if th_parent.needResetTimer:
            i = 0
            th_parent.needResetTimer = False

        # Увеличить значение таймера
        i += 1

    # Уничтожить поток
    userData = GetUserData(userID)
    userData["th_notification"] = None

# Обработка команды оповещения
def NotifCommandProcessing(chat_id, request):
# ----------------------------------
#   Входные параметры:
#       chat_id - идентификатор пользователя
#       request - данные полученного сообщения
# ----------------------------------
    global data
    answer = request.json.get("callback_query")
    if answer is not None:
        # Инициализация переменных
        answer          = answer["data"]
        userData        = data[chat_id]
        th_notification = userData["th_notification"]

        # Начать повтор
        if answer == "repeat":
            userData["test"]["repeat"] = True
            th_notification.stop()
            ProcessCommand(chat_id, "начать тест")
            GetUserData(chat_id)["localBotState"] = States.TEST
            print(GetUserData(chat_id)["localBotState"])
            ExecTest(chat_id, request, None)

        # Отложить повторение
        if answer == "later":
            # Создать новый поток уведомления
            if th_notification is None:
                th_notification = NotifThread(Timer, chat_id)
                th_notification.start()

            # Сбросить таймер
            if th_notification.is_alive():
                th_notification.resetTimer()
                print("Thead counter was resetTimered: " + str(th_notification.needResetTimer))
            # Запустить поток
            else:
                th_notification.start()

        # Выключить оповещение
        if answer == "disable":
            userData.update({"notifications" : False})
            th_notification.stop()

        # Включить оповещение
        if answer == "enable":
            userData.update({"notifications": True})

# Инициализация потока уведомлений
def InitNotifications():
    thread = Thread(target=AutoCheck)
    thread.start()
