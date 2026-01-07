import vk_api
import json
from datetime import datetime
from site_config import SiteConfig, get_donate_orders, save_donate_orders, get_donate_users, save_donate_users

def create_donate_order(user_id, package_type):
    """Создание заказа на донат"""
    if package_type not in SiteConfig.DONATE_PACKAGES:
        return None
    
    package = SiteConfig.DONATE_PACKAGES[package_type]
    orders = get_donate_orders()
    
    order_id = f"order_{int(datetime.now().timestamp())}_{user_id}"
    
    order_data = {
        'order_id': order_id,
        'user_id': user_id,
        'package_type': package_type,
        'package_name': package['name'],
        'amount': package['price'],
        'status': 'completed',  # сразу completed для демо
        'created_at': datetime.now().isoformat(),
        'completed_at': datetime.now().isoformat()
    }
    
    orders[order_id] = order_data
    save_donate_orders(orders)
    
    return order_id

def apply_donate_package(user_id, package_type):
    """Применение донат-набора к аккаунту пользователя"""
    try:
        package = SiteConfig.DONATE_PACKAGES[package_type]
        
        # Загружаем данные пользователя из основного бота
        with open(SiteConfig.USERS_DB_FILE, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        
        user_id_str = str(user_id)
        if user_id_str not in users_data['users']:
            return False, "Пользователь не найден в игре!"
        
        user = users_data['users'][user_id_str]
        
        # Выдаем деньги
        user['money'] += package['money']
        
        # Выдаем машины
        cars_data = load_cars_data()
        for car_name in package['cars']:
            car_id = find_car_id_by_name(car_name, cars_data)
            if car_id:
                new_car_id = str(len(user.get('cars', {})) + 1)
                if 'cars' not in user:
                    user['cars'] = {}
                
                user['cars'][new_car_id] = {
                    'name': car_name,
                    'hp': cars_data['cars_shop'][car_id]['hp'],
                    'max_speed': cars_data['cars_shop'][car_id]['max_speed'],
                    'tire_health': 100,
                    'durability': 100,
                    'bought_date': datetime.now().isoformat()
                }
        
        # Сохраняем изменения
        with open(SiteConfig.USERS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        
        # Обновляем историю донатов
        users_donate = get_donate_users()
        if user_id_str in users_donate:
            if 'donations' not in users_donate[user_id_str]:
                users_donate[user_id_str]['donations'] = []
            
            users_donate[user_id_str]['donations'].append({
                'package': package_type,
                'package_name': package['name'],
                'amount': package['price'],
                'date': datetime.now().isoformat()
            })
            save_donate_users(users_donate)
        
        # Отправляем уведомление в ЛС
        send_vk_notification(user_id, package)
        
        return True, "Набор успешно применен!"
        
    except Exception as e:
        return False, f"Ошибка применения набора: {str(e)}"

def send_vk_notification(user_id, package):
    """Отправка уведомления в VK"""
    try:
        vk_session = vk_api.VkApi(token=SiteConfig.VK_ACCESS_TOKEN)
        vk = vk_session.get_api()
        
        message = (
            f"🎁 Вам применен донат-набор '{package['name']}'!\n\n"
            f"💰 Получено: {package['money']:,} руб.\n"
            f"🚗 Машины: {', '.join(package['cars'])}\n"
            f"💎 Premium: {package['premium_days']} дней\n\n"
            f"Спасибо за поддержку бота! 🏎️"
        ).replace(",", " ")
        
        vk.messages.send(
            user_id=int(user_id),
            message=message,
            random_id=0
        )
    except Exception as e:
        print(f"Ошибка отправки уведомления VK: {e}")

def load_cars_data():
    """Загрузка данных о машинах"""
    try:
        with open('cars.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'cars_shop': {}}

def find_car_id_by_name(car_name, cars_data):
    """Поиск ID машины по имени"""
    for car_id, car in cars_data['cars_shop'].items():
        if car['name'] == car_name:
            return car_id
    return None