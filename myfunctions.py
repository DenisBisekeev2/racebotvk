# [file name]: myfunctions.py
from image_generator import RaceImageGenerator
from myclass import *
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import time
import random
import threading
from config import *

local_races = {}
drag_races = {}
global_races_waiting = {}
global_races_active = {}

def register_chat(message):
    """Регистрация чата в базе данных"""
    chats_data = load_data(CHATS_DB_FILE)

    if str(message.peer_id) not in chats_data.get('chats', {}):
        chats_data.setdefault('chats', {})[str(message.peer_id)] = {
            'title': message.chat_title or "Чат",
            'premium': False,
            'registered_date': datetime.datetime.now().isoformat(),
            'total_races': 0
        }
        save_data(chats_data, CHATS_DB_FILE)
        return True
    return False

def check_level_up(user):
    """Проверка и повышение уровня"""
    levels_gained = 0
    while user['exp'] >= 100:
        user['level'] += 1
        user['exp'] -= 100
        user['money'] += LEVEL_REWARD
        levels_gained += 1

    return levels_gained

def show_menu(message):
    # Регистрируем чат если это групповой чат
    if message.is_group_chat:
        register_chat(message)

    db = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in db.get('users', {}):
        return reg_user(message)

    user = db['users'][user_id]

    text = f"🏎️ ДОБРО ПОЖАЛОВАТЬ В ГОНОЧНЫЙ БОТ!\n\n"
    text += f"Здесь вы можете участвовать в захватывающих гонках, покупать машины и улучшать их!\n\n"
    text += f"💎 Ваш уровень: {user['level']}\n"
    text += f"📊 Опыт до следующего уровня: {user['exp']}/100\n"
    text += f"🚗 Машин в гараже: {len(user.get('cars', {}))}\n\n"
    text += f"Выберите раздел:"

    keyboard = VkKeyboard(inline=True)
    keyboard.add_button("🚗 Гараж", VkKeyboardColor.PRIMARY, payload={'cmd': 'garage'})
    keyboard.add_button("🏪 Автосалон", VkKeyboardColor.POSITIVE, payload={'cmd': 'cars_shop'})
    keyboard.add_line()
    keyboard.add_button("🔧 Техцентр", VkKeyboardColor.SECONDARY, payload={'cmd': 'service'})

    if message.is_private:
        keyboard.add_button("🎮 PvP Гонка", VkKeyboardColor.PRIMARY, payload={'cmd': 'pvp_race'})
        keyboard.add_button("🌍 Глобальные гонки", VkKeyboardColor.PRIMARY, payload={'cmd': 'global_races'})
    else:
        keyboard.add_button("🏎️ Создать гонку", VkKeyboardColor.PRIMARY, payload={'cmd': 'create_race'})

    message.reply(text, keyboard=keyboard.get_keyboard())

def show_garage(message):
    db = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in db.get('users', {}):
        return message.reply("❌ У вас нет аккаунта в боте! Напишите 'Начать' для регистрации.")

    user = db['users'][user_id]
    cars = user.get('cars', {})

    if not cars:
        return message.reply("❌ У вас нет машин! Посетите автосалон.")

    text = "🚗 ВАШ ГАРАЖ\n\n"
    for car_id, car_data in cars.items():
        active_indicator = " ✅" if user.get('active_car') == car_id else ""
        text += f"🏁 {car_data['name']}{active_indicator}\n"
        text += f"   💪 {format_number(car_data['hp'])} л.с. | 🚀 {format_number(car_data['max_speed'])} км/ч\n"
        text += f"   🛞 Шины: {car_data['tire_health']}% | 🛠️ Состояние: {car_data['durability']}%\n\n"

    keyboard = VkKeyboard(inline=True)
    keyboard.add_button("🏪 Автосалон", VkKeyboardColor.POSITIVE, payload={'cmd': 'cars_shop'})
    keyboard.add_button("🔧 Техцентр", VkKeyboardColor.SECONDARY, payload={'cmd': 'service'})
    keyboard.add_line()
    keyboard.add_button("📊 Выбрать машину", VkKeyboardColor.PRIMARY, payload={'cmd': 'select_car'})

    message.reply(text, keyboard=keyboard.get_keyboard(), attachment="photo-233724428_456239026")

def show_cars_shop(message):
    cars_data = load_data(CARS_DB_FILE)
    user_data = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь!")

    user = user_data['users'][user_id]

    text = "🏪 АВТОСАЛОН\n\n"
    text += f"💰 Ваш баланс: {format_number(user['money'])} руб.\n\n"

    cars_shop = cars_data.get('cars_shop', {})
    for car_id, car in cars_shop.items():
        text += f"🏁 {car['name']}\n"
        text += f"   💪 {format_number(car['hp'])} л.с. | 🚀 {format_number(car['max_speed'])} км/ч\n"
        text += f"   💰 Цена: {format_number(car['price'])} руб.\n\n"

    keyboard = VkKeyboard(inline=True)
    row_count = 0
    for car_id in cars_shop.keys():
        if row_count == 2:
            keyboard.add_line()
            row_count = 0
        keyboard.add_button(f"Купить {cars_shop[car_id]['name']}",
                           VkKeyboardColor.SECONDARY,
                           payload={'cmd': 'buy_car', 'car_id': car_id})
        row_count += 1

    if row_count > 0:
        keyboard.add_line()
    keyboard.add_button("🚗 Гараж", VkKeyboardColor.PRIMARY, payload={'cmd': 'garage'})

    message.reply(text, keyboard=keyboard.get_keyboard(), attachment="photo-233724428_456239025")

def buy_car(message, car_id):
    cars_data = load_data(CARS_DB_FILE)
    user_data = load_data(USERS_DB_FILE)

    user_id = str(message.from_id)
    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь!")

    user = user_data['users'][user_id]
    car = cars_data.get('cars_shop', {}).get(car_id)

    if not car:
        return message.reply("❌ Машина не найдена!")

    if user['money'] < car['price']:
        return message.reply(f"❌ Недостаточно денег! Нужно: {format_number(car['price'])} руб.")

    # Добавляем машину в гараж
    if 'cars' not in user:
        user['cars'] = {}

    new_car_id = str(len(user['cars']) + 1)
    user['cars'][new_car_id] = {
        'name': car['name'],
        'hp': car['hp'],
        'max_speed': car['max_speed'],
        'tire_health': car['tire_health'],
        'durability': car['durability'],
        'bought_date': datetime.datetime.now().isoformat()
    }

    user['money'] -= car['price']
    save_data(user_data, USERS_DB_FILE)

    message.reply(f"✅ Вы купили {car['name']} за {format_number(car['price'])} руб!")

def show_service(message):
    user_data = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь!")

    user = user_data['users'][user_id]

    if not user.get('cars'):
        return message.reply("❌ У вас нет машин!")

    # Находим активную машину
    active_car_id = user.get('active_car')
    cars = user.get('cars', {})

    if not active_car_id or active_car_id not in cars:
        active_car_id = list(cars.keys())[0]
        user['active_car'] = active_car_id
        save_data(user_data, USERS_DB_FILE)

    car = cars[active_car_id]

    text = f"🔧 ТЕХЦЕНТР - {car['name']}\n\n"
    text += f"🛞 Шины: {car['tire_health']}%\n"
    text += f"🛠️ Состояние: {car['durability']}%\n\n"
    text += "Услуги:\n"
    text += "🛞 Замена шин - 500 руб. (до 100%)\n"
    text += "🛠️ Ремонт кузова - 800 руб. (до 100%)\n"
    text += "💪 Улучшение двигателя - 2000 руб. (+10% л.с.)\n"
    text += "🚀 Улучшение скорости - 3000 руб. (+5% скорости)\n\n"
    text += f"💰 Ваш баланс: {format_number(user['money'])} руб."

    keyboard = VkKeyboard(inline=True)
    keyboard.add_button("🛞 Заменить шины", VkKeyboardColor.SECONDARY, payload={'cmd': 'repair_tires'})
    keyboard.add_button("🛠️ Починить кузов", VkKeyboardColor.SECONDARY, payload={'cmd': 'repair_body'})
    keyboard.add_line()
    keyboard.add_button("💪 Улучшить двигатель", VkKeyboardColor.PRIMARY, payload={'cmd': 'upgrade_engine'})
    keyboard.add_button("🚀 Улучшить скорость", VkKeyboardColor.PRIMARY, payload={'cmd': 'upgrade_speed'})
    keyboard.add_line()
    keyboard.add_button("🚗 Гараж", VkKeyboardColor.POSITIVE, payload={'cmd': 'garage'})

    message.reply(text, keyboard=keyboard.get_keyboard(), attachment="photo-233724428_456239024")

def repair_tires(message):
    user_data = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь!")

    user = user_data['users'][user_id]

    if not user.get('cars'):
        return message.reply("❌ У вас нет машин!")

    active_car_id = user.get('active_car')
    if not active_car_id or active_car_id not in user['cars']:
        return message.reply("❌ Сначала выберите активную машину!")

    car = user['cars'][active_car_id]

    if car['tire_health'] >= 100:
        return message.reply("❌ Шины и так в идеальном состоянии!")

    cost = 500
    if user['money'] < cost:
        return message.reply(f"❌ Недостаточно денег! Нужно: {cost} руб.")

    user['money'] -= cost
    car['tire_health'] = 100
    save_data(user_data, USERS_DB_FILE)

    message.reply(f"✅ Шины заменены! Состояние: 100% (-{cost} руб.)")

def repair_body(message):
    user_data = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь!")

    user = user_data['users'][user_id]

    if not user.get('cars'):
        return message.reply("❌ У вас нет машин!")

    active_car_id = user.get('active_car')
    if not active_car_id or active_car_id not in user['cars']:
        return message.reply("❌ Сначала выберите активную машину!")

    car = user['cars'][active_car_id]

    if car['durability'] >= 100:
        return message.reply("❌ Кузов и так в идеальном состоянии!")

    cost = 800
    if user['money'] < cost:
        return message.reply(f"❌ Недостаточно денег! Нужно: {cost} руб.")

    user['money'] -= cost
    car['durability'] = 100
    save_data(user_data, USERS_DB_FILE)

    message.reply(f"✅ Кузов отремонтирован! Состояние: 100% (-{cost} руб.)")

def upgrade_engine(message):
    user_data = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь!")

    user = user_data['users'][user_id]

    if not user.get('cars'):
        return message.reply("❌ У вас нет машин!")

    active_car_id = user.get('active_car')
    if not active_car_id or active_car_id not in user['cars']:
        return message.reply("❌ Сначала выберите активную машину!")

    car = user['cars'][active_car_id]

    cost = 2000
    if user['money'] < cost:
        return message.reply(f"❌ Недостаточно денег! Нужно: {cost} руб.")

    hp_increase = int(car['hp'] * 0.1)
    user['money'] -= cost
    car['hp'] += hp_increase
    save_data(user_data, USERS_DB_FILE)

    message.reply(f"✅ Двигатель улучшен! +{format_number(hp_increase)} л.с. (-{cost} руб.)")

def upgrade_speed(message):
    user_data = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь!")

    user = user_data['users'][user_id]

    if not user.get('cars'):
        return message.reply("❌ У вас нет машин!")

    active_car_id = user.get('active_car')
    if not active_car_id or active_car_id not in user['cars']:
        return message.reply("❌ Сначала выберите активную машину!")

    car = user['cars'][active_car_id]

    cost = 3000
    if user['money'] < cost:
        return message.reply(f"❌ Недостаточно денег! Нужно: {cost} руб.")

    speed_increase = int(car['max_speed'] * 0.05)
    user['money'] -= cost
    car['max_speed'] += speed_increase
    save_data(user_data, USERS_DB_FILE)

    message.reply(f"✅ Скорость улучшена! +{format_number(speed_increase)} км/ч (-{cost} руб.)")

def select_car(message):
    user_data = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь!")

    user = user_data['users'][user_id]
    cars = user.get('cars', {})

    if not cars:
        return message.reply("❌ У вас нет машин! Посетите автосалон.")

    text = "🚗 ВЫБЕРИТЕ АКТИВНУЮ МАШИНУ:\n\n"

    keyboard = VkKeyboard(inline=True)
    for i, (car_id, car_data) in enumerate(cars.items()):
        if i % 2 == 0 and i != 0:
            keyboard.add_line()

        is_active = user.get('active_car') == car_id
        button_color = VkKeyboardColor.POSITIVE if is_active else VkKeyboardColor.SECONDARY
        keyboard.add_button(f"{car_data['name']}{' ✅' if is_active else ''}",
                           button_color,
                           payload={'cmd': 'set_active_car', 'car_id': car_id})

        text += f"{'➤ ' if is_active else '  '}{car_data['name']} - {format_number(car_data['hp'])} л.с., {format_number(car_data['max_speed'])} км/ч\n"

    keyboard.add_line()
    keyboard.add_button("🚗 Гараж", VkKeyboardColor.PRIMARY, payload={'cmd': 'garage'})

    message.reply(text, keyboard=keyboard.get_keyboard())

def set_active_car(message, car_id):
    user_data = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь!")

    user = user_data['users'][user_id]

    if car_id not in user.get('cars', {}):
        return message.reply("❌ Машина не найдена!")

    user['active_car'] = car_id
    save_data(user_data, USERS_DB_FILE)

    car_name = user['cars'][car_id]['name']
    message.reply(f"✅ {car_name} теперь ваша активная машина!")

# СИСТЕМА ГОНОК
def show_races(message):
    if message.is_private:
        return show_global_races(message)

    db = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in db.get('users', {}):
        return message.reply("❌ У вас нет аккаунта в боте! Напишите 'Начать' для регистрации.")

    user = db['users'][user_id]

    if not user.get('cars'):
        return message.reply("❌ У вас нет машин! Сначала купите машину в автосалоне.")

    chat_id = str(message.peer_id)

    if chat_id in local_races:
        race = local_races[chat_id]
        return show_race_status(message, race)
    else:
        return create_race_menu(message)

def create_race_menu(message):
    text = "🏎️ ГОНКИ!\n\n"
    text += "Вы можете создать гонку в этом чате.\n"
    text += f"📍 Дистанция: {format_number(RACE_DISTANCE)}м\n"
    text += f"👥 Максимум игроков: {MAX_PLAYERS} (с Premium: {MAX_PREMIUM_PLAYERS})\n"
    text += f"🎯 Минимум для старта: {MIN_PLAYERS}\n\n"
    text += " - Выберите действие:"

    keyboard = VkKeyboard(inline=True)
    keyboard.add_button("➕ Создать гонку", VkKeyboardColor.POSITIVE, payload={'cmd': 'create_race'})

    message.reply(text, keyboard=keyboard.get_keyboard(), attachment="photo-233724428_456239020")

def create_race(message):
    chat_id = str(message.peer_id)

    if chat_id in local_races:
        return message.reply("❌ В этом чате уже есть активная гонка!")

    user_data = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь!")

    user = user_data['users'][user_id]

    if not user.get('cars'):
        return message.reply("❌ У вас нет машин! Сначала купите машину.")

    # Получаем активную машину
    active_car_id = user.get('active_car')
    cars = user.get('cars', {})

    if not active_car_id or active_car_id not in cars:
        active_car_id = list(cars.keys())[0]
        user['active_car'] = active_car_id
        save_data(user_data, USERS_DB_FILE)

    car_data = cars[active_car_id]

    # Создаем гонку
    race_id = f"local_{chat_id}_{int(time.time())}"
    race = Race(race_id, chat_id, message.from_id, is_global=False)

    # Добавляем создателя в гонку
    success, msg = race.add_player(message.from_id, user['username'], car_data)

    local_races[chat_id] = race

    # Отправляем сообщение о гонке
    race_text = race.get_race_info()
    keyboard = VkKeyboard(inline=True)
    keyboard.add_callback_button("✅ Присоединиться", VkKeyboardColor.POSITIVE, payload={'cmd': 'join_race'})
    keyboard.add_line()
    if message.from_id == race.creator_id:
        keyboard.add_button("🏁 Начать гонку", VkKeyboardColor.PRIMARY, payload={'cmd': 'start_race'})
    keyboard.add_callback_button("❌ Выйти", VkKeyboardColor.NEGATIVE, payload={'cmd': 'leave_race'})

    result = message.reply(race_text, keyboard=keyboard.get_keyboard(), attachment="photo-233724428_456239020")

    return True

def join_race(message):
    chat_id = str(message.peer_id)

    if chat_id not in local_races:
        return message.reply("❌ В этом чате нет активной гонка!")

    race = local_races[chat_id]
    user_data = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь!")

    user = user_data['users'][user_id]

    if not user.get('cars'):
        return message.reply("❌ У вас нет машин!")

    # Получаем активную машину
    active_car_id = user.get('active_car')
    cars = user.get('cars', {})

    if not active_car_id or active_car_id not in cars:
        active_car_id = list(cars.keys())[0]

    car_data = cars[active_car_id]

    success, msg = race.add_player(message.from_id, user['username'], car_data)

    if success:
        # Отправляем новое сообщение с обновленным списком игроков
        race_text = race.get_race_info()
        keyboard = VkKeyboard(inline=True)
        keyboard.add_callback_button("✅ Присоединиться", VkKeyboardColor.POSITIVE, payload={'cmd': 'join_race'})
        keyboard.add_line()
        if race.creator_id in race.players:
            keyboard.add_button("🏁 Начать гонку", VkKeyboardColor.PRIMARY, payload={'cmd': 'start_race'})
        keyboard.add_callback_button("❌ Выйти", VkKeyboardColor.NEGATIVE, payload={'cmd': 'leave_race'})
        message.reply(f"✅ {user['username']} присоединился к гонке!")
        message.reply(race_text, keyboard=keyboard.get_keyboard(), attachment="photo-233724428_456239020")

    else:
        message.reply(f"❌ {msg}")

def leave_race(message):
    chat_id = str(message.peer_id)

    if chat_id not in local_races:
        return message.reply("❌ В этом чате нет активной гонка!")

    race = local_races[chat_id]

    if message.from_id not in race.players:
        return message.reply("❌ Вы не участвуете в этой гонке!")

    player_name = race.players[message.from_id]['user_name']
    race.remove_player(message.from_id)

    # Если гонка пустая, удаляем её
    if not race.players:
        del local_races[chat_id]
        message.reply("✅ Гонка удалена, так как в ней не осталось участников.")
    else:
        # Отправляем новое сообщение с обновленным списком игроков
        race_text = race.get_race_info()
        keyboard = VkKeyboard(inline=True)
        keyboard.add_callback_button("✅ Присоединиться", VkKeyboardColor.POSITIVE, payload={'cmd': 'join_race'})
        keyboard.add_line()
        if race.creator_id in race.players:
            keyboard.add_button("🏁 Начать гонку", VkKeyboardColor.PRIMARY, payload={'cmd': 'start_race'})
        keyboard.add_callback_button("❌ Выйти", VkKeyboardColor.NEGATIVE, payload={'cmd': 'leave_race'})
        message.reply(f"✅ {player_name} вышел из гонки")
        message.reply(race_text, keyboard=keyboard.get_keyboard(), attachment="photo-233724428_456239020")


def start_race(message):
    chat_id = str(message.peer_id)

    if chat_id not in local_races:
        return message.reply("❌ В этом чате нет активной гонка!")

    race = local_races[chat_id]

    success, msg = race.start_race(message.from_id)

    if success:
        message.reply("🏁 ГОНКА НАЧАЛАСЬ! 🏁", attachment="photo-233724428_456239023")

        # Запускаем обновление гонки в отдельном потоке
        threading.Thread(target=run_race_updates, args=(message, race)).start()
    else:
        message.reply(f"❌ {msg}")

def show_race_status(message, race=None):
    if not race:
        chat_id = str(message.peer_id)
        if chat_id not in local_races:
            return message.reply("❌ В этом чате нет активной гонка!")
        race = local_races[chat_id]

    race_text = race.get_race_info()
    keyboard = VkKeyboard(inline=True)

    if race.status == "waiting":
        attachment = "photo-233724428_456239020"
        keyboard.add_callback_button("✅ Присоединиться", VkKeyboardColor.POSITIVE, payload={'cmd': 'join_race'})
        if message.from_id in race.players and message.from_id == race.creator_id:
            keyboard.add_button("🏁 Начать гонку", VkKeyboardColor.PRIMARY, payload={'cmd': 'start_race'})
        keyboard.add_line()
        keyboard.add_callback_button("❌ Выйти", VkKeyboardColor.NEGATIVE, payload={'cmd': 'leave_race'})
    elif race.status == "in_progress":
        attachment="photo-233724428_456239023"
        keyboard.add_button("🔄 Обновить", VkKeyboardColor.SECONDARY, payload={'cmd': 'race_status'})
    else:
        attachment="photo-233724428_456239020"
        keyboard.add_button("🏎️ Новая гонка", VkKeyboardColor.POSITIVE, payload={'cmd': 'create_race'})

    message.reply(race_text, keyboard=keyboard.get_keyboard(), attachment=attachment)

def run_race_updates(message, race):
    """Запуск обновлений гонки"""
    chat_id = str(message.peer_id)
    start_time = time.time()
    last_update_time = start_time

    while race.status == "in_progress" and chat_id in local_races and (time.time() - start_time) < 60:
        race_updated = race.update_race()

        # Отправляем обновление каждые 5 секунд или при завершении гонки
        current_time = time.time()
        if race_updated or (current_time - last_update_time) >= 5:
            race_text = race.get_race_info()
            message.reply(race_text)
            last_update_time = current_time

        if race_updated:
            break

        time.sleep(UPDATE_INTERVAL)

    # Гонка завершена
    if race.status == "finished" and chat_id in local_races:
        award_players(race)
        results_text = race.get_race_info()
        message.reply(results_text, attachment="photo-233724428_456239023")

        # Удаляем гонку через некоторое время
        time.sleep(10)
        if chat_id in local_races:
            del local_races[chat_id]

def award_players(race):
    """Выдача наград за гонку"""
    user_data = load_data(USERS_DB_FILE)

    for user_id, player in race.players.items():
        user_id_str = str(user_id)
        if user_id_str in user_data.get('users', {}):
            user = user_data['users'][user_id_str]

            # Награды в зависимости от позиции
            if player['position'] == 1:
                reward = 1000
                exp = 50
            elif player['position'] == 2:
                reward = 600
                exp = 30
            elif player['position'] == 3:
                reward = 300
                exp = 20
            else:
                reward = 100
                exp = 10

            user['money'] += reward
            user['exp'] += exp

            # Проверка повышения уровня
            levels_gained = check_level_up(user)
            if levels_gained > 0:
                user['money'] += levels_gained * LEVEL_REWARD

    save_data(user_data, USERS_DB_FILE)

# ДРАГ-РЕЙСИНГ
def handle_drag_race(message):
    """Обработка команды драг-рейсинга"""
    text = message.text.lower()
    parts = text.split()

    if len(parts) < 2:
        return message.reply("❌ Использование: драг [упоминание/@id]")

    target_text = parts[1]
    target_id = message.extract_user_id(target_text)

    if not target_id:
        return message.reply("❌ Не удалось определить пользователя! Укажите упоминание или ссылку.")

    if target_id == message.from_id:
        return message.reply("❌ Нельзя устраивать драг с самим собой!")

    # Проверяем, что оба игрока зарегистрированы
    user_data = load_data(USERS_DB_FILE)
    user_id_str = str(message.from_id)
    target_id_str = str(target_id)

    if user_id_str not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь в боте!")

    if target_id_str not in user_data.get('users', {}):
        return message.reply("❌ Этот пользователь не зарегистрирован в боте!")

    user = user_data['users'][user_id_str]
    target_user = user_data['users'][target_id_str]

    if not user.get('cars') or not target_user.get('cars'):
        return message.reply("❌ У кого-то из игроков нет машин!")

    # Создаем драг-рейсинг
    drag_id = f"drag_{message.peer_id}_{int(time.time())}"
    drag_race = DragRace(message.from_id, target_id, message.peer_id)

    # Добавляем игроков
    user_car = user['cars'].get(user.get('active_car')) or list(user['cars'].values())[0]
    target_car = target_user['cars'].get(target_user.get('active_car')) or list(target_user['cars'].values())[0]

    drag_race.add_player(message.from_id, user['username'], user_car)
    drag_race.add_player(target_id, target_user['username'], target_car)

    drag_races[drag_id] = drag_race

    # Отправляем сообщение о вызове
    challenge_text = f"🔥 ВЫЗОВ НА ДРАГ-РЕЙСИНГ! 🔥\n\n"
    challenge_text += f"{user['username']} вызывает {target_user['username']} на гонку!\n"
    challenge_text += f"📍 Дистанция: 400м\n\n"
    challenge_text += f"Готовы ли вы принять вызов?"

    keyboard = VkKeyboard(inline=True)
    keyboard.add_button("✅ Принять вызов", VkKeyboardColor.POSITIVE, payload={'cmd': 'accept_drag', 'drag_id': drag_id})
    keyboard.add_button("❌ Отклонить", VkKeyboardColor.NEGATIVE, payload={'cmd': 'decline_drag', 'drag_id': drag_id})

    message.reply(challenge_text, keyboard=keyboard.get_keyboard(), attachment="photo-233724428_456239021")

def accept_drag_race(message, drag_id):
    """Принять вызов на драг-рейсинг"""
    if drag_id not in drag_races:
        return message.reply("❌ Вызов не найден или устарел!")

    drag_race = drag_races[drag_id]

    if message.from_id != drag_race.player2_id:
        return message.reply("❌ Этот вызов не для вас!")

    # Начинаем драг-рейсинг
    drag_race.start_race()

    message.reply("🎯 ВЫЗОВ ПРИНЯТ! ДРАГ-РЕЙСИНГ НАЧИНАЕТСЯ! 🎯", attachment="photo-233724428_456239022")

    # Запускаем драг в отдельном потоке
    threading.Thread(target=run_drag_race, args=(message, drag_race, drag_id)).start()

def run_drag_race(message, drag_race, drag_id):
    """Запуск драг-рейсинга с обновлениями раз в 10 секунд"""
    start_time = time.time()
    last_update_time = start_time

    while drag_race.status == "in_progress" and (time.time() - start_time) < 15:
        finished = drag_race.update_race()

        # Отправляем обновление только раз в 10 секунд или при финише
        current_time = time.time()
        if finished or (current_time - last_update_time) >= 10:
            race_text = drag_race.get_race_info()
            message.reply(race_text)
            last_update_time = current_time

        if finished:
            break

        time.sleep(0.5)  # небольшая пауза между обновлениями состояния

    # Завершаем драг
    if drag_race.status == "in_progress":
        drag_race.status = "finished"
        # Принудительно завершаем гонку и определяем победителя по прогрессу
        max_progress = 0
        winner_id = None
        for user_id, player in drag_race.players.items():
            if player['progress'] > max_progress:
                max_progress = player['progress']
                winner_id = user_id

    # Определяем победителя
    winner_id = drag_race.get_winner()
    if not winner_id:
        # Если нет победителя по времени, выбираем по прогрессу
        max_progress = 0
        for user_id, player in drag_race.players.items():
            if player['progress'] > max_progress:
                max_progress = player['progress']
                winner_id = user_id

    if winner_id:
        winner_name = drag_race.players[winner_id]['user_name']
        message.reply(f"🏆 ПОБЕДИТЕЛЬ: {winner_name}!")

        # Награждаем победителя
        user_data = load_data(USERS_DB_FILE)
        if str(winner_id) in user_data.get('users', {}):
            user = user_data['users'][str(winner_id)]
            user['money'] += 500
            user['exp'] += 25
            save_data(user_data, USERS_DB_FILE)

    # Удаляем драг из активных
    if drag_id in drag_races:
        del drag_races[drag_id]

# ГЛОБАЛЬНЫЕ ГОНКИ
def show_global_races(message):
    text = "🌍 ГЛОБАЛЬНЫЕ ГОНКИ\n\n"
    text += f"📍 Дистанция: {format_number(GLOBAL_RACE_DISTANCE)}м\n"
    text += f"⏰ Время ожидания: 15 минут\n"
    text += f"👥 Минимум игроков: {MIN_PLAYERS}\n"
    text += f"💰 Награды в 2 раза выше!\n\n"
    text += "Присоединяйтесь к гонке и соревнуйтесь с игроками со всей сети!"

    keyboard = VkKeyboard(inline=True)
    keyboard.add_button("🎮 Найти гонку", VkKeyboardColor.POSITIVE, payload={'cmd': 'find_global_race'})
    keyboard.add_line()
    keyboard.add_button("📊 Мои результаты", VkKeyboardColor.PRIMARY, payload={'cmd': 'my_results'})

    message.reply(text, keyboard=keyboard.get_keyboard())

def find_global_race(message):
    message.reply("🌍 Система глобальных гонок находится в разработке. Скоро будет доступна!")

def my_results(message):
    user_data = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь!")

    user = user_data['users'][user_id]

    text = f"📊 СТАТИСТИКА ИГРОКА\n\n"
    text += f"👤 {user['username']}\n"
    text += f"💰 Баланс: {format_number(user['money'])} руб.\n"
    text += f"⭐ Уровень: {user['level']}\n"
    text += f"📈 Опыт: {user['exp']}/100\n"
    text += f"🚗 Машин в гараже: {len(user.get('cars', {}))}\n\n"

    text += "🏆 Статистика:\n"
    text += "• Побед: в разработке\n"
    text += "• Участий: в разработке\n"

    message.reply(text)

# ОСНОВНЫЕ ФУНКЦИИ
def reg_user(message):
    db = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id in db.get('users', {}):
        message.reply("❌ Вы уже зарегистрированы в боте!")
        show_menu(message)
        return

    if message.is_group_chat:
        return message.reply("❌ Регистрация в боте возможна только в лс бота.")
    if message.isMember(user_id=user_id) == False:
        return message.reply("🙃 Регистрация в боте невозможна, если вы не подписаны на него!")

    db.setdefault('users', {})[user_id] = {
        'username': message.full_name,
        'money': 5000,
        'exp': 0,
        'level': 1,
        'cars': {},
        'active_car': None,
        'referral_code': f"ref_{user_id}",
        'referred_by': None,
        'pistons': 0
    }

    save_data(db, USERS_DB_FILE)
    keyboard = VkKeyboard(inline=True)
    keyboard.add_openlink_button("📚 Правила бота", "https://vk.com/@gonka_bot-rules")
    keyboard.add_line()
    keyboard.add_vkapps_button(
        app_id=6441755,
        owner_id=-233724428,
        label="➕ Добавить в чат",
        hash=""
    )

    message.reply(f"😁 Отлично, {message.get_mention(message.from_id)}, регистрация прошла успешно!\n\n🎮 Теперь вы можете участвовать в гонках и покупать машины!\n\n⚠️ Чтобы начать участвовать в гонках, купите первую машину, написав: автосалон", keyboard=keyboard.get_keyboard())

def show_commands(message):
    db = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)

    if user_id not in db.get('users', {}):
        return message.reply("❌ У вас нет аккаунта в боте! Напишите 'Начать' для регистрации.")

    text = f"📚 Привет, {message.get_mention(message.from_id)}, вот все команды бота:\n\n"
    text += f"🏎️ ОСНОВНЫЕ КОМАНДЫ:\n"
    text += f"- Меню - главное меню бота\n"
    text += f"- Помощь - показать команды\n"
    text += f"- Гонка - меню гонок\n"
    text += f"- Поддержка - поддержка бота\n\n"

    text += f"🚗 АВТОМОБИЛИ:\n"
    text += f"- Гараж - ваши машины\n"
    text += f"- Автосалон - купить машину\n"
    text += f"- Техцентр - улучшить машину\n\n"

    text += f"🎮 В ЧАТАХ:\n"
    text += f"- Гонка - создать/присоединиться к гонке\n"
    text += f"- Старт - начать гонку\n"
    text += f"- Драг [@игрок] - вызвать на драг-рейсинг\n\n"

    text += f"🙂 Команды будут добавляться, следите за новостями!"
    message.reply(text)

def welcome_message(message):
    text = "🏎️ Добро пожаловать в Гонки Бот!\n\n"
    text += "Я помогу вам организовать захватывающие гоночные соревнования!\n\n"
    text += "📋 Основные команды:\n"
    text += "• 'Гонка' - создать/присоединиться к гонке\n"
    text += "• 'Меню' - показать главное меню\n"
    text += "• 'Помощь' - список всех команд\n"
    text += "• 'Драг @игрок' - вызвать на драг-рейсинг\n\n"
    text += "🚀 Чтобы начать, напишите 'Гонка' и создайте свою первую гонку!"

    message.reply(text)

def admin_add_premium(message, chat_id):
    db = load_data(CHATS_DB_FILE)
    if str(chat_id) not in db.get('chats', {}):
        return message.reply("⚠️ Этого чата нет в базе данных!")
    chat = db['chats'][str(chat_id)]
    if chat['premium'] != False:
        return message.reply("⚠️ У этого чата уже есть Premium")
    chat['premium'] = True
    save_data(db, CHATS_DB_FILE)
    message.reply("✅ Успешно!")
# Добавляем в начало файла с другими глобальными переменными
klans_data = {}

def load_klans_data():
    """Загрузка данных кланов"""
    global klans_data
    try:
        with open('klans.json', 'r', encoding='utf-8') as f:
            klans_data = json.load(f)
    except FileNotFoundError:
        klans_data = {"klans": {}, "klan_battles": {}, "next_klan_id": 1}
        save_klans_data()

def save_klans_data():
    """Сохранение данных кланов"""
    with open('klans.json', 'w', encoding='utf-8') as f:
        json.dump(klans_data, f, ensure_ascii=False, indent=2)

# Вызываем при старте
load_klans_data()

def handle_klan_command(message, args=None):
    """Обработка команд кланов"""
    if not args:
        return show_klan_menu(message)

    command = args[0].lower()

    if command == "создать":
        create_klan(message, args[1:])
    elif command == "удалить":
        delete_klan(message)
    elif command == "приглос":
        invite_to_klan(message, args[1:])
    elif command == "кик":
        kick_from_klan(message, args[1:])
    elif command == "гонка":
        start_klan_battle(message)
    elif command == "инфо":
        show_klan_info(message)
    elif command == "выйти":
        leave_klan(message)
    elif command == "принять":
        accept_klan_invite(message, args[1:])
    elif command == "отклонить":
        decline_klan_invite(message, args[1:]) #type: ignor
    else:
        show_klan_menu(message)

def show_klan_menu(message):
    """Показать меню кланов"""
    text = "🏆 СИСТЕМА КЛАНОВ\n\n"
    text += "Объединяйтесь с друзьями и соревнуйтесь с другими кланами!\n\n"
    text += "📋 Команды кланов:\n"
    text += "• клан создать [название] [тег] - создать клан\n"
    text += "• клан инфо - информация о вашем клане\n"
    text += "• клан приглос [@игрок] - пригласить в клан\n"
    text += "• клан кик [@игрок] - исключить из клана\n"
    text += "• клан гонка - начать битву кланов\n"
    text += "• клан выйти - покинуть клан\n"
    text += "• клан удалить - удалить клан (только лидер)\n\n"
    text += "👥 Максимум участников: 15\n"
    text += "⚔️ Битвы: гонка 5 на 5"

    user_klan = get_user_klan(message.from_id)
    if user_klan:
        klan_info = klans_data['klans'][user_klan]
        text += f"\n\n🏁 Ваш клан: {klan_info['name']} [{klan_info['tag']}]"

    keyboard = VkKeyboard(inline=True)

    if not user_klan:
        keyboard.add_button("🏆 Создать клан", VkKeyboardColor.POSITIVE,
                          payload={'cmd': 'klan_create_menu'})
        keyboard.add_line()
    else:
        keyboard.add_button("📊 Инфо о клане", VkKeyboardColor.PRIMARY,
                          payload={'cmd': 'klan_info'})
        keyboard.add_button("👥 Участники", VkKeyboardColor.PRIMARY,
                          payload={'cmd': 'klan_members'})
        keyboard.add_line()
        keyboard.add_button("⚔️ Битва кланов", VkKeyboardColor.NEGATIVE,
                          payload={'cmd': 'klan_battle'})

    keyboard.add_button("🏆 Топ кланов", VkKeyboardColor.SECONDARY,
                      payload={'cmd': 'klan_top'})

    message.reply(text, keyboard=keyboard.get_keyboard())

def create_klan(message, args):
    """Создание клана"""
    user_id = str(message.from_id)

    # Проверяем, не состоит ли уже в клане
    if get_user_klan(message.from_id):
        return message.reply("❌ Вы уже состоите в клане!")

    # Проверяем аргументы
    if len(args) < 2:
        return message.reply("❌ Использование: клан создать [название] [тег]\nПример: клан создать ГонщикиПро GP")

    name = args[0]
    tag = args[1].upper()

    # Проверяем длину названия и тега
    if len(name) > 20:
        return message.reply("❌ Название клана не должно превышать 20 символов!")

    if len(tag) > 5:
        return message.reply("❌ Тег клана не должен превышать 5 символов!")

    # Проверяем уникальность названия и тега
    for klan_id, klan in klans_data['klans'].items():
        if klan['name'].lower() == name.lower():
            return message.reply("❌ Клан с таким названием уже существует!")
        if klan['tag'].upper() == tag.upper():
            return message.reply("❌ Клан с таким тегом уже существует!")

    # Создаем клан
    klan_id = str(klans_data['next_klan_id'])
    klans_data['next_klan_id'] += 1

    user_data = load_data(USERS_DB_FILE)
    username = user_data['users'][user_id]['username']

    klans_data['klans'][klan_id] = {
        "name": name,
        "tag": tag,
        "creator_id": message.from_id,
        "members": {
            user_id: {
                "username": username,
                "role": "leader",
                "join_date": datetime.datetime.now().isoformat()
            }
        },
        "created_date": datetime.datetime.now().isoformat(),
        "level": 1,
        "exp": 0,
        "wins": 0,
        "losses": 0,
        "description": "Новый гоночный клан"
    }

    save_klans_data()

    message.reply(f"✅ Клан '{name}' [{tag}] успешно создан!\nИспользуйте 'клан приглос [@игрок]' чтобы пригласить друзей.")

def get_user_klan(user_id):
    """Получить ID клана пользователя"""
    user_id_str = str(user_id)
    for klan_id, klan in klans_data['klans'].items():
        if user_id_str in klan['members']:
            return klan_id
    return None

def show_klan_info(message):
    """Показать информацию о клане"""
    klan_id = get_user_klan(message.from_id)

    if not klan_id:
        return message.reply("❌ Вы не состоите в клане!")

    klan = klans_data['klans'][klan_id]

    text = f"🏆 ИНФОРМАЦИЯ О КЛАНЕ\n\n"
    text += f"🏁 Название: {klan['name']} [{klan['tag']}]\n"
    text += f"⭐ Уровень: {klan['level']}\n"
    text += f"📊 Опыт: {format_number(klan['exp'])}\n"
    text += f"👥 Участников: {len(klan['members'])}/15\n"
    text += f"⚔️ Побед/Поражений: {klan['wins']}/{klan['losses']}\n"
    text += f"📝 Описание: {klan['description']}\n\n"

    # Сортируем участников по роли
    leaders = []
    members = []

    for member_id, member_data in klan['members'].items():
        if member_data['role'] == 'leader':
            leaders.append(member_data['username'])
        else:
            members.append(member_data['username'])

    text += "👑 Лидеры:\n"
    for leader in leaders:
        text += f"• {leader}\n"

    if members:
        text += "\n👥 Участники:\n"
        for member in members:
            text += f"• {member}\n"

    keyboard = VkKeyboard(inline=True)
    keyboard.add_button("👥 Участники", VkKeyboardColor.PRIMARY, payload={'cmd': 'klan_members'})
    keyboard.add_button("⚔️ Битва", VkKeyboardColor.NEGATIVE, payload={'cmd': 'klan_battle'})
    keyboard.add_line()
    keyboard.add_button("📤 Пригласить", VkKeyboardColor.POSITIVE, payload={'cmd': 'klan_invite_menu'})

    message.reply(text, keyboard=keyboard.get_keyboard())

def invite_to_klan(message, args):
    """Пригласить пользователя в клан"""
    klan_id = get_user_klan(message.from_id)

    if not klan_id:
        return message.reply("❌ Вы не состоите в клане!")

    klan = klans_data['klans'][klan_id]

    # Проверяем права
    user_id_str = str(message.from_id)
    if klan['members'][user_id_str]['role'] != 'leader':
        return message.reply("❌ Только лидеры клана могут приглашать игроков!")

    # Проверяем лимит участников
    if len(klan['members']) >= 15:
        return message.reply("❌ В клане достигнут лимит участников (15)!")

    if not args:
        return message.reply("❌ Укажите пользователя для приглашения!\nПример: клан приглос @username")

    target_text = args[0]
    target_id = message.extract_user_id(target_text)

    if not target_id:
        return message.reply("❌ Не удалось определить пользователя!")

    if target_id == message.from_id:
        return message.reply("❌ Нельзя пригласить самого себя!")

    # Проверяем, не состоит ли уже в клане
    if get_user_klan(target_id):
        return message.reply("❌ Этот пользователь уже состоит в клане!")

    # Проверяем, что пользователь зарегистрирован в боте
    user_data = load_data(USERS_DB_FILE)
    if str(target_id) not in user_data.get('users', {}):
        return message.reply("❌ Этот пользователь не зарегистрирован в боте!")

    # Создаем приглашение
    invite_id = f"{klan_id}_{target_id}"

    keyboard = VkKeyboard(inline=True)
    keyboard.add_button("✅ Принять", VkKeyboardColor.POSITIVE,
                       payload={'cmd': 'klan_accept', 'invite_id': invite_id})
    keyboard.add_button("❌ Отклонить", VkKeyboardColor.NEGATIVE,
                       payload={'cmd': 'klan_decline', 'invite_id': invite_id})

    target_user_data = user_data['users'][str(target_id)]
    inviter_name = klan['members'][str(message.from_id)]['username']

    # Отправляем приглашение целевому пользователю
    try:
        invite_text = f"🎯 ПРИГЛАШЕНИЕ В КЛАН!\n\n"
        invite_text += f"{inviter_name} приглашает вас в клан {klan['name']} [{klan['tag']}]\n\n"
        invite_text += f"📊 Информация о клане:\n"
        invite_text += f"• Уровень: {klan['level']}\n"
        invite_text += f"• Участников: {len(klan['members'])}/15\n"
        invite_text += f"• Побед: {klan['wins']}\n\n"
        invite_text += f"Примите приглашение чтобы присоединиться!"

        message.reply(invite_text, keyboard=keyboard.get_keyboard(), peer_id=target_id)
        message.reply(f"✅ Приглашение отправлено {target_user_data['username']}!")
    except Exception as e:
        message.reply("❌ Не удалось отправить приглашение. Возможно, пользователь заблокировал бота.")

def accept_klan_invite(message, args):
    """Принять приглашение в клан"""
    user_id = str(message.from_id)

    if get_user_klan(message.from_id):
        return message.reply("❌ Вы уже состоите в клане!")

    if not args:
        return message.reply("❌ Не указан ID приглашения!")

    invite_id = args[0]
    parts = invite_id.split('_')

    if len(parts) != 2:
        return message.reply("❌ Неверный формат приглашения!")

    klan_id, target_id = parts

    if str(message.from_id) != target_id:
        return message.reply("❌ Это приглашение не для вас!")

    if klan_id not in klans_data['klans']:
        return message.reply("❌ Клан больше не существует!")

    klan = klans_data['klans'][klan_id]

    # Проверяем лимит участников
    if len(klan['members']) >= 15:
        return message.reply("❌ В клане достигнут лимит участников!")

    # Добавляем в клан
    user_data = load_data(USERS_DB_FILE)
    username = user_data['users'][user_id]['username']

    klan['members'][user_id] = {
        "username": username,
        "role": "member",
        "join_date": datetime.datetime.now().isoformat()
    }

    save_klans_data()

    message.reply(f"✅ Вы присоединились к клану {klan['name']} [{klan['tag']}]!")

    # Уведомляем лидеров клана
    for member_id, member_data in klan['members'].items():
        if member_data['role'] == 'leader' and int(member_id) != message.from_id:
            try:
                message.reply(f"🎉 {username} присоединился к вашему клану!", peer_id=int(member_id))
            except:
                pass

def kick_from_klan(message, args):
    """Исключить пользователя из клана"""
    klan_id = get_user_klan(message.from_id)

    if not klan_id:
        return message.reply("❌ Вы не состоите в клане!")

    klan = klans_data['klans'][klan_id]
    user_id_str = str(message.from_id)

    # Проверяем права
    if klan['members'][user_id_str]['role'] != 'leader':
        return message.reply("❌ Только лидеры клана могут исключать игроков!")

    if not args:
        return message.reply("❌ Укажите пользователя для исключения!\nПример: клан кик @username")

    target_text = args[0]
    target_id = message.extract_user_id(target_text)

    if not target_id:
        return message.reply("❌ Не удалось определить пользователя!")

    target_id_str = str(target_id)

    if target_id == message.from_id:
        return message.reply("❌ Нельзя исключить самого себя!")

    if target_id_str not in klan['members']:
        return message.reply("❌ Этот пользователь не состоит в вашем клане!")

    # Исключаем
    kicked_name = klan['members'][target_id_str]['username']
    del klan['members'][target_id_str]

    save_klans_data()

    message.reply(f"✅ {kicked_name} исключен из клана!")

    # Уведомляем исключенного
    try:
        message.reply(f"❌ Вы были исключены из клана {klan['name']} [{klan['tag']}]!", peer_id=target_id)
    except:
        pass

def start_klan_battle(message):
    """Начать битву кланов"""
    klan_id = get_user_klan(message.from_id)

    if not klan_id:
        return message.reply("❌ Вы не состоите в клане!")

    klan = klans_data['klans'][klan_id]

    # Проверяем количество участников
    if len(klan['members']) < 5:
        return message.reply("❌ Для битвы кланов нужно минимум 5 участников в клане!")

    # Ищем случайного противника
    available_klans = []
    for other_klan_id, other_klan in klans_data['klans'].items():
        if (other_klan_id != klan_id and
            len(other_klan['members']) >= 5 and
            other_klan_id not in klans_data.get('klan_battles', {})):
            available_klans.append((other_klan_id, other_klan))

    if not available_klans:
        return message.reply("❌ Нет доступных кланов для битвы! Попробуйте позже.")

    # Выбираем случайного противника
    opponent_klan_id, opponent_klan = random.choice(available_klans)

    # Создаем битву
    battle_id = f"{klan_id}_{opponent_klan_id}_{int(time.time())}"

    klans_data.setdefault('klan_battles', {})[battle_id] = {
        "klan1_id": klan_id,
        "klan2_id": opponent_klan_id,
        "status": "waiting",
        "created_time": time.time(),
        "players": {},
        "results": {}
    }

    save_klans_data()

    text = f"⚔️ БИТВА КЛАНОВ НАЧАЛАСЬ!\n\n"
    text += f"🏁 {klan['name']} [{klan['tag']}] vs {opponent_klan['name']} [{opponent_klan['tag']}]\n\n"
    text += f"Участники, присоединяйтесь к битве!\n"
    text += f"Напишите 'битва присоединиться {battle_id}'"

    # Уведомляем оба клана
    for member_id in klan['members']:
        try:
            message.reply(text, peer_id=int(member_id))
        except:
            pass

    for member_id in opponent_klan['members']:
        try:
            message.reply(text, peer_id=int(member_id))
        except:
            pass

    message.reply(f"✅ Битва кланов создана! Ожидаем участников...")

def leave_klan(message):
    """Покинуть клан"""
    klan_id = get_user_klan(message.from_id)

    if not klan_id:
        return message.reply("❌ Вы не состоите в клане!")

    klan = klans_data['klans'][klan_id]
    user_id_str = str(message.from_id)

    # Проверяем, не лидер ли
    if klan['members'][user_id_str]['role'] == 'leader':
        return message.reply("❌ Лидер не может покинуть клан! Сначала передайте лидерство или удалите клан.")

    # Покидаем клан
    username = klan['members'][user_id_str]['username']
    del klan['members'][user_id_str]

    # Если в клане не осталось участников, удаляем его
    if not klan['members']:
        del klans_data['klans'][klan_id]

    save_klans_data()

    message.reply(f"✅ Вы покинули клан {klan['name']} [{klan['tag']}]!")

def delete_klan(message):
    """Удалить клан"""
    klan_id = get_user_klan(message.from_id)

    if not klan_id:
        return message.reply("❌ Вы не состоите в клане!")

    klan = klans_data['klans'][klan_id]
    user_id_str = str(message.from_id)

    # Проверяем права
    if klan['members'][user_id_str]['role'] != 'leader':
        return message.reply("❌ Только лидер может удалить клан!")

    # Удаляем клан
    klan_name = klan['name']
    klan_tag = klan['tag']

    # Уведомляем всех участников
    for member_id in klan['members']:
        if int(member_id) != message.from_id:
            try:
                message.reply(f"❌ Клан {klan_name} [{klan_tag}] был удален лидером!",
                            peer_id=int(member_id))
            except:
                pass

    del klans_data['klans'][klan_id]
    save_klans_data()

    message.reply(f"✅ Клан {klan_name} [{klan_tag}] удален!")
def show_klan_members(message):
    """Показать участников клана"""
    klan_id = get_user_klan(message.from_id)

    if not klan_id:
        return message.reply("❌ Вы не состоите в клане!")

    klan = klans_data['klans'][klan_id]

    text = f"👥 УЧАСТНИКИ КЛАНА {klan['name']} [{klan['tag']}]\n\n"

    leaders = []
    members = []

    for member_id, member_data in klan['members'].items():
        join_date = datetime.datetime.fromisoformat(member_data['join_date'])
        days_in_klan = (datetime.datetime.now() - join_date).days

        member_info = f"{member_data['username']} ({days_in_klan}д.)"

        if member_data['role'] == 'leader':
            leaders.append("👑 " + member_info)
        else:
            members.append("👤 " + member_info)

    text += "👑 Лидеры:\n" + "\n".join(leaders) + "\n\n"
    text += "👤 Участники:\n" + "\n".join(members)

    message.reply(text)

def show_klan_top(message):
    """Показать топ кланов"""
    # Сортируем кланы по опыту
    sorted_klans = sorted(klans_data['klans'].values(),
                         key=lambda x: x['exp'], reverse=True)[:10]

    text = "🏆 ТОП КЛАНОВ\n\n"

    for i, klan in enumerate(sorted_klans, 1):
        if i == 1:
            place = "🥇"
        elif i == 2:
            place = "🥈"
        elif i == 3:
            place = "🥉"
        else:
            place = f"{i}."

        win_rate = klan['wins'] / (klan['wins'] + klan['losses']) * 100 if (klan['wins'] + klan['losses']) > 0 else 0

        text += f"{place} {klan['name']} [{klan['tag']}]\n"
        text += f"   ⭐ Ур. {klan['level']} | 📊 {format_number(klan['exp'])} опыта\n"
        text += f"   ⚔️ {klan['wins']}-{klan['losses']} ({win_rate:.1f}% побед)\n"
        text += f"   👥 {len(klan['members'])}/15 участников\n\n"

    message.reply(text)

def create_race_visualization(race):
    """Создать визуализацию гонки с цветами машин"""
    players_with_colors = race.get_players_with_colors()
    track_length = 20  # Длина трека в символах

    visualization = "🏁 ГОНОЧНЫЙ ТРЕК 🏁\n\n"

    # Сортируем игроков по прогрессу
    sorted_players = sorted(players_with_colors.items(),
                          key=lambda x: x[1]['progress'],
                          reverse=True)

    for i, (user_id, player) in enumerate(sorted_players):
        progress_percent = min(100, int(player['progress'] / race.distance * 100))
        car_position = min(track_length - 1, int((player['progress'] / race.distance) * track_length))

        # Создаем трек с машиной
        track = "─" * track_length
        if car_position < track_length:
            # Используем эмодзи машины с учетом цвета (в тексте цвет не отображается, но можно использовать для веб-версии)
            track = track[:car_position] + "🚗" + track[car_position+1:]

        status = "🏁 ФИНИШ!" if player['finished'] else f"{progress_percent}%"

        visualization += f"{i+1}. {player['user_name']}\n"
        visualization += f"   {track}\n"
        visualization += f"   {status}\n\n"

    return visualization
def unknow_command(message):
    if message.is_private:
        show_menu(message)

# Добавляем в myfunctions.py глобальные переменные
pvp_waiting_players = {}  # {user_id: player_data}
pvp_active_races = {}     # {race_id: PvPRace object}

# Добавляем новые функции в myfunctions.py

def start_pvp_race(message):
    """Начать поиск PvP гонки"""
    user_data = load_data(USERS_DB_FILE)
    user_id = str(message.from_id)
    
    if user_id not in user_data.get('users', {}):
        return message.reply("❌ Сначала зарегистрируйтесь в боте!")
    
    user = user_data['users'][user_id]
    
    if not user.get('cars'):
        return message.reply("❌ У вас нет машин! Сначала купите машину.")
    
    # Проверяем, не ищет ли уже пользователь гонку
    if message.from_id in pvp_waiting_players:
        return message.reply("🔍 Вы уже ищете противника...")
    
    # Получаем активную машину
    active_car_id = user.get('active_car')
    cars = user.get('cars', {})
    
    if not active_car_id or active_car_id not in cars:
        active_car_id = list(cars.keys())[0]
    
    car_data = cars[active_car_id]
    
    # Добавляем в очередь ожидания
    pvp_waiting_players[message.from_id] = {
        'user_name': user['username'],
        'car_data': car_data,
        'search_start_time': time.time(),
        'message': message
    }
    
    message.reply("🔍 Ищем противника для PvP гонки...")
    
    # Запускаем поиск противника
    threading.Thread(target=find_pvp_opponent, args=(message.from_id,)).start()

def find_pvp_opponent(player_id):
    """Найти противника для PvP гонки"""
    max_wait_time = 30  # максимальное время ожидания в секундах
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        # Ищем случайного противника из ожидающих
        waiting_players = list(pvp_waiting_players.keys())
        
        if len(waiting_players) >= 2:
            # Ищем другого игрока (не себя)
            potential_opponents = [p for p in waiting_players if p != player_id]
            
            if potential_opponents:
                opponent_id = random.choice(potential_opponents)
                
                # Создаем гонку
                race_id = f"pvp_{player_id}_{opponent_id}_{int(time.time())}"
                pvp_race = PvPRace(race_id, player_id, opponent_id)
                
                # Добавляем игроков в гонку
                player_data = pvp_waiting_players[player_id]
                opponent_data = pvp_waiting_players[opponent_id]
                
                pvp_race.add_player(player_id, player_data['user_name'], player_data['car_data'])
                pvp_race.add_player(opponent_id, opponent_data['user_name'], opponent_data['car_data'])
                
                # Удаляем из ожидания
                del pvp_waiting_players[player_id]
                del pvp_waiting_players[opponent_id]
                
                # Добавляем в активные гонки
                pvp_active_races[race_id] = pvp_race
                
                # Создаем и отправляем изображение начала гонки
                image_generator = RaceImageGenerator()
                image_path = image_generator.create_race_start_image(
                    player_id, opponent_id, 
                    player_data['car_data']['name'], 
                    opponent_data['car_data']['name']
                )
                
                # Уведомляем обоих игроков
                notify_players_race_start(pvp_race, image_path)
                
                # Запускаем гонку
                threading.Thread(target=run_pvp_race, args=(race_id,)).start()
                return
    
        time.sleep(2)  # проверяем каждые 2 секунды
    
    # Если не нашли противника
    if player_id in pvp_waiting_players:
        del pvp_waiting_players[player_id]
        try:
            pvp_waiting_players[player_id]['message'].reply("❌ Не удалось найти противника. Попробуйте позже!")
        except:
            pass

def notify_players_race_start(pvp_race, image_path):
    """Уведомить игроков о начале гонки"""
    players_data = pvp_race.get_players_data()
    
    if players_data and image_path:
        # Загружаем изображение в VK
        upload = vk_api.VkUpload(pvp_race.vk)
        photo = upload.photo_messages(image_path)
        
        if photo:
            attachment = f"photo{photo[0]['owner_id']}_{photo[0]['id']}"
            
            # Отправляем обоим игрокам
            for player_key in ['player1', 'player2']:
                player_id = players_data[player_key]['id']
                try:
                    pvp_race.vk.messages.send(
                        user_id=player_id,
                        message="🏁 PvP ГОНКА НАЧАЛАСЬ! 🏁",
                        attachment=attachment,
                        random_id=0
                    )
                except:
                    pass

def run_pvp_race(race_id):
    """Запустить PvP гонку"""
    if race_id not in pvp_active_races:
        return
        
    pvp_race = pvp_active_races[race_id]
    start_time = time.time()
    
    # Обновляем гонку каждую секунду
    while pvp_race.status == "in_progress" and (time.time() - start_time) < 60:
        race_finished = pvp_race.update_race()
        
        # Отправляем обновление прогресса каждые 3 секунды
        if int(time.time() - start_time) % 3 == 0 or race_finished:
            progress_text = pvp_race.get_race_progress()
            
            # Отправляем обоим игрокам
            for player_id in [pvp_race.player1_id, pvp_race.player2_id]:
                try:
                    pvp_race.vk.messages.send(
                        user_id=player_id,
                        message=progress_text,
                        random_id=0
                    )
                except:
                    pass
        
        if race_finished:
            break
            
        time.sleep(1)
    
    # Завершаем гонку
    if pvp_race.status == "finished":
        award_pvp_players(pvp_race)
        
        # Создаем и отправляем изображение победителя
        image_generator = RaceImageGenerator()
        winner_data = pvp_race.players[pvp_race.winner]
        image_path = image_generator.create_race_finish_image(
            pvp_race.winner, winner_data['car_name']
        )
        
        # Уведомляем игроков о результате
        notify_players_race_finish(pvp_race, image_path)
    
    # Удаляем гонку
    if race_id in pvp_active_races:
        del pvp_active_races[race_id]

def notify_players_race_finish(pvp_race, image_path):
    """Уведомить игроков о завершении гонки"""
    winner_name = pvp_race.players[pvp_race.winner]['user_name']
    loser_id = pvp_race.player1_id if pvp_race.winner == pvp_race.player2_id else pvp_race.player2_id
    
    attachment = None
    if image_path:
        # Загружаем изображение в VK
        upload = vk_api.VkUpload(pvp_race.vk)
        photo = upload.photo_messages(image_path)
        if photo:
            attachment = f"photo{photo[0]['owner_id']}_{photo[0]['id']}"
    
    # Сообщение о результате
    result_text = f"🏁 PvP ГОНКА ЗАВЕРШЕНА! 🏁\n\n🏆 ПОБЕДИТЕЛЬ: {winner_name}"
    
    # Отправляем обоим игрокам
    for player_id in [pvp_race.player1_id, pvp_race.player2_id]:
        try:
            if attachment:
                pvp_race.vk.messages.send(
                    user_id=player_id,
                    message=result_text,
                    attachment=attachment,
                    random_id=0
                )
            else:
                pvp_race.vk.messages.send(
                    user_id=player_id,
                    message=result_text,
                    random_id=0
                )
        except:
            pass

def award_pvp_players(pvp_race):
    """Выдать награды за PvP гонку"""
    user_data = load_data(USERS_DB_FILE)
    
    # Награда победителю
    if str(pvp_race.winner) in user_data.get('users', {}):
        winner = user_data['users'][str(pvp_race.winner)]
        winner['money'] += 800
        winner['exp'] += 40
        
        # Проверка повышения уровня
        levels_gained = check_level_up(winner)
        if levels_gained > 0:
            winner['money'] += levels_gained * LEVEL_REWARD
    
    # Награда проигравшему
    loser_id = pvp_race.player1_id if pvp_race.winner == pvp_race.player2_id else pvp_race.player2_id
    if str(loser_id) in user_data.get('users', {}):
        loser = user_data['users'][str(loser_id)]
        loser['money'] += 300
        loser['exp'] += 15
        check_level_up(loser)
    
    save_data(user_data, USERS_DB_FILE)

# Добавляем команду в обработчик сообщений
def handle_pvp_command(message):
    """Обработка команды PvP гонки"""
    if message.is_private:
        return start_pvp_race(message)
    else:
        return message.reply("❌ PvP гонки доступны только в личных сообщениях с ботом!")

