import configparser
import mws
import requests


def connection_test():
    config = configparser.ConfigParser()
    config.read('../../account.ini')
    manne_conf = config['MANNE']

    access_key = manne_conf['aws_access_key_id']
    secret_key = manne_conf['secret_key']
    seller_id = manne_conf['seller_id']
    mws_auth_token = manne_conf['mws_auth_token']
    marketplace_de = 'A1PA6795UKMFR9'

    # mws test
    reports_api = mws.Reports(access_key, secret_key, seller_id, auth_token=mws_auth_token, region='DE')
    report_list = reports_api.get_report_list()

    print('amazon geht: ' + str(report_list.response.status_code == 200))
