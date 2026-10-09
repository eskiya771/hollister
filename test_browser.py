import unittest
from unittest.mock import patch
from playwright.sync_api import sync_playwright
from browser_check import inspect_variant, dismiss_cookies, CookieDialogError, protected
from test_app import CFG, page as data, variant


class BrowserRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = sync_playwright().start()
        cls.browser = cls.p.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.p.stop()

    def test_protection_script_and_footer_are_not_a_captcha(self):
        page = self.browser.new_page()
        try:
            page.set_content('<title>Henley mit Logografik</title><h1>Henley mit Logografik</h1><footer>Protected by CAPTCHA</footer><script type="text/plain" src="/_fs-ch-example/script.js"></script>')
            self.assertFalse(protected(page))
            page.set_content('<title>Client Challenge</title><p>Enter the characters seen in the image below:</p>')
            self.assertTrue(protected(page))
            page.set_content('<title>Henley</title><h1>Henley</h1><div>Verify you are human</div>')
            self.assertTrue(protected(page))
        finally:
            page.close()

    def test_delayed_onetrust_banner_and_overlay_are_dismissed(self):
        page = self.browser.new_page()
        try:
            page.set_content('''<h1>Product already visible</h1><script>
            setTimeout(() => {
              document.body.insertAdjacentHTML('beforeend',
                '<div class="onetrust-pc-dark-filter">overlay</div>' +
                '<div id="onetrust-banner-sdk"><button id="onetrust-reject-all-handler">Reject All</button></div>');
              document.querySelector('button').onclick = () => setTimeout(() => {
                document.querySelector('#onetrust-banner-sdk').remove();
                document.querySelector('.onetrust-pc-dark-filter').remove();
              }, 200);
            }, 200);
            </script>''')
            dismiss_cookies(page, wait_timeout=2000, action_timeout=2000)
            self.assertEqual(page.locator('#onetrust-banner-sdk').count(), 0)
            self.assertEqual(page.locator('.onetrust-pc-dark-filter').count(), 0)
        finally:
            page.close()

    def test_unclosed_banner_is_explicit_failure(self):
        page = self.browser.new_page()
        try:
            page.set_content('<div id="onetrust-banner-sdk"><button id="onetrust-reject-all-handler">Reject All</button></div>')
            with self.assertRaises(CookieDialogError):
                dismiss_cookies(page, action_timeout=300)
        finally:
            page.close()

    def test_saved_consent_needs_no_banner(self):
        page = self.browser.new_page()
        try:
            page.set_content('<h1>Product</h1>')
            dismiss_cookies(page, wait_timeout=100)
        finally:
            page.close()

    def test_ui_stock_requires_matching_headings_and_no_loading_or_conflict(self):
        page = self.browser.new_page()
        cfg = dict(CFG, PRODUCT_SIZE='XXL', PRODUCT_COLOR='Weiß', PRODUCT_SKU='')
        try:
            page.set_content('<main><h2>Farbe: Weiss</h2><h2>Größe: S</h2>'
                             '<input type="radio" aria-label="Weiss" checked>'
                             '<input type="radio" aria-label="XXL" checked>'
                             '<button>In den Warenkorb</button></main>')
            color = page.get_by_role('radio', name='Weiss')
            size = page.get_by_role('radio', name='XXL')
            with patch('browser_check.german_product', return_value=True):
                self.assertEqual(inspect_variant(page, cfg, color, size), 'unknown')
                page.locator('h2').nth(1).evaluate('(e) => e.textContent = "Größe: XXL"')
                self.assertEqual(inspect_variant(page, cfg, color, size), 'available')
                page.locator('main').evaluate('(e) => e.insertAdjacentHTML("beforeend", "<p aria-busy=true>Loading</p>")')
                self.assertEqual(inspect_variant(page, cfg, color, size), 'unknown')
                page.locator('p').evaluate('(e) => {e.removeAttribute("aria-busy"); e.textContent="Dieser Artikel ist ausverkauft"}')
                self.assertEqual(inspect_variant(page, cfg, color, size), 'unknown')
        finally:
            page.close()

    def test_delayed_variant_update_does_not_report_previous_stock(self):
        page = self.browser.new_page()
        try:
            page.set_content('<main><input type="radio" aria-label="Helles Pink" checked><input type="radio" aria-label="XS" checked><button>In den Warenkorb</button></main>' + data(variant(size='S', sku='999')))
            color, size = page.get_by_role('radio', name='Helles Pink'), page.get_by_role('radio', name='XS', exact=True)
            with patch('browser_check.german_product', return_value=True):
                self.assertEqual(inspect_variant(page, CFG, color, size), 'unknown')
                page.evaluate('''product => setTimeout(() => {
                    document.querySelector('script').textContent = JSON.stringify(product);
                    document.querySelector('button').disabled = true;
                    document.querySelector('main').insertAdjacentHTML('beforeend', '<p>Dieser Artikel ist ausverkauft</p>');
                }, 400)''', variant(status='OutOfStock'))
                self.assertEqual(inspect_variant(page, CFG, color, size), 'unknown')
                page.get_by_text('Dieser Artikel ist ausverkauft').wait_for()
                self.assertEqual(inspect_variant(page, CFG, color, size), 'unavailable')
                page.get_by_role('radio', name='XS', exact=True).evaluate('(el) => el.checked = false')
                self.assertEqual(inspect_variant(page, CFG, color, size), 'unknown')
        finally:
            page.close()


if __name__ == '__main__':
    unittest.main()
