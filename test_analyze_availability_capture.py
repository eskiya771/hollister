import unittest
from analyze_availability_capture import analyze


def capture(inventory=0, state='Unavailable', sku='123', ui='ausverkauft'):
    return {'product_id': '63270319', 'snapshots': [{'phase': 'select_white', 'selection': [{'value': '63617331'}]}],
            'responses': [{'type': 'document', 'phase': 'initial_load', 'initial_html': {'json': [{'records': [
                {'path': '$.CACHE.ROOT_QUERY.*.collection.skus[1]', 'fields': {'productId': '63617331', 'sizePrimary': 'XS_p', 'shortSku': sku, 'inventory': inventory, 'inventoryStatus': state}}]}]}}],
            'requests': [], 'sizes': {'XS': {'status': ui}, 'S': {'status': 'nicht prüfbar'}, 'XXL': {'status': 'nicht prüfbar'}}, 'http_tests': [], 'errors': []}


class ExactVariantTests(unittest.TestCase):
    def test_positive_and_zero_stock(self):
        self.assertEqual(analyze(capture())['sizes']['XS']['status'], 'ausverkauft')
        self.assertEqual(analyze(capture(42, 'Available', ui='verfügbar'))['sizes']['XS']['status'], 'verfügbar')

    def test_missing_size_unknown(self):
        self.assertEqual(analyze(capture())['sizes']['S']['status'], 'nicht prüfbar')

    def test_conflicting_status_and_inventory_unknown(self):
        self.assertEqual(analyze(capture(42))['sizes']['XS']['status'], 'nicht prüfbar')

    def test_wrong_color_or_ui_conflict_unknown(self):
        wrong = capture()
        wrong['snapshots'][0]['selection'][0]['value'] = '63617320'
        self.assertEqual(analyze(wrong)['sizes']['XS']['status'], 'nicht prüfbar')
        self.assertEqual(analyze(capture(ui='verfügbar'))['sizes']['XS']['status'], 'nicht prüfbar')

    def test_henley_color_and_requested_sizes(self):
        sample = capture()
        sample.update(product_id='63757420', color='Helles Pink',
                      selected_color={'name': 'Helles Pink', 'product_id': '12345678', 'checked': True, 'heading_confirmed': True})
        sample['sizes'].pop('XXL')
        sample['responses'][0]['initial_html']['json'][0]['records'][0]['fields']['productId'] = '12345678'
        result = analyze(sample)
        self.assertEqual(result['color'], 'Helles Pink')
        self.assertEqual(set(result['sizes']), {'XS', 'S'})
        self.assertEqual(result['sizes']['XS']['status'], 'ausverkauft')
        sample['selected_color']['heading_confirmed'] = False
        self.assertEqual(analyze(sample)['sizes']['XS']['status'], 'nicht prüfbar')


if __name__ == '__main__':
    unittest.main()
