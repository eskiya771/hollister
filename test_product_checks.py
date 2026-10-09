import unittest
from unittest.mock import patch
from product_checks import configured_products, CAMISOLE_URL
from test_app import CFG
from app import send_status
from variant_checks import variant_config


class ProductChecksTests(unittest.TestCase):
    def test_unknown_color_does_not_enable_product(self):
        self.assertEqual(len(configured_products(CFG)), 1)

    def test_product_and_size_identifiers_stay_separate(self):
        cfg = dict(CFG, CAMISOLE_COLOR='Testfarbe', PRODUCT_SKU_S='henley-s')
        first, second = configured_products(cfg)
        self.assertEqual(first['PRODUCT_SKU'], CFG['PRODUCT_SKU'])
        self.assertEqual(second['PRODUCT_URL'], CAMISOLE_URL)
        self.assertEqual(second['PRODUCT_SIZES'], 'XS,S,XXL')
        for size in ('XS', 'S', 'XXL'):
            variant = variant_config(second, size)
            self.assertEqual(variant['PRODUCT_SKU'], '')
            with patch('app.notify', return_value=1) as notify:
                send_status(variant, 'unknown', 'test')
            message = notify.call_args.args[1]
            self.assertIn('Camisole mit Spitzenbesatz', message)
            self.assertIn(CAMISOLE_URL, message)
            self.assertNotIn('Henley', message)
        self.assertNotIn('CAMISOLE_COLOR', CFG)
