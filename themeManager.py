import json 

# Словарная тема
class WordTheme:
    # Конструктор
    def __init__(self, name, description, dictionary):
        self.name        = name        # Название
        self.description = description # Описание
        self.dictionary  = dictionary  # Словарь

    # Добавить слово в словарь
    def AddWord(self, word, translate, example):
        if self.dictionary.get(word) is None:
            self.dictionary.update({word: {"translate": translate, "example": example}})

# Менеджер словарных тем    
class ThemeManager:
    def __init__(self, jsonFile):
        # Инициализация полей
        self.themes = []

        # Загрузка содержимого из JSON-файла
        with open(jsonFile, "r", encoding='utf-8') as openedFile:
            data = json.load(openedFile)

        # Заполнить список тем
        for theme in data:
            newTheme = WordTheme(data[theme]["name"], data[theme]["description"], {})
            for wordInfo in data[theme]["dictionary"]:
                word      = wordInfo["word"]
                translate = wordInfo["translate"]
                example   = wordInfo["example"]
                newTheme.AddWord(word, translate, example)
            self.AddTheme(newTheme)

    # Получить тему по названию
    def GetThemeByName(self, themeName):
        for theme in self.themes:
            if theme.name == themeName:
                return theme
        return None

    # Добавить тему
    def AddTheme(self, theme):
        if self.GetThemeByName(theme.name) is None:
            self.themes.append(theme)

tManager = ThemeManager("Themes.json")
