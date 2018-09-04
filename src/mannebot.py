import csv
import datetime
import json
import math
from time import sleep

import requests

from . import mws


class ManneBot:
    aws_id = ''
    seller_id = ''
    secret_key = ''
    mws_token = ''
    marketplace_id = 'A1PA6795UKMFR9'

    bb_api_key = ''
    bb_header = ''
    bb_url = 'https://api.bigbuy.eu'

    running = False
    start_at_h = 0
    start_at_m = 0
    end_at_h = 23
    end_at_m = 59

    current_index = 0

    minimum_marge_percentage = 0.1

    product_list = []
    amazon_listing = []

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
        self.feeds_api = mws.Feeds(self.aws_id, self.secret_key, self.seller_id, auth_token=self.mws_token,
                                   region='DE')
        self.products_api = mws.Products(self.aws_id, self.secret_key, self.seller_id, auth_token=self.mws_token,
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
            self.product_list = self.product_filter(amazon_listing, bb_catalog)
            self.amazon_listing = amazon_listing
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

    def update_price(self):
        current_item = self.product_list[self.current_index]
        current_item_information = self.get_product_information(current_item, True)
        is_valid, is_german = self.is_valid_item(current_item, current_item_information)
        if is_valid:
            shipping_cost = self.get_shipping_cost(current_item)
            price = self.calculate_price(current_item, shipping_cost)
            if not is_german:
                pass  # todo
            self.submit_price(current_item, current_item_information, price, shipping_cost)

    def is_valid_item(self, item, item_information):
        correct_size = self.is_approved_size(item)
        correct_price = self.is_an_approved_price(item)
        correct_brand = self.is_an_approved_brand(item_information)
        correct_sku = self.is_an_approved_sku(item_information)
        correct_category = self.is_an_approved_category(item_information)
        correct_name, german_name = self.is_same_name(item_information)
        result = not (correct_size or correct_price or correct_brand or correct_sku or correct_category or correct_name)
        return result, german_name

    def is_same_name(self, item_information):
        amazon_item_list = [x for x in self.amazon_listing if x[3] == item_information['sku']]
        if not len(amazon_item_list) > 0:
            print('Error while evaluating if item is valid for new pricing')
            return
        if amazon_item_list[0]['name'] == item_information['name']:
            return True, True
        else:
            spanish_item = self.get_product_information(item_information, False)
            if amazon_item_list[0]['name'] == spanish_item['name']:
                return True, False
        return False, False

    def is_an_approved_category(self, item_information):
        category_url = self.bb_url + '/rest/catalog/productcategories/' + str(item_information['id']) + '.json'
        r = requests.get(category_url, headers=self.bb_header)
        item_categories = json.loads(r.text)
        category_list = self.get_csv_file_as_list('../categories.csv')
        same_categories = [x for x in item_categories if str(x['category']) in category_list]
        if len(same_categories) > 0:
            return False
        return True

    def is_an_approved_sku(self, item_information):
        sku_list = self.get_csv_file_as_list('../skus.csv')
        for sku in sku_list:
            if sku == item_information['sku']:
                return False
        return True

    def is_an_approved_brand(self, item_information):
        brand_list = self.get_csv_file_as_list('../brands.csv')
        for brand in brand_list:
            if brand in item_information['name']:
                return False
        return True

    def is_approved_size(self, item):
        if self.calculate_gurtmass([item['height'], item['width'], item['depth']]) < 300:
            return True
        return False

    def submit_price(self, item, item_information, price, shipping):
        rounded_price = self.round_price(price)
        print('Price submitted for SKU: ', item['sku'], ' with price: ', rounded_price, ' + ', shipping)

    def calculate_price(self, item, shipping):
        wholesale_price = price = item['wholesalePrice']
        mwst = 1 / 1.19
        amazon_fee = self.get_amazon_fee(item['sku'], price, shipping)
        while price * mwst - (shipping * mwst) - (wholesale_price + amazon_fee) < 0.1 * price:
            price *= 1.05
            amazon_fee = self.get_amazon_fee(item['sku'], price, shipping)
        return price

    def get_product_information(self, item, german):
        iso_code = 'de'
        if not german:
            iso_code = 'es'
        item_url = self.bb_url + '/rest/catalog/productinformation/' + str(item['id']) + '.json?isoCode=' + iso_code
        r = requests.get(item_url, headers=self.bb_header)
        return json.loads(r.text)

    def get_amazon_fee(self, sku, shipping, price):
        response = self.products_api.get_my_fee_estimate(self.marketplace_id, sku, price, shipping)
        fee_objects = response.parsed['FeesEstimateResultList']['FeesEstimateResult']
        return float(fee_objects['FeesEstimate']['TotalFeesEstimate']['Amount']['value'])

    def get_shipping_cost(self, item):
        order_object = {"order": {"delivery": {"isoCountry": "DE", "postcode": "74336"},
                                  "products": [{"reference": item['sku'], "quantity": "1"}]}}
        json_body = json.dumps(order_object)
        r = requests.post(self.bb_url + '/rest/shipping/orders.json', data=json_body, headers=self.bb_header)
        return min(json.loads(r.text)['shippingOptions'], key=lambda x: x['cost'])['cost']

    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def get_csv_file_as_list(filename):
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            return [item for sublist in list(reader) for item in sublist]

    @staticmethod
    def is_an_approved_price(item):
        if item['wholesalePrice'] > 5:
            return True
        return False

    @staticmethod
    def calculate_gurtmass(dimensions):
        longest = max(dimensions)
        dimensions.remove(longest)
        return longest + sum(map(lambda x: 2 * x, dimensions))

    @staticmethod
    def round_price(price):
        if price / 100 < 1:
            return round(math.ceil(price * 10) / 10, 1)
        else:
            return math.ceil(price)

    @staticmethod
    def get_new_order_object():
        return {"order": {"delivery": {"isoCountry": "de", "postcode": "74336"}},
                "products": [{"reference": "F1515101", "quantity": "1"}]}

    @staticmethod
    def product_filter(amazon_listing, bb_catalog):
        result = []
        for i in bb_catalog:
            matches = [x for x in amazon_listing if x[3] == i['sku']]
            if len(matches) > 0:
                result.append(i)
            if len(matches) > 1:
                print('Multiple products with the same SKU detected')
        return result


# ----------------------------------------------------------------------------------------------------------------------
class RefreshmentError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
