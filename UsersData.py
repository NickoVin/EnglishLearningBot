from enum         import IntEnum
from enum         import Enum
from themeManager import tManager
from TelegramAPI  import send_message
from AppDB        import *
import datetime
import json

# Границы допустимых значений
minRightCount = 5  # Минимальное количество правильных ответов для зачёта слова
maxRightCount = 25 # Максимальное количество правильных ответов для зачёта слова
minQuestCount = 5  # Минимальное количество задаваемых вопросов
maxQuestCount = 25 # Максимальное количество задаваемых вопросов

# Состояния
class States(IntEnum):
    DEFAULT   = 1
    TEST      = 2

# Данные пользователей
data = {}

# Переключение состояния
def ProcessCommand(chat_id, command):
# ----------------------------------
#   Входные параметры:
#       chat_id - идентификатор чата получателя
#       command - команда
# ----------------------------------
    # Инициализация данных
    global data
    userData = GetUserData(chat_id)
    state    = userData["localBotState"]

    # Проверка на пустое сообщение
    if command is None:
        return

    # Переход в состояние DEFAULT
    if command == "/start":
        userData.update({"localBotState" : States.DEFAULT})
        send_message(chat_id, "Здравствуйте! Вы находитесь в главном меню. Для выбора пункта отправьте его название. Вам доступно:\n• Начать тест\n• Статистика\n• Настройка параметров")
        return

    # Переход в состояние TEST
    if command.upper() == "НАЧАТЬ ТЕСТ" and state == States.DEFAULT:
        userData.update({"localBotState" : States.TEST})

    # Показать статистику пользователя
    if command.upper() == "СТАТИСТИКА" and state == States.DEFAULT:
        ShowStatistic(chat_id)
        return

    # Переход в настройки параметров
    if command.upper() == "НАСТРОЙКА ПАРАМЕТРОВ":
        # Формирование кнопок inline-клавиатуры
        reply_markup = { "inline_keyboard": [
            [
                {
                    "text": "Выбор темы для изучения",
                    "callback_data": '{"code": "themePick", "arg": ""}'
                }
            ],
            [
                {
                    "text": "Количество вопросов в тесте",
                    "callback_data": '{"code": "testQuestCount", "arg": ""}'
                }
            ],
            [
                {
                    "text": "Количетсво правильных ответов для зачёта слова",
                    "callback_data": '{"code": "rightAnswersCount", "arg": ""}'
                }
            ],
            [
                {
                    "text": "Включить оповещения",
                    "callback_data": 'enable'
                }
            ],
            [
                {
                    "text": "Выключить оповещения",
                    "callback_data": 'disable'
                }
            ],
            [
                {
                    "text": "Меню",
                    "callback_data": '{"code": "menu", "arg": ""}'
                }
            ]
        ] }

        # Отправить меню настроек
        notifMode = "Выкл"
        if (userData.get(userData.get("notifications"))):
            notifMode = "Вкл."
        info =  "ТЕКУЩИЕ НАСТРОЙКИ\n" +\
                "Оповещения: " + notifMode + "\n" +\
                "Тема: " + userData.get("theme").name + "\n" +\
                "Количество вопросов в тесте: " + str(userData.get("questCount")) + "\n" +\
                "Необходимое количество правильных ответов для зачёта слова: " + str(userData.get("rightCount")) + "\n"
        send_message(chat_id, info, json.dumps(reply_markup))
        return

# Показать статистику
def ShowStatistic(user_id):
# ----------------------------------
#   Входные параметры:
#       chat_id - идентификатор чата получателя
# ----------------------------------
    # Инициализация данных
    themeStat = ''
    userData = GetUserData(user_id)

    # Подсчитать количество изученных слов по каждой теме
    for theme in tManager.themes: # По каждой теме
        userThemeData = userData.get("wordsStatus").get(theme.name)
        learnedCount = 0
        for word in userThemeData:
            if userThemeData.get(word) >= userData.get("rightCount"):
                learnedCount += 1
        themeStat += "    " + theme.name + ": " + str(learnedCount) + " из " + str(len(theme.dictionary)) + "\n"

    # Отправить сообщение со статистикой
    send_message(user_id,   "СТАТИСТИКА\n" +
                            "Выученные слова:\n" + themeStat +
                            "Дата последнего прохождения теста: " + str(userData.get("lastTestDate")) + "\n")

# Инициализация пользовательских данных
def InitUsersData():
    tgIDs = GetUsersTgID()
    for user_id in tgIDs:
        userData = GetUserData(user_id)
        userData["localBotState"] = States.DEFAULT

# Получить данные пользователя
def GetUserData(user_id):
# ----------------------------------
#   Входные параметры:
#       user_id - идентификатор пользователя
#   Выходные параметры:
#       userData - данные пользователя
# ----------------------------------
    TryAddDataNewUser(user_id)
    userData = data[user_id]
    return userData

# Попробовать добавить данные нового пользователя
def TryAddDataNewUser(user_id):
# ----------------------------------
#   Входные параметры:
#       user_id - идентификатор пользователя
#   Выходные параметры:
#       True  - успешное добавление
#       False - безуспешное добавление
# ----------------------------------
    global data
    if data.get(user_id) is None:
        # Cформировать шаблон данных
        data.update({user_id : {
            "localBotState": States.DEFAULT,
            "lastTestDate" : datetime.datetime.now(),
            "wordsStatus"  : { },
            "theme"        : tManager.GetThemeByName("Хэллоуин"),
            "rightCount"   : minRightCount,
            "questCount"   : minQuestCount,
            "test"         : {
                "targetWord" : '',
                "targetIndex": -1,
                "qCounter"   : 0,
                "repeat"     : False
            },
            "th_notification": None,
            "notifications"  : True
        }})

        # Внести данные нового пользователя в БД
        InsertUserData(user_id, data.get(user_id))
        UpdateLocalUserData(user_id, data.get(user_id))
        return True

    return False

# Настройки
def Settings(user_id, request):
# ----------------------------------
#   Входные параметры:
#       user_id - идентификатор пользователя
#       request - данные полученного ответа
# ----------------------------------
    answer = request.json.get("callback_query")
    if answer is not None:
        # Проверить формат ответа
        answer = answer["data"]
        try:
            answer = json.loads(answer)
            tryGet = answer["code"]
        except:
            return

        # Вызвать меню выбора темы
        if answer["code"] == "themePick":
            # Сформировать кнопки выбора
            reply_markup = { "inline_keyboard": []}
            for theme in tManager.themes:
                reply_markup["inline_keyboard"].append([])
                lastIndex =  len(reply_markup["inline_keyboard"]) - 1
                reply_markup["inline_keyboard"][lastIndex].append({
                    "text": theme.name,
                    "callback_data": '{"code": "setTheme", "arg": "' + theme.name + '"}'
                })

            # Отправить клавиатуру выбора
            send_message(user_id, "Доступные темы:", json.dumps(reply_markup))
            return

        # Установить тему
        if answer["code"] == "setTheme":
            theme = tManager.GetThemeByName(answer.get("arg"))
            GetUserData(user_id)["theme"] = theme
            send_message(user_id, "Вы установили тему теста: \"" + theme.name + "\"")
            UpdateServerUserData(user_id, GetUserData(user_id))
            return
        
        # Вызвать меню выбора количества вопросов в тесте
        if answer["code"] == "testQuestCount":
            # Сформировать кнопки вариантов ответа
            reply_markup = { "inline_keyboard": []}
            for i in range(minQuestCount, maxQuestCount, +5):
                reply_markup["inline_keyboard"].append([])
                lastIndex =  len(reply_markup["inline_keyboard"]) - 1
                reply_markup["inline_keyboard"][lastIndex].append({
                    "text": i,
                    "callback_data": '{"code": "setQuestCount", "arg": "' + str(i) + '"}'
                })

            # Добавить кнопку выхода к меню
            reply_markup["inline_keyboard"].append([])
            lastIndex =  len(reply_markup["inline_keyboard"]) - 1
            reply_markup["inline_keyboard"][lastIndex].append({
                "text": "Меню",
                "callback_data": '{"code": "menu", "arg": ""}'
            })

            # Отправить сообщение
            send_message(user_id, "Какое количество вопросов вы хотите видеть в тесте:", json.dumps(reply_markup))
            return

        # Установить количество вопросов в тесте
        if answer["code"] == "setQuestCount":
            userData = GetUserData(user_id)
            userData["questCount"] = int(answer["arg"])
            send_message(user_id, "Теперь в тесте будет \"" + answer["arg"] + "\" вопросов.")
            UpdateServerUserData(user_id, GetUserData(user_id))
            return

        # Вызвать меню для выбора количества правильных ответов для зачёта слова
        if answer["code"] == "rightAnswersCount":
            # Сформировать кнопки настроек
            reply_markup = { "inline_keyboard": []}
            for i in range(minRightCount, maxRightCount, +5):
                reply_markup["inline_keyboard"].append([])
                lastIndex =  len(reply_markup["inline_keyboard"]) - 1
                reply_markup["inline_keyboard"][lastIndex].append({
                    "text": i,
                    "callback_data": '{"code": "setRightCount", "arg": "' + str(i) + '"}'
                })

            # Добавить кнопку выхода в меню
            reply_markup["inline_keyboard"].append([])
            lastIndex =  len(reply_markup["inline_keyboard"]) - 1
            reply_markup["inline_keyboard"][lastIndex].append({
                "text": "Меню",
                "callback_data": '{"code": "menu", "arg": ""}'
            })

            # Отправить сообщение
            send_message(user_id, "Какое количество вопросов вы хотите видеть в тесте:", json.dumps(reply_markup))
            return

        # Установить количество ответов для зачёта слова
        if answer["code"] == "setRightCount":
            userData = GetUserData(user_id)
            userData["rightCount"] = int(answer["arg"])
            send_message(user_id, "Теперь для зачёта слова нужно правильно ответить на \"" + answer["arg"] + "\" вопросов без ошибок.")
            UpdateServerUserData(user_id, GetUserData(user_id))
            return

        # Выход в меню
        if answer["code"] == "menu":
            ProcessCommand(user_id, "/start")
            return

# Увеличить счётчик слова
def IncWordScore(user_id, word):
# ----------------------------------
#   Входные параметры:
#       user_id - идентификатор пользователя
#       word    - изучаемое слово
# ----------------------------------
    global data
    userData   = GetUserData(user_id)
    themeScore = userData["wordsStatus"][userData["theme"].name]
    if themeScore.get(word) is None:
        themeScore.update({word: 0})
    themeScore[word] += 1

# Обнулить счётчик слова
def ResetWordScore(user_id, word):
# ----------------------------------
#   Входные параметры:
#       user_id - идентификатор пользователя
#       word    - изучаемое слово
# ----------------------------------
    global data
    userData = GetUserData(user_id)
    themeScore = userData["wordsStatus"][userData["theme"].name]
    if themeScore.get(word) is None:
        themeScore.update({word: 0})
        return
    themeScore[word] = 0

# Получить счётчик слова
def GetWordScore(user_id, word):
# ----------------------------------
#   Входные параметры:
#       user_id - идентификатор пользователя
#       word    - изучаемое слово
# ----------------------------------
    global data
    userData = GetUserData(user_id)
    themeScore = userData["wordsStatus"][userData["theme"].name]
    if themeScore.get(word) is None:
        themeScore.update({word: 0})
    return themeScore[word]

# Увеличить счётчик вопросов
def IncQuestCounter(user_id):
# ----------------------------------
#   Входные параметры:
#       user_id - идентификатор пользователя
# ----------------------------------
    global data
    userData = GetUserData(user_id)
    userData["test"]["qCounter"] += 1

# Сбросить счётчик вопросов
def ResetQuestCounter(user_id):
# ----------------------------------
#   Входные параметры:
#       user_id - идентификатор пользователя
# ----------------------------------
    global data
    userData = GetUserData(user_id)
    userData["test"]["qCounter"] = 0

# Обновить дату прохождения последнего теста
def UpdateLastTestDate(user_id):
# ----------------------------------
#   Входные параметры:
#       user_id - идентификатор пользователя
# ----------------------------------
    global data
    userData = GetUserData(user_id)
    userData["lastTestDate"] = datetime.datetime.now()
