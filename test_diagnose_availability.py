import json
import unittest
from diagnose_availability import embedded, endpoint, extract, public_parameters, validate_target


class DiagnosticPrivacyTests(unittest.TestCase):
    def test_nested_personal_and_auth_fields_never_exported(self):
        raw = {'data': {'sku': '123', 'size': 'XS', 'availability': 'InStock',
                        'customer': {'sku': 'SECRET_CUSTOMER'}, 'token': 'SECRET_TOKEN',
                        'email': 'SECRET_EMAIL', 'description': 'SECRET_DESCRIPTION'}}
        result = json.dumps(extract(raw))
        self.assertIn('InStock', result)
        self.assertNotIn('SECRET', result)

    def test_query_credentials_and_unknown_values_removed(self):
        result = endpoint('https://name:password@www.hollisterco.com/api/product?productId=63617320&token=SECRET&tracking=PRIVATE#SECRET')
        self.assertIn('63617320', result)
        for value in ('password', 'SECRET', 'PRIVATE', 'name:'):
            self.assertNotIn(value, result)

    def test_initial_json_and_assignments_preserve_stock_evidence(self):
        html = '<script type="application/ld+json">{"sku":"123","availability":"https://schema.org/InStock","token":"SECRET"}</script><script>window.product = {"size":"XS","inventory":0};</script>'
        result = embedded(html)
        self.assertEqual(len(result['json']), 2)
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertIn('inventory', json.dumps(result))

    def test_external_urls_omitted(self):
        self.assertEqual(endpoint('https://tracker.example/SECRET'), '[external omitted]')

    def test_public_graphql_parameters_do_not_export_credentials(self):
        result = public_parameters({'operationName': 'ProductInventory', 'variables': {'productId': '63617320', 'token': 'SECRET'}, 'extensions': {'persistedQuery': {'version': 1, 'sha256Hash': 'a' * 64}}, 'authorization': 'SECRET'})
        self.assertEqual(result['variables'], {'productId': '63617320'})
        self.assertEqual(result['extensions']['persistedQuery']['sha256Hash'], 'a' * 64)
        self.assertNotIn('SECRET', json.dumps(result))

    def test_both_targets_and_mismatched_url(self):
        validate_target('63757420', 'Helles Pink', ('XS', 'S'), 'https://www.hollisterco.com/shop/eu-de/p/henley-63757420')
        validate_target('63270319', 'Weiß', ('XS', 'S', 'XXL'), 'https://www.hollisterco.com/shop/eu-de/p/camisole-63270319')
        with self.assertRaises(ValueError):
            validate_target('63757420', 'Helles Pink', ('XS', 'S'), 'https://www.hollisterco.com/shop/eu-de/p/camisole-63270319')


if __name__ == '__main__':
    unittest.main()
