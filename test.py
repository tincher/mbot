import configparser
import mws

config = configparser.ConfigParser()
config.read('../account.ini')
manne_conf = config['MANNE']

access_key = manne_conf['aws_access_key_id']
seller_id = manne_conf['seller_id']
secret_key = manne_conf['secret_key']
marketplace_de = 'A1PA6795UKMFR9'


products_api = mws.Products(access_key, secret_key, seller_id, region='DE')
products = products_api.list_matching_products(marketplaceid=marketplace_de, query='tv')
print(products.parsed)
