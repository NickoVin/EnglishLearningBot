import requests
import json
import random
from themeManager import tManager
from TelegramAPI  import send_message
from UsersData    import *
from AppDB        import *

answersCount = 4 # Количество вариантов ответа

# Проведение теста
def ExecTest(chat_id, request, messageText):
# ----------------------------------
#   Входные параметры:
#       chat_id     - идентификатор чата отправителя
#       request     - данные полученного сообщения
#       messageText - текст сообщения
# ----------------------------------
    # Инициализация данных
    userData     = GetUserData(chat_id)
    questCount   = userData.get("questCount")
    theme        = userData.get("theme")

    # Проверить состояние
    if userData.get("localBotState") != States.TEST:
        return

    # Проверить корректность ответа
    if not isCorrectAnswer(chat_id, request, messageText):
        return
    questCounter = userData["test"]["qCounter"]

    # Инициализация
    if not InitTest(chat_id):
        return

    # Проверить количество ответов
    if questCounter == questCount:
        send_message(chat_id, "Тест завершен!", json.dumps({'remove_keyboard':True}))
        ProcessCommand(chat_id, "/start")
        ResetQuestCounter(chat_id)
        UpdateServerUserData(chat_id, userData)
        UpdateLastTestDate(chat_id)
        userData["test"]["repeat"] = False
        return

    # Проверить количество изученных слов
    if not userData.get("test").get("repeat"):
        # Подсчитать количество изученных слов
        learningWords = userData.get("wordsStatus").get(theme.name)
        learnedThemeWordCount = 0
        for word in learningWords:
            if userData.get("wordsStatus").get(theme.name).get(word) >= userData.get("rightCount"):
                learnedThemeWordCount += 1
        themeWordCount = len(theme.dictionary)

        # Завершить тестирование
        if (learnedThemeWordCount == themeWordCount):
            send_message(chat_id, "Поздравляем! Вы выучили все слова текущей темы!", json.dumps({'remove_keyboard':True}))
            ProcessCommand(chat_id, "/start")
            ResetQuestCounter(chat_id)
            UpdateServerUserData(chat_id, userData)
            UpdateLastTestDate(chat_id)
            return

    # Выбрать случайное не изученное слово
    while True:
        themeWords = list(userData.get("theme").dictionary.keys())
        randomWord = themeWords[random.randint(0, len(themeWords) - 1)]
        if GetWordScore(chat_id, randomWord) < userData.get("rightCount"):
            userData["test"]["targetWord"] = randomWord
            break

    # Сформировать варианты ответа
    reply_markup = GenAnswersOptions(chat_id)

    # Задать вопрос
    send_message(chat_id,
                "Вопрос " + str(questCounter + 1) + "/" + str(questCount) +
                    ": Укажите верный перевод слова \"" + userData.get("test").get("targetWord") + "\"\n",
                json.dumps(reply_markup))

# Проверка ответов на корректность
def isCorrectAnswer(chat_id, request, messageText):
# ----------------------------------
#   Входные параметры:
#       chat_id     - идентификатор чата отправителя
#       request     - данные полученного сообщения
#       messageText - текст сообщения
#   Выходные параметры:
#       True  - корректный ответ
#       False - некорректный ответ
# ----------------------------------
    # Инициализация данных
    userData = GetUserData(chat_id)
    theme    = userData.get("theme")
    word     = userData.get("test").get("targetWord")

    # Обработать reply ответ
    if messageText == "Пример использования":
        send_message(chat_id, "Пример использования: " + theme.dictionary.get(word)["example"])
        return False
    if messageText == "Вернуться в меню":
        send_message(chat_id, "Вы досрочно завершили тест.", json.dumps({'remove_keyboard':True}))
        ProcessCommand(chat_id, "/start")
        ResetQuestCounter(chat_id)
        UpdateServerUserData(chat_id, userData)
        UpdateLastTestDate(chat_id)
        userData["test"]["repeat"] = False
        return False
    if messageText == "Начать тест" and userData.get("test").get("qCounter") == 0:
        return True

    # Обработать inline ответ
    answer = request.json.get("callback_query")
    if answer is not None:
        answer = answer["data"]
        messageText = ""
        if answer == "repeat":
            print("rep")
            return True
        if int(answer) == userData.get("test").get("targetIndex"):
            messageText = "Верно!"
            IncWordScore(chat_id, word)
        else:
            messageText = "Неверно :("
            ResetWordScore(chat_id, word)
        IncQuestCounter(chat_id)
        send_message(chat_id, messageText)
    else:
        return False

    return True

# Инициализация теста
def InitTest(chat_id):
# ----------------------------------
#   Входные параметры:
#       chat_id - идентификатор чата отправителя
#   Выходные параметры:
#       True  - успешная инициализация
#       False - безуспешная инициализация
# ----------------------------------
    # Инициализация данных
    userData = GetUserData(chat_id)
    theme    = userData.get("theme")

    # Проверка необходимости инициализации
    if userData.get("test").get("qCounter") != 0:
        return True

    # Сбросить счётчик вопросов
    ResetQuestCounter(chat_id)

    # Проверить количество изученных слов
    if not userData.get("test").get("repeat"):
        # Подсчитать количество изученных слов
        learningWords = userData.get("wordsStatus").get(theme.name)
        learnedThemeWordCount = 0
        for word in learningWords:
            if userData.get("wordsStatus").get(theme.name).get(word) >= userData.get("rightCount"):
                learnedThemeWordCount += 1
        themeWordCount        = len(theme.dictionary)

        # Завершить тестирование
        if (learnedThemeWordCount == themeWordCount):
            send_message(chat_id, "Вы уже выучили все слова этой темы.", json.dumps({'remove_keyboard':True}))
            ProcessCommand(chat_id, "/start")
            UpdateLastTestDate(chat_id)
            return False

    # Формирование Reply Keyboard
    replyKeyboard = [
                        [{
                                "text": "Пример использования",
                        }],
                        [{
                                "text": "Вернуться в меню",
                        }]
                    ]
    send_message(chat_id, "Начнём тест! Ваша тема: " + theme.name + ".", json.dumps({"keyboard": replyKeyboard}))
    return True

# Формирование вариантов ответа
def GenAnswersOptions(chat_id):
# ----------------------------------
#   Входные параметры:
#       chat_id - идентификатор чата отправителя
#   Выходные параметры:
#       reply_markup - данные inline-клавиатуры
# ----------------------------------
    # Инициализация данных
    userData     = GetUserData(chat_id)
    word         = userData.get("test").get("targetWord")
    theme        = userData.get("theme")
    themeWords   = list(theme.dictionary.keys())
    reply_markup = { "inline_keyboard": [[],[]] }
    userData["test"]["targetIndex"] = random.randint(0, answersCount - 1)

    # Сформировать ответы
    for i in range(answersCount):
        # Получить перевод слова для i-й ячейки
        translateText = ""
        if i == userData.get("test").get("targetIndex"):
            translateText = theme.dictionary.get(word)["translate"]
        else:
            randWord = word
            while randWord == word:
                randWord  = themeWords[random.randint(0, len(themeWords) - 1)]
            translateText = theme.dictionary.get(randWord)["translate"]

        # Добавить i-ю ячейку
        reply_markup["inline_keyboard"][int(i//(answersCount/2))].append({
                    "text": translateText,
                    "callback_data": i
        })
    return reply_markup
