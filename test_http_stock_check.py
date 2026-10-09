import unittest
from unittest.mock import patch
from http_stock_check import check, query_for, TARGETS
from session_http_diagnostic import summarize_stock


def api_response(color_id='63766393', sku='673107742', quantity=0, state='Unavailable'):
    return {'status': 200, 'records': [{'path': '$.data.collection.collection.skus[0]',
             'fields': {'productId': color_id, 'shortSku': sku, 'sizePrimary': 'XS_p',
                        'inventory': quantity, 'inventoryStatus': state}}]}


class HttpStockTests(unittest.TestCase):
    def test_exact_sku_and_missing_size(self):
        with patch('http_stock_check.fetch', return_value=api_response()):
            result = check('henley')
        self.assertEqual(result['sizes']['XS']['status'], 'ausverkauft')
        self.assertEqual(result['sizes']['S']['status'], 'nicht prüfbar')

    def test_wrong_color_and_wrong_sku_are_unknown(self):
        for response in (api_response(color_id='63757975'), api_response(sku='999')):
            with patch('http_stock_check.fetch', return_value=response):
                self.assertEqual(check('henley')['sizes']['XS']['status'], 'nicht prüfbar')

    def test_partial_graphql_error_and_boolean_quantity_are_unknown(self):
        response = api_response()
        response['graphql_error_types'] = ['graphql_error']
        self.assertEqual(summarize_stock(response, '63766393', ('XS',), {})['XS']['status'], 'nicht prüfbar')
        self.assertEqual(summarize_stock(api_response(quantity=False), '63766393', ('XS',), {})['XS']['status'], 'nicht prüfbar')

    def test_camisole_query_uses_its_own_collection_and_color(self):
        query = query_for(TARGETS['camisole'])
        self.assertIn('706282', query)
        self.assertIn('63617331', query)
        self.assertNotIn('711658', query)
        with patch('http_stock_check.fetch', return_value=api_response('63617331', '671819156')):
            result = check('camisole')
        self.assertEqual(result['sizes']['XS']['status'], 'ausverkauft')
        self.assertEqual(result['sizes']['XXL']['status'], 'nicht prüfbar')


if __name__ == '__main__':
    unittest.main()
