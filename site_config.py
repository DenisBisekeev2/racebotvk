import os
import json
from datetime import datetime
from config import BOT_TOKEN as token

class SiteConfig:
    SECRET_KEY = os.environ.get('TOcYhfoFaaNWsNeaGElN') or 'TOcYhfoFaaNWsNeaGElN'
    
    # Файлы данных
    USERS_DB_FILE = 'users.json'
    DONATE_USERS_FILE = 'donate_users.json'
    DONATE_ORDERS_FILE = 'donate_orders.json'
    
    # Настройки VK API
    VK_ACCESS_TOKEN = token
    VK_APP_ID = '6441755'  # ID вашего приложения VK
    VK_APP_SECRET = 'TOcYhfoFaaNWsNeaGElN'  # Добавьте секретный ключ приложения
    VK_REDIRECT_URI = 'https://racebotvk.pythonanywhere.com/vk-id-callback'  # Для VK ID
    
    # Донат пакеты
    DONATE_PACKAGES = {
        'starter': {
            'name': 'Стартовый набор',
            'price': 299,
            'money': 50000,
            'cars': ['Lada Vesta'],
            'premium_days': 0,
            'description': 'Отличный старт для новичка',
            'color': 'blue'
        },
        'racer': {
            'name': 'Набор гонщика', 
            'price': 599,
            'money': 150000,
            'cars': ['Kia Rio'],
            'premium_days': 7,
            'description': 'Для тех, кто серьезно настроен',
            'color': 'green'
        },
        'pro': {
            'name': 'PRO набор',
            'price': 999, 
            'money': 500000,
            'cars': ['BMW 3 Series'],
            'premium_days': 30,
            'description': 'Профессиональный уровень',
            'color': 'purple'
        },
        'vip': {
            'name': 'VIP набор',
            'price': 1999,
            'money': 1500000,
            'cars': ['Porsche 911'],
            'premium_days': 90,
            'description': 'Максимальные преимущества',
            'color': 'gold'
        }
    }

def load_json_data(filename):
    """Загрузка данных из JSON файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_json_data(data, filename):
    """Сохранение данных в JSON файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_donate_users():
    return load_json_data(SiteConfig.DONATE_USERS_FILE)

def save_donate_users(users):
    save_json_data(users, SiteConfig.DONATE_USERS_FILE)

def get_donate_orders():
    return load_json_data(SiteConfig.DONATE_ORDERS_FILE)

def save_donate_orders(orders):
    save_json_data(orders, SiteConfig.DONATE_ORDERS_FILE)