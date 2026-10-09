"""Keep human verification and stock checks in one running browser page."""
import logging
from browser_check import protected, check_page, german_product

LOG = logging.getLogger('hollister.live')


class LiveSession:
    def __init__(self, page, cfg):
        self.page = page
        self.cfg = cfg
        self.refresh_next = False

    def adopt_product_page(self, pages):
        """Follow a user-opened product tab, without altering a challenge tab."""
        for candidate in pages:
            if candidate is self.page:
                continue
            if german_product(candidate.url, self.cfg['PRODUCT_URL']):
                heading = candidate.get_by_role('heading', level=1)
                if heading.count() and heading.first.is_visible() and not protected(candidate):
                    # Keep our existing product tab if it is already usable.
                    if not self.page.is_closed() and not protected(self.page):
                        return
                    self.page = candidate
                    self.refresh_next = False
                    LOG.info('live_tab=adopted_visible_product')
                    return

    def recover_closed_page(self, context):
        """Replace a dead tab without replacing the shared browser session."""
        if not self.page.is_closed():
            return
        self.adopt_product_page(context.pages)
        if self.page.is_closed():
            self.page = context.new_page()
            self.refresh_next = True
            LOG.info('live_tab=recreated_closed_product product=%s',
                     self.cfg.get('PRODUCT_NAME', 'unknown'))

    def check(self, variant_cfg=None, force_refresh=False):
        active_cfg = variant_cfg if variant_cfg is not None else self.cfg
        try:
            challenge = protected(self.page)
            LOG.info('live_page challenge=%s product_url=%s', challenge,
                     german_product(self.page.url, self.cfg['PRODUCT_URL']))
            if challenge:
                # Leave the challenge untouched for the user. Once solved,
                # inspect that very page before performing another navigation.
                self.refresh_next = False
                return 'unknown', 'CAPTCHA im sichtbaren NAS-Browser bitte manuell lösen. Die Sitzung bleibt geöffnet.'
            result = check_page(self.page, active_cfg, navigate=self.refresh_next or force_refresh)
            self.refresh_next = True
            return result
        except Exception as exc:
            return 'unknown', 'Prüfung der laufenden Browsersitzung fehlgeschlagen (' + type(exc).__name__ + ').'
