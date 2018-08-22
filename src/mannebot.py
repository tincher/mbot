import requests
import mws
import datetime
from time import sleep
import csv


class ManneBot:
    aws_id = ''
    seller_id = ''
    secret_key = ''
    mws_token = ''

    bb_api_key = ''
    bb_header = ''
    bb_url = 'https://api.bigbuy.eu'

    running = False
    start_at_h = 0
    start_at_m = 0
    end_at_h = 23
    end_at_m = 59

    product_list = list()

    def __init__(self, config):
        self.aws_id = config['aws_access_key_id']
        self.secret_key = config['secret_key']
        self.seller_id = config['seller_id']
        self.mws_token = config['mws_auth_token']
        self.bb_api_key = config['bigbuy_api_key']
        self.bb_header = {'Authorization': 'Bearer ' + config['bigbuy_api_key']}
        self.reports_api = mws.Reports(self.aws_id, self.secret_key, self.seller_id, auth_token=self.mws_token,
                                       region='DE')

        def connection_test():
            bb_test_url = self.bb_url + '/rest/user/purse.json?_format=json'
            r = requests.get(bb_test_url, headers=self.bb_header)
            report_list = self.reports_api.get_report_list()
            if report_list.response.status_code == 200 and r.status_code == 200:
                print('Connections successful')
                self.running = True

    def refresh_product_list(self):
        report_request = self.reports_api.request_report(report_type='_GET_MERCHANT_LISTINGS_DATA_')
        fromdate = datetime.datetime.now() - datetime.timedelta(hours=5)
        sleep(30)
        report_list = self.reports_api.get_report_list(fromdate=fromdate)
        newest_report_meta = list(
            filter(lambda x: x.ReportType == '_GET_MERCHANT_LISTINGS_DATA_', report_list.parsed.ReportInfo))[0]
        report = self.reports_api.get_report(newest_report_meta.ReportId)
        self.product_list = report.parsed.decode('iso-8859-1').split('\n')
        print('Products successfully refreshed')
