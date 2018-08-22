import configparser
import requests


def connection_test():
    config = configparser.ConfigParser()
    config.read('../../account.ini')
    manne_conf = config['MANNE']

    # bigbuy test
    headers = {'Authorization': 'Bearer ' + manne_conf['bigbuy_api_key']}
    test_url = '/rest/catalog/categories.json?isoCodce=de&_format=json'
    url = '/rest/shipping/carriers.json?_format=json'
    production_api = 'https://api.bigbuy.eu'
    sandbox_api = 'https://api.sandbox.bigbuy.eu'
    r = requests.get(production_api + url, headers=headers)
    print('bigbuy geht: ' + str(r.status_code == 200))
