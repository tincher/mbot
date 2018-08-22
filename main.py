from src import ManneBot
import configparser

config = configparser.ConfigParser()
config.read('../account.ini')
manne_conf = config['MANNE']
mbot = ManneBot(manne_conf)
mbot.refresh_product_list()

# while mbot.running:
