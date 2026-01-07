# [file name]: main.py
from admin import handle_admin_command
from myfunctions import *
from myclass import *
from config import BOT_TOKEN as token
import vk_api
import json
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

TOKEN = token
GROUP_ID = "233724428"

# Инициализация бота
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

print("Гонки бот запущен...")

def handle_message_event(event):
    """Обработка обычных сообщений"""
    message = Message(event.object['message'], vk)
    text = message.text.lower()

    # Обработка payload для обычных кнопок
    payload = None
    try:
        if 'payload' in event.object['message'] and event.object['message']['payload']:
            payload = json.loads(event.object['message']['payload'])
    except (KeyError, json.JSONDecodeError, TypeError):
        pass

    # Если есть payload - обрабатываем команду из кнопки
    if payload and 'cmd' in payload:
        handle_button_command(message, payload['cmd'], payload)
        return
    # Обработка текстовых команд
    if text in ["меню", "/start", "start", "начать"]:
        show_menu(message)
    elif text in ['помощь', 'команды', 'help']:
        show_commands(message)
    elif text in ['гонка', 'гонки', 'race']:
        show_races(message)
    elif text in ["старт", "начать гонку"]:
        start_race(message)
    elif text in ["гараж", "garage"]:
        show_garage(message)
    elif text in ["автосалон", "магазин", "shop"]:
        show_cars_shop(message)
    elif text in ["техцентр", "сервис", "service"]:
        show_service(message)
    elif text in ["глобальные гонки", "глобальные", "global"]:
        show_global_races(message)
    elif text in ["мои результаты", "статистика", "stats"]:
        my_results(message)
    elif text in ["выйти из гонки", "покинуть гонку"]:
        leave_race(message)
    elif text.startswith("драг"):
        handle_drag_race(message)
    elif text.startswith("/admin"):
        args = text.split()
        handle_admin_command(message, args)
    elif text.startswith("рассылка"):
        # Проверяем что отправитель - администратор
        admin_ids = admins_ids # Добавь сюда ID администраторов

        if message.from_id not in admin_ids:
            return message.reply("❌ У вас нет прав для рассылки!")

        broadcast_text = text[9:].strip()

        if not broadcast_text:
            return message.reply("❌ Укажите текст для рассылки!\nПример: рассылка Привет всем!")

        formatted_text = f"📢 РАССЫЛКА ОТ АДМИНИСТРАЦИИ:\n\n{broadcast_text}\n\n— Бот Гонки"

        db = load_data("chats.json")
        chats_data = db.get('chats', {})

        if not chats_data:
            return message.reply("❌ Нет чатов в базе данных!")

        # Отправляем сообщение о начале рассылки
        message.reply(f"🚀 Начинаю рассылку в {len(chats_data)} чатов...")

        success_count = 0
        error_count = 0
        error_list = []

        for chat_id, chat_info in chats_data.items():
            try:
                chat_message = Message({
                    'from_id': message.from_id,
                    'peer_id': int(chat_id)
                }, vk)

                result = chat_message.reply(formatted_text)

                if result:
                    success_count += 1
                else:
                    error_count += 1
                    error_list.append(f"{chat_info.get('title', 'Без названия')} (ID: {chat_id})")

                # Задержка чтобы не получить бан от VK API
                time.sleep(0.2)

            except Exception as e:
                error_count += 1
                error_list.append(f"{chat_info.get('title', 'Без названия')} (ID: {chat_id}) - {str(e)}")
                print(f"❌ Ошибка в чате {chat_id}: {e}")

        # Формируем итоговый отчет
        report = (
            f"📊 РАССЫЛКА ЗАВЕРШЕНА:\n\n"
            f"✅ Успешно: {success_count}\n"
            f"❌ Ошибок: {error_count}\n"
            f"📝 Всего чатов: {len(chats_data)}"
        )

        # Если есть ошибки, добавляем их в отчет (первые 5)
        if error_list:
            report += f"\n\nПоследние ошибки:\n" + "\n".join(error_list[:5])
            if len(error_list) > 5:
                report += f"\n... и ещё {len(error_list) - 5} ошибок"

        message.reply(report)
    else:
        unknow_command(message)

def handle_button_command(message, cmd, payload):
    """Обработка команд из обычных кнопок"""
    if cmd == 'garage':
        show_garage(message)
    elif cmd == 'cars_shop':
        show_cars_shop(message)
    elif cmd == 'service':
        show_service(message)
    elif cmd == 'global_races':
        show_global_races(message)
    elif cmd == 'buy_car':
        buy_car(message, payload.get('car_id'))
    elif cmd == 'repair_tires':
        repair_tires(message)
    elif cmd == 'repair_body':
        repair_body(message)
    elif cmd == 'upgrade_engine':
        upgrade_engine(message)
    elif cmd == 'upgrade_speed':
        upgrade_speed(message)
    elif cmd == 'select_car':
        select_car(message)
    elif cmd == 'set_active_car':
        set_active_car(message, payload.get('car_id'))
    elif cmd == 'create_race':
        create_race(message)
    elif cmd == 'start_race':
        start_race(message)
    elif cmd == 'race_status':
        show_race_status(message)
    elif cmd == 'find_global_race':
        find_global_race(message)
    elif cmd == 'my_results':
        my_results(message)
    elif cmd == 'accept_drag':
        accept_drag_race(message, payload.get('drag_id'))
    elif cmd == 'decline_drag':
        message.reply("❌ Вызов на драг-рейсинг отклонен.")

def handle_callback_event(event):
    """Обработка callback кнопок"""
    user_id = event.object.user_id
    peer_id = event.object.peer_id

    # Создаем объект сообщения для callback с правильным peer_id
    message_data = {
        'from_id': user_id,
        'peer_id': peer_id,
        'payload': event.object.payload,
        'conversation_message_id': event.object.conversation_message_id
    }

    message = Message(message_data, vk)

    cmd = event.object.payload.get('cmd')

    # Только определенные команды обрабатываем как callback
    if cmd == 'join_race':
        join_race(message)
    elif cmd == 'leave_race':
        leave_race(message)

    # Подтверждаем обработку callback
    vk.messages.sendMessageEventAnswer(
        event_id=event.object.event_id,
        user_id=user_id,
        peer_id=peer_id,
        event_data=json.dumps({"type": "show_snackbar", "text": "✅ Обработано"})
    )
while True:
    for event in longpoll.listen():
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                handle_message_event(event)

            elif event.type == VkBotEventType.MESSAGE_EVENT:
                handle_callback_event(event)

            # Обработка события добавления бота в беседу
            elif event.type == VkBotEventType.GROUP_JOIN:
                try:
                    # Создаем сообщение для приветствия
                    message_data = {
                        'from_id': event.object.user_id,
                        'peer_id': event.object.peer_id
                    }
                    message = Message(message_data, vk)
                    welcome_message(message)
                except Exception as e:
                    print(f"Ошибка при welcome сообщении: {e}")

        except Exception as e:
            print(f"Ошибка обработки события: {e}")