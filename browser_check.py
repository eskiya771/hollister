"""Browser adapter for the German Hollister product page.

Uses ordinary browser controls; does not solve or evade security challenges.
"""
import re
from pathlib import Path
from profile_lock import profile_lock
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def dismiss_cookies(page):
    # OneTrust loads asynchronously; its IDs are independent of shop language.
    banner = page.locator('#onetrust-banner-sdk')
    reject = page.locator('#onetrust-reject-all-handler')
    try:
        banner.wait_for(state='visible', timeout=10000)
    except PlaywrightTimeoutError:
        return  # No banner: consent may already be saved in the profile.
    try:
        reject.wait_for(state='visible', timeout=5000)
        reject.click(timeout=10000)
        banner.wait_for(state='hidden', timeout=10000)
    except PlaywrightTimeoutError as exc:
        raise RuntimeError('Cookie-Dialog konnte nicht geschlossen werden') from exc


def check_browser(cfg):
    try:
        with profile_lock(cfg.get('BROWSER_PROFILE_DIR', 'browser-profile')):
            return _check_browser(cfg)
    except RuntimeError as exc:
        if str(exc) == 'Browserprofil wird bereits verwendet':
            return 'unknown', 'Browserprofil wird im manuellen Modus oder von einem anderen Monitor verwendet.'
        raise


def _check_browser(cfg):
    profile = Path(cfg.get('BROWSER_PROFILE_DIR', 'browser-profile'))
    profile.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        options = {'headless': True}
        if cfg.get('BROWSER_EXECUTABLE_PATH'):
            options['executable_path'] = cfg['BROWSER_EXECUTABLE_PATH']
        context = p.chromium.launch_persistent_context(str(profile), **options)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(15000)
        try:
            page.goto(cfg['PRODUCT_URL'], wait_until='domcontentloaded', timeout=60000)
            dismiss_cookies(page)
            page.get_by_role('heading', level=1).wait_for(timeout=20000)
            if '/shop/us/' in page.url:
                page.get_by_role('button', name='US', exact=True).click()
                page.get_by_role('combobox', name='Ship to', exact=True).select_option(label='Germany')
                page.get_by_role('button', name='Update Preferences', exact=True).click()
                page.wait_for_url('**/shop/eu-de/**', timeout=45000)
                dismiss_cookies(page)
            if '/shop/eu-de/' not in page.url:
                return 'unknown', 'Der Browser konnte den deutschen Shop nicht bestätigen.'
            dismiss_cookies(page)
            main = page.get_by_role('main')
            main.get_by_role('radio', name=re.compile('^' + re.escape(cfg['PRODUCT_COLOR']) + '$', re.I)).check()
            main.get_by_role('heading', name=re.compile('^Farbe:.*' + re.escape(cfg['PRODUCT_COLOR']), re.I)).wait_for()
            main.get_by_role('radio', name=cfg['PRODUCT_SIZE'], exact=True).check()
            main.get_by_role('heading', name='Größe: ' + cfg['PRODUCT_SIZE'], exact=True).wait_for()
            # Let variant-specific asynchronous stock rendering settle.
            page.wait_for_timeout(2000)
            # Wait for the selected variant's availability response to render.
            sold_out = main.get_by_text(re.compile('Dieser Artikel ist ausverkauft'))
            bag = main.get_by_role('button', name='In den Warenkorb', exact=True)
            sold_out.or_(bag).first.wait_for(timeout=15000)
            if sold_out.count() and sold_out.first.is_visible():
                return 'unavailable', 'Deutscher Shop: Helles Pink und XS ausgewählt; Artikel als ausverkauft angezeigt.'
            if bag.count() == 1 and bag.is_visible() and bag.is_enabled():
                return 'available', 'Deutscher Shop: Gewünschte Farbe und Größe ausgewählt; Warenkorb-Schaltfläche aktiv.'
            return 'unknown', 'Kein eindeutiger Bestandsstatus für die ausgewählte Variante.'
        except Exception as exc:
            try:
                title = page.title()
                text = page.locator('body').inner_text(timeout=3000)
                if re.search(r'Client Challenge|verify you are human|checking your browser|access denied', title + ' ' + text, re.I):
                    return 'unknown', 'Hollister blockiert diesen automatisierten Browser mit einer Schutzseite.'
            except Exception:
                pass
            if isinstance(exc, RuntimeError) and str(exc) == 'Cookie-Dialog konnte nicht geschlossen werden':
                return 'unknown', str(exc) + '.'
            return 'unknown', 'Browserabfrage fehlgeschlagen (' + type(exc).__name__ + ').'
        finally:
            context.close()
