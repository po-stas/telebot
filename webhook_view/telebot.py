# Backend part. process_query called by django when telegram sends an update through webhook

import requests
import telegram
import json
import re
from allclimbApp.logging import log
from django.http import HttpResponse

try:
    global bot
    global TOKEN
    TOKEN = 'telegram_token'
    bot = telegram.Bot(token=TOKEN)
except Exception as e:
    log('TELEBOT: init error!!')
    log(str(e))

url = 'http://127.0.0.1:5000/' # internal url for flask app with squad (in dev mode now, but later it will use wsgi)
URL = 'url_for_telegram'

def process_query(request):
    try:
        received_json_data = json.loads(request.body)
        update = telegram.Update.de_json(received_json_data, bot)

        if update.message is None:
            log('TELEBOT: message is None')
            return HttpResponse('')

        chat_id = update.message.chat.id
        msg_id = update.message.message_id

        text = update.message.text.encode('utf-8').decode()

        if text == "/start":
            # print the welcoming message
            bot_welcome = """
Привет!
Это чат-бот AllClimb.
Я могу рассказать вам о скалолазных маршрутах, которые есть в нашей базе.
Просто напишите название интересующего маршрута, или задайте вопрос, например:
'Сколько веревки нужно на крымском гекконе' или
'Кто автор кардамона молотого' или
'Где находится маршрут химера'..
И я постараюсь ответить :)
            """
            # send the welcoming message
            bot.sendMessage(chat_id=chat_id, text=bot_welcome, reply_to_message_id=msg_id)
            return HttpResponse('')

        else:
            try:
                bot.sendChatAction(chat_id=chat_id, action="typing")
                try:
                    response = requests.get(url=url, params={'query': text})
                except Exception as e:
                    log('TELEBOT: error querying flask-squad')
                    log(str(e))
                    raise
                if response.ok:
                    answer = response.json()
                    score = answer['score']

                    if float(score) > 0.3:
                        # Poor match...
                        bot.sendMessage(chat_id=chat_id, text='''Не очень понял о каком маршруте идет речь,
Пожалуйста, попробуй написать название точнее..''', reply_to_message_id=msg_id)
                        return HttpResponse('')

                    bot.sendMessage(chat_id=chat_id, text=answer['answer'], reply_to_message_id=msg_id)
                    return HttpResponse('')

            except Exception as e:
                # if things went wrong
                log('TELEBOT: something wrong')
                log(str(e))
                bot.sendMessage(chat_id=chat_id,
                                text="Что-то пошло не так... Попробуй спросить снова",
                                reply_to_message_id=msg_id)
                return HttpResponse('')
    except Exception as e:
        log('TELEBOT: some error!!!')
        log(str(e))
        return HttpResponse('')


# Function to call manually only once (through the shell interface)
def set_webhook():
    result = bot.setWebhook(f'{URL}')
    if result:
        return "Webhook setup is OK"
    else:
        return "Webhook setup failed"
