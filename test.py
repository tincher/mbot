import configparser
import mws
import requests

config = configparser.ConfigParser()
config.read('../account.ini')
manne_conf = config['MANNE']

access_key = manne_conf['aws_access_key_id']
seller_id = manne_conf['seller_id']
secret_key = manne_conf['secret_key']
marketplace_de = 'A1PA6795UKMFR9'

# mws test
products_api = mws.Products(access_key, secret_key, seller_id, region='DE')
products = products_api.list_matching_products(marketplaceid=marketplace_de, query='tv')
print('amazon geht: ' + str(products.response.status_code == 200))

# bigbuy test
headers = {'Authorization': 'Bearer ' + manne_conf['bigbuy_api_key']}
test_url = '/rest/catalog/categories.json?isoCode=de&_format=json'
url = '/rest/shipping/carriers.json?_format=json'
production_api = 'https://api.bigbuy.eu'
sandbox_api = 'https://api.sandbox.bigbuy.eu'
r = requests.get(production_api + url, headers=headers)
print('bigbuy geht: ' + str(r.status_code == 200))
