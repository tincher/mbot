import configparser
import mws
import requests
import datetime


aa = datetime.datetime(2017, 1, 1).isoformat()
bb = datetime.datetime.now()
config = configparser.ConfigParser()
config.read('../account.ini')
manne_conf = config['MANNE']

access_key = manne_conf['aws_access_key_id']
seller_id = manne_conf['seller_id']
secret_key = manne_conf['secret_key']
mws_auth_token = manne_conf['mws_auth_token']
marketplace_de = 'A1PA6795UKMFR9'

# mws test
products_api = mws.Products(access_key, secret_key, seller_id, region='DE')
inventory_api = mws.Inventory(access_key, secret_key, seller_id, region = 'DE')
reports_api = mws.Reports(access_key, secret_key, seller_id, auth_token=mws_auth_token, region = 'DE')
# products = products_api.list_matching_products(marketplaceid=marketplace_de, query='tv')
# print('amazon geht: ' + str(products.response.status_code == 200))


# bigbuy test
headers = {'Authorization': 'Bearer ' + manne_conf['bigbuy_api_key']}
test_url = '/rest/catalog/categories.json?isoCode=de&_format=json'
url = '/rest/shipping/carriers.json?_format=json'
production_api = 'https://api.bigbuy.eu'
sandbox_api = 'https://api.sandbox.bigbuy.eu'
r = requests.get(production_api + url, headers=headers)
print('bigbuy geht: ' + str(r.status_code == 200))

url3 = '/rest/shipping/orders.json'
body = '{"order":{"delivery": { "isoCountry": "DE", "postcode": "46005"},"products": [{"reference": "F1505138","quantity": 1},{"reference": "F1505151","quantity": 4}]}}'

r2 = requests.post(sandbox_api + url3, headers=headers, data=body)
print(r2.json())



def getreport():
    # test = reports_api.request_report(report_type='_GET_MERCHANT_LISTINGS_DATA_')
    # id = test.parsed.ReportRequestInfo.ReportRequestId
    # print(id)
    id2 = str(11677573669017734)
    skus = reports_api.get_report(report_id=id2)
    print(skus.parsed)



getreport()
