import unittest
from unittest.mock import Mock, patch
from variant_checks import variant_config, check_sizes
from test_app import CFG, page, variant
from browser_check import verified_status
from app import send_status


class VariantChecksTests(unittest.TestCase):
    def test_size_s_does_not_inherit_xs_sku(self):
        result = variant_config(CFG, 'S')
        self.assertEqual(result['PRODUCT_SIZE'], 'S')
        self.assertEqual(result['PRODUCT_SKU'], '')
        self.assertEqual(CFG['PRODUCT_SIZE'], 'XS')
        self.assertEqual(variant_config(CFG, 'XS')['PRODUCT_SKU'], '673107873')

    def test_additional_size_uses_fresh_document_in_same_session(self):
        session = Mock()
        session.check.side_effect = [('unavailable', 'XS test'), ('unknown', 'S test')]
        results = list(check_sizes(session, CFG, ['XS', 'S']))
        self.assertEqual([r[0]['PRODUCT_SIZE'] for r in results], ['XS', 'S'])
        self.assertFalse(session.check.call_args_list[0].kwargs['force_refresh'])
        self.assertTrue(session.check.call_args_list[1].kwargs['force_refresh'])

    def test_s_cannot_be_available_without_its_variant_identity(self):
        cfg = variant_config(CFG, 'S')
        self.assertEqual(verified_status(page(variant(size='S', sku='')), cfg, True, False, True), 'unknown')
        self.assertEqual(verified_status('', cfg, True, True, False), 'unavailable')

    def test_telegram_labels_size_s_without_xs_sku(self):
        with patch('app.notify', return_value=1) as notify:
            send_status(variant_config(CFG, 'S'), 'unknown', 'test')
        message = notify.call_args.args[1]
        self.assertIn(' · S · Helles Pink', message)
        self.assertNotIn('673107873', message)


if __name__ == '__main__':
    unittest.main()
