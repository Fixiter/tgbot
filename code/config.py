BOT_API_TOKEN = '6884099789:AAGods1wM1dFib-1-zCaZYLtv4bEpVR5SkI' # Токен бота из BotFather
HOST = 'https://flast-test-fixiter.amvera.io/' # Адрес сервера, куда будет стучать telegram post запросами при написании сообщения в чате.
PORT = 5000 # Порт на котором запускается приложение flask
WEBHOOK_URL = f'https://api.telegram.org/bot{BOT_API_TOKEN}/setWebhook?url={HOST}' # Задавал вручную в строке браузера. Для удаления не передаем вообще параметр url.
WEBHOOK_INFO = f'https://api.telegram.org/bot{BOT_API_TOKEN}/getWebhookInfo' # Забирает информацию о рабочем вебхуке
