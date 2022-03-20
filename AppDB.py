import psycopg2
from themeManager import tManager
import datetime

# Данные БД для подключения
mydb = psycopg2.connect(
    dbname   = "",
    user     = "",
    password = "",
    host     = ""
)

# Установка курсора БД
myCursor  = mydb.cursor()

# Получить телеграмм ID всех пользователей в БД 
def GetUsersTgID():
    # Получить ID всех пользователей из БД
    query = "SELECT TelegramID FROM Users;"
    myCursor.execute(query) 
    tgIDs = []
    for tgID in myCursor:
        tgIDs.append(int(tgID[0]))
    return tgIDs

# Добавить данные пользователя в БД
def InsertUserData(user_id, dictData):
# ----------------------------------
#   Входные параметры:
#       user_id  - идентификатор пользователя
#       dictData - словарь данных
# ----------------------------------
    # Проверить наличие записи в БД о пользователе
    if UserInDataBase(user_id):
        return

    # Добавить данные в таблицу User
    insertSQL = "INSERT INTO Users (TelegramID, QuestCount, RightCount, InstalledThemeName, LastTestDate, BotState)\
                VALUES(%s, %s, %s, %s, %s, %s) RETURNING id;"
    myCursor.execute(insertSQL, (
                                    str(user_id),
                                    dictData.get("questCount"),
                                    dictData.get("rightCount"),
                                    tManager.themes[0].name,
                                    dictData.get("lastTestDate"),
                                    int(dictData.get("localBotState")),
                                )
                     )
    userDB_ID = myCursor.fetchone()[0]
    mydb.commit()

    # Добавить данные в таблицу Learning
    myCursor.execute("SELECT * FROM Word;")
    subCursor = mydb.cursor()
    for word in myCursor:
        insertSQL = "INSERT INTO Learning (ID_User, ID_Word, Counter, UpdateDate) VALUES(%s, %s, %s, %s);"
        subCursor.execute(insertSQL, (
                                        userDB_ID,
                                        word[0],
                                        0,
                                        datetime.datetime.now(),
                                    )
                          )
    mydb.commit()

# Проверить наличие данных пользователя в БД
def UserInDataBase(user_id):
# ----------------------------------
#   Входные параметры:
#       user_id   - идентификатор пользователя
#   Выходные параметры:
#       True  - пользователь в БД
#       False - пользователя нет в БД
# ----------------------------------
    existCheck = "SELECT TelegramID FROM Users WHERE TelegramID = %s;"
    myCursor.execute(existCheck, (str(user_id), ))
    if myCursor.rowcount != 0:
        return True
    return False

# Обновить локальные пользовательские данные
def UpdateLocalUserData(user_id, localData):
# ----------------------------------
#   Входные параметры:
#       user_id   - идентификатор пользователя
#       localData - словарь локальных данных
# ----------------------------------
    # Запрос получения полной информации о пользователе в БД
    query = "\
        SELECT  Users.QuestCount,\
            Users.RightCount,\
            Users.InstalledThemeName,\
            Users.LastTestDate,\
            Users.BotState,\
            Word.Content,\
            Learning.Counter,\
            Learning.UpdateDate,\
            Theme.Name,\
            Users.Notifications\
        FROM Users\
            JOIN Learning\
              ON Learning.ID_User = Users.ID\
            JOIN Word\
              ON Word.ID = Learning.ID_Word\
            JOIN Theme\
              ON Theme.ID = Word.ID_Theme\
        WHERE Users.TelegramID = %s;\
    "
    myCursor.execute(query, (str(user_id),))

    # Заполнить основные пользователя поля в локальном словаре данных
    queryRows = myCursor.fetchall()
    localData["notifications"] = queryRows[0][9]
    localData["localBotState"] = queryRows[0][4]
    localData["lastTestDate"]  = queryRows[0][3]
    localData["theme"]         = tManager.GetThemeByName(queryRows[0][2])
    localData["rightCount"]    = queryRows[0][1]
    localData["questCount"]    = queryRows[0][0]

    # Заполнить данные изученных слов пользователя в локальном словаре данных
    for row in queryRows:
        # Получить значения столбцов
        word       = row[5]
        counter    = row[6]
        updateDate = row[7]
        themeName  = row[8]

        # Создать словарь темы
        if localData["wordsStatus"].get(themeName) is None:
            localData["wordsStatus"].update({themeName: {}})

        # Внести данные изучаемого слова
        localData["wordsStatus"][themeName].update({word: counter})

# Обновить пользовательские данные в БД
def UpdateServerUserData(user_id, localData):
# ----------------------------------
#   Входные параметры:
#       user_id   - идентификатор пользователя
#       localData - словарь локальных данных
# ----------------------------------
    # Инициализировать необходимые данные из локального словаря данных
    botState     = int(localData.get("localBotState"))
    lastTestDate = localData.get("lastTestDate")
    theme        = localData.get("theme").name
    rightCount   = localData.get("rightCount")
    questCount   = localData.get("questCount")
    notifs       = localData.get("notifications")

    # Обновить поля в таблице User
    updateSQL = "                   \
        UPDATE Users                 \
        SET QuestCount         = %s,\
            RightCount         = %s,\
            InstalledThemeName = %s,\
            LastTestDate       = %s,\
            BotState           = %s,\
            Notifications      = %s \
        WHERE TelegramID = %s;"
    myCursor.execute(updateSQL, ( 
                                    questCount,
                                    rightCount,
                                    theme,
                                    lastTestDate,
                                    botState,
                                    notifs,
                                    str(user_id),
                                )
                    )

    # Обновить данные изучаемых слов в таблице Learning
    for themeSection in localData.get("wordsStatus"): # По каждой теме
        for word in localData.get("wordsStatus").get(themeSection): # Для каждого слова в теме
            # Получить ID слова в БД
            query = "SELECT ID FROM Word WHERE Word.Content = %s;"
            myCursor.execute(query, (word,))
            wordID = myCursor.fetchone()[0]

            # Получить ID пользователя из БД
            myCursor.execute("SELECT ID FROM Users WHERE Users.TelegramID = %s;", (str(user_id),))
            userID = myCursor.fetchone()[0]

            # Обновить данные в таблице Learning
            updateSQL = "UPDATE Learning SET Counter = %s WHERE ID_User = %s AND ID_Word = %s;"
            counter   = localData.get("wordsStatus").get(themeSection).get(word)
            myCursor.execute(updateSQL, (counter, userID, wordID,))
    mydb.commit()

# Инициализировать данные словарных тем
def InitThemesData():
    for theme in tManager.themes: # По каждой теме
        # Получить данные темы из базы данных
        existCheck = "SELECT Name FROM Theme WHERE Name = %s;"
        myCursor.execute(existCheck, (theme.name,))

        # Проверить наличие данных темы в БД
        if myCursor.rowcount != 0:
            print("Тема \"" + theme.name + "\" уже добавлена.")
            continue

        # Добавить данные темы в таблицу Theme
        insertSQL = "INSERT INTO Theme (Name) VALUES(%s) RETURNING id;"
        myCursor.execute(insertSQL, (theme.name,))
        themeID = myCursor.fetchone()[0]
        mydb.commit()

        # Добавить слова темы в таблицу
        for word in theme.dictionary:
            insertSQL = "INSERT INTO Word (Content, ID_Theme) VALUES(%s, %s);"
            myCursor.execute(insertSQL, (word, themeID,))
        mydb.commit() 
