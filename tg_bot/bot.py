import telebot
import sqlite3
import requests
import json
from telebot import types
import datetime


API_TOKEN = '6884099789:AAGods1wM1dFib-1-zCaZYLtv4bEpVR5SkI'
bot = telebot.TeleBot(API_TOKEN)
token = ''
domen = ''
contLang = ''
listPhoto = []
myReviews = []
now = datetime.datetime.now()
# Приветствие на команды 'help', 'start'
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    bot.reply_to(message,f'Здравствуйте, {message.from_user.first_name}!\U0001F91A\n Для работы с ботом, введите следующие данные:\n 1. Домен аккаунта в формате ******.brandquad.ru\n 2. Email в системе BQ\n 3. Действующий TOKEN авторизации\n \U00002757 Данные необходимо ввести одной строкой, последовательно, через запятую.')
# Обработка любых сообщений
@bot.message_handler()
def get_info(message):
    global token
    global domen
    if 'brandquad.ru,' in message.text.replace(' ', ''):
        try:
            domen = message.text.replace(' ', '').split(',')[0]
            token = message.text.replace(' ', '').split(',')[2]
            email = message.text.replace(' ', '').split(',')[1]
            return check_db(message, domen, token, email)
        except:
            bot.reply_to(message, 'Введены некорректные данные\U0001F613 повторите попытку')
    else:
        bot.reply_to(message, 'Что то на непонятном\U0001F614 повторите ввод')
# Проверка наличия указанных доступов в базе, если она уже создана
def check_db(message, domen, token, email):
        global contLang
        try:
            conn = sqlite3.connect('users_data.sql')
            cur = conn.cursor()
            cur.execute(f'SELECT * FROM users WHERE tgid={message.from_user.id}')
            users = cur.fetchall()
            cur.close()
            conn.close()
            if len(users) != 0:
                for user in users:
                    if domen == user[7] and email == user[6] and token == user[5]:
                        contLang = user[2]
                        userName = user[1]
                        accId = user[3]
                        tgid = user[4]
                        markup = types.InlineKeyboardMarkup(row_width=2)
                        btn_start = types.InlineKeyboardButton('Начать', callback_data='back')
                        markup.add(btn_start)
                        bot.send_message(message.chat.id, f'{userName}, вы авторизованы\U00002714', reply_markup=markup)
                        break
                    else:
                        return connect_api(domen, token, email, message)
        except:
            return connect_api(domen, token, email, message)

# Подключение по указанным доступам, получение данных о пользователе
def connect_api(domen, token, email, message):
    global contLang
    headers = {
        'TOKEN': token
    }
    api_user = requests.get(f'https://{domen}/api/public/v3/user/?email_in={email}', headers=headers)
    if api_user.status_code == 200:
        userName = json.loads(api_user.text)['results'][0]['username']
        contLang = json.loads(api_user.text)['results'][0]['_content_language']
        accId = json.loads(api_user.text)['results'][0]['id']
        return data_save(userName, contLang, accId, message, token, email, domen)
    else:
        return 'Введены некорректные данные, повторите попытку'
# Создание базы, если ее не было, добавление новых уникальных записей    
def data_save(userName, contLang, accId, message, token, email, domen):
    global now
    try:
        conn = sqlite3.connect('users_data.sql')
        cur = conn.cursor()

        cur.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username varchar(50), contlang varchar(50), accid varchar(50), tgid varchar(50), token varchar(50), email varchar(50), domen varchar(50), date varchar(50))')
        conn.commit()
        cur.close()
        conn.close()

        conn = sqlite3.connect('users_data.sql')
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, contlang, accid, tgid, token, email, domen, date) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')" % (userName, contLang, accId, message.from_user.id, token, email, domen, now))
        conn.commit()
        cur.close()
        conn.close()
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_start = types.InlineKeyboardButton('Начать', callback_data='back')
        markup.add(btn_start)
        return bot.send_message(message.chat.id, f'{userName}, регистрация прошла успешно\U00002714', reply_markup=markup)
    except:
        return bot.reply_to(message, 'Ошибка регистрации')
# Обработчик всех кнопок    
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    global listPhoto
    global domen
    global token
    global contLang
    values = call.data
    if domen and token and contLang:
        if values == 'products':
            markup = types.InlineKeyboardMarkup(row_width=1)
            btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data='back')
            markup.add(btn_back)
            bot.send_message(call.message.chat.id, 'Введите SKU или название товара для поиска', reply_markup=markup)
            bot.register_next_step_handler(call.message, getprod)
        elif values == 'files':
            markup = types.InlineKeyboardMarkup(row_width=1)
            btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data='back')
            markup.add(btn_back)
            bot.send_message(call.message.chat.id, 'Введите название файла', reply_markup=markup)
            bot.register_next_step_handler(call.message, getphoto)
        elif values == 'info':
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn_lim = types.InlineKeyboardButton('\U0001F6A9 Лимит запросов', callback_data='limits')
            btn_dinfo = types.InlineKeyboardButton('\U00002754 Информация', callback_data='data_info')
            btn_rev = types.InlineKeyboardButton('\U0000270F Оставить отзыв', callback_data='review')
            btn_about = types.InlineKeyboardButton('\U0001F9F7 О боте', callback_data='about')
            btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data='back')
            markup.add(btn_lim, btn_dinfo, btn_rev, btn_about, btn_back)
            bot.send_message(call.message.chat.id, 'Выберите опцию', reply_markup=markup)
        elif values == 'back':
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn_prod = types.InlineKeyboardButton('\U0001F50D Поиск товара', callback_data='products')
            btn_file = types.InlineKeyboardButton('\U0001F4C4 Поиск файла', callback_data='files')
            btn_info = types.InlineKeyboardButton('\U00002754 Информация и помощь', callback_data='info')
            markup.add(btn_prod, btn_file, btn_info)
            bot.send_message(call.message.chat.id, 'Выберите опцию:', reply_markup=markup)
        elif values == 'limits':
            return getLimits(call.message)
        elif values == 'data_info':
            markup = types.InlineKeyboardMarkup(row_width=1)
            btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data='back')
            markup.add(btn_back)
            info = '''
Представляем вашему вниманию уникального помощника Brand Quad! Этот бот создан специально для облегчения работы с продуктами компании.
Он позволит вам моментально находить нужную информацию и экономить ваше время.
Вам больше не придется тратить часы на поиски товаров или файлов! Просто введите запрос - и бот выдаст результаты за считанные секунды.

Вы сможете:
\U00002714 Быстро искать товары по SKU или названию
\U00002714 Находить нужные файлы по ключевым словам
\U00002714 Получать контакты ответственных менеджеров
\U00002714 Узнавать о дополнительных возможностях бота
\U00002714 Оставлять отзывы и предложения по улучшению

Работа с ботом интуитивно понятна и проста. Он сам подстроится под ваши потребности, учитывая предпочитаемый язык.
Повысьте эффективность с Brand Quad! Экономьте время и получайте нужную информацию за считанные секунды. Попробуйте уже сейчас!
'''
            bot.send_message(call.message.chat.id, info, reply_markup=markup)
        elif values == 'review':
            markup = types.InlineKeyboardMarkup(row_width=1)
            btn_back = types.InlineKeyboardButton('\U0001F519 Отменить и вернуться', callback_data='back')
            markup.add(btn_back)
            bot.send_message(call.message.chat.id, 'Укажите текст отзыва:\n Какие улучшения или нововведения хотелось бы видеть в боте.\n Пожелания.', reply_markup=markup)
            bot.register_next_step_handler(call.message, get_review)
        elif values == 'more':
            if len(listPhoto) > 5:
                listPhotoToSend = listPhoto[0:5]
                for url in listPhotoToSend:
                    listPhoto.remove(url)
                markup = types.InlineKeyboardMarkup(row_width=1)
                btn_more = types.InlineKeyboardButton('Показать еще >>>', callback_data='more')
                btn_file = types.InlineKeyboardButton('\U0001F50D Новый поиск файла', callback_data='files')
                btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data='back')
                markup.add(btn_more, btn_file, btn_back)
                bot.send_message(call.message.chat.id, '\n'.join(listPhotoToSend), reply_markup=markup)
            else:
                markup = types.InlineKeyboardMarkup(row_width=1)
                btn_file = types.InlineKeyboardButton('\U0001F50D Новый поиск файла', callback_data='files')
                btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data='back')
                markup.add(btn_file, btn_back)
                bot.send_message(call.message.chat.id, '\n'.join(listPhoto), reply_markup=markup)
                listPhoto.clear()
        elif values == 'my_rev':
            markup = types.InlineKeyboardMarkup(row_width=1)
            btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data='back')
            markup.add(btn_back)
            listRev = []
            if len(myReviews) != 0:
                for rev in myReviews:
                    listRev.append(rev[1])
                    listRev.append(rev[3])
                bot.send_message(call.message.chat.id, '\n'.join(listRev), reply_markup=markup)
            else:
                bot.send_message(call.message.chat.id, 'Отзывы не найдены', reply_markup=markup)
        elif values == 'about':
            markup = types.InlineKeyboardMarkup(row_width=1)
            btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data='back')
            markup.add(btn_back)
            try:
                with open('about.txt', "r", encoding='utf-8') as aboutInfo:
                    bot.send_message(call.message.chat.id, aboutInfo.read(), reply_markup=markup)
            except:
                bot.send_message(call.message.chat.id, 'Файл с информацией недоступен', reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, 'Вы не авторизованы. Пройдите авторизацию, подробнее /start')

# Получение данных о товаре
def getprod(message):
        global domen
        global token
        global contLang
        if domen and token and contLang:
            headers = {
                'TOKEN': token
            }
            markup = types.InlineKeyboardMarkup(row_width=1)
            btn_prod = types.InlineKeyboardButton('\U0001F50D Новый поиск товара', callback_data='products')
            btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data='back')
            markup.add(btn_prod, btn_back)
            try:
                prodRequest = requests.get(f'https://{domen}/api/public/v3/products/{message.text}', headers=headers).json()
                attributes = prodRequest[0]['attributes']
                photo = prodRequest[0]['meta']['cover']
                result_attrs = ''
                for attr in attributes.values():
                    try:
                        if attr[0]['locale'] == contLang: # Учет языка контента для вывода атрибутов
                            aName = attr[0]['name']
                            if type(attr[0]['value']) == list: # Если у атрибута несколько значений
                                aValue = ', '.join(attr[0]['value'])
                            else:
                                aValue = attr[0]['value']
                            result_attrs += f'{aName}: {aValue}\n'
                    except:
                        pass
                bot.send_photo(message.chat.id, photo)
                bot.send_message(message.chat.id, result_attrs, reply_markup=markup)

            except:
                try:
                    # Вещи, которые идут индивидуально для каждого аккаунта, у всех разные наименования, ID атрибутов, filters будут разные.
                    params = {
                            'filters': '{"attribute_type": 1, "id": 6, "exp": "in", "name": "Наименование товара", "lang": "'+ contLang + '", "pickle__strong": true, "val": ["'+ message.text +'"], "ref_list_id": null,"type": "6"}'}
                    prodRequest = requests.get(f'https://{domen}/api/public/v3/products/', headers=headers, params=params).json()
                    photo = prodRequest['results'][0]['meta']['cover']
                    attributes = prodRequest['results'][0]['attributes']
                    result_attrs = ''
                    for attr in attributes.values():
                        try:
                            aName = attr[0]['name']
                            if type(attr[0]['value']) == list:
                                aValue = ', '.join(attr[0]['value'])
                            else:
                                aValue = attr[0]['value']
                            result_attrs += f'{aName}: {aValue}\n'
                        except:
                            pass
                    bot.send_photo(message.chat.id, photo)
                    bot.send_message(message.chat.id, result_attrs, reply_markup=markup)
                except:
                    bot.send_message(message.chat.id, 'Товар не найден', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, 'Вы не авторизованы, воспользуйтесь /start')
# Поиск фото            
def getphoto(message):
        global domen
        global token
        global listPhoto
        if domen and token:
            headers = {
                'TOKEN': token
            }
            markup1 = types.InlineKeyboardMarkup(row_width=1)
            btn_photo = types.InlineKeyboardButton('\U0001F50D Новый поиск файла', callback_data='files')
            btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data='back')
            markup1.add(btn_photo, btn_back)
            fileRequest = requests.get(f'https://{domen}/api/public/v3/dam/files/?name={message.text}', headers=headers)
            if fileRequest.status_code == 200:
                try:
                    listPhotoToSend = []
                    for i in range(len(fileRequest.json()['results'])):
                        listPhoto.append(fileRequest.json()['results'][i]['url'])
                    if len(listPhoto) > 5:
                        listPhotoToSend = listPhoto[0:5]
                        for url in listPhotoToSend:
                            listPhoto.remove(url)
                        markup = types.InlineKeyboardMarkup(row_width=1)
                        btn_more = types.InlineKeyboardButton('Показать еще >>>', callback_data='more')
                        markup.add(btn_more, btn_photo, btn_back)
                        bot.send_message(message.chat.id, '\n'.join(listPhotoToSend), reply_markup=markup)
                    else:
                        bot.send_message(message.chat.id, '\n'.join(listPhoto), reply_markup=markup1)
                        listPhoto.clear()
                except:
                    bot.send_message(message.chat.id, 'Файл не найден', reply_markup=markup1)
        else:
            bot.send_message(message.chat.id, 'Вы не авторизованы, воспользуйтесь /start')

def getLimits(message): # Забирает лимит запросов
    global domen
    global token
    if domen and token:
        headers = {
            'TOKEN': token
        }
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data='back')
        markup.add(btn_back)
        limitReq = requests.get(f'https://{domen}/api/public/v3/request-limits', headers=headers)
        if limitReq.status_code == 200:
            try:
                jsonLimitReq = json.loads(limitReq.text)
                limitDay = jsonLimitReq['api_requests_per_day']
                countDay = jsonLimitReq['api_requests_count_by_day']
                bot.send_message(message.chat.id,f'На данный момент у вас {countDay} запросов из {limitDay} доступных.\n При поиске файла или товара, а также регистрации, запросы расходуются.', reply_markup=markup)
            except:
                bot.send_message(message.chat.id, 'Нет информации о лимитах запросов', reply_markup=markup)


    else:
        bot.send_message(message.chat.id, 'Вы не авторизованы, воспользуйтесь /start')

def get_review(message): # Записывает отзыв в бд
    global myReviews
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data='back')
    btnMyRev = types.InlineKeyboardButton('Мои отзывы', callback_data='my_rev')
    markup.add(btnMyRev, btn_back)
    try:
        conn = sqlite3.connect('users_data.sql')
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, date varchar(50), username varchar(50), review varchar(50), tgid varchar(50))')
        conn.commit()
        cur.close()
        conn.close()
        conn = sqlite3.connect('users_data.sql')
        cur = conn.cursor()
        cur.execute("INSERT INTO reviews (date, username, review, tgid) VALUES ('%s', '%s', '%s', '%s')" % (now, message.from_user.first_name + ' ' + message.from_user.last_name, message.text, message.from_user.id))
        conn.commit()
        cur.execute(f'SELECT * FROM reviews WHERE tgid={message.from_user.id}')
        myReviews = cur.fetchall()
        cur.close()
        conn.close()
        bot.send_message(message.chat.id, 'Отзыв был успешно записан, спасибо!', reply_markup=markup)
    except:
        bot.send_message(message.chat.id, 'Не удалось записать отзыв, повторите попытку позже', reply_markup=markup)
        
bot.infinity_polling()