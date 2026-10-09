import unittest
from unittest.mock import Mock, patch
from live_monitor import LiveSession
from test_app import CFG


class LiveSessionTests(unittest.TestCase):
    def test_challenge_is_untouched_then_same_page_is_used(self):
        page = Mock(url=CFG['PRODUCT_URL'])
        session = LiveSession(page, CFG)
        with patch('live_monitor.protected', side_effect=[True, True, False, False]), patch('live_monitor.check_page', return_value=('unavailable', 'test')) as check:
            self.assertEqual(session.check()[0], 'unknown')
            self.assertEqual(session.check()[0], 'unknown')
            check.assert_not_called()
            page.goto.assert_not_called()
            page.reload.assert_not_called()
            self.assertEqual(session.check()[0], 'unavailable')
            check.assert_called_with(page, CFG, navigate=False)
            self.assertEqual(session.check()[0], 'unavailable')
            check.assert_called_with(page, CFG, navigate=True)
            page.close.assert_not_called()

    def test_reappearing_challenge_requires_manual_resolution(self):
        page = Mock(url=CFG['PRODUCT_URL'])
        session = LiveSession(page, CFG)
        with patch('live_monitor.protected', side_effect=[False, True, False]), patch('live_monitor.check_page', return_value=('unknown', 'test')) as check:
            session.check()
            session.check()
            self.assertEqual(check.call_count, 1)
            session.check()
            check.assert_called_with(page, CFG, navigate=False)

    def test_error_text_does_not_leak_secrets(self):
        session = LiveSession(Mock(), CFG)
        with patch('live_monitor.protected', side_effect=RuntimeError('SECRET')):
            status, reason = session.check()
        self.assertEqual(status, 'unknown')
        self.assertNotIn('SECRET', reason)

    def test_user_product_tab_replaces_challenge_tab(self):
        old = Mock(url=CFG['PRODUCT_URL'])
        old.is_closed.return_value = False
        product = Mock(url=CFG['PRODUCT_URL'])
        product.get_by_role.return_value.count.return_value = 1
        product.get_by_role.return_value.first.is_visible.return_value = True
        session = LiveSession(old, CFG)
        with patch('live_monitor.protected', side_effect=lambda p: p is old):
            session.adopt_product_page([old, product])
        self.assertIs(session.page, product)
        old.close.assert_not_called()
        product.goto.assert_not_called()


if __name__ == '__main__':
    unittest.main()
