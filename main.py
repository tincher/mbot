import configparser

from src import ManneBot

config = configparser.ConfigParser()
config.read('../account.ini')
manne_conf = config['MANNE']
mbot = ManneBot(manne_conf)

mbot.refresh_product_list()
mbot.is_same_name({'sku': 'F1515101'})

# while mbot.running:
#     mbot.update_price()
