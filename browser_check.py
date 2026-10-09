"""Ordinary browser controls, exact variant evidence, no challenge bypass."""
import re
import logging
import time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout

CHALLENGE_TITLE = re.compile(r'Client Challenge|verify you are human|checking your browser|access denied|^\s*CAPTCHA\s*$', re.I)
CHALLENGE_PROMPT = re.compile(
    r'enter the characters (?:seen|shown) in the image|verify (?:that )?you are human|'
    r'checking your browser|bestätigen sie,? dass sie ein mensch sind|'
    r'geben sie die zeichen (?:aus|in|auf) dem bild', re.I)
LOG = logging.getLogger('hollister.browser')


class CookieDialogError(RuntimeError):
    pass


def german_product(url, expected):
    actual, target = urlsplit(url), urlsplit(expected)
    return actual.scheme == 'https' and actual.netloc == 'www.hollisterco.com' and actual.path == target.path and actual.path.startswith('/shop/eu-de/')


def protected(page):
    # A loaded protection script or footer mentioning CAPTCHA does not mean
    # that a challenge is displayed. Require an actual title or visible prompt.
    return bool(CHALLENGE_TITLE.search(page.title()) or
                CHALLENGE_PROMPT.search(page.locator('body').inner_text(timeout=3000)))


def dismiss_cookies(page, wait_timeout=0, action_timeout=10000):
    # Upstream b745f8f: OneTrust arrives asynchronously. Wait once after
    # navigation, then use nonblocking detection while polling stock.
    banner = page.locator('#onetrust-banner-sdk')
    if wait_timeout:
        try:
            banner.wait_for(state='visible', timeout=wait_timeout)
        except BrowserTimeout:
            pass  # Saved consent may mean there is no banner.
    if banner.count() and banner.is_visible():
        try:
            reject = page.locator('#onetrust-reject-all-handler')
            reject.wait_for(state='visible', timeout=action_timeout)
            reject.click(timeout=action_timeout)
            banner.wait_for(state='hidden', timeout=action_timeout)
            page.locator('.onetrust-pc-dark-filter').first.wait_for(state='hidden', timeout=action_timeout)
            LOG.info('cookie_dialog=closed provider=OneTrust')
            return
        except BrowserTimeout as exc:
            raise CookieDialogError('Cookie-Dialog konnte nicht geschlossen werden.') from exc
    for name in ('Reject All', 'Alle ablehnen', 'Alles ablehnen', 'Ablehnen', 'Nur notwendige Cookies'):
        button = page.get_by_role('button', name=name, exact=True)
        if button.count() == 1 and button.is_visible():
            try:
                button.click(timeout=action_timeout)
                button.wait_for(state='hidden', timeout=action_timeout)
            except BrowserTimeout as exc:
                raise CookieDialogError('Cookie-Dialog konnte nicht geschlossen werden.') from exc
            LOG.info('cookie_dialog=closed provider=role_fallback')
            return


def ready(page, timeout=30):
    deadline = time.monotonic() + timeout
    if protected(page):
        raise ValueError('protection')
    dismiss_cookies(page, wait_timeout=10000)
    while time.monotonic() < deadline:
        if protected(page):
            raise ValueError('protection')
        dismiss_cookies(page)
        if page.get_by_role('heading', level=1).count():
            if page.get_by_role('heading', level=1).first.is_visible():
                return
        page.wait_for_timeout(250)
    raise BrowserTimeout('product not ready')


def verified_status(html, cfg, selected, sold_out, bag_enabled, ui_confirmed=False):
    # The observed JSON-LD describes the style (SKU 357-293-00059-630), not
    # the selected XS variant. An explicit sold-out state after confirmed
    # selection is usable even when this generic Product says InStock.
    # Positive stock still requires exact variant evidence, never just a button.
    from app import stock_from_html
    if not selected:
        return 'unknown'
    if sold_out and not bag_enabled:
        return 'unavailable'
    if ui_confirmed and bag_enabled and not sold_out:
        return 'available'
    # Never reuse XS's requested SKU as a confirmed identifier for size S.
    if not cfg.get('PRODUCT_SKU'):
        return 'unknown'
    status, _ = stock_from_html(html, cfg['PRODUCT_SIZE'], cfg['PRODUCT_COLOR'], cfg['PRODUCT_SKU'])
    if status == 'available' and bag_enabled and not sold_out:
        return status
    return 'unknown'


def color_pattern(value):
    # German shop labels may spell the same color with ss instead of sharp s.
    escaped = re.escape(value.strip().casefold())
    return re.compile(escaped.replace('ss', '(?:ss|ß)'), re.I)


def inspect_variant(page, cfg, color, size):
    main = page.get_by_role('main')
    sold = main.get_by_text(re.compile(r'Dieser Artikel ist ausverkauft', re.I))
    bag = main.get_by_role('button', name='In den Warenkorb', exact=True)
    selected = (german_product(page.url, cfg['PRODUCT_URL']) and color.is_checked() and size.is_checked())
    sold_visible = any(sold.nth(i).is_visible() for i in range(sold.count()))
    bag_enabled = bag.count() == 1 and bag.is_visible() and bag.is_enabled()
    color_heading = main.get_by_role('heading', name=re.compile(
        r'^Farbe:\s*' + color_pattern(cfg['PRODUCT_COLOR']).pattern + r'\s*$', re.I))
    size_heading = main.get_by_role('heading', name='Größe: ' + cfg['PRODUCT_SIZE'], exact=True)
    busy = main.locator('[aria-busy="true"]')
    ui_confirmed = (color_heading.count() == 1 and color_heading.is_visible()
                    and size_heading.count() == 1 and size_heading.is_visible()
                    and size.is_enabled()
                    and not any(busy.nth(i).is_visible() for i in range(busy.count())))
    return verified_status(page.content(), cfg, selected, sold_visible, bag_enabled, ui_confirmed)


def check_page(page, cfg, navigate=True):
    """Check a page without creating or closing its browser/session."""
    stage = 'Produktseite laden'
    page.set_default_timeout(10000)
    from stock_diagnostics import observe_response, report
    responses = []
    def collect(response):
        observe_response(response, cfg['PRODUCT_SKU'], responses)
    page.on('response', collect)
    try:
        stage = 'Produktseite laden'
        if navigate:
            response = page.goto(cfg['PRODUCT_URL'], wait_until='domcontentloaded', timeout=60000)
            if response and response.status >= 400:
                return 'unknown', f'Shop-Ladefehler (HTTP {response.status}); keine Bestandsaussage.'
        ready(page)
        if '/shop/us/' in urlsplit(page.url).path:
            stage = 'Deutschland auswählen'
            page.get_by_role('button', name='US', exact=True).click()
            page.get_by_role('combobox', name='Ship to', exact=True).select_option(label='Germany')
            page.get_by_role('button', name='Update Preferences', exact=True).click()
            page.wait_for_url('**/shop/eu-de/**', timeout=45000)
            # Reload the exact requested product if country switching changed it.
            page.goto(cfg['PRODUCT_URL'], wait_until='domcontentloaded', timeout=60000)
            ready(page)
        if not german_product(page.url, cfg['PRODUCT_URL']):
            return 'unknown', 'Die gewünschte Produktseite im deutschen Shop wurde nicht bestätigt.'
        main = page.get_by_role('main')
        dismiss_cookies(page)
        stage = 'Farbe auswählen'
        color_name = color_pattern(cfg['PRODUCT_COLOR']).pattern
        color = main.get_by_role('radio', name=re.compile(r'^\s*' + color_name + r'\s*$', re.I))
        color.check()
        stage = 'Ausgewählte Farbe bestätigen'
        main.get_by_role('heading', name=re.compile(r'^Farbe:\s*' + color_name + r'\s*$', re.I)).wait_for()
        stage = 'Größe auswählen'
        size = main.get_by_role('radio', name=cfg['PRODUCT_SIZE'], exact=True)
        size.check()
        main.get_by_role('heading', name='Größe: ' + cfg['PRODUCT_SIZE'], exact=True).wait_for()
        stage = 'SKU und aktualisierten Variantenbestand bestätigen'
        deadline = time.monotonic() + 20
        stable_since, previous = None, 'unknown'
        while time.monotonic() < deadline:
            if protected(page):
                raise ValueError('protection')
            dismiss_cookies(page)
            status = inspect_variant(page, cfg, color, size)
            if status != previous or status == 'unknown':
                stable_since = time.monotonic() if status != 'unknown' else None
            previous = status
            if stable_since is not None and time.monotonic() - stable_since >= (5 if status == 'available' else 2):
                if status == 'unavailable':
                    return status, f'Deutscher Shop: {cfg["PRODUCT_COLOR"]} und {cfg["PRODUCT_SIZE"]} ausdrücklich ausgewählt; die Seite zeigt diese Auswahl als ausverkauft. Interne SKU-Zuordnung nicht separat bestätigt.'
                return status, f'Deutscher Shop: {cfg["PRODUCT_COLOR"]} und {cfg["PRODUCT_SIZE"]} in Auswahl und Überschriften bestätigt; Warenkorb aktiv, keine Ausverkauft-Meldung, Zustand 5 Sekunden stabil. Verfügbarkeit laut Produktseite, keine Kaufgarantie.'
            page.wait_for_timeout(250)
        report(page, cfg, responses)
        return 'unknown', 'Auswahl vorhanden, aber keine widerspruchsfreien Bestandsdaten mit exakter SKU, Farbe und Größe. Warenkorbstatus allein reicht nicht.'
    except Exception as exc:
        try:
            if protected(page):
                return 'unknown', 'Hollister zeigt eine Schutzseite/CAPTCHA. Keine Umgehung; keine Bestandsaussage möglich.'
        except Exception:
            pass
        if isinstance(exc, CookieDialogError):
            return 'unknown', 'Cookie-Dialog konnte nicht geschlossen werden; keine Bestandsaussage.'
        report(page, cfg, responses)
        return 'unknown', f'Prüfschritt „{stage}“ fehlgeschlagen ({type(exc).__name__}); keine Bestandsaussage.'
    finally:
        page.remove_listener('response', collect)


def check_browser(cfg):
    from profile_lock import profile_lock
    try:
        with profile_lock(cfg.get('BROWSER_PROFILE_DIR', 'browser-profile')):
            return _check_browser(cfg)
    except RuntimeError as exc:
        if str(exc) == 'Browserprofil wird bereits verwendet':
            return 'unknown', 'Browserprofil wird im manuellen Modus oder von einem anderen Monitor verwendet.'
        raise


def _check_browser(cfg):
    profile = Path(cfg.get('BROWSER_PROFILE_DIR', 'browser-profile')).resolve()
    profile.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        options = dict(headless=True, locale='de-DE', timezone_id='Europe/Berlin', timeout=30000)
        if cfg.get('BROWSER_EXECUTABLE_PATH'):
            options['executable_path'] = cfg['BROWSER_EXECUTABLE_PATH']
        context = p.chromium.launch_persistent_context(str(profile), **options)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            return check_page(page, cfg)
        finally:
            context.close()
