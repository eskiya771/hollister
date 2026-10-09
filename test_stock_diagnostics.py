import json
import unittest
from stock_diagnostics import clean, find_records


class DiagnosticTests(unittest.TestCase):
    def test_only_product_fields_are_retained(self):
        data = {'sku': '673063170', 'size': 'XS', 'color': 'Helles Pink',
                'offers': {'availability': 'OutOfStock', 'seller': {'email': 'PRIVATE'}},
                'token': 'SECRET', 'customer': {'name': 'PRIVATE'},
                'attributes': [{'name': 'token', 'value': 'SECRET'}]}
        result = clean(data)
        self.assertEqual(result['sku'], '673063170')
        self.assertEqual(result['offers'], {'availability': 'OutOfStock'})
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_exact_sku_response_records_only(self):
        data = {'items': [{'sku': 'wrong', 'inventory': 10},
                          {'sku': '673063170', 'inventory': 0}],
                'customer': {'email': 'PRIVATE'}}
        self.assertEqual(find_records(data, '673063170'), [{'sku': '673063170', 'inventory': 0}])

    def test_sku_keyed_inventory(self):
        self.assertEqual(find_records({'673063170': {'available': False}}, '673063170'),
                         [{'sku': '673063170', 'inventory': {'available': False}}])


if __name__ == '__main__':
    unittest.main()
