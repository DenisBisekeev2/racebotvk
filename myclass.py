# [file name]: myclass.py
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import datetime
import json
import random
import time
import re
from config import *
GROUP_ID = "233724428"

class Message:
    def __init__(self, event, vk_api_instance):
        self.event = event
        self.vk = vk_api_instance
        self._user_info_cache = None
        self._chat_info_cache = None

        # Определяем тип события (объект или словарь)
        self._is_dict = isinstance(event, dict)

    @property
    def peer_id(self):
        """ID чата/беседы"""
        if self._is_dict:
            return self.event.get('peer_id')
        return getattr(self.event, 'peer_id', None)

    # БАЗОВЫЕ СВОЙСТВА СООБЩЕНИЯ
    @property
    def from_id(self):
        """ID отправителя"""
        if self._is_dict:
            return self.event.get('from_id', self.event.get('user_id'))
        return self.event.user_id

    @property
    def payload(self):
        """Получить Payload"""
        if self._is_dict:
            payload_str = self.event.get('payload')
            if payload_str:
                try:
                    if isinstance(payload_str, str):
                        return json.loads(payload_str)
                    else:
                        return payload_str
                except:
                    return None
        return getattr(self.event, 'payload', None)

    @property
    def text(self):
        """Текст сообщения"""
        if self._is_dict:
            return self.event.get('text', '')
        return self.event.text

    @property
    def id(self):
        """ID сообщения"""
        if self._is_dict:
            return self.event.get('id')
        return self.event.message_id

    @property
    def conversation_message_id(self):
        """ID сообщения в беседе"""
        if self._is_dict:
            return self.event.get('conversation_message_id')
        return getattr(self.event, 'conversation_message_id', None)

    # ТИПЫ СООБЩЕНИЙ
    @property
    def is_private(self):
        """Личное сообщение"""
        return self.peer_id == self.from_id

    @property
    def is_group_chat(self):
        """Беседа/групповой чат"""
        return self.peer_id != self.from_id

    @property
    def is_chat(self):
        """Сообщение из беседы"""
        return self.peer_id > 2000000000

    @property
    def chat_id(self):
        """ID беседы (если это беседа)"""
        return self.peer_id - 2000000000 if self.is_chat else None

    # ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ
    @property
    def user_info(self):
        """Полная информация о пользователе"""
        if self._user_info_cache is None:
            try:
                users = self.vk.users.get(
                    user_ids=self.from_id,
                    fields='first_name,last_name'
                )
                self._user_info_cache = users[0] if users else {}
            except Exception as e:
                print(f"Ошибка получения информации о пользователе: {e}")
                self._user_info_cache = {}
        return self._user_info_cache

    @property
    def first_name(self):
        """Имя пользователя"""
        return self.user_info.get('first_name', 'Неизвестно')

    @property
    def last_name(self):
        """Фамилия пользователя"""
        return self.user_info.get('last_name', 'Неизвестно')

    @property
    def full_name(self):
        """Полное имя пользователя"""
        return f"{self.first_name} {self.last_name}"

    # ИНФОРМАЦИЯ О ЧАТЕ (для бесед)
    @property
    def chat_info(self):
        """Информация о беседе"""
        if self._chat_info_cache is None and self.is_chat:
            try:
                chat = self.vk.messages.getConversationsById(peer_ids=self.peer_id)
                self._chat_info_cache = chat['items'][0] if chat.get('items') else {}
            except Exception as e:
                print(f"Ошибка получения информации о чате: {e}")
                self._chat_info_cache = {}
        return self._chat_info_cache or {}

    @property
    def chat_title(self):
        """Название беседы"""
        if self.is_chat:
            chat_settings = self.chat_info.get('chat_settings', {})
            return chat_settings.get('title', 'Без названия')
        return None

    # МЕТОДЫ ДЛЯ РАБОТЫ С СООБЩЕНИЯМИ
    def reply(self, text, attachment=None, keyboard=None, peer_id=None):
        """Ответить на сообщение"""
        if peer_id == None:
            peer_id = self.peer_id
        else:
            peer_id = peer_id
        params = {
            'peer_id': peer_id,
            'message': text,
            'random_id': 0
        }

        if attachment:
            params['attachment'] = attachment
        if keyboard:
            params['keyboard'] = keyboard

        try:
            result = self.vk.messages.send(**params)
            return result
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
            return None

    def edit(self, text, keyboard=None):
        """Редактировать сообщение (для callback)"""
        if not self.conversation_message_id:
            return False

        try:
            params = {
                'peer_id': self.peer_id,
                'conversation_message_id': self.conversation_message_id,
                'message': text
            }

            if keyboard:
                params['keyboard'] = keyboard

            self.vk.messages.edit(**params)
            return True
        except Exception as e:
            print(f"Ошибка редактирования сообщения: {e}")
            return False

    def pin_message(self, message_id):
        """Закрепить сообщение в чате"""
        if not self.is_chat:
            return False

        try:
            self.vk.messages.pin(
                peer_id=self.peer_id,
                conversation_message_id=message_id
            )
            return True
        except Exception as e:
            print(f"Ошибка закрепления сообщения: {e}")
            return False
    def isMember(self, user_id):
        if self.vk.groups.isMember(group_id=GROUP_ID, user_id=user_id):
            return True
        return False
    def get_mention(self, user_id=None):
        """Получить упоминание пользователя"""
        target_id = user_id or self.from_id
        return f"[id{target_id}|{self.first_name}]"

    def extract_user_id(self, text):
        """Извлечь ID пользователя из текста (упоминание или ссылка)"""
        # Упоминание [id123|Name]
        mention_match = re.search(r'\[id(\d+)\|', text)
        if mention_match:
            return int(mention_match.group(1))

        # Ссылка vk.com/id123 или vk.com/username
        link_match = re.search(r'vk\.com/(?:id(\d+)|([\w\.]+))', text)
        if link_match:
            if link_match.group(1):  # id123
                return int(link_match.group(1))
            else:  # username
                username = link_match.group(2)
                try:
                    users = self.vk.users.get(user_ids=username)
                    return users[0]['id'] if users else None
                except:
                    return None

        return None

class Race:
    def __init__(self, race_id, chat_id, creator_id, is_global=False):
        self.race_id = race_id
        self.chat_id = chat_id
        self.creator_id = creator_id
        self.is_global = is_global
        self.players = {}  # {user_id: player_data}
        self.status = "waiting"  # waiting, in_progress, finished
        self.start_time = None
        self.distance = GLOBAL_RACE_DISTANCE if is_global else RACE_DISTANCE
        self.message_id = None
        self.pinned_message_id = None
        self.creation_time = time.time()

    def add_player(self, user_id, user_name, car_data):
        if self.status != "waiting":
            return False, "Гонка уже началась!"

        max_players = MAX_PREMIUM_PLAYERS if self.is_chat_premium() else MAX_PLAYERS
        if len(self.players) >= max_players:
            return False, "Достигнут лимит игроков!"

        if user_id in self.players:
            return False, "Вы уже участвуете в гонке!"

        self.players[user_id] = {
            'user_name': user_name,
            'car': car_data,
            'progress': 0,
            'speed': 0,
            'finished': False,
            'position': 0,
            'finish_time': None
        }
        return True, "Игрок добавлен!"
    def get_players_with_colors(self):
        """Получить игроков с информацией о цветах их машин"""
        players_with_colors = {}
        users_data = load_data(USERS_DB_FILE)

        for user_id, player in self.players.items():
            user_id_str = str(user_id)
            if user_id_str in users_data.get('users', {}):
                user = users_data['users'][user_id_str]
                car_colors = user.get('car_colors', {})

                # Находим активную машину
                active_car_id = user.get('active_car')
                if active_car_id and active_car_id in user.get('cars', {}):
                    car_color = car_colors.get(active_car_id, '#FF0000')  # Красный по умолчанию

                    players_with_colors[user_id] = {
                        'user_name': player['user_name'],
                        'car': player['car'],
                        'color': car_color,
                        'progress': player['progress'],
                        'finished': player['finished']
                    }

        return players_with_colors
    def remove_player(self, user_id):
        if user_id in self.players:
            del self.players[user_id]
            return True
        return False

    def start_race(self, user_id):
        if user_id != self.creator_id:
            return False, "Только создатель гонки может её начать!"

        if len(self.players) < MIN_PLAYERS:
            return False, f"Недостаточно игроков! Минимум: {MIN_PLAYERS}"

        self.status = "in_progress"
        self.start_time = time.time()
        return True, "Гонка началась!"

    def update_race(self):
        if self.status != "in_progress":
            return False

        race_finished = True

        # Обновляем прогресс каждого игрока
        for user_id, player in self.players.items():
            if player['finished']:
                continue

            # Расчет скорости
            player['speed'] = self.calculate_speed(player)
            player['progress'] += player['speed']

            # Проверка на финиш
            if player['progress'] >= self.distance:
                player['finished'] = True
                player['progress'] = self.distance
                player['finish_time'] = time.time() - self.start_time
            else:
                race_finished = False

        if race_finished:
            self.status = "finished"
            self.calculate_results()
            return True

        return False

    def calculate_speed(self, player_data):
        """Расчет скорости с учетом всех характеристик"""
        car = player_data['car']

        # Базовая скорость
        base_speed = car['max_speed'] * 0.3

        # Бонус от лошадиных сил
        hp_boost = car['hp'] * 0.002

        # Эффект износа шин и состояния
        tire_effect = car['tire_health'] / 100
        durability_effect = car.get('durability', 100) / 100

        # Случайный фактор
        random_factor = random.uniform(0.9, 1.1)

        # Итоговая скорость
        final_speed = (base_speed + hp_boost) * tire_effect * durability_effect * random_factor

        return final_speed

    def calculate_results(self):
        """Расчет результатов гонки"""
        results = []
        for user_id, player in self.players.items():
            if player['finished']:
                results.append((user_id, player['finish_time'], player['progress']))
            else:
                results.append((user_id, float('inf'), player['progress']))

        # Сортировка по прогрессу (убывание), затем по времени финиша
        results.sort(key=lambda x: (-x[2], x[1]))

        for i, (user_id, _, _) in enumerate(results):
            self.players[user_id]['position'] = i + 1

    def is_chat_premium(self):
        chats_data = load_data(CHATS_DB_FILE)
        chat_info = chats_data.get('chats', {}).get(str(self.chat_id), {})
        return chat_info.get('premium', False)

    def get_race_info(self):
        if self.status == "waiting":
            text = "🏎️ ГОНКА ОЖИДАЕТ ИГРОКОВ\n\n"
            text += f"📍 Дистанция: {format_number(self.distance)}м\n"
            text += f"👥 Участников: {len(self.players)}/{MAX_PLAYERS}\n"
            text += f"🎯 Необходимо минимум: {MIN_PLAYERS}\n\n"

            if self.players:
                text += "Участники:\n"
                for user_id, player in self.players.items():
                    text += f"• {player['user_name']} - {player['car']['name']}\n"
            else:
                text += "Пока нет участников\n"

            return text

        elif self.status == "in_progress":
            text = "🏁 ГОНКА В ПРОЦЕССЕ!\n\n"
            # Сортируем по прогрессу
            sorted_players = sorted(self.players.items(), key=lambda x: x[1]['progress'], reverse=True)

            for i, (user_id, player) in enumerate(sorted_players):
                progress_percent = min(100, int(player['progress'] / self.distance * 100))
                progress_bar = "█" * int(progress_percent / 5) + "▒" * (20 - int(progress_percent / 5))

                if player['finished']:
                    status = f"🏁 ФИНИШ ({player['finish_time']:.1f}с)"
                else:
                    status = f"🚗 {progress_percent}%"

                text += f"{i+1}. {player['user_name']}\n   {progress_bar} {status}\n"

            return text

        else:  # finished
            text = "🏆 ГОНКА ЗАВЕРШЕНА!\n\nРЕЗУЛЬТАТЫ:\n\n"
            sorted_players = sorted(self.players.items(), key=lambda x: x[1]['position'])

            for user_id, player in sorted_players:
                position = player['position']
                if position == 1:
                    position_emoji = "🥇"
                elif position == 2:
                    position_emoji = "🥈"
                elif position == 3:
                    position_emoji = "🥉"
                else:
                    position_emoji = f"{position}."

                status = f"{player.get('finish_time', 0):.1f}с"

                text += f"{position_emoji} {player['user_name']} - {player['car']['name']} ({status})\n"

            return text

class DragRace:
    def __init__(self, player1_id, player2_id, chat_id):
        self.player1_id = player1_id
        self.player2_id = player2_id
        self.chat_id = chat_id
        self.status = "waiting"
        self.start_time = None
        self.distance = 400  # короткая дистанция для драга
        self.players = {}

    def add_player(self, user_id, user_name, car_data):
        self.players[user_id] = {
            'user_name': user_name,
            'car': car_data,
            'progress': 0,
            'finished': False,
            'finish_time': None
        }

    def start_race(self):
        self.status = "in_progress"
        self.start_time = time.time()

    def update_race(self):
        if self.status != "in_progress":
            return False

        race_finished = True

        # Обновляем прогресс каждого игрока
        for user_id, player in self.players.items():
            if player['finished']:
                continue

            # Расчет скорости для драга
            speed = self.calculate_drag_speed(player)
            player['progress'] += speed

            # Проверка на финиш
            if player['progress'] >= self.distance:
                player['finished'] = True
                player['progress'] = self.distance
                player['finish_time'] = time.time() - self.start_time
            else:
                race_finished = False

        if race_finished:
            self.status = "finished"
            return True

        return False

    def calculate_drag_speed(self, player_data):
        """Расчет скорости для драг-рейсинга - УВЕЛИЧЕНА СКОРОСТЬ"""
        car = player_data['car']

        # УВЕЛИЧЕНА базовая скорость для быстрого прохождения 400м
        base_speed = car['hp'] * 0.03

        # Бонус от максимальной скорости
        speed_boost = car['max_speed'] * 0.01

        # Эффект износа
        condition_effect = (car['tire_health'] * car.get('durability', 100)) / 10000

        # Случайный фактор (уменьшен разброс)
        random_factor = random.uniform(0.95, 1.05)

        final_speed = (base_speed + speed_boost) * condition_effect * random_factor
        return final_speed

    def get_winner(self):
        """Получить победителя драга"""
        times = {}
        for user_id, player in self.players.items():
            if player['finished']:
                times[user_id] = player['finish_time']

        if len(times) == 2:
            return min(times, key=times.get)
        return None

    def get_race_info(self):
        text = "🔥 ДРАГ-РЕЙСИНГ!\n\n"
        text += "📍 Дистанция: 400м\n\n"

        for user_id, player in self.players.items():
            progress_percent = min(100, int(player['progress'] / self.distance * 100))
            # Визуальная полоса прогресса
            track_length = 20
            car_position = min(track_length - 1, int((player['progress'] / self.distance) * track_length))
            track_visual = "─" * track_length
            if car_position < track_length:
                track_visual = track_visual[:car_position] + "🚗" + track_visual[car_position+1:]

            if player['finished']:
                status = f"🏁 ФИНИШ! ({player['finish_time']:.2f}с)"
            else:
                status = f"{progress_percent}%"

            text += f"{player['user_name']}\n{track_visual}\n{status}\n\n"

        return text
# Добавляем в myclass.py после класса DragRace

class PvPRace:
    def __init__(self, race_id, player1_id, player2_id):
        self.race_id = race_id
        self.player1_id = player1_id
        self.player2_id = player2_id
        self.status = "waiting"  # waiting, in_progress, finished
        self.start_time = None
        self.distance = 1000  # дистанция гонки
        self.players = {}
        self.winner = None
        
    def add_player(self, user_id, user_name, car_data):
        """Добавить игрока в гонку"""
        self.players[user_id] = {
            'user_name': user_name,
            'car': car_data,
            'progress': 0,
            'speed': 0,
            'finished': False,
            'finish_time': None,
            'car_name': car_data['name']
        }
        
        # Если оба игрока добавлены - начинаем гонку
        if len(self.players) == 2:
            self.status = "in_progress"
            self.start_time = time.time()
            return True, "ready"
        return True, "waiting"
    
    def update_race(self):
        """Обновить состояние гонки"""
        if self.status != "in_progress":
            return False
            
        race_finished = True
        
        for user_id, player in self.players.items():
            if player['finished']:
                continue
                
            # Более реалистичный расчет скорости
            player['speed'] = self.calculate_realistic_speed(player)
            player['progress'] += player['speed']
            
            if player['progress'] >= self.distance:
                player['finished'] = True
                player['progress'] = self.distance
                player['finish_time'] = time.time() - self.start_time
            else:
                race_finished = False
        
        if race_finished:
            self.status = "finished"
            self.determine_winner()
            return True
            
        return False
    
    def calculate_realistic_speed(self, player_data, user_id):
        """Реалистичный расчет скорости с учетом характеристик машины"""
        car = player_data['car']
        
        # Базовые характеристики
        base_speed = (car['max_speed'] * 0.25) + (car['hp'] * 0.15)
        
        # Эффект износа (небольшое влияние)
        condition_multiplier = (car['tire_health'] * 0.7 + car.get('durability', 100) * 0.3) / 100
        
        # Случайный фактор (небольшой разброс)
        random_factor = random.uniform(0.95, 1.05)
        
        # Разница в характеристиках между машинами
        if len(self.players) == 2:
            player_ids = list(self.players.keys())
            other_player_id = player_ids[0] if player_ids[1] == user_id else player_ids[1]
            other_car = self.players[other_player_id]['car']
            
            # Сравнение характеристик (небольшое преимущество)
            hp_advantage = (car['hp'] - other_car['hp']) * 0.001
            speed_advantage = (car['max_speed'] - other_car['max_speed']) * 0.002
            
            advantage_bonus = hp_advantage + speed_advantage
        else:
            advantage_bonus = 0
        
        # Итоговая скорость (более сбалансированная)
        final_speed = base_speed * condition_multiplier * random_factor + advantage_bonus
        
        # Ограничиваем минимальную и максимальную скорость
        return max(5, min(25, final_speed))
    
    def determine_winner(self):
        """Определить победителя"""
        times = {}
        for user_id, player in self.players.items():
            if player['finished']:
                times[user_id] = player['finish_time']
        
        if times:
            self.winner = min(times, key=times.get)
            return self.winner
        return None
    
    def get_race_progress(self):
        """Получить визуальное представление гонки"""
        if len(self.players) != 2:
            return "Ожидание второго игрока..."
            
        player1 = self.players[self.player1_id]
        player2 = self.players[self.player2_id]
        
        track_length = 20
        p1_pos = min(track_length - 1, int((player1['progress'] / self.distance) * track_length))
        p2_pos = min(track_length - 1, int((player2['progress'] / self.distance) * track_length))
        
        # Создаем визуализацию трека
        track_visual = "─" * track_length
        
        # Размещаем машины на треке
        track_p1 = list(track_visual)
        track_p2 = list(track_visual)
        
        if p1_pos < track_length:
            track_p1[p1_pos] = "🚗"
        if p2_pos < track_length:
            track_p2[p2_pos] = "🚗"
            
        track_p1 = "".join(track_p1)
        track_p2 = "".join(track_p2)
        
        text = "🏁 PvP ГОНКА 🏁\n\n"
        text += f"{player1['user_name']}\n{track_p1} {player1['progress']:.0f}m\n\n"
        text += f"{player2['user_name']}\n{track_p2} {player2['progress']:.0f}m\n\n"
        
        if self.status == "finished" and self.winner:
            winner_name = self.players[self.winner]['user_name']
            text += f"🏆 ПОБЕДИТЕЛЬ: {winner_name}!"
            
        return text
    
    def get_players_data(self):
        """Получить данные игроков для создания изображения"""
        if len(self.players) != 2:
            return None
            
        return {
            'player1': {
                'id': self.player1_id,
                'name': self.players[self.player1_id]['user_name'],
                'car_name': self.players[self.player1_id]['car_name']
            },
            'player2': {
                'id': self.player2_id,
                'name': self.players[self.player2_id]['user_name'],
                'car_name': self.players[self.player2_id]['car_name']
            }
        }
def format_number(number):
    """Красивый вывод чисел"""
    return f"{number:,}".replace(",", " ")

def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": {}, "chats": {}} if filename == "users.json" or filename == "chats.json" else {}

def save_data(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)