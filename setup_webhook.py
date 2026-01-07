# [file name]: setup_webhook.py
import vk_api
from config import BOT_TOKEN, WEBHOOK_URL

def setup_webhook():
    vk_session = vk_api.VkApi(token=BOT_TOKEN)
    vk = vk_session.get_api()
    
    # Установка вебхука
    result = vk.groups.setLongPollSettings(
        group_id=233724428,
        enabled=1,
        api_version='5.199',
        message_new=1,
        message_event=1,
        group_join=1,
        message_reply=1
    )
    
    print("Webhook settings updated:", result)
    
    # Альтернативный способ через Bots LongPoll API
    # Нужно настроить в настройках группы в разделе "Работа с API"

if __name__ == '__main__':
    setup_webhook()