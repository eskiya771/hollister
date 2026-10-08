import json
import unittest
from app import stock_from_html


def page(products):
    return '<script type="application/ld+json">' + json.dumps(products) + '</script>'


def variant(size='XS', color='Helles Pink', status='InStock'):
    return {'@type': 'Product', 'size': size, 'color': color, 'offers': {'availability': 'https://schema.org/' + status}}


class StockTests(unittest.TestCase):
    def check(self, html):
        return stock_from_html(html, 'XS', 'Helles Pink')[0]

    def test_exact_variant_available(self):
        self.assertEqual(self.check(page({'@type': 'ProductGroup', 'hasVariant': [variant()]})), 'available')

    def test_wrong_size_or_color_cannot_trigger_alert(self):
        self.assertEqual(self.check(page([variant(size='S'), variant(color='White')])), 'unknown')

    def test_exact_variant_sold_out(self):
        self.assertEqual(self.check(page(variant(status='OutOfStock'))), 'unavailable')

    def test_conflicting_data_is_unknown(self):
        self.assertEqual(self.check(page([variant(), variant(status='OutOfStock')])), 'unknown')

    def test_generic_stock_and_challenge_cannot_trigger_alert(self):
        self.assertEqual(self.check(page({'@type': 'Product', 'offers': {'availability': 'https://schema.org/InStock'}})), 'unknown')
        self.assertEqual(self.check('<title>Client Challenge</title>'), 'unknown')

    def test_bad_json_is_unknown(self):
        self.assertEqual(self.check('<script type="application/ld+json">{oops}</script>'), 'unknown')


if __name__ == '__main__':
    unittest.main()
