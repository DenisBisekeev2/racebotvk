# [file name]: config.py
import os

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN', 'vk1.a.MTzBXxQQyLu72tOMdVYarZLJ3yOOmHXJ2d-MIyWIw55LLJnAryrh1ueQTmh7lsmNXYYyLaU8c59brz9S2gBZ1YK_5HYujr809X2mn7N8OlHwOGiIVOzRJJQ1f_9tjsCquwGdHcKKBQ94Bx1TjKl3hQOX0iLel_1FNwgJ7ycrrK2efdNyrdXlqb31SpXpFk_ChGJDWnLnU6moOlIsVKQvtA')
admins_ids = [819016396, 761815201]
# Вебхук настройки
CONFIRMATION_TOKEN = "f9691f4b"  # Токен из настроек Callback API
SECRET_KEY = "gonkaWow"  # Секретный ключ из настроек Callback API
GROUP_ID = 233724428

RACE_DISTANCE = 1000
GLOBAL_RACE_DISTANCE = 1500
MAX_PLAYERS = 10
MAX_PREMIUM_PLAYERS = 15
MIN_PLAYERS = 2
UPDATE_INTERVAL = 2
GLOBAL_RACE_TIMEOUT = 900

# Файлы базы данных
USERS_DB_FILE = 'users.json'
CHATS_DB_FILE = 'chats.json'
CARS_DB_FILE = 'cars.json'
GLOBAL_RACES_FILE = 'global_races.json'

# Награды за уровни
LEVEL_REWARD = 500