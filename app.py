from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import json
import os
import time
import datetime
from yoomoney import Client, Quickpay
from admin import handle_admin_command
from myfunctions import *
from myclass import *
from config import BOT_TOKEN as token, admins_ids
import threading
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Инициализация бота
vk_session = vk_api.VkApi(token=token)
vk = vk_session.get_api()

# Конфигурация вебхука
CONFIRMATION_TOKEN = "f9691f4b"
SECRET_KEY = "gonkaWow"
GROUP_ID = 233724428
# =============================================================================
# НАСТРОЙКИ ЮMONEY
# =============================================================================

# Получите здесь: https://yoomoney.ru/myservices/new
YOOMONEY_RECEIVER = "4100119211392665"  # Номер кошелька ЮMoney
YOOMONEY_SECRET = "23DF37D7EBE0F6DE798D0777123EBF2D6812B95852784C60B4C7091A7A6B69EB"  # Секретный ключ из настроек

# Донат пакеты
DONATE_PACKAGES = {
    "money": {
        "name": "Деньги",
        'price': 1,  # Будет пересчитываться
        'money': 50,  # Курс: 1 рубль = 50 игровых рублей
        'cars': [],
        'description': "1₽ = 50₽",
        'dynamic': True  # Флаг что цена рассчитывается динамически
    },
    "starter": {
        "name": "Стартовый набор",
        "price": 100,
        "money": 5000,
        "cars": [],
        "description": "Набор для новичков",
        'dynamic': False
    },
    "racer": {
        "name": "Набор гонщика",
        "price": 300,
        "money": 15000,
        "cars": ["Kia Rio"],
        "description": "Для опытных гонщиков",
        'dynamic': False
    },
    "pro": {
        "name": "PRO набор",
        "price": 500,
        "money": 30000,
        "cars": ["BMW 3 Series"],
        "description": "Для профессионалов",
        'dynamic': False
    },
    "vip": {
        "name": "VIP набор",
        "price": 1000,
        "money": 50000,
        "cars": ["Porsche 911"],
        "description": "Элитный набор",
        'dynamic': False
    }
}
# Цвета для кастомизации
CAR_COLORS = [
    "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF",
    "#FFA500", "#800080", "#FFC0CB", "#A52A2A", "#000000", "#FFFFFF",
    "#808080", "#FFD700", "#008000", "#000080"
]

def load_payments():
    """Загрузить данные о платежах"""
    try:
        with open('payments.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"payments": {}, "last_check": 0}

def save_payments(data):
    """Сохранить данные о платежах"""
    with open('payments.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_by_id(user_id):
    """Получить данные пользователя по ID"""
    users_data = load_data(USERS_DB_FILE)
    return users_data.get('users', {}).get(str(user_id))

def update_user_data(user_id, user_data):
    """Обновить данные пользователя"""
    users_data = load_data(USERS_DB_FILE)
    users_data['users'][str(user_id)] = user_data
    save_data(users_data, USERS_DB_FILE)

def get_car_colors(user_id):
    """Получить цвета машин пользователя"""
    users_data = load_data(USERS_DB_FILE)
    user = users_data.get('users', {}).get(str(user_id), {})
    return user.get('car_colors', {})

def save_car_color(user_id, car_id, color):
    """Сохранить цвет для машины"""
    users_data = load_data(USERS_DB_FILE)
    user = users_data.get('users', {}).get(str(user_id), {})

    if 'car_colors' not in user:
        user['car_colors'] = {}

    user['car_colors'][car_id] = color
    users_data['users'][str(user_id)] = user
    save_data(users_data, USERS_DB_FILE)

def create_payment(user_id, package_type):
    """Создать платеж в ЮMoney"""
    try:
        package = DONATE_PACKAGES[package_type]
        payment_id = f"{user_id}_{package_type}_{int(time.time())}"

        # Создаем быструю форму оплаты
        quickpay = Quickpay(
            receiver=YOOMONEY_RECEIVER,
            quickpay_form="shop",
            targets=f"Донат: {package['name']}",
            paymentType="SB",
            sum=package['price'],
            label=payment_id,
            successURL="https://racebotvk.pythonanywhere.com/payment_success"
        )

        # СОХРАНЯЕМ ПАКЕТ СРАЗУ - пользователь получит его даже если проверка API задерживается
        payments_data = load_payments()
        payments_data['payments'][payment_id] = {
            "user_id": user_id,
            "package_type": package_type,
            "amount": package['price'],
            "status": "pending",
            "created_at": datetime.datetime.now().isoformat(),
            "payment_url": quickpay.base_url,
            "applied": False  # Флаг что пакет еще не применен
        }
        save_payments(payments_data)

        return payment_id, quickpay.redirected_url

    except Exception as e:
        print(f"Ошибка в create_payment: {str(e)}")
        raise





def check_payment(payment_id):
    """Проверить статус платежа через API"""
    try:
        client = Client(YOOMONEY_SECRET)
        history = client.operation_history(label=payment_id)

        for operation in history.operations:
            if operation.status == "success":
                return True
        return False
    except Exception as e:
        print(f"Ошибка проверки платежа: {e}")
        return False

def apply_package(user_id, package_type):
    """Применить донат-пакет"""
    user_data = get_user_by_id(user_id)
    package = DONATE_PACKAGES[package_type]

    if not user_data:
        return False, "Пользователь не найден"

    # Добавляем деньги
    user_data['money'] += package['money']

    # Добавляем машины если есть
    if package['cars']:
        cars_data = load_data(CARS_DB_FILE)
        cars_shop = cars_data.get('cars_shop', {})

        for car_name in package['cars']:
            # Находим ID машины по имени
            for car_id, car_info in cars_shop.items():
                if car_info['name'] == car_name:
                    new_car_id = str(len(user_data.get('cars', {})) + 1)
                    if 'cars' not in user_data:
                        user_data['cars'] = {}

                    user_data['cars'][new_car_id] = {
                        'name': car_info['name'],
                        'hp': car_info['hp'],
                        'max_speed': car_info['max_speed'],
                        'tire_health': car_info['tire_health'],
                        'durability': car_info['durability'],
                        'bought_date': datetime.datetime.now().isoformat()
                    }
                    break

    # Сохраняем изменения
    update_user_data(user_id, user_data)

    return True, "Пакет успешно применен"

# =============================================================================
# МАРШРУТЫ САЙТА
# =============================================================================
@app.context_processor
def utility_processor():
    """Добавляем функции в контекст шаблонов"""
    def check_is_admin(user_id):
        return is_admin(user_id)

    def check_can_edit_admins(user_id):
        return can_edit_admins(user_id)

    return dict(
        is_admin=check_is_admin,
        can_edit_admins=check_can_edit_admins
    )
@app.route('/')
def index():
    """Главная страница"""
    user_id = session.get('user_id')
    user_data = None
    if user_id:
        user_data = get_user_by_id(user_id)
    return render_template('index.html', user=user_data, user_id=user_id)
database_login = {

    }
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Авторизация по user_id"""
    if request.method == 'POST':
        user_id = request.form.get('user_id')

        if not user_id:
            flash('Введите ваш VK ID', 'error')
            return redirect(url_for('login'))

        keyboard = VkKeyboard(inline=True)
        keyboard.add_callback_button("Подтвердить", VkKeyboardColor.POSITIVE, payload={'cmd': 'login'})
        # Проверяем существование пользователя
        user_data = get_user_by_id(user_id)
        tim = str(datetime.datetime.now().isoformat())
        if not user_data:
            flash('Пользователь с таким ID не найден в базе бота', 'error')
            return redirect(url_for('login'))
        if str(user_id) not in database_login:
            flash('Всё прошло отлично, теперь нам нужно получить ваше согласие. Перейдите в бота и нажмите кнопку "Подтвердить".\nЭто делается для того, чтобы посторонний человек не зашёл на ваш аккаунт.')
            database_login[str(user_id)] = {
                'status': 'login'
                }



            vk.messages.send(peer_id=user_id, random_id=0, message=f"🚨 Кто-то пытается зайти в ваш аккаунт на нашем сайте!\n⌚ Время: {tim}\n❗ Если это не вы, то проигнорируйте данное сообщение.", keyboard=keyboard.get_keyboard())

            return redirect(url_for('login'))
        if database_login[str(user_id)]['status'] != 'success':
            vk.messages.send(peer_id=user_id, random_id=0, message=f"🚨 Кто-то пытается зайти в ваш аккаунт на нашем сайте!\n⌚ Время: {tim}\n❗ Если это не вы, то проигнорируйте данное сообщение.", keyboard=keyboard.get_keyboard())
            flash("Не удалось подтвердить ваш вход. Нажмите кнопку 'Подтвердить', чтобы зайти на сайт.")
            return redirect(url_for('login'))
        del database_login[str(user_id)]
        # Сохраняем в сессию
        session['user_id'] = user_id
        session.permanent = True


        flash(f'Добро пожаловать, {user_data["username"]}!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Личный кабинет"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Сначала авторизуйтесь!', 'error')
        return redirect(url_for('login'))

    user_data = get_user_by_id(user_id)
    if not user_data:
        session.clear()
        flash('Пользователь не найден!', 'error')
        return redirect(url_for('login'))

    return render_template('dashboard.html',
                         user=user_data,
                         packages=DONATE_PACKAGES)

@app.route('/garage')
def garage():
    """Гараж - кастомизация машин"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Сначала авторизуйтесь!', 'error')
        return redirect(url_for('login'))

    user_data = get_user_by_id(user_id)
    if not user_data:
        session.clear()
        flash('Пользователь не найден!', 'error')
        return redirect(url_for('login'))

    cars = user_data.get('cars', {})
    car_colors = get_car_colors(user_id)

    return render_template('garage.html',
                         user=user_data,
                         cars=cars,
                         car_colors=car_colors,
                         colors=CAR_COLORS)
@app.route('/buy_money')
def buy_money():
    """Страница покупки денег"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Сначала авторизуйтесь!', 'error')
        return redirect(url_for('login'))

    return render_template('buy_money.html')

@app.route('/calculate_money_price', methods=['POST'])
def calculate_money_price():
    """Рассчитать стоимость запрошенной суммы"""
    try:
        requested_money = int(request.form.get('money_amount', 0))

        if requested_money <= 0:
            return jsonify({'success': False, 'error': 'Введите сумму больше 0'})

        # Курс: 1 реальный рубль = 50 игровых рублей
        COURSE = 50
        price = max(1, round(requested_money / COURSE))  # Минимум 1 рубль

        return jsonify({
            'success': True,
            'requested_money': requested_money,
            'price': price,
            'course': f"1₽ = {COURSE}₽"
        })

    except ValueError:
        return jsonify({'success': False, 'error': 'Введите корректное число'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/create_money_payment', methods=['POST'])
def create_money_payment():
    """Создать платеж для покупки денег"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Не авторизован'})

        requested_money = int(request.form.get('money_amount', 0))
        price = int(request.form.get('price', 0))

        if requested_money <= 0 or price <= 0:
            return jsonify({'success': False, 'error': 'Неверная сумма'})

        # Создаем кастомный пакет для денег
        custom_package = {
            "name": f"Покупка {requested_money}₽",
            "price": price,
            "money": requested_money,
            "cars": [],
            "description": f"Покупка игровых денег"
        }

        # Создаем платеж
        payment_id = f"money_{user_id}_{requested_money}_{int(time.time())}"

        quickpay = Quickpay(
            receiver=YOOMONEY_RECEIVER,
            quickpay_form="shop",
            targets=f"Донат: {custom_package['name']}",
            paymentType="SB",
            sum=price,
            label=payment_id,
            successURL="https://racebotvk.pythonanywhere.com/payment_success"
        )

        # Сохраняем информацию о платеже
        payments_data = load_payments()
        payments_data['payments'][payment_id] = {
            "user_id": user_id,
            "package_type": "money_custom",
            "custom_money": requested_money,  # Сохраняем кастомную сумму
            "amount": price,
            "status": "pending",
            "created_at": datetime.datetime.now().isoformat(),
            "payment_url": quickpay.base_url,
            "applied": False
        }
        save_payments(payments_data)

        session['current_payment'] = payment_id

        return jsonify({
            'success': True,
            'payment_url': quickpay.redirected_url
        })

    except Exception as e:
        print(f"Ошибка создания платежа для денег: {e}")
        return jsonify({'success': False, 'error': str(e)})
@app.route('/buy_package/<package_type>')
def buy_package(package_type):
    """Начать процесс покупки"""
    try:
        print(f"Начало покупки пакета: {package_type}")

        user_id = session.get('user_id')
        if not user_id:
            flash('Сначала авторизуйтесь!', 'error')
            return redirect(url_for('login'))

        print(f"Пользователь: {user_id}")

        if package_type not in DONATE_PACKAGES:
            flash('Неверный тип набора!', 'error')
            return redirect(url_for('dashboard'))

        package = DONATE_PACKAGES[package_type]
        print(f"Пакет найден: {package['name']}")

        # Создаем платеж
        payment_id, payment_url = create_payment(user_id, package_type)
        print(f"Платеж создан: {payment_id}")
        print(f"URL оплаты: {payment_url}")

        # Сохраняем ID платежа в сессии
        session['current_payment'] = payment_id

        # Перенаправляем на страницу оплаты
        return redirect(payment_url)

    except Exception as e:
        print(f"Ошибка в buy_package: {str(e)}")
        import traceback
        print(f"Трассировка: {traceback.format_exc()}")
        flash(f'Ошибка при создании платежа: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/payment_success', methods=['GET'])
def payment_success():
    """Страница успешной оплаты"""
    try:
        payment_id = session.get('current_payment')

        if not payment_id:
            flash('Информация о платеже не найдена.', 'info')
            return redirect(url_for('dashboard'))

        payments_data = load_payments()
        payment_info = payments_data['payments'].get(payment_id)

        if not payment_info:
            flash('Платеж не найден в базе.', 'warning')
            return redirect(url_for('dashboard'))

        # Применяем пакет
        if not payment_info.get('applied', False):
            if payment_info['package_type'] == 'money_custom':
                # Для кастомной покупки денег
                success, message = apply_package(
                    payment_info['user_id'],
                    'money_custom',
                    custom_money=payment_info.get('custom_money')
                )
            else:
                # Для обычных пакетов
                success, message = apply_package(
                    payment_info['user_id'],
                    payment_info['package_type']
                )

            if success:
                payment_info['status'] = 'completed'
                payment_info['applied'] = True
                payment_info['completed_at'] = datetime.datetime.now().isoformat()
                payments_data['payments'][payment_id] = payment_info
                save_payments(payments_data)

                flash(f'✅ {message}', 'success')
            else:
                flash(f'❌ {message}', 'error')
        else:
            flash('✅ Пакет уже был применен ранее!', 'info')

        session.pop('current_payment', None)
        return render_template('payment_success.html')

    except Exception as e:
        print(f"Ошибка в payment_success: {e}")
        flash('✅ Оплата прошла успешно! Бонусы будут начислены автоматически.', 'success')
        return render_template('payment_success.html')

@app.route('/payment_failed')
def payment_failed():
    """Страница неудачной оплаты"""
    flash('Оплата не была завершена. Попробуйте еще раз.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/payment_webhook', methods=['POST'])
def payment_webhook():
    """Вебхук для уведомлений от ЮMoney (Notification URI)"""
    try:
        # ЮMoney отправляет уведомления в формате application/x-www-form-urlencoded
        data = request.form

        # Проверяем подпись (если нужно)
        # notification_secret = data.get('notification_secret')

        # Получаем информацию о платеже
        operation_id = data.get('operation_id')
        label = data.get('label')  # Это наш payment_id
        amount = data.get('amount')
        status = data.get('status')

        print(f"Webhook received: {label} - {status} - {amount}")

        if status == 'success' and label:
            # Загружаем данные о платежах
            payments_data = load_payments()
            payment_info = payments_data['payments'].get(label)

            if payment_info and payment_info['status'] != 'completed':
                # Применяем пакет
                success, message = apply_package(payment_info['user_id'], payment_info['package_type'])

                if success:
                    # Обновляем статус платежа
                    payment_info['status'] = 'completed'
                    payment_info['completed_at'] = datetime.datetime.now().isoformat()
                    payment_info['operation_id'] = operation_id
                    payments_data['payments'][label] = payment_info
                    save_payments(payments_data)

                    print(f"Платеж {label} обработан успешно: {message}")
                else:
                    print(f"Ошибка обработки платежа {label}: {message}")

        return 'OK', 200

    except Exception as e:
        print(f"Ошибка в вебхуке: {e}")
        return 'Error', 500

@app.route('/check_payment_status')
def check_payment_status():
    """Проверка статуса платежа (для AJAX)"""
    payment_id = session.get('current_payment')

    if not payment_id:
        return jsonify({'status': 'error', 'message': 'Платеж не найден'})

    payments_data = load_payments()
    payment_info = payments_data['payments'].get(payment_id)

    if not payment_info:
        return jsonify({'status': 'error', 'message': 'Платеж не найден в базе'})

    # Если пакет уже применен - сразу возвращаем успех
    if payment_info.get('applied', False):
        return jsonify({'status': 'completed'})

    # Пытаемся проверить через API, но не блокируем пользователя
    try:
        if check_payment(payment_id):
            success, message = apply_package(payment_info['user_id'], payment_info['package_type'])
            if success:
                payment_info['status'] = 'completed'
                payment_info['applied'] = True
                payment_info['completed_at'] = datetime.datetime.now().isoformat()
                payments_data['payments'][payment_id] = payment_info
                save_payments(payments_data)
                return jsonify({'status': 'success', 'message': message})
    except:
        # Если API не отвечает - ничего страшного, пакет уже применен
        pass

    return jsonify({'status': 'pending'})

def apply_package(user_id, package_type, custom_money=None):
    """Применить донат-пакет"""
    user_data = get_user_by_id(user_id)

    if not user_data:
        return False, "Пользователь не найден"

    if package_type == "money_custom" and custom_money:
        # Для кастомной покупки денег
        user_data['money'] += custom_money
        message = f"Начислено {custom_money} игровых рублей!"
    else:
        # Для обычных пакетов
        package = DONATE_PACKAGES[package_type]
        user_data['money'] += package['money']

        # Добавляем машины если есть
        if package['cars']:
            cars_data = load_data(CARS_DB_FILE)
            cars_shop = cars_data.get('cars_shop', {})

            for car_name in package['cars']:
                # Находим ID машины по имени
                for car_id, car_info in cars_shop.items():
                    if car_info['name'] == car_name:
                        new_car_id = str(len(user_data.get('cars', {})) + 1)
                        if 'cars' not in user_data:
                            user_data['cars'] = {}

                        user_data['cars'][new_car_id] = {
                            'name': car_info['name'],
                            'hp': car_info['hp'],
                            'max_speed': car_info['max_speed'],
                            'tire_health': car_info['tire_health'],
                            'durability': car_info['durability'],
                            'bought_date': datetime.datetime.now().isoformat()
                        }
                        break

        message = f"Пакет '{package['name']}' применен! +{package['money']}₽"

    # Сохраняем изменения
    update_user_data(user_id, user_data)

    return True, message

@app.route('/update_car_color', methods=['POST'])
def update_car_color():
    """Обновить цвет машины"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'})

    car_id = request.form.get('car_id')
    color = request.form.get('color')

    if not car_id or not color:
        return jsonify({'success': False, 'error': 'Неверные данные'})

    # Сохраняем цвет
    save_car_color(user_id, car_id, color)

    return jsonify({'success': True})

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы успешно вышли из системы!', 'success')
    return redirect(url_for('index'))
# Добавляем в начало файла
import requests
from functools import wraps

# =============================================================================
# АДМИН-ФУНКЦИИ
# =============================================================================

def load_admin_data():
    """Загрузить данные админов"""
    try:
        with open('admin.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"moders": {"users_ids": []}}

def save_admin_data(data):
    """Сохранить данные админов"""
    with open('admin.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(user_id):
    """Проверить является ли пользователь админом"""
    try:
        admin_data = load_admin_data()
        user_id_str = str(user_id)
        print(f"Проверка админа: {user_id_str} в {admin_data.get('moders', {}).get('users_ids', [])}")
        return user_id_str in admin_data.get('moders', {}).get('users_ids', [])
    except Exception as e:
        print(f"Ошибка проверки админа: {e}")
        return False


def get_admin_permissions(user_id):
    """Получить права админа"""
    admin_data = load_admin_data()
    user_data = admin_data.get('moders', {}).get(str(user_id), {})
    return user_data.get('perm', [])

def admin_required(f):
    """Декоратор для проверки прав админа"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id or not is_admin(user_id):
            flash('Доступ запрещен!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def can_edit_admins(user_id):
    """Может ли редактировать админов"""
    return str(user_id) == "819016396" or "can_admins_edit" in get_admin_permissions(user_id)

def get_vk_user_info(user_id):
    """Получить информацию о пользователе VK"""
    try:
        url = f"https://api.vk.com/method/users.get"
        params = {
            'user_ids': user_id,
            'fields': 'photo_200,first_name,last_name',
            'access_token': token,
            'v': '5.199'
        }
        response = requests.get(url, params=params)
        data = response.json()

        if 'response' in data and data['response']:
            user = data['response'][0]
            return {
                'id': user['id'],
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'photo': user.get('photo_200', '')
            }
    except Exception as e:
        print(f"Ошибка получения информации о пользователе: {e}")

    return None

# =============================================================================
# АДМИН-МАРШРУТЫ
# =============================================================================
@app.route('/admin/search_users')
def search_users():
    if not is_admin(session.get('user_id')):
        return jsonify({'success': False, 'error': 'Доступ запрещен'})

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'success': False, 'error': 'Пустой запрос'})

    # Поиск пользователей по имени в базе данных
    users = user.query.filter(
        (user.vk_info['first_name'].astext.ilike(f'%{query}%')) |
        (user.vk_info['last_name'].astext.ilike(f'%{query}%'))
    ).all()

    # Преобразование в JSON-совместимый формат
    users_data = []
    for user in users:
        users_data.append({
            'vk_info': {
                'id': user.vk_info.get('id'),
                'first_name': user.vk_info.get('first_name'),
                'last_name': user.vk_info.get('last_name'),
                'photo': user.vk_info.get('photo')
            },
            'money': user.money,
            'level': user.level,
            'is_banned': user.is_banned
        })

    return jsonify({'success': True, 'users': users_data})
@app.route('/admin/login', methods=['GET', 'POST'])
@admin_required
def admin_login():
    """Вход в админ-панель"""
    if request.method == 'POST':
        secret_code = request.form.get('secret_code')
        user_id = session.get('user_id')

        expected_code = f"gonka_bot_admin_{user_id}"

        if secret_code == expected_code:
            session['admin_authenticated'] = True
            flash('Успешный вход в админ-панель!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Неверный секретный код!', 'error')

    return render_template('admin_login.html')

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Главная админ-панель"""
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))

    return render_template('admin_dashboard.html')

@app.route('/admin/users')
@admin_required
def admin_users():
    """Управление пользователями"""
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))

    users_data = load_data(USERS_DB_FILE)
    admin_data = load_admin_data()

    # Получаем информацию о пользователях VK
    users_with_info = []
    for user_id, user_data in users_data.get('users', {}).items():
        vk_info = get_vk_user_info(user_id)
        if vk_info:
            user_data['vk_info'] = vk_info
            user_data['is_banned'] = user_id in admin_data.get('ban', {}).get('users_ids', [])
            users_with_info.append(user_data)

    return render_template('admin_users.html', users=users_with_info)

@app.route('/admin/user/<user_id>')
@admin_required
def admin_user_detail(user_id):
    """Детальная информация о пользователе"""
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))

    users_data = load_data(USERS_DB_FILE)
    admin_data = load_admin_data()

    user_data = users_data.get('users', {}).get(user_id)
    if not user_data:
        flash('Пользователь не найден!', 'error')
        return redirect(url_for('admin_users'))

    vk_info = get_vk_user_info(user_id)
    ban_info = admin_data.get('ban', {}).get(user_id)

    return render_template('admin_user_detail.html',
                         user=user_data,
                         user_id=user_id,
                         vk_info=vk_info,
                         ban_info=ban_info)

@app.route('/admin/update_user_field', methods=['POST'])
@admin_required
def admin_update_user_field():
    """Обновить поле пользователя"""
    try:
        user_id = request.form.get('user_id')
        field = request.form.get('field')
        value = request.form.get('value')

        users_data = load_data(USERS_DB_FILE)

        if user_id not in users_data.get('users', {}):
            return jsonify({'success': False, 'error': 'Пользователь не найден'})

        # Преобразуем значение в правильный тип
        if field in ['money', 'exp', 'level', 'pistons']:
            value = int(value)
        elif field in ['cars', 'car_colors']:
            try:
                value = json.loads(value)
            except:
                return jsonify({'success': False, 'error': 'Неверный формат данных'})

        users_data['users'][user_id][field] = value
        save_data(users_data, USERS_DB_FILE)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/ban_user', methods=['POST'])
@admin_required
def admin_ban_user():
    """Забанить пользователя"""
    try:
        user_id = request.form.get('user_id')
        days = int(request.form.get('days', 1))
        reason = request.form.get('reason', '')

        admin_data = load_admin_data()

        if 'ban' not in admin_data:
            admin_data['ban'] = {'users_ids': []}

        admin_data['ban']['users_ids'].append(user_id)
        admin_data['ban'][user_id] = {
            'days': days,
            'time': int(time.time()),
            'reason': reason
        }

        save_admin_data(admin_data)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/unban_user', methods=['POST'])
@admin_required
def admin_unban_user():
    """Разбанить пользователя"""
    try:
        user_id = request.form.get('user_id')

        admin_data = load_admin_data()

        if user_id in admin_data.get('ban', {}).get('users_ids', []):
            admin_data['ban']['users_ids'].remove(user_id)
            if user_id in admin_data['ban']:
                del admin_data['ban'][user_id]

            save_admin_data(admin_data)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/make_admin', methods=['POST'])
@admin_required
def admin_make_admin():
    """Назначить администратором"""
    try:
        target_user_id = request.form.get('user_id')
        role = request.form.get('role', 'moder')

        current_user_id = session.get('user_id')
        if not can_edit_admins(current_user_id):
            return jsonify({'success': False, 'error': 'Недостаточно прав'})

        admin_data = load_admin_data()

        if 'moders' not in admin_data:
            admin_data['moders'] = {'users_ids': []}

        if target_user_id not in admin_data['moders']['users_ids']:
            admin_data['moders']['users_ids'].append(target_user_id)

        admin_data['moders'][target_user_id] = {
            'status': role,
            'reports': 0,
            'perm': ['basic']
        }

        save_admin_data(admin_data)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/broadcast')
@admin_required
def admin_broadcast():
    """Рассылка сообщений"""
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))

    return render_template('admin_broadcast.html')

@app.route('/admin/send_broadcast', methods=['POST'])
@admin_required
def admin_send_broadcast():
    """Отправить рассылку"""
    try:
        message = request.form.get('message')

        if not message:
            return jsonify({'success': False, 'error': 'Введите сообщение'})

        # Здесь код рассылки (можно взять из существующей функции)
        chats_data = load_data("chats.json")
        success_count = 0

        for chat_id, chat_info in chats_data.get('chats', {}).items():
            try:
                chat_message = Message({
                    'from_id': session.get('user_id'),
                    'peer_id': int(chat_id)
                }, vk)

                result = chat_message.reply(f"📢 РАССЫЛКА:\n\n{message}\n\n— Администрация")
                if result:
                    success_count += 1

                time.sleep(0.2)
            except:
                pass

        return jsonify({'success': True, 'sent_count': success_count})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/admins')
@admin_required
def admin_admins():
    """Управление администраторами"""
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))

    current_user_id = session.get('user_id')
    if not can_edit_admins(current_user_id):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('admin_dashboard'))

    admin_data = load_admin_data()
    moderators = admin_data.get('moders', {})

    # Получаем информацию об админах
    admins_with_info = []
    for user_id in moderators.get('users_ids', []):
        if user_id in moderators:
            vk_info = get_vk_user_info(user_id)
            if vk_info:
                admin_info = moderators[user_id]
                admin_info['vk_info'] = vk_info
                admin_info['id'] = user_id
                admins_with_info.append(admin_info)

    return render_template('admin_admins.html', admins=admins_with_info)

@app.route('/admin/logout')
def admin_logout():
    """Выход из админ-панели"""
    session.pop('admin_authenticated', None)
    flash('Вы вышли из админ-панели', 'info')
    return redirect(url_for('dashboard'))
# =============================================================================
# ВЕБХУК ДЛЯ VK BOT API
# =============================================================================

# Инициализация бота
vk_session = vk_api.VkApi(token=token)
vk = vk_session.get_api()

# Конфигурация вебхука
CONFIRMATION_TOKEN = "f9691f4b"
SECRET_KEY = "gonkaWow"
GROUP_ID = 233724428

def handle_message_event(message_data):
    """Обработка новых сообщений"""
    message = Message(message_data, vk)
    text = message.text.lower()

    # Обработка payload для обычных кнопок
    payload = None
    try:
        if 'payload' in message_data and message_data['payload']:
            payload = json.loads(message_data['payload'])
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
        if message.from_id != message.peer_id:
            show_races(message)
    elif text in ["pvp", "пвп", "гонка пвп"]:
        handle_pvp_command(message)
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

    elif text == "мой айди":
        if message.from_id != message.peer_id:
            message.reply("Данная команда доступна только в лс бота!")
        else:
            message.reply(message.from_id)
    elif text == "поддержка":
        message.reply("Если у вас возникли какие-то проблемы, обращайтесь к - @deniska_bisekeev")
    elif text == "вход":
        user_id = message.from_id
        if str(user_id) not in database_login:
            message.reply("Вы не пытаетесь войти в данный момент на сайт!")
            pass
        message.reply("Согласие дано, напишите заново свой айди в форме, чтобы войти..")
        database_login[str(user_id)]['status'] = 'success'
    elif text == "донат":
        keyboard = VkKeyboard(inline=True)
        keyboard.add_openlink_button("Перейти на сайт", "https://racebotvk.pythonanywhere.com")
        t = f"Привет, {message.get_mention(message.from_id)}, чтобы оплатить донат, перейдите на наш сайт. При входе вас попросят написать ваш айди, перейдите в лс бота - [vk.me/gonka_bot|тык] и напишите 'мой айди'"
        message.reply(t, keyboard=keyboard.get_keyboard())
    elif text.startswith("клан"):
        args = text.split()[1:]
        handle_klan_command(message, args)
    elif text.startswith("битва присоединиться"):
        join_klan_battle(message, text.split()[2])
    elif text.startswith("драг"):
        handle_drag_race(message)
    elif text.startswith("/admin"):
        data = load_data('admin.json')
        if str(message.from_id) in data['moders']['users_ids']:
            args = text.split()
            handle_admin_command(message, args)
        else:
            None
    elif text == "айди чата":
        message.reply(message.peer_id)
    elif text.startswith("рассылка"):
        # Проверяем что отправитель - администратор
        admin_ids = admins_ids

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

def handle_callback_event(event_data):
    """Обработка callback кнопок"""
    user_id = event_data['user_id']
    peer_id = event_data['peer_id']

    # Создаем объект сообщения для callback
    message_data = {
        'from_id': user_id,
        'peer_id': peer_id,
        'payload': event_data.get('payload', {}),
        'conversation_message_id': event_data.get('conversation_message_id')
    }

    message = Message(message_data, vk)

    cmd = event_data.get('payload', {}).get('cmd')

    # Только определенные команды обрабатываем как callback
    if cmd == 'join_race':
        join_race(message)
    elif cmd == 'leave_race':
        leave_race(message)
    elif cmd == 'login':
        message.edit("Вы дали согласие на вход! Теперь введите заново ваш айди в форме, чтобы войти. На вход даётся 5 минут!")
        threading.Thread(target=check_login, args=(message,)).start()
        database_login[str(user_id)]['status'] = 'success'

    # Подтверждаем обработку callback
    try:
        vk.messages.sendMessageEventAnswer(
            event_id=event_data['event_id'],
            user_id=user_id,
            peer_id=peer_id,
            event_data=json.dumps({"type": "show_snackbar", "text": "✅ Обработано"})
        )
    except Exception as e:
        print(f"Ошибка подтверждения callback: {e}")
def check_login(message):
    time.sleep(300)
    try:
        del database_login[str(message.from_id)]
    except:
        return
def handle_group_join_event(event_data):
    """Обработка вступления в группу"""
    try:
        message_data = {
            'from_id': event_data['user_id'],
            'peer_id': event_data['user_id']  # Отправляем в ЛС
        }
        message = Message(message_data, vk)
        welcome_message(message)
    except Exception as e:
        print(f"Ошибка при welcome сообщении: {e}")

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
    # В handle_button_command добавьте:
    elif cmd == 'pvp_race':
        handle_pvp_command(message)

    # Команды кланов
    elif cmd == 'klan_create_menu':
        message.reply("Для создания клана используйте команду:\nклан создать [название] [тег]\n\nПример: клан создать ГонщикиПро GP")
    elif cmd == 'klan_info':
        show_klan_info(message)
    elif cmd == 'klan_members':
        show_klan_members(message)
    elif cmd == 'klan_battle':
        start_klan_battle(message)
    elif cmd == 'klan_invite_menu':
        message.reply("Для приглашения в клан используйте команду:\nклан приглос [@игрок]\n\nПример: клан приглос @username")
    elif cmd == 'klan_accept':
        accept_klan_invite(message, [payload.get('invite_id')])
    elif cmd == 'klan_decline':
        message.reply("❌ Приглашение в клан отклонено.")
    elif cmd == 'klan_top':
        show_klan_top(message)

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """Обработка вебхуков от VK"""
    if request.method == 'GET':
        # Для проверки доступности сервера
        return render_template("app.html"), 200

    data = request.json

    # Проверяем тип события
    event_type = data.get('type')

    # Обработка подтверждения вебхука
    if event_type == 'confirmation':
        # Проверяем group_id
        if data.get('group_id') == GROUP_ID:
            return CONFIRMATION_TOKEN
        else:
            return 'Invalid group_id', 403

    # Проверка секретного ключа для остальных событий
    if data.get('secret') != SECRET_KEY:
        return 'Invalid secret', 403

    # Обработка основных событий
    try:
        if event_type == 'message_new':
            handle_message_event(data['object']['message'])
        elif event_type == 'message_event':
            handle_callback_event(data['object'])
        elif event_type == 'group_join':
            handle_group_join_event(data['object'])
    except Exception as e:
        print(f"Ошибка обработки события: {e}")
        return 'Error', 500

    return 'ok', 200

# =============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =============================================================================

if __name__ == '__main__':
    print("Гонки бот запущен через вебхук...")
    print("Веб-сайт доступен по адресу: http://localhost:7000")
    app.run(host='0.0.0.0', port=7000, debug=True)