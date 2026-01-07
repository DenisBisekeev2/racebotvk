# [file name]: image_generator.py
import os
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import vk_api
from config import BOT_TOKEN

class RaceImageGenerator:
    def __init__(self):
        self.vk_session = vk_api.VkApi(token=BOT_TOKEN)
        self.vk = self.vk_session.get_api()
        
    def get_user_photo(self, user_id):
        """Получить фото пользователя"""
        try:
            users = self.vk.users.get(user_ids=user_id, fields='photo_200')
            if users and 'photo_200' in users[0]:
                response = requests.get(users[0]['photo_200'])
                return Image.open(BytesIO(response.content))
            return None
        except:
            return None
    
    def get_user_info(self, user_id):
        """Получить информацию о пользователе"""
        try:
            users = self.vk.users.get(user_ids=user_id, fields='first_name,last_name,photo_200')
            return users[0] if users else None
        except:
            return None
    
    def create_race_start_image(self, player1_id, player2_id, car1_name, car2_name):
        """Создать изображение начала гонки"""
        # Создаем основное изображение (800x400)
        img = Image.new('RGB', (800, 400), color=(30, 30, 40))
        draw = ImageDraw.Draw(img)
        
        try:
            # Загружаем шрифт (используем стандартный если нет кастомного)
            try:
                font_large = ImageFont.truetype("arial.ttf", 24)
                font_medium = ImageFont.truetype("arial.ttf", 18)
                font_small = ImageFont.truetype("arial.ttf", 14)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Получаем данные игроков
            player1_info = self.get_user_info(player1_id)
            player2_info = self.get_user_info(player2_id)
            
            # Загружаем аватарки
            player1_photo = self.get_user_photo(player1_id)
            player2_photo = self.get_user_photo(player2_id)
            
            # Левый игрок (игрок 1)
            if player1_photo:
                player1_photo = player1_photo.resize((80, 80))
                img.paste(player1_photo, (50, 50))
            
            # Правый игрок (игрок 2)
            if player2_photo:
                player2_photo = player2_photo.resize((80, 80))
                img.paste(player2_photo, (670, 50))
            
            # Имена игроков
            if player1_info:
                name1 = f"{player1_info['first_name']} {player1_info['last_name']}"
                draw.text((50, 140), name1, fill=(255, 255, 255), font=font_medium)
            
            if player2_info:
                name2 = f"{player2_info['first_name']} {player2_info['last_name']}"
                text_width = draw.textlength(name2, font=font_medium)
                draw.text((800 - 50 - text_width, 140), name2, fill=(255, 255, 255), font=font_medium)
            
            # Названия машин
            draw.text((50, 170), car1_name, fill=(200, 200, 200), font=font_small)
            text_width = draw.textlength(car2_name, font=font_small)
            draw.text((800 - 50 - text_width, 170), car2_name, fill=(200, 200, 200), font=font_small)
            
            # Линия старта
            draw.line([(400, 0), (400, 400)], fill=(100, 100, 100), width=2)
            
            # Эмодзи машин
            draw.text((180, 180), "🚗", fill=(255, 255, 255), font=ImageFont.load_default())
            draw.text((620, 180), "🚗", fill=(255, 255, 255), font=ImageFont.load_default())
            
            # Текст гонки
            draw.text((400, 300), "🏁 ГОНКА НАЧАЛАСЬ! 🏁", fill=(255, 215, 0), 
                     font=font_large, anchor="mm")
            
            # Сохраняем изображение
            os.makedirs('temp_images', exist_ok=True)
            filename = f"temp_images/race_{player1_id}_{player2_id}.png"
            img.save(filename)
            return filename
            
        except Exception as e:
            print(f"Ошибка создания изображения: {e}")
            return None
    
    def create_race_finish_image(self, winner_id, winner_car_name, loser_id=None):
        """Создать изображение финиша гонки"""
        img = Image.new('RGB', (600, 300), color=(30, 30, 40))
        draw = ImageDraw.Draw(img)
        
        try:
            try:
                font_large = ImageFont.truetype("arial.ttf", 28)
                font_medium = ImageFont.truetype("arial.ttf", 18)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
            
            winner_info = self.get_user_info(winner_id)
            winner_photo = self.get_user_photo(winner_id)
            
            if winner_photo:
                winner_photo = winner_photo.resize((100, 100))
                img.paste(winner_photo, (250, 50))
            
            # Победитель
            if winner_info:
                name = f"{winner_info['first_name']} {winner_info['last_name']}"
                draw.text((300, 160), name, fill=(255, 255, 255), font=font_medium, anchor="mm")
            
            draw.text((300, 185), winner_car_name, fill=(200, 200, 200), font=font_medium, anchor="mm")
            draw.text((300, 220), "🏆 ПОБЕДИТЕЛЬ! 🏆", fill=(255, 215, 0), font=font_large, anchor="mm")
            
            # Эмодзи машины победителя
            draw.text((300, 120), "🚗", fill=(255, 255, 255), font=ImageFont.load_default(), anchor="mm")
            
            os.makedirs('temp_images', exist_ok=True)
            filename = f"temp_images/finish_{winner_id}.png"
            img.save(filename)
            return filename
            
        except Exception as e:
            print(f"Ошибка создания финального изображения: {e}")
            return None