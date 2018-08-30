import mws, requests, datetime, json
from time import sleep


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

    product_list = []

    # ------------------------------------------------------------------------------------------------------------------
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
            else:
                if report_list.response.status_code != 200:
                    print('Connection to Amazon unsuccessful')
                if r.status_code != 200:
                    print('Connection to BigBuy unsuccessful')

        connection_test()
        self.running = True

    # ------------------------------------------------------------------------------------------------------------------
    def refresh_product_list(self):
        try:
            amazon_sku_list, amazon_listing = self.get_amazon_listing()
            bb_sku_list, bb_catalog = self.get_bb_listing_skus_and_catalog()
            self.product_list = self.product_filter(amazon_listing, bb_catalog, amazon_listing[0])
            pass
        except RefreshmentError as e:
            print('Products could not be refreshed due to an Error: ', e.value)
        else:
            print('Products successfully refreshed')
            print('Product count: ', len(self.product_list))

    def get_bb_listing_skus_and_catalog(self):
        bb_catalog_url = self.bb_url + '/rest/catalog/products.json'
        bb_catalog = json.loads(requests.get(bb_catalog_url, headers=self.bb_header).text)
        sku_list = list(map(lambda x: x["sku"], bb_catalog))
        if not len(sku_list) > 0:
            raise RefreshmentError('BigBuy: Catalog not receivable')
        return sku_list, bb_catalog

    def get_amazon_listing(self):
        report_request = self.reports_api.request_report(report_type='_GET_MERCHANT_LISTINGS_DATA_')
        if report_request.response.status_code == 200:
            starting_date = datetime.datetime.now() - datetime.timedelta(hours=5)
            sleep(60)
            report_list = self.reports_api.get_report_list(fromdate=starting_date)
            newest_report_meta_list = list(
                filter(lambda x: x.ReportType == '_GET_MERCHANT_LISTINGS_DATA_', report_list.parsed.ReportInfo))
            if len(newest_report_meta_list) <= 0:
                raise RefreshmentError('Amazon: No Merchant Listing Data')
            report = self.reports_api.get_report(newest_report_meta_list[0].ReportId)
            parsed_report = report.parsed.decode('iso-8859-1').split('\n')
            amazon_listing = [x for x in list(map(lambda x: x.split('\t'), parsed_report)) if len(x) == 48]
            sku_list = list(map(lambda x: x[3] if not len(x) < 3 else 0, amazon_listing))
            return sku_list, amazon_listing

    def update_prices(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def product_filter(amazon_listing, bb_catalog, keys):
        result = []
        for i in bb_catalog:
            matches = [x for x in amazon_listing if x[3] == i['sku']]
            if len(matches) > 0:
                result.append(dict(zip(keys, matches[0])))
            if len(matches) > 1:
                print('Multiple products with the same SKU detected')
        return result


# ----------------------------------------------------------------------------------------------------------------------
class RefreshmentError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
