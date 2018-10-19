import csv
import datetime
import json
import math
from time import sleep

import mysql.connector
import requests

from . import mws


# sys.stdout = open('file.log', 'w')


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
    last_product_refreshment_h = 0
    last_product_refreshment_min = 0
    last_feed_submitted_h = 0
    last_feed_submitted_min = 0
    last_feed_submitted_datetime = datetime.datetime.now()
    price_submitting_feed = ''
    delete_submitting_feed = ''
    message_counter = 1
    delete_message_counter = 1

    current_index = 10000

    minimum_marge_percentage = 0.2

    product_list = []
    amazon_listing = []

    db = {}
    cursor = {}

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, config, conf):
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

        self.price_submitting_feed = self.get_empty_price_feed_head()
        self.delete_submitting_feed = self.get_empty_delete_feed_head()

        self.db = mysql.connector.connect(
            host=conf['host'],
            user=conf['user'],
            passwd=conf['password'],
            database='mbot')
        self.cursor = self.db.cursor()

        def connection_test():
            bb_test_url = self.bb_url + '/rest/user/purse.json?_format=json'
            r = requests.get(bb_test_url, headers=self.bb_header)
            report_list = self.reports_api.get_report_list()
            if report_list.response.status_code == 200 and r.status_code == 200:
                myprint('Connections successful')
                self.running = True
            else:
                if report_list.response.status_code != 200:
                    myprint('Connection to Amazon unsuccessful')
                if r.status_code != 200:
                    myprint('Connection to BigBuy unsuccessful')

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
            myprint('Products could not be refreshed due to an Error: ' + e.value)
            self.running = False
        else:
            myprint('Products successfully refreshed')
            myprint('Product count: ' + str(len(self.product_list)))

    def update_price(self):
        if self.current_index >= len(self.product_list):
            self.current_index = 0
        print('index' + str(self.current_index))
        current_item = self.product_list[self.current_index]
        current_item_information = self.get_product_information(current_item, True)
        is_valid, is_german = self.is_valid_item(current_item, current_item_information)
        if is_valid:
            shipping_cost, shipper = self.get_shipping_cost(current_item)
            price = self.calculate_price(current_item, shipping_cost)
            if not is_german:
                pass  # todo
            self.submit_price(current_item, shipper, price, shipping_cost)
        else:
            self.delete_item(current_item)
        self.current_index += 1

    def delete_item(self, item):
        self.delete_submitting_feed += self.get_delete_message_for_item(item)
        myprint('trying to delete')
        if self.last_feed_submitted_datetime + datetime.timedelta(minutes=20) < datetime.datetime.now():
            self.delete_submitting_feed += self.get_empty_delete_feed_foot()
            self.delete_submitting_feed = self.delete_submitting_feed.encode('utf-8')
            self.last_feed_submitted_datetime = datetime.datetime.now()
            deletion_response = self.feeds_api.submit_feed(self.delete_submitting_feed, '_POST_PRODUCT_PRICING_DATA_',
                                                           marketplaceids=self.marketplace_id)
            self.delete_submitting_feed = self.get_empty_delete_feed_head()
            myprint(deletion_response.parsed)
            myprint('items deleted')

    def submit_price(self, item, shipper, price, shipping):
        rounded_price = self.round_price(price + shipping - 5)
        self.price_submitting_feed += self.get_price_feed_for_product(item, rounded_price)
        myprint('trying to submit')
        if self.last_feed_submitted_datetime + datetime.timedelta(minutes=20) < datetime.datetime.now():
            # if self.last_feed_submitted_h < now.hour or self.last_feed_submitted_min + 20 < now.minute:
            # self.last_feed_submitted_h = now.hour
            # self.last_feed_submitted_min = now.minute
            self.last_feed_submitted_datetime = datetime.datetime.now()
            self.price_submitting_feed += self.get_emtpy_price_feed_footer()
            self.price_submitting_feed = self.price_submitting_feed.encode('utf-8')
            price_response = self.feeds_api.submit_feed(self.price_submitting_feed, '_POST_PRODUCT_PRICING_DATA_',
                                                        marketplaceids=self.marketplace_id)
            self.price_submitting_feed = self.get_empty_price_feed_head()
            myprint(price_response.parsed)
            myprint('Prices submitted')

    def get_empty_delete_feed_head(self):
        return '<?xml version="1.0" encoding="UTF-8"?> ' \
               '<AmazonEnvelope' \
               'xmlns: xsi = "http://www.w3.org/2001/XMLSchema-instance"' \
               'xsi: noNamespaceSchemaLocation = "amzn-envelope.xsd">' \
               '<Header>' \
               '<DocumentVersion>1.01</DocumentVersion >' \
               '<MerchantIdentifier>' + str(self.seller_id) + '</MerchantIdentifier>' \
                                                              '</Header>' \
                                                              '<MessageType>Product</MessageType> '

    def get_delete_message_for_item(self, item):
        return '<Message><MessageID>' + str(
            self.delete_message_counter) + '</MessageID><OperationType>Delete</OperationType><Product><SKU>' + str(
            item['sku']) + '</SKU></Message>'

    @staticmethod
    def get_empty_delete_feed_foot():
        return '</AmazonEnvelope>'

    def get_empty_price_feed_head(self):
        return '<?xml version="1.0" encoding="utf-8" ?> ' \
               '<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' \
               'xsi:noNamespaceSchemaLocation="amzn-envelope.xsd"> ' \
               '<Header> <DocumentVersion>1.01</DocumentVersion> ' \
               '<MerchantIdentifier>' + self.seller_id + '</MerchantIdentifier> </Header>' \
                                                         '<MessageType>Price</MessageType> '

    @staticmethod
    def get_emtpy_price_feed_footer():
        return '</AmazonEnvelope>'

    def get_price_feed_for_product(self, item, price):
        return '<Message> <MessageID>' + str(self.message_counter) + '</MessageID> ' \
                                                                     '<Price> <SKU>' \
               + str(item['sku']) + '</SKU><StandardPrice currency="EUR">' + str(price) + \
               '</StandardPrice> ' \
               '</Price> </Message> '

    # ------------------------------------------------------------------------------------------------------------------
    def get_bb_listing_skus_and_catalog(self):
        # bb_catalog_url = self.bb_url + '/rest/catalog/products.json'
        # bb_catalog = json.loads(requests.get(bb_catalog_url, headers=self.bb_header).text)
        self.cursor.execute('SELECT * FROM bb_items')
        keys = ['id', 'sku', 'wholesalePrice', 'height', 'width', 'depth']
        bb_catalog = [dict(zip(keys, x)) for x in self.cursor.fetchall()]
        sku_list = list(map(lambda x: x["sku"], bb_catalog))
        if not len(sku_list) > 0:
            raise RefreshmentError('BigBuy: Catalog not receivable')
        return sku_list, bb_catalog

    def get_amazon_listing(self):
        report_request = self.reports_api.request_report(report_type='_GET_MERCHANT_LISTINGS_DATA_')
        if report_request.response.status_code == 200:
            starting_date = datetime.datetime.now() - datetime.timedelta(hours=6)
            sleep(60)
            report_list = self.reports_api.get_report_list(fromdate=starting_date)
            newest_report_meta_list = list(
                filter(lambda x: x.ReportType == '_GET_MERCHANT_LISTINGS_DATA_', report_list.parsed.ReportInfo))
            while bool(report_list.parsed['HasNext']['value']) and len(newest_report_meta_list) < 1:
                report_list = self.reports_api.get_report_list(fromdate=starting_date,
                                                               next_token=report_list.parsed['NextToken']['value'])
                newest_report_meta_list = list(
                    filter(lambda x: x.ReportType == '_GET_MERCHANT_LISTINGS_DATA_', report_list.parsed.ReportInfo))
            report = self.reports_api.get_report(newest_report_meta_list[0].ReportId)
            parsed_report = report.parsed.decode('iso-8859-1').split('\n')
            amazon_listing = [x for x in list(map(lambda x: x.split('\t'), parsed_report)) if len(x) > 3]
            sku_list = list(map(lambda x: x[3] if not len(x) < 3 else 0, amazon_listing))
            return sku_list, amazon_listing

    def calculate_price(self, item, shipping):
        wholesale_price = price = item['wholesalePrice']
        mwst = 1 / 1.19
        amazon_fee = self.get_amazon_fee(item['sku'], price, shipping)
        while price * mwst - (shipping * mwst) - (wholesale_price + amazon_fee) < 0.1 * price:
            price *= 1.05
            amazon_fee = self.get_amazon_fee(item['sku'], price, shipping)
        return price

    # ------------------------------------------------------------------------------------------------------------------
    def get_product_information(self, item, german):
        # spanish items!
        iso_code = 'de'
        if not german:
            iso_code = 'es'
        self.cursor.execute(
            'SELECT * FROM bb_item_information WHERE id = ' + str(item['id']) + ' AND isoCode = "' + iso_code + '"')
        if self.cursor.rowcount < 1:
            item_url = self.bb_url + '/rest/catalog/productinformation/' + str(item['id']) + '.json?isoCode=' + iso_code
            r = requests.get(item_url, headers=self.bb_header)
            self.cursor.fetchall()
            print('fetching item for the first time')
            print('Index : ' + str(self.current_index))
            while 'code' in r.text:
                sleep(30)
                print('trying to fetch item_info again')
                r = requests.get(item_url, headers=self.bb_header)
            return json.loads(r.text)
        else:
            item_info = self.cursor.fetchone()
            keys = ['id', 'name', 'sku', 'isoCode']
            return dict(zip(keys, item_info))

    def get_amazon_fee(self, sku, shipping, price):
        response = self.products_api.get_my_fee_estimate(self.marketplace_id, sku, price, shipping)
        fee_objects = response.parsed['FeesEstimateResultList']['FeesEstimateResult']
        while 'FeesEstimate' not in fee_objects:
            sleep(5)
            response = self.products_api.get_my_fee_estimate(self.marketplace_id, sku, price, shipping)
            fee_objects = response.parsed['FeesEstimateResultList']['FeesEstimateResult']
        return float(fee_objects['FeesEstimate']['TotalFeesEstimate']['Amount']['value'])

    def get_shipping_cost(self, item):
        order_object = {"order": {"delivery": {"isoCountry": "DE", "postcode": "74336"},
                                  "products": [{"reference": item['sku'], "quantity": "1"}]}}
        json_body = json.dumps(order_object)
        r = requests.post(self.bb_url + '/rest/shipping/orders.json', data=json_body, headers=self.bb_header)
        cheapest_shipper = min(json.loads(r.text)['shippingOptions'], key=lambda x: x['cost'])
        return cheapest_shipper['cost'], cheapest_shipper

    # ------------------------------------------------------------------------------------------------------------------

    def is_valid_item(self, item, item_information):
        correct_size = self.is_approved_size(item)
        correct_price = self.is_an_approved_price(item)
        correct_brand = self.is_an_approved_brand(item_information)
        correct_sku = self.is_an_approved_sku(item_information)
        correct_category = self.is_an_approved_category(item_information)
        correct_name, german_name = self.is_same_name(item_information)
        result = correct_size and correct_price and correct_brand and correct_sku and correct_category and correct_name
        return result, german_name

    def is_same_name(self, item_information):
        amazon_item_list = [x for x in self.amazon_listing if x[3] == item_information['sku']]
        if not len(amazon_item_list) > 0:
            myprint('Error while evaluating if item is valid for new pricing')
            return
        if amazon_item_list[0][0] == item_information['name']:
            return True, True
        else:
            spanish_item = self.get_product_information(item_information, False)
            while 'code' in spanish_item:
                sleep(5)
                spanish_item = self.get_product_information(item_information, False)
            if amazon_item_list[0][0] in spanish_item['name']:
                return True, False
        return False, False

    def is_an_approved_category(self, item_information):
        item_categories = []
        self.cursor.execute(
            'SELECT * FROM bb_item_categories WHERE id = ' + str(item_information['id']))
        if self.cursor.rowcount < 1:
            category_url = self.bb_url + '/rest/catalog/productcategories/' + str(item_information['id']) + '.json'
            r = requests.get(category_url, headers=self.bb_header)
            item_categories = json.loads(r.text)
        else:
            keys = ['id', 'name', 'sku', 'isoCode']
            item_categories = [dict(zip(keys, item_category)) for item_category in self.cursor.fetchall()]
        category_list = self.get_csv_file_as_list('../categories.csv')
        same_categories = [x for x in item_categories if str(x['category']) in category_list]
        self.cursor.fetchall()
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
                myprint('Multiple products with the same SKU detected')
        return result


# ----------------------------------------------------------------------------------------------------------------------
class RefreshmentError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def myprint(text):
    print(text, flush=True)
