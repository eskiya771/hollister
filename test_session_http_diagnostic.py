import json
import unittest
from urllib.request import Request
from session_http_diagnostic import allowed_url, cookie_jar, parse_response, ScopedRedirect, summarize_stock


class SessionHttpTests(unittest.TestCase):
    def test_scope_rejects_external_redirect_and_plain_http(self):
        self.assertTrue(allowed_url('https://www.hollisterco.com/shop/eu-de/p/test-63757420'))
        for url in ('http://www.hollisterco.com/x', 'https://other.example/x', 'https://www.hollisterco.com:444/x', 'https://secret@www.hollisterco.com/x'):
            self.assertFalse(allowed_url(url))
        with self.assertRaises(ValueError):
            ScopedRedirect().redirect_request(Request('https://www.hollisterco.com/x'), None, 302, '', {}, 'https://other.example/x')

    def test_cookies_are_domain_scoped_and_expired_values_not_sent(self):
        jar = cookie_jar([
            {'name': 'test', 'value': 'SECRET_COOKIE', 'domain': '.hollisterco.com', 'path': '/', 'secure': True, 'expires': -1},
            {'name': 'foreign', 'value': 'SECRET_FOREIGN', 'domain': '.other.example', 'path': '/', 'expires': -1},
            {'name': 'expired', 'value': 'SECRET_EXPIRED', 'domain': '.hollisterco.com', 'path': '/', 'expires': 1},
        ])
        own = Request('https://www.hollisterco.com/shop/')
        jar.add_cookie_header(own)
        self.assertIn('SECRET_COOKIE', own.get_header('Cookie'))
        self.assertNotIn('SECRET_EXPIRED', own.get_header('Cookie'))
        external = Request('https://other.example/')
        jar.add_cookie_header(external)
        self.assertIsNone(external.get_header('Cookie'))

    def test_response_filters_secrets_and_exact_stock_matches(self):
        html = b'<script>window.state={"CACHE":{"ROOT_QUERY":{"product":{"collection":{"skus":[{"productId":"12345678","shortSku":"123","sizePrimary":"XS_p","inventory":0,"inventoryStatus":"Unavailable"}]}},"sessionToken":"SECRET_RESPONSE"}}};</script>'
        response = parse_response(html, 200, 'https://www.hollisterco.com/shop/eu-de/p/test-63757420')
        self.assertNotIn('SECRET_RESPONSE', json.dumps(response))
        expected = {'XS': {'shortSku': '123', 'inventory': 0, 'inventoryStatus': 'Unavailable'}}
        result = summarize_stock(response, '12345678', ('XS', 'S'), expected)
        self.assertEqual(result['XS']['status'], 'ausverkauft')
        self.assertTrue(result['XS']['matches_browser_snapshot'])
        self.assertEqual(result['S']['status'], 'nicht prüfbar')
        self.assertEqual(summarize_stock(response, 'wrong', ('XS',), expected)['XS']['status'], 'nicht prüfbar')

    def test_challenge_or_non200_never_stock_confirmation(self):
        response = parse_response(b'<title>Client Challenge</title>', 200, 'https://www.hollisterco.com/x')
        self.assertTrue(response['challenge_detected'])
        self.assertEqual(summarize_stock(response, '123', ('XS',), {})['XS']['status'], 'nicht prüfbar')


if __name__ == '__main__':
    unittest.main()
