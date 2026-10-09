import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import stock_from_html, validate_config, notify, run_once, load_env, main, STOP
from browser_check import verified_status, german_product

CFG = dict(PRODUCT_URL='https://www.hollisterco.com/shop/eu-de/p/henley-mit-leopardenprint-und-logo-63757420?seq=08', PRODUCT_SKU='673107873', PRODUCT_SIZE='XS', PRODUCT_COLOR='Helles Pink', TELEGRAM_BOT_TOKEN='test-only', TELEGRAM_CHAT_ID='123')


def page(products):
    return '<script type="application/ld+json">' + json.dumps(products) + '</script>'


def variant(size='XS', color='Helles Pink', status='InStock', sku='673107873'):
    return {'@type': 'Product', 'sku': sku, 'size': size, 'color': color, 'offers': {'availability': 'https://schema.org/' + status}}


class StockTests(unittest.TestCase):
    def check(self, html):
        return stock_from_html(html, 'XS', 'Helles Pink', '673107873')[0]

    def test_exact_variant_available(self):
        self.assertEqual(self.check(page({'@type': 'ProductGroup', 'hasVariant': [variant()]})), 'available')

    def test_old_protection_script_does_not_discard_variant_data(self):
        self.assertEqual(self.check('<script src="/_fs-ch-example/script.js"></script>' + page(variant())), 'available')

    def test_wrong_identity_never_triggers(self):
        for product in (variant(size='S'), variant(color='White'), variant(sku='999'), variant(sku='')):
            self.assertEqual(self.check(page(product)), 'unknown')

    def test_exact_variant_sold_out(self):
        self.assertEqual(self.check(page(variant(status='OutOfStock'))), 'unavailable')

    def test_conflicting_data_is_unknown(self):
        self.assertEqual(self.check(page([variant(), variant(status='OutOfStock')])), 'unknown')

    def test_generic_stock_challenge_and_bad_json(self):
        for html in (page({'@type': 'Product', 'offers': {'availability': 'https://schema.org/InStock'}}), '<title>Client Challenge</title>', '<script type="application/ld+json">{oops}</script>'):
            self.assertEqual(self.check(html), 'unknown')

    def test_stale_button_and_mismatched_ui(self):
        self.assertEqual(verified_status(page(variant(size='S')), CFG, True, False, True), 'unknown')
        self.assertEqual(verified_status(page(variant(status='OutOfStock')), CFG, True, False, True), 'unknown')
        self.assertEqual(verified_status(page(variant()), CFG, False, False, True), 'unknown')
        self.assertEqual(verified_status(page(variant()), CFG, True, True, True), 'unknown')
        self.assertEqual(verified_status(page(variant()), CFG, True, False, True), 'available')
        self.assertEqual(verified_status(page(variant(status='OutOfStock')), CFG, True, True, False), 'unavailable')

    def test_observed_generic_style_stock_does_not_override_selected_sold_out(self):
        html = page({'@type': 'Product', 'SKU': '357-293-00059-630',
                     'offers': {'availability': 'http://schema.org/InStock'}})
        self.assertEqual(verified_status(html, CFG, True, True, False), 'unavailable')
        self.assertEqual(verified_status(html, CFG, False, True, False), 'unknown')
        self.assertEqual(verified_status(html, CFG, True, False, True), 'unknown')

    def test_german_product_only(self):
        self.assertTrue(german_product(CFG['PRODUCT_URL'], CFG['PRODUCT_URL']))
        for url in ('https://www.hollisterco.com/shop/us/p/other', CFG['PRODUCT_URL'].replace('hollisterco.com', 'hollisterco.com.attacker.test'), CFG['PRODUCT_URL'].replace('63757420', '123')):
            self.assertFalse(german_product(url, CFG['PRODUCT_URL']))


class AppTests(unittest.TestCase):
    def test_validate(self):
        cfg = dict(CFG)
        del cfg['PRODUCT_SKU']
        self.assertEqual(validate_config(cfg), 60)
        self.assertEqual(cfg['PRODUCT_SKU'], '673107873')
        for change in ({'PRODUCT_SIZE': 'S'}, {'CHECK_INTERVAL_SECONDS': '59'}, {'CHECK_MODE': 'http'}, {'PRODUCT_URL': CFG['PRODUCT_URL'].replace('eu-de', 'us')}, {'TZ': 'Bad/Zone'}):
            with self.assertRaises(ValueError):
                validate_config(CFG | change)

    def test_utf8_bom_env_and_existing_values(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ', {'EXISTING': 'keep'}, clear=True):
            import os
            path = Path(directory) / '.env'
            path.write_text('COLOR="Helles Pink"\nEXISTING=replace\n', encoding='utf-8-sig')
            load_env(path)
            self.assertEqual(os.environ['COLOR'], 'Helles Pink')
            self.assertEqual(os.environ['EXISTING'], 'keep')

    def test_telegram_requires_correct_chat_ack(self):
        for body, expected in (({'ok': True, 'result': {'chat': {'id': 123}, 'message_id': 7}}, 7), ({'ok': True, 'result': {'chat': {'id': 999}, 'message_id': 7}}, None), ({'ok': False}, None)):
            with patch('app.urllib.request.urlopen', return_value=io.BytesIO(json.dumps(body).encode())):
                if expected:
                    self.assertEqual(notify(CFG, 'test'), expected)
                else:
                    with self.assertRaises(RuntimeError):
                        notify(CFG, 'test')

    def test_every_check_sends_including_unknown_and_unchanged(self):
        for status in ('available', 'unavailable', 'unknown'):
            with patch('app.check', return_value=(status, 'test')), patch('app.notify', return_value=7) as send:
                run_once(CFG)
                run_once(CFG)
                self.assertEqual(send.call_count, 2)
                self.assertIn('673107873', send.call_args.args[1])

    def test_delivery_failure_redacts_error(self):
        with patch('app.check', return_value=('unknown', 'test')), patch('app.notify', side_effect=RuntimeError('SECRET_TOKEN')), self.assertLogs('hollister') as logs:
            self.assertEqual(run_once(CFG), 'delivery_failed')
        self.assertNotIn('SECRET_TOKEN', '\n'.join(logs.output))

    def test_immediate_then_one_minute_schedule(self):
        STOP.clear()
        def stop_after_wait(seconds):
            self.assertEqual(seconds, 55)
            STOP.set()
        try:
            with patch.dict('os.environ', CFG, clear=True), patch('app.load_env'), patch('sys.argv', ['app.py']), patch('app.signal.signal'), patch('app.run_once', return_value='unavailable') as run, patch('app.time.monotonic', side_effect=[100, 105]), patch.object(STOP, 'wait', side_effect=stop_after_wait):
                self.assertEqual(main(), 0)
                run.assert_called_once()
        finally:
            STOP.clear()


if __name__ == '__main__':
    unittest.main()
