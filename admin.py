# [file name]: admin.py
from myclass import *
from myfunctions import *
import json

def admin_panel(message):
    """Панель администратора"""
    text = "⚙️ ПАНЕЛЬ АДМИНИСТРАТОРА\n\n"
    text += "Доступные команды:\n"
    text += "/admin premium [chat_id] - выдать Premium\n"
    text += "/admin money [user_id] [amount] - выдать деньги\n"
    text += "/admin cars - список всех машин\n"
    text += "/admin stats - статистика бота\n"
    text += "/admin ban [user_id] [дни] [причина]\n"
    text += "/admin checkban [user_id]\n"
    text += "/admin unban [user_id]\n"
    text += "/admin обнул [user_id]"

    message.reply(text)

def handle_admin_command(message, args):
    """Обработка админских команд"""
    if len(args) < 2:
        return admin_panel(message)

    command = args[1]

    if command == "premium" and len(args) >= 3:
        chat_id = args[2]
        admin_add_premium(message, chat_id)

    elif command == "money" and len(args) >= 4:
        try:
            user_input = args[2]
            amount = int(args[3])

            if amount <= 0:
                return message.reply("❌ Сумма должна быть положительной!")
            if amount > 1000000:  # Лимит на выдачу
                return message.reply("❌ Слишком большая сумма! Максимум 1.000.000 руб.")

            db = load_data("users.json")
            users_data = db.get("users", {})

            # Функция поиска пользователя
            def find_user(identifier):
                # Пробуем как упоминание
                user_id = message.extract_user_id(identifier)
                if user_id and str(user_id) in users_data:
                    return users_data[str(user_id)], user_id

                # Пробуем как числовой ID
                if identifier.isdigit():
                    user_id = int(identifier)
                    if str(user_id) in users_data:
                        return users_data[str(user_id)], user_id

                # Пробуем найти по имени (точное совпадение)
                for uid, user_data in users_data.items():
                    if identifier.lower() == user_data.get('username', '').lower():
                        return user_data, int(uid)

                return None, None

            user_data, user_id = find_user(user_input)

            if user_data is None:
                return message.reply("❌ Пользователь не найден! Укажите:\n• Упоминание (@user)\n• ID пользователя\n• Точное имя")

            # Выдаем деньги
            old_balance = user_data['money']
            user_data['money'] += amount
            save_data(db, "users.json")

            username = user_data.get('username', 'Неизвестно')
            message.reply(
                f"✅ Деньги выданы успешно!\n\n"
                f"👤 Получатель: {username}\n"
                f"💰 Сумма: {format_number(amount)} руб.\n"
                f"📊 Баланс: {format_number(old_balance)} → {format_number(user_data['money'])} руб.\n"
                f"🆔 ID: {user_id}"
            )

        except ValueError:
            message.reply("❌ Неверный формат суммы! Укажите число.")
        except Exception as e:
            message.reply(f"❌ Ошибка при выдаче денег: {str(e)}")

    elif command == "cars":
        cars_data = load_data(CARS_DB_FILE)
        text = "🚗 ВСЕ МАШИНЫ В МАГАЗИНЕ:\n\n"
        for car_id, car in cars_data['cars_shop'].items():
            text += f"{car_id}. {car['name']} - {car['price']} руб.\n"
        message.reply(text)

    elif command == "stats":
        users_data = load_data(USERS_DB_FILE)
        chats_data = load_data(CHATS_DB_FILE)

        text = "📊 СТАТИСТИКА БОТА:\n\n"
        text += f"👤 Пользователей: {len(users_data.get('users', {}))}\n"
        text += f"💬 Чатов: {len(chats_data.get('chats', {}))}\n"
        text += f"🏎️ Активных гонок: {len(local_races)}\n"
        text += f"🌍 Глобальных гонок: 0\n"

        message.reply(text)
    elif command == "обнул":
        db = load_data("users.json")
        user_id = message.extract_user_id(args[2])

        try:
            user = db['users'][str(user_id)]
        except:
            return message.reply("Этого юзера нет в базе данных!")
        user['money'] = 0
        user['exp'] = 0
        user['level'] = 0
        user['pistons'] = 0
        del user['cars']
        user['cars'] = {}
        save_data(db, "users.json")
        message.reply(f"[id{user_id}|{message.get_mention(user_id)}] успешно обнулён!")
    elif command == "ban":
        db = load_data('admin.json')

        if len(args) < 5:
            return message.reply("❌ Использование: /admin ban [user_id] [кол-во дней] [причина]")

        user_id = message.extract_user_id(args[2])

        try:
            days = int(args[3])
            if days <= 0:
                return message.reply("❌ Количество дней должно быть положительным числом!")
        except ValueError:
            return message.reply("❌ Количество дней должно быть числом!")

        reason = " ".join(args[4:])
        current_time = int(time.time())

        # Проверяем, забанен ли пользователь (исправленный доступ)
        if str(user_id) in db['ban'] and user_id in db['ban']['users_ids']:
            # Получаем информацию о текущем бане
            old_ban = db['ban'][str(user_id)]
            old_dt = datetime.fromtimestamp(old_ban['time'], tz=pytz.timezone('Europe/Moscow'))

            reply_text = (
                f"⚠️ Пользователь уже забанен!\n"
                f"📋 Текущий бан:\n"
                f"• Причина: {old_ban['reason']}\n"
                f"• Дата: {old_dt.strftime('%d.%m.%Y %H:%M:%S')}\n"
                f"• Срок: {old_ban['days']} дней\n\n"
                f"🔄 Начинаю процесс перебана..."
            )
            message.reply(reply_text)

            # Удаляем старый бан
            del db['ban'][str(user_id)]
            db['ban']['users_ids'].remove(user_id)

        # Создаем новый бан
        db['ban'][str(user_id)] = {
            'days': days,
            'time': current_time,
            'reason': reason
        }
        if user_id not in db['ban']['users_ids']:
            db['ban']['users_ids'].append(user_id)

        save_data(db, "admin.json")

        # Форматируем время
        ban_dt = datetime.fromtimestamp(current_time, tz=pytz.timezone('Europe/Moscow'))
        end_time = current_time + (days * 24 * 60 * 60)
        end_dt = datetime.fromtimestamp(end_time, tz=pytz.timezone('Europe/Moscow'))

        success_text = (
            f"✅ [id{user_id}|Пользователь] успешно заблокирован!\n\n"
            f"📊 Информация о бане:\n"
            f"• Дата: {ban_dt.strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"• До: {end_dt.strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"• Срок: {days} дней\n"
            f"• Причина: {reason}\n\n"
            f"⏰ Бан истечет через {days} дней"
        )

        return message.reply(success_text)

    elif command == "unban":
        db = load_data('admin.json')

        if len(args) < 3:
            return message.reply("❌ Использование: /admin unban [user_id]")

        user_id = message.extract_user_id(args[2])

        # Проверяем, забанен ли пользователь (исправленный доступ)
        if str(user_id) not in db['ban'] or user_id not in db['ban']['users_ids']:
            return message.reply("❌ Пользователь не забанен!")

        # Получаем информацию о бане перед удалением
        user_ban_info = db['ban'][str(user_id)]
        ban_time = user_ban_info['time']
        ban_days = user_ban_info['days']
        ban_reason = user_ban_info['reason']

        # Вычисляем время окончания бана
        end_time = ban_time + (ban_days * 24 * 60 * 60)
        current_time = time.time()
        remaining = end_time - current_time

        # Форматируем даты
        start_dt = datetime.fromtimestamp(ban_time, tz=pytz.timezone('Europe/Moscow'))
        end_dt = datetime.fromtimestamp(end_time, tz=pytz.timezone('Europe/Moscow'))

        # Удаляем пользователя из бана
        del db['ban'][str(user_id)]
        db['ban']['users_ids'].remove(user_id)

        save_data(db, "admin.json")

        # Формируем сообщение
        t = f"✅ [id{user_id}|Пользователь] успешно разблокирован!\n\n"
        t += f"📊 Информация о снятом бане:\n"
        t += f"• Дата бана: {start_dt.strftime('%d.%m.%Y %H:%M:%S')}\n"
        t += f"• Плановый конец: {end_dt.strftime('%d.%m.%Y %H:%M:%S')}\n"
        t += f"• Причина: {ban_reason}\n"
        t += f"• Срок: {ban_days} дней\n"

        if remaining > 0:
            days_left = int(remaining // (24 * 60 * 60))
            hours_left = int((remaining % (24 * 60 * 60)) // (60 * 60))
            t += f"• Снят досрочно: за {days_left}д {hours_left}ч до окончания"
        else:
            t += f"• Бан истек: снятие по окончании срока"

        return message.reply(t)

    elif command == "checkban":
        db = load_data('admin.json')

        if len(args) < 3:
            return message.reply("❌ Использование: /admin checkban [user_id]")

        user_id = message.extract_user_id(args[2])

        # Проверяем, забанен ли пользователь (исправленный доступ)
        if str(user_id) not in db['ban'] or user_id not in db['ban']['users_ids']:
            return message.reply("❌ Пользователь не забанен!")

        user_ban_info = db['ban'][str(user_id)]
        ban_time = user_ban_info['time']
        days = user_ban_info['days']

        # Вычисляем время окончания бана
        end_time = ban_time + (days * 24 * 60 * 60)
        current_time = time.time()

        # Время в читаемом формате
        start_dt = datetime.fromtimestamp(ban_time, tz=pytz.timezone('Europe/Moscow'))
        end_dt = datetime.fromtimestamp(end_time, tz=pytz.timezone('Europe/Moscow'))

        # Вычисляем оставшееся время
        remaining = end_time - current_time

        if remaining <= 0:
            time_left = "⏰ Бан истек"
            progress = "██████████"  # 100%
        else:
            total_duration = days * 24 * 60 * 60
            progress_percent = (1 - remaining / total_duration) * 100
            progress_bars = int(progress_percent / 10)
            progress = "█" * progress_bars + "░" * (10 - progress_bars)

            # Форматируем оставшееся время
            if remaining > 86400:  # больше суток
                time_left = f"⏳ Осталось: {int(remaining // 86400)} дн. {int((remaining % 86400) // 3600)} час."
            elif remaining > 3600:  # больше часа
                time_left = f"⏳ Осталось: {int(remaining // 3600)} час. {int((remaining % 3600) // 60)} мин."
            else:  # меньше часа
                time_left = f"⏳ Осталось: {int(remaining // 60)} мин. {int(remaining % 60)} сек."

        t = f"🚫 Информация о бане [id{user_id}|Пользователя]\n\n"
        t += f"📅 Начало: {start_dt.strftime('%d.%m.%Y %H:%M')}\n"
        t += f"📅 Конец: {end_dt.strftime('%d.%m.%Y %H:%M')}\n"
        t += f"⏰ {time_left}\n"

        if remaining > 0:
            t += f"📊 Прогресс: [{progress}] {min(100, int(progress_percent))}%\n"

        t += f"📝 Причина: {user_ban_info['reason']}\n"
        t += f"⏱️ Срок: {days} дней"

        return message.reply(t)



