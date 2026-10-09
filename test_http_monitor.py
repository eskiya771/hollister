import copy
import io
import json
import unittest
from unittest.mock import MagicMock, patch
import http_stock as stock
import http_monitor as monitor


def response():
    target = stock.TARGETS['henley']
    return {'data': {'collection': {'collection': {'skus': [
        dict(productId=target['product'], shortSku=sku, sizePrimary=size + '_p',
             sizeSecondary=None, inventory=0, inventoryStatus='Unavailable')
        for size, sku in target['skus'].items()]}}}}


class ProductionHttpTests(unittest.TestCase):
    def test_strict_stock_contract(self):
        data = response()
        target = stock.TARGETS['henley']
        self.assertEqual(stock.classify(data, target)['XS'][0], 'unavailable')
        row = data['data']['collection']['collection']['skus'][0]
        row.update(inventory=4, inventoryStatus='Available')
        self.assertEqual(stock.classify(data, target)['XS'][0], 'available')
        for change in ({'inventory': True}, {'inventory': -1}, {'shortSku': 'other'},
                       {'productId': 'other'}, {'sizeSecondary': 'other'},
                       {'inventoryStatus': 'Unavailable'}):
            changed = copy.deepcopy(data)
            changed['data']['collection']['collection']['skus'][0].update(change)
            self.assertEqual(stock.classify(changed, target)['XS'][0], 'unknown')
        data['errors'] = [{'message': 'SECRET'}]
        self.assertTrue(all(s == 'unknown' for s, _ in stock.classify(data, target).values()))

    def test_duplicates_missing_and_malformed(self):
        data = response()
        rows = data['data']['collection']['collection']['skus']
        rows.append(dict(rows[0]))
        self.assertEqual(stock.classify(data, stock.TARGETS['henley'])['XS'][0], 'unknown')
        for invalid in (None, [], {}, {'data': None}):
            self.assertTrue(all(s == 'unknown' for s, _ in stock.classify(invalid, stock.TARGETS['henley']).values()))

    def test_transport_no_credentials_and_cache_guard(self):
        opener = MagicMock()
        res = opener.open.return_value.__enter__.return_value
        res.status = 200
        res.headers = {'Age': '120'}
        res.read.return_value = json.dumps(response()).encode()
        with patch('http_stock.urllib.request.build_opener', return_value=opener):
            self.assertEqual(stock.check_product(stock.TARGETS['henley'])['XS'][0], 'unavailable')
            req = opener.open.call_args.args[0]
            self.assertEqual(req.method, 'POST')
            self.assertFalse(any(k.lower() in ('cookie', 'authorization') for k in req.headers))
            for age in ('901', 'invalid', '-1'):
                res.headers = {'Age': age}
                self.assertEqual(stock.check_product(stock.TARGETS['henley'])['XS'][0], 'unknown')
            res.headers = {}
            res.read.return_value = b'<html>challenge</html>'
            self.assertEqual(stock.check_product(stock.TARGETS['henley'])['XS'][0], 'unknown')
            opener.open.side_effect = RuntimeError('SECRET')
            self.assertNotIn('SECRET', str(stock.check_product(stock.TARGETS['henley'])))

    def test_cycle_batches_five_variants_in_two_requests(self):
        def fake(target, age, inventories):
            return {size: ('unknown', 'API: test') for size in target['skus']}
        with patch('http_stock.check_product', side_effect=fake) as check:
            results = stock.check_all({})
        self.assertEqual(check.call_count, 2)
        self.assertEqual(len(results), 5)
        self.assertEqual([v['PRODUCT_SIZE'] for v, _, _ in results], ['XS', 'S', 'XS', 'S', 'XXL'])

    def test_immediate_cycle_and_interval(self):
        stop = MagicMock()
        stop.is_set.side_effect = [False, True]
        with patch('http_monitor.STOP', stop), patch('http_monitor.load_env'), \
             patch('http_monitor.os.environ', {'TELEGRAM_BOT_TOKEN': 'test', 'TELEGRAM_CHAT_ID': 'test'}), \
             patch('http_monitor.signal.signal'), patch('http_monitor.time.monotonic', side_effect=[100, 105]), \
             patch('http_monitor.check_all', return_value=[]) as check, \
             patch('http_monitor.send_summary', return_value=True) as send, \
             patch('sys.argv', ['http_monitor.py']):
            self.assertEqual(monitor.main(), 0)
        check.assert_called_once()
        send.assert_called_once()
        stop.wait.assert_called_once_with(55)

    def test_config(self):
        self.assertEqual(monitor.validate({}, False), 60)
        for cfg in ({'CHECK_INTERVAL_SECONDS': '59'}, {'HTTP_MAX_CACHE_AGE_SECONDS': '901'}, {'TZ': 'bad'}):
            with self.assertRaises(ValueError):
                monitor.validate(cfg, False)


if __name__ == '__main__':
    unittest.main()
