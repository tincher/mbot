import configparser
import datetime

from src import ManneBot

start_time = datetime.datetime.now()


config = configparser.ConfigParser()
config.read('../account.ini')
manne_conf = config['MANNE']
mbot = ManneBot(manne_conf)
mbot.refresh_product_list()

while mbot.running:
    mbot.update_price()
    if (start_time - datetime.datetime.now()).seconds > 60 * 60 * 3:
        mbot.refresh_product_list()
