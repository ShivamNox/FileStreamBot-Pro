# (c) ShivamNox
import os
from os import getenv, environ
from dotenv import load_dotenv



load_dotenv()

class Var(object):
    MULTI_CLIENT = False
    API_ID = int(getenv('API_ID', '21302177'))
    API_HASH = str(getenv('API_HASH', '7f21bc2ae7b8b9e610cb8b1808dd045e'))
    BOT_TOKEN = str(getenv('BOT_TOKEN', '7875065960:AAEpp-CsAzBPmwsOp67sBvmqsTbKoJIhG9E'))
    name = str(getenv('name', 'FileStreamBot'))
    SLEEP_THRESHOLD = int(getenv('SLEEP_THRESHOLD', '60'))
    WORKERS = int(getenv('WORKERS', '4'))
    BIN_CHANNEL = int(getenv('BIN_CHANNEL', '-1002791607060'))
    PORT = int(getenv('PORT', '3000'))
    BIND_ADRESS = str(getenv('WEB_SERVER_BIND_ADDRESS', '0.0.0.0'))
    PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200"))  # 20 minutes
    OWNER_ID = set(int(x) for x in os.environ.get("OWNER_ID", "6713397633").split())  
    NO_PORT = bool(getenv('NO_PORT', False))
    APP_NAME = None
    OWNER_USERNAME = str(getenv('OWNER_USERNAME', 'hivajoysupport'))
    if 'DYNO' in environ:
        ON_HEROKU = True
        APP_NAME = str(getenv('APP_NAME'))
    
    else:
        ON_HEROKU = False
    FQDN = str(getenv('FQDN', '0.0.0.0:3000')) if not ON_HEROKU or getenv('FQDN', '0.0.0.0:3000') else APP_NAME+'.herokuapp.com'
    HAS_SSL=bool(getenv('HAS_SSL',False))
    if HAS_SSL:
        URL = "http://hivajoy.fwh.is/".format(FQDN)
    else:
        URL = "http://hivajoy.fwh.is/".format(FQDN)
    DATABASE_URL = str(getenv('DATABASE_URL', 'mongodb+srv://hivajoy:vFzCknGyfyi38a9n@cluster0.6tny5.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'))
    UPDATES_CHANNEL = str(getenv('UPDATES_CHANNEL', 'innoshiv'))
    BANNED_CHANNELS = list(set(int(x) for x in str(getenv("BANNED_CHANNELS", "-1001362659779")).split())) 
