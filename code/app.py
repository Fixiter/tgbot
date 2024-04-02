import telebot
import sqlite3
import requests
import json
from telebot import types
import datetime
from flask import Flask
from flask import request
from flask import jsonify
from flask import Response
from fpdf import FPDF
import config
import os

app = Flask(__name__)
@app.route('/', methods = ['POST', 'GET'])
def index():
    if request.method == 'POST':
        update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
        return Response('ok', status=200)
    else:
        return 'tg_bot'

bot = telebot.TeleBot(config.BOT_API_TOKEN)
now = datetime.datetime.now()
# Приветствие на команды 'help', 'start'
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    bot.reply_to(message,f'Здравствуйте, {message.from_user.first_name}!\U0001F91A\n Для работы с ботом, понадобятся следующие данные:\n 1. Домен аккаунта\n 2. Email в системе BQ\n 3. Действующий TOKEN авторизации')
    bot.send_message(message.chat.id, 'Введите домен аккаунта в формате learning.brandquad.ru (без слешей и https):')
@bot.message_handler()
def get_info(message):
    if 'brandquad.ru,' in message.text.replace(' ', ''):
        try:
            domen = message.text.replace(' ', '').split(',')[0]
            token = message.text.replace(' ', '').split(',')[2]
            email = message.text.replace(' ', '').split(',')[1]
            return check_db(message, domen, token, email)
        except:
            bot.reply_to(message, 'Введены некорректные данные пользователя. Повторите ввод /start')
    elif 'brandquad' in message.text.lower() and not '@' in message.text.lower():
        bot.send_message(message.chat.id, 'Отлично! Теперь введите email аккаунта в формате login@brandquad.ru:')
        domen = message.text.lower()
        bot.register_next_step_handler(message, getEmail, domen)
    else:
        bot.reply_to(message, 'Невозможно определить ввод. Нажмите любую кнопку или воспользуйтесь /start')
# Проверка наличия указанных доступов в базе, если она уже создана
def check_db(message, domen, token, email):
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
                        id = user[0]
                        print(str(id) + 'есть в бд')
                        markup = types.InlineKeyboardMarkup(row_width=2)
                        btn_start = types.InlineKeyboardButton('Начать', callback_data=str(id) + '_back')
                        markup.add(btn_start)
                        bot.send_message(message.chat.id, f'{userName}, вы авторизованы\U00002714', reply_markup=markup)
                        break
                if not userName:
                    return connect_api(domen, token, email, message)

            else:
                return connect_api(domen, token, email, message)
        except:
            return connect_api(domen, token, email, message)

# Подключение по указанным доступам, получение данных о пользователе
def connect_api(domen, token, email, message):
    headers = {
        'TOKEN': token
    }
    api_user = requests.get(f'https://{domen}/api/public/v3/user/?email_in={email}', headers=headers)
    if api_user.status_code == 200:
        userName = json.loads(api_user.text)['results'][0]['username']
        contLang = json.loads(api_user.text)['results'][0]['_content_language']
        accId = json.loads(api_user.text)['results'][0]['id']
        print(f'Данные верны, {userName}, {contLang}, {accId}')
        return data_save(userName, contLang, accId, message, token, email, domen)
    else:
        bot.send_message(message.chat.id, 'Введены некорректные данные, проверьте, все ли верно указано - /start')
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
        conn = sqlite3.connect('users_data.sql')
        cur = conn.cursor()
        cur.execute(f'SELECT * FROM users WHERE tgid={message.from_user.id} AND username="{userName}" AND contlang="{contLang}" AND accid={accId} AND token="{token}" AND email="{email}" AND domen="{domen}"')
        user = cur.fetchall()
        user = user[0]
        cur.close()
        conn.close()
        id = user[0]
        userMethod = str(id) + '_back'
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_start = types.InlineKeyboardButton('Начать', callback_data=userMethod)
        markup.add(btn_start)
        bot.send_message(message.chat.id, f'{userName}, регистрация прошла успешно\U00002714', reply_markup=markup)
    except:
        return bot.reply_to(message, 'Ошибка регистрации')
# Обработчик всех кнопок    
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    try:
        id = call.data.split('_')[0]
        values = call.data.split('_')[1]
        user_data = getUser(id)
        domen = user_data['domen']
        token = user_data['token']
        contLang = user_data['contLang']
        if domen and token and contLang:
            if values == 'products':
                markup = types.InlineKeyboardMarkup(row_width=1)
                btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data= str(id) + '_back')
                markup.add(btn_back)
                bot.send_message(call.message.chat.id, 'Введите SKU или название товара для поиска', reply_markup=markup)
                bot.register_next_step_handler(call.message, getprod, id)
            elif values == 'files':
                markup = types.InlineKeyboardMarkup(row_width=1)
                btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
                markup.add(btn_back)
                bot.send_message(call.message.chat.id, 'Введите название файла', reply_markup=markup)
                bot.register_next_step_handler(call.message, getphoto, id)
            elif values == 'info':
                bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
                markup = types.InlineKeyboardMarkup(row_width=2)
                btn_lim = types.InlineKeyboardButton('\U0001F6A9 Лимит запросов', callback_data=str(id) +'_limits')
                btn_dinfo = types.InlineKeyboardButton('\U00002754 Информация', callback_data=str(id) +'_datainfo')
                btn_rev = types.InlineKeyboardButton('\U0000270F Оставить отзыв', callback_data=str(id) +'_review')
                btn_about = types.InlineKeyboardButton('\U0001F9F7 О боте', callback_data=str(id) +'_about')
                #btn_attr_count = types.InlineKeyboardButton('\U00002699 Вывод атрибутов', callback_data=str(id) +'_attr_count')
                btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) +'_back')
                markup.add(btn_lim, btn_dinfo, btn_rev, btn_about, btn_back)
                bot.send_message(call.message.chat.id, 'Выберите опцию', reply_markup=markup)
            elif values == 'back':
                bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
                markup = types.InlineKeyboardMarkup(row_width=2)
                btn_prod = types.InlineKeyboardButton('\U0001F50D Поиск товара', callback_data= str(id)+'_products')
                btn_file = types.InlineKeyboardButton('\U0001F4C4 Поиск файла', callback_data=str(id)+'_files')
                btn_info = types.InlineKeyboardButton('\U00002754 Информация и помощь', callback_data=str(id)+'_info')
                markup.add(btn_prod, btn_file, btn_info)
                bot.send_message(call.message.chat.id, 'Выберите опцию:', reply_markup=markup)
            elif values == 'limits':
                return getLimits(call.message, id)
            elif values == 'datainfo':
                markup = types.InlineKeyboardMarkup(row_width=1)
                btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
                markup.add(btn_back)
                info = '''
    Представляем вашему вниманию уникального помощника Brandquad! Этот бот создан специально для облегчения работы с продуктами компании.
    Он позволит вам моментально находить нужную информацию и экономить ваше время.
    Вам больше не придется тратить часы на поиски товаров или файлов! Просто введите запрос - и бот выдаст результаты за считанные секунды.

    Вы сможете:
    \U00002714 Быстро искать товары по SKU или названию
    \U00002714 Находить нужные файлы по ключевым словам
    \U00002714 Получать контакты ответственных менеджеров
    \U00002714 Узнавать о дополнительных возможностях бота
    \U00002714 Оставлять отзывы и предложения по улучшению

    Работа с ботом интуитивно понятна и проста. Он сам подстроится под ваши потребности, учитывая предпочитаемый язык.
    Повысьте эффективность с Brandquad! Экономьте время и получайте нужную информацию за считанные секунды. Попробуйте уже сейчас!
    '''
                bot.send_message(call.message.chat.id, info, reply_markup=markup)
            elif values == 'review':
                markup = types.InlineKeyboardMarkup(row_width=1)
                btn_back = types.InlineKeyboardButton('\U0001F519 Отменить и вернуться', callback_data=str(id)+'_back')
                markup.add(btn_back)
                bot.send_message(call.message.chat.id, 'Укажите текст отзыва:\n Какие улучшения или нововведения хотелось бы видеть в боте.\n Пожелания.', reply_markup=markup)
                bot.register_next_step_handler(call.message, get_review, id)
            elif values == 'more':
                conn = sqlite3.connect('users_data.sql')
                cur = conn.cursor()
                cur.execute(f'SELECT * FROM userSettings WHERE userID={id}')
                listPhoto = cur.fetchall()
                cur.close()
                conn.close()
                listPhoto = listPhoto[0][2]
                prod = []
                if ',' in listPhoto:
                    listPhoto = listPhoto.split(',')
                else:
                    prod.append(listPhoto)
                    listPhoto = prod
                markup1 = types.InlineKeyboardMarkup(row_width=1)
                btn_photo = types.InlineKeyboardButton('\U0001F50D Новый поиск файла', callback_data= str(id) + '_files')
                btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
                markup1.add(btn_photo, btn_back)
                if len(listPhoto) > 5:
                    count = 0
                    filesBTNS = types.InlineKeyboardMarkup(row_width=1)
                    checkList = []
                    for photo in listPhoto:
                        if count < 5:
                            print(2)
                            name = photo.split('---')[0]
                            url = photo.split('---')[1]
                            print(3)
                            try:
                                print(name, url)
                                bot.send_photo(call.message.chat.id, url)
                                bot.send_message(call.message.chat.id, name)
                            except:
                                fileBtn = types.InlineKeyboardMarkup(row_width=1)
                                link_btn = types.InlineKeyboardButton(text="Открыть", url=url)
                                fileBtn.add(link_btn)
                                bot.send_message(call.message.chat.id, f'{name}', reply_markup=fileBtn)
                            count+= 1
                            checkList.append(photo)
                        else:
                            break
                    for photo in checkList:
                        listPhoto.remove(photo)
                    getUserSettings(id, listPhoto)
                    btn_more = types.InlineKeyboardButton('Показать еще >>>', callback_data=str(id) + '_more')
                    filesBTNS.add(btn_more, btn_photo, btn_back)
                    bot.send_message(call.message.chat.id, f'Выведено {count} файлов. Найдено ещё {len(listPhoto)}.\nВыберите опцию:', reply_markup=filesBTNS)
                else:
                    filesBTNS = types.InlineKeyboardMarkup(row_width=1)
                    count = 0
                    for photo in listPhoto:
                        name = photo.split('---')[0]
                        url = photo.split('---')[1]
                        try:
                            bot.send_photo(call.message.chat.id, url)
                            bot.send_message(call.message.chat.id, name)
                        except:
                            fileBtn = types.InlineKeyboardMarkup(row_width=1)
                            link_btn = types.InlineKeyboardButton(text="Открыть", url=url)
                            fileBtn.add(link_btn)
                            bot.send_message(call.message.chat.id, f'{name}', reply_markup=fileBtn)
                        count+=1
                    btn_photo = types.InlineKeyboardButton('\U0001F50D Новый поиск файла', callback_data= str(id) + '_files')
                    btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
                    filesBTNS.add(btn_photo, btn_back)
                    bot.send_message(call.message.chat.id, f'Найдено файлов: {count}.\n Выберите опцию:', reply_markup=filesBTNS)
            elif values == 'myrev':
                markup = types.InlineKeyboardMarkup(row_width=1)
                btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id)+'_back')
                markup.add(btn_back)
                conn = sqlite3.connect('users_data.sql')
                cur = conn.cursor()
                cur.execute(f'SELECT * FROM reviews WHERE userID={id}')
                myReviews = cur.fetchall()
                cur.close()
                conn.close()
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
                btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
                markup.add(btn_back)
                try:
                    with open('about.txt', "r", encoding='utf-8') as aboutInfo:
                        bot.send_message(call.message.chat.id, aboutInfo.read(), reply_markup=markup)
                except:
                    bot.send_message(call.message.chat.id, 'Файл с информацией недоступен', reply_markup=markup)
            elif values == 'prodinfo':
                sku = call.data.split('_')[2]
                markup = types.InlineKeyboardMarkup(row_width=1)
                btn_prod = types.InlineKeyboardButton('\U0001F50D Новый поиск товара', callback_data=str(id) + '_products')
                btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
                btn_pdf = types.InlineKeyboardButton('Посмотреть в PDF', callback_data=str(id) + '_pdf_' + str(sku))
                markup.add(btn_pdf, btn_prod, btn_back)
                message = getBySKU(call.message, id, sku)
                photo = message.split('\n')[0]
                message = message.split('\n')
                message.remove(photo)
                try:
                    bot.send_photo(call.message.chat.id, photo)
                except:
                    pass
                bot.send_message(call.message.chat.id, '\n'.join(message[:5]), reply_markup=markup)
            elif values == 'pdf':
                try:
                    markup = types.InlineKeyboardMarkup(row_width=1)
                    btn_prod = types.InlineKeyboardButton('\U0001F50D Новый поиск товара', callback_data=str(id) + '_products')
                    btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
                    markup.add(btn_prod, btn_back)
                    sku = call.data.split('_')[2]
                    sendPDF(call.message, id, sku)
                    output_path = "/data/"
                    filename = os.path.join(output_path, f"{sku}_info.pdf")
                    url = open(filename, 'rb')
                    bot.send_document(call.message.chat.id, url, reply_markup=markup)
                    url.close()
                    os.unlink(filename)
                except:
                    bot.send_message(call.message.chat.id, 'Не удалось сформировать PDF файл')
            elif values == 'prodmore':
                conn = sqlite3.connect('users_data.sql')
                cur = conn.cursor()
                cur.execute(f'SELECT * FROM userSettings WHERE userID={id}')
                products = cur.fetchall()
                cur.close()
                conn.close()
                products = products[0][2]
                prod = []
                if ',' in products:
                    products = products.split(',')
                else:
                    prod.append(products)
                    products = prod
                getBySKUList(call.message, id, products)
        else:
            bot.send_message(call.message.chat.id, 'Вы не авторизованы. Пройдите авторизацию, подробнее /start')
    except:
        bot.send_message(call.message.chat.id, 'Вы не авторизованы. Пройдите авторизацию, подробнее /start')

# Формирование файла PDF на сервере в папке /data/
def sendPDF(message, id, sku):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_prod = types.InlineKeyboardButton('\U0001F50D Новый поиск товара', callback_data=str(id) + '_products')
    btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
    markup.add(btn_prod, btn_back)
    message = getBySKU(message, id, sku)
    photo = message.split('\n')[0]
    message = message.split('\n')
    message.remove(photo)
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
    pn = message[1]
    message.remove(pn)
    message.remove(sku)
    pdf.set_font('DejaVu', '', 18)
    pdf.multi_cell(0, 6, txt=sku)
    pdf.multi_cell(0, 6, txt=' ')
    pdf.multi_cell(0, 6, txt=pn)
    pdf.set_font('DejaVu', '', 10)
    pdf.multi_cell(0, 6, txt=' ')
    pdf.multi_cell(0, 6, txt='\n'.join(message))
    output_path = "/data/"
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    filename = os.path.join(output_path, f"{sku}_info.pdf")
    pdf.output(filename)
#Запрос данных о товарах по списку SKU
def getBySKUList(message, id, products):
    user_data = getUser(id)
    domen = user_data['domen']
    token = user_data['token']
    contLang = user_data['contLang']
    if domen and token and contLang:
        headers = {
            'TOKEN': token
        }
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_prod = types.InlineKeyboardButton('\U0001F50D Новый поиск товара', callback_data=str(id) + '_products')
        btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
        markup.add(btn_prod, btn_back)
        checked = []
        count = 1
        for sku in products:
            if not count > 5:
                prodRequest = requests.get(f'https://{domen}/api/public/v3/products/{sku}', headers=headers).json()
                pn = prodRequest[0]['meta']['name']
                desc_btn = f'{str(sku)}\n{str(pn)}'
                mark = types.InlineKeyboardMarkup(row_width=1)
                btn_prod = types.InlineKeyboardButton('Открыть', callback_data=str(id) + '_prodinfo_' + str(sku))
                mark.add(btn_prod)
                bot.send_message(message.chat.id, desc_btn, reply_markup=mark)
                checked.append(sku)
                count += 1
            else:
                break
        for sku in checked:
            products.remove(sku)
        if len(products) > 0:
            getUserSettings(id, products)
            btn_prodmore = types.InlineKeyboardButton('Показать еще >>>', callback_data=str(id) + '_prodmore')
            markup.add(btn_prodmore)
            bot.send_message(message.chat.id, f'Выведено еще {len(checked)} товаров. Осталось: {len(products)}.\nВыберите опцию:', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, f'Выберите опцию:', reply_markup=markup)
# Запрос данных по одному SKU        
def getBySKU(message, id, sku):
    user_data = getUser(id)
    domen = user_data['domen']
    token = user_data['token']
    contLang = user_data['contLang']
    attrCount = 5
    if domen and token and contLang:
        headers = {
            'TOKEN': token
        }
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_prod = types.InlineKeyboardButton('\U0001F50D Новый поиск товара', callback_data=str(id) + '_products')
        btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
        markup.add(btn_prod, btn_back)
        try:
            prodRequest = requests.get(f'https://{domen}/api/public/v3/products/{sku}', headers=headers).json()
            attributes = prodRequest[0]['attributes']
            photo = 'Нет основного фото'
            try:
                assets = prodRequest[0]['assets']
                photo = prodRequest[0]['meta']['cover']
                for ass in assets:
                    if ass['dam']['is_cover'] == True:
                        photo = ass['dam']['url']
                        break
            except:
                bot.send_message(message.chat.id, 'Нет основного фото')
            sku = prodRequest[0]['meta']['id']
            pn = prodRequest[0]['meta']['name']
            result_attrs = ''
            if len(attributes.values()) != 0 :
                for attr in attributes.values():
                    try:
                        if type(attr) == list and len(attr) != 0:
                            if attr[0]['locale'] == contLang: # Учет языка контента для вывода атрибутов
                                aName = attr[0]['name']
                                if type(attr[0]['value']) == list: # Если у атрибута несколько значений
                                    aValue = ', '.join(attr[0]['value'])
                                else:
                                    aValue = attr[0]['value']
                                result_attrs += f'{aName}: {aValue}\n'
                    except:
                        pass
            result_attrs = photo + '\n' + sku + '\n' + pn + '\n' + result_attrs
            return result_attrs

        except:
            bot.send_message(message.chat.id, 'Ошибка поиска товара по SKU', reply_markup=markup)


# Получение данных о товаре, основная функция при нажатии "Поиск товара"
def getprod(message, id):
        user_data = getUser(id)
        domen = user_data['domen']
        token = user_data['token']
        contLang = user_data['contLang']
        attrCount = 5
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_prod = types.InlineKeyboardButton('\U0001F50D Новый поиск товара', callback_data=str(id) + '_products')
        btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
        markup.add(btn_prod, btn_back)
        if domen and token and contLang:
            headers = {
                'TOKEN': token
            }
            try:
                prodRequest = requests.get(f'https://{domen}/api/public/v3/products/{message.text}', headers=headers).json()
                attributes = prodRequest[0]['attributes']
                photo = ''
                assets = prodRequest[0]['assets']
                photo = prodRequest[0]['meta']['cover']
                try:
                    for ass in assets:
                        if ass['dam']['is_cover'] == True:
                            photo = ass['dam']['url']
                            break
                except:
                    bot.send_message(message.chat.id, 'Нет основного фото')
                sku = prodRequest[0]['meta']['id']
                pn = prodRequest[0]['meta']['name']
                result_attrs = ''
                attrs_count = 0
                if len(attributes.values()) != 0 :
                    for attr in attributes.values():
                        try:
                            if type(attr) == list and len(attr) != 0 and attrs_count < attrCount:
                                if attr[0]['locale'] == contLang: # Учет языка контента для вывода атрибутов
                                    aName = attr[0]['name']
                                    if type(attr[0]['value']) == list: # Если у атрибута несколько значений
                                        aValue = ', '.join(attr[0]['value'])
                                    else:
                                        aValue = attr[0]['value']
                                    result_attrs += f'{aName}: {aValue}\n'
                                    attrs_count += 1
                        except:
                            pass
                btn_pdf = types.InlineKeyboardButton('Посмотреть в PDF', callback_data=str(id) + '_pdf_' + str(sku))
                markup.add(btn_pdf)
                result_attrs = sku + '\n' + pn + '\n' + result_attrs
                if photo:
                    bot.send_photo(message.chat.id, photo)
                if result_attrs:
                    bot.send_message(message.chat.id, result_attrs, reply_markup=markup)

            except:
                try:
                    PNRequest = requests.get(f'https://{domen}/api/public/v3/attributes/?is_SKU=true', headers=headers).json()
                    sku_id = str(PNRequest['results'][0]['id'])
                    sku_name = PNRequest['results'][0]['name'][0]['value']
                    sku_type = str(PNRequest['results'][0]['type'])
                    params = {
                            'filters': '{"attribute_type": '+ sku_type +', "id": '+ sku_id +', "exp": "term", "name": "' + sku_name + '", "lang": "'+ contLang + '", "pickle__strong": true, "val": ["'+ message.text.lower() +'"], "ref_list_id": null,"type": "'+ sku_id +'"}'}
                    prodRequest = requests.get(f'https://{domen}/api/public/v3/products/', headers=headers, params=params).json()
                    prodRequest = prodRequest['results']
                    skuRNG = []
                    for p in range(len(prodRequest)):
                        sku = prodRequest[p]['meta']['id']
                        skuRNG.append(sku)
                    count = 1
                    for p in range(len(prodRequest)):
                        if count <= 5:
                            photo = prodRequest[p]['meta']['cover']
                            attributes = prodRequest[p]['attributes']
                            sku = prodRequest[p]['meta']['id']
                            skuRNG.remove(sku)
                            pn = prodRequest[p]['meta']['name']
                            desc_btn = f'{sku}\n{pn}'
                            mark = types.InlineKeyboardMarkup(row_width=1)
                            btn_prod = types.InlineKeyboardButton('Открыть', callback_data=str(id) + '_prodinfo_' + str(sku))
                            mark.add(btn_prod)
                            bot.send_message(message.chat.id, desc_btn, reply_markup=mark)
                            count += 1
                    if len(skuRNG) > 0:
                        getUserSettings(id, skuRNG)
                        btn_prodmore = types.InlineKeyboardButton('Показать еще >>>', callback_data=str(id) + '_prodmore')
                        markup.add(btn_prodmore)
                        bot.send_message(message.chat.id, f'Выведено 5 товаров из {len(skuRNG) + 5}. Выберите опцию:', reply_markup=markup)
                    elif len(skuRNG) == 0:
                        bot.send_message(message.chat.id, f'Найдено товаров: {count-1}.\nВыберите опцию:', reply_markup=markup)
                except:
                    try:
                        PNRequest = requests.get(f'https://{domen}/api/public/v3/attributes/?is_PN=true', headers=headers).json()
                        pn_id = str(PNRequest['results'][0]['id'])
                        pn_name = PNRequest['results'][0]['name'][0]['value']
                        pn_type = str(PNRequest['results'][0]['type'])
                        params = {
                                'filters': '{"attribute_type": '+ pn_type +', "id": '+ pn_id +', "exp": "term", "name": "' + pn_name + '", "lang": "'+ contLang + '", "pickle__strong": true, "val": ["'+ message.text.lower() +'"], "ref_list_id": null,"type": "'+ pn_id +'"}'}
                        prodRequest = requests.get(f'https://{domen}/api/public/v3/products/', headers=headers, params=params).json()
                        prodRequest = prodRequest['results']
                        skuRNG = []
                        for p in range(len(prodRequest)):
                            sku = prodRequest[p]['meta']['id']
                            skuRNG.append(sku)
                        count = 1
                        for p in range(len(prodRequest)):
                            if count <= 5:
                                photo = prodRequest[p]['meta']['cover']
                                attributes = prodRequest[p]['attributes']
                                sku = prodRequest[p]['meta']['id']
                                skuRNG.remove(sku)
                                pn = prodRequest[p]['meta']['name']
                                desc_btn = f'{sku}\n{pn}'
                                mark = types.InlineKeyboardMarkup(row_width=1)
                                btn_prod = types.InlineKeyboardButton('Открыть', callback_data=str(id) + '_prodinfo_' + str(sku))
                                mark.add(btn_prod)
                                bot.send_message(message.chat.id, desc_btn, reply_markup=mark)
                                count += 1
                        if len(skuRNG) > 0:
                            getUserSettings(id, skuRNG)
                            btn_prodmore = types.InlineKeyboardButton('Показать еще >>>', callback_data=str(id) + '_prodmore')
                            markup.add(btn_prodmore)
                            bot.send_message(message.chat.id, f'Выведено 5 товаров из {len(skuRNG) + 5}. Выберите опцию:', reply_markup=markup)
                        elif len(skuRNG) == 0:
                            bot.send_message(message.chat.id, f'Найдено товаров: {count-1}.\nВыберите опцию:', reply_markup=markup)
                    except:
                        bot.send_message(message.chat.id, 'Товар не найден.', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, 'Вы не авторизованы, воспользуйтесь /start')
# Поиск фото            
def getphoto(message, id):
        data_user = getUser(id)
        domen = data_user['domen']
        token = data_user['token']
        listPhoto  = []
        if domen and token:
            headers = {
                'TOKEN': token
            }
            markup1 = types.InlineKeyboardMarkup(row_width=1)
            btn_photo = types.InlineKeyboardButton('\U0001F50D Новый поиск файла', callback_data= str(id) + '_files')
            btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
            markup1.add(btn_photo, btn_back)
            fileRequest = requests.get(f'https://{domen}/api/public/v3/dam/files/?search={message.text}', headers=headers)
            if fileRequest.status_code == 200:
                try:
                    for i in range(len(fileRequest.json()['results'])):
                        name = fileRequest.json()['results'][i]['name']
                        url = fileRequest.json()['results'][i]['url']
                        linkName = f'{name}---{url}'
                        listPhoto.append(linkName)
                    if len(listPhoto) > 5:
                        count = 0
                        filesBTNS = types.InlineKeyboardMarkup(row_width=1)
                        checkList = []
                        for photo in listPhoto:
                            if count < 5:
                                name = photo.split('---')[0]
                                url = photo.split('---')[1]
                                try:
                                    bot.send_photo(message.chat.id, url)
                                    bot.send_message(message.chat.id, name)
                                except:
                                    fileBtn = types.InlineKeyboardMarkup(row_width=1)
                                    link_btn = types.InlineKeyboardButton(text="Открыть", url=url)
                                    fileBtn.add(link_btn)
                                    bot.send_message(message.chat.id, f'{name}', reply_markup=fileBtn)
                                count+= 1
                                checkList.append(photo)
                            else:
                                break
                        for photo in checkList:
                            listPhoto.remove(photo)
                        getUserSettings(id, listPhoto)
                        btn_more = types.InlineKeyboardButton('Показать еще >>>', callback_data=str(id) + '_more')
                        filesBTNS.add(btn_more, btn_photo, btn_back)
                        bot.send_message(message.chat.id, f'Выведено {count} файлов. Найдено ещё {len(listPhoto)}.\nВыберите опцию:', reply_markup=filesBTNS)
                    else:
                        filesBTNS = types.InlineKeyboardMarkup(row_width=1)
                        count = 0
                        for photo in listPhoto:
                            name = photo.split('---')[0]
                            url = photo.split('---')[1]
                            try:
                                bot.send_photo(message.chat.id, url)
                                bot.send_message(message.chat.id, name)
                            except:
                                fileBtn = types.InlineKeyboardMarkup(row_width=1)
                                link_btn = types.InlineKeyboardButton(text="Открыть", url=url)
                                fileBtn.add(link_btn)
                                bot.send_message(message.chat.id, f'{name}', reply_markup=fileBtn)
                            count+=1
                        btn_photo = types.InlineKeyboardButton('\U0001F50D Новый поиск файла', callback_data= str(id) + '_files')
                        btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
                        filesBTNS.add(btn_photo, btn_back)
                        bot.send_message(message.chat.id, f'Выведено файлов: {count}.\n Выберите опцию:', reply_markup=filesBTNS)
                except:
                    bot.send_message(message.chat.id, 'Файл не найден', reply_markup=markup1)
        else:
            bot.send_message(message.chat.id, 'Вы не авторизованы, воспользуйтесь /start')

def getLimits(message, id): # Забирает лимит запросов
    data_user = getUser(id)
    domen = data_user['domen']
    token = data_user['token']
    if domen and token:
        headers = {
            'TOKEN': token
        }
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data=str(id) + '_back')
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

def get_review(message, id): # Записывает отзыв в бд
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_back = types.InlineKeyboardButton('\U0001F519 Назад', callback_data= str(id)+'_back')
    btnMyRev = types.InlineKeyboardButton('Мои отзывы', callback_data=str(id) +'_myrev')
    markup.add(btnMyRev, btn_back)
    try:
        conn = sqlite3.connect('users_data.sql')
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, date varchar(50), username varchar(50), review varchar(50), tgid varchar(50), userID varchar(50))')
        conn.commit()
        cur.close()
        conn.close()
        conn = sqlite3.connect('users_data.sql')
        cur = conn.cursor()
        cur.execute("INSERT INTO reviews (date, username, review, tgid, userID) VALUES ('%s', '%s', '%s', '%s', '%s')" % (now, message.from_user.first_name, message.text, message.from_user.id, id))
        conn.commit()
        cur.close()
        conn.close()
        bot.send_message(message.chat.id, 'Отзыв был успешно записан, спасибо!', reply_markup=markup)
    except:
        bot.send_message(message.chat.id, 'Не удалось записать отзыв, повторите попытку позже', reply_markup=markup)

def getUser(id): # Функция запроса данных и доступов пользователя в БД
    conn = sqlite3.connect('users_data.sql')
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM users WHERE id={id}')
    user = cur.fetchall()[0]
    cur.close()
    conn.close()
    dictUser = {
        'id': user[0],
        'domen': user[7],
        'email': user[6],
        'token': user[5],
        'contLang': user[2],
        'userName': user[1],
        'accId': user[3],
        'tgid': user[4]
    }
    return dictUser

def getUserSettings(id, products): # Вспомогательная функция для записи данных о товара/фото. Записи временные и сами удаляются при вызове.
    try:
        conn = sqlite3.connect('users_data.sql')
        cur = conn.cursor()
        cur.execute(f'DELETE from userSettings where userID={id}')
        conn.commit()
        cur.close()
        conn.close()
        conn = sqlite3.connect('users_data.sql')
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS userSettings (id INTEGER PRIMARY KEY AUTOINCREMENT, userID varchar(50), products varchar(50000))')
        conn.commit()
        cur.close()
        conn.close()
        conn = sqlite3.connect('users_data.sql')
        cur = conn.cursor()
        cur.execute("INSERT INTO userSettings (userID, products) VALUES ('%s', '%s')" % (id, ','.join(products)))
        conn.commit()
        cur.close()
        conn.close()
        print('[INFO] Запись UserSettings выполнена успешно')
    except:
        print('[INFO] Невозможно подключиться к базе UserSettings')

def getEmail(message, domen): # Запрос email у пользователя при регистрации
    email = message.text.lower()
    if '@' in email:
        bot.send_message(message.chat.id, 'Последний шаг, введите токен авторизации:')
        bot.register_next_step_handler(message, getToken, domen, email)
    else:
        bot.send_message(message.chat.id, 'Вы ввели некорректный email, повторите попытку - /start')
def getToken(message, domen, email): # Запрос token у пользователя при регистрации, а также вызов check_db для проверки пользователя в базе.
    token = message.text
    try:
        return check_db(message, domen, token, email)
    except:
        bot.send_message(message.chat.id, 'Не удалось подключиться по заданным доступам, повторите попытку - /start')

if __name__ == "__main__":
    app.run(port=config.PORT)