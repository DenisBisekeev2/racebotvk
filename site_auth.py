import vk_api
import hashlib
import secrets
import requests
from flask import session, flash, redirect, url_for, request
from site_config import SiteConfig, get_donate_users, save_donate_users
from datetime import datetime

def exchange_vkid_code(code, device_id):
    """Обмен кода VK ID на access token"""
    try:
        token_url = "https://id.vk.com/oauth2/auth"
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'device_id': device_id,
            'client_id': SiteConfig.VK_APP_ID,
            'client_secret': SiteConfig.VK_APP_SECRET,
            'redirect_uri': SiteConfig.VK_REDIRECT_URI
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_data = token_response.json()
        
        if 'access_token' not in token_data:
            return None, "Ошибка обмена кода VK ID"
        
        return token_data, None
        
    except Exception as e:
        return None, f"Ошибка VK ID: {str(e)}"

def get_vk_user_by_vkid(access_token):
    """Получение данных пользователя через VK ID"""
    try:
        # Получаем информацию о пользователе
        api_url = "https://api.vk.com/method/users.get"
        params = {
            'access_token': access_token,
            'fields': 'first_name,last_name,photo_200,photo_max_orig',
            'v': '5.199'
        }
        
        user_response = requests.get(api_url, params=params)
        user_data = user_response.json()
        
        if 'error' in user_data or not user_data.get('response'):
            return None, "Не удалось получить данные пользователя"
        
        user_info = user_data['response'][0]
        user_info['access_token'] = access_token
        user_info['vk_link'] = f"https://vk.com/id{user_info['id']}"
        
        return user_info, None
        
    except Exception as e:
        return None, f"Ошибка получения данных: {str(e)}"

def get_vk_auth_url():
    """Генерация URL для авторизации через VK (старый метод)"""
    return (f"https://oauth.vk.com/authorize?"
            f"client_id={SiteConfig.VK_APP_ID}&"
            f"display=page&"
            f"redirect_uri={SiteConfig.VK_REDIRECT_URI}&"
            f"scope=email&"
            f"response_type=code&"
            f"v=5.199")

def get_vk_user_by_code(code):
    """Получение данных пользователя VK по коду авторизации (старый метод)"""
    try:
        # Получаем access token
        token_url = "https://oauth.vk.com/access_token"
        token_params = {
            'client_id': SiteConfig.VK_APP_ID,
            'client_secret': SiteConfig.VK_APP_SECRET,
            'redirect_uri': SiteConfig.VK_REDIRECT_URI,
            'code': code
        }
        
        token_response = requests.get(token_url, params=token_params)
        token_data = token_response.json()
        
        if 'access_token' not in token_data:
            return None, "Ошибка авторизации VK"
        
        access_token = token_data['access_token']
        user_id = token_data['user_id']
        email = token_data.get('email', '')
        
        # Получаем информацию о пользователе
        vk_session = vk_api.VkApi(token=access_token)
        vk = vk_session.get_api()
        
        users = vk.users.get(user_ids=user_id, fields='first_name,last_name,photo_200,photo_max_orig')
        if not users:
            return None, "Не удалось получить данные пользователя"
        
        user_info = users[0]
        user_info['access_token'] = access_token
        user_info['email'] = email
        user_info['vk_link'] = f"https://vk.com/id{user_id}"
        
        return user_info, None
        
    except Exception as e:
        return None, f"Ошибка авторизации: {str(e)}"

def register_vk_user(vk_user_info):
    """Регистрация пользователя через VK"""
    users = get_donate_users()
    user_id_str = str(vk_user_info['id'])
    
    # Проверяем, не зарегистрирован ли уже пользователь
    if user_id_str in users:
        return False, "Этот VK аккаунт уже зарегистрирован!"
    
    # Создаем пользователя
    new_user = {
        'vk_id': user_id_str,
        'vk_link': vk_user_info['vk_link'],
        'email': vk_user_info.get('email', ''),
        'access_token': vk_user_info.get('access_token', ''),
        'created_at': datetime.now().isoformat(),
        'donations': [],
        'vk_info': {
            'first_name': vk_user_info.get('first_name', ''),
            'last_name': vk_user_info.get('last_name', ''),
            'photo': vk_user_info.get('photo_200', vk_user_info.get('photo_max_orig', ''))
        }
    }
    
    users[user_id_str] = new_user
    save_donate_users(users)
    
    return True, new_user

def login_vk_user(vk_user_info):
    """Авторизация пользователя через VK"""
    users = get_donate_users()
    user_id_str = str(vk_user_info['id'])
    
    if user_id_str in users:
        # Обновляем токен и информацию
        users[user_id_str]['access_token'] = vk_user_info.get('access_token', '')
        users[user_id_str]['vk_info'] = {
            'first_name': vk_user_info.get('first_name', ''),
            'last_name': vk_user_info.get('last_name', ''),
            'photo': vk_user_info.get('photo_200', vk_user_info.get('photo_max_orig', ''))
        }
        save_donate_users(users)
        return True, users[user_id_str]
    
    # Если пользователь не найден, регистрируем
    return register_vk_user(vk_user_info)

def get_current_user():
    """Получение текущего пользователя из сессии"""
    if 'user_id' in session:
        users = get_donate_users()
        return users.get(session['user_id'])
    return None

def handle_vkid_callback():
    """Обработка callback от VK ID"""
    code = request.json.get('code')
    device_id = request.json.get('device_id')
    
    if not code or not device_id:
        return False, "Не получены необходимые данные от VK ID"
    
    # Обмен кода на токен
    token_data, error = exchange_vkid_code(code, device_id)
    if error:
        return False, error
    
    # Получение данных пользователя
    vk_user, error = get_vk_user_by_vkid(token_data['access_token'])
    if error:
        return False, error
    
    # Авторизация/регистрация пользователя
    success, result = login_vk_user(vk_user)
    if success:
        session['user_id'] = str(vk_user['id'])
        session.permanent = True
        return True, result
    else:
        return False, result