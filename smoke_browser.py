"""Run inside the image to verify UID, writable directories and real Chromium."""
import os
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    print('runtime_uid=', os.getuid() if hasattr(os, 'getuid') else 'Windows')
    for value in (os.environ.get('HOME', str(Path.home())), os.environ.get('BROWSER_PROFILE_DIR', 'browser-profile'), tempfile.gettempdir(), os.environ.get('XDG_CACHE_HOME', tempfile.gettempdir()), os.environ.get('XDG_CONFIG_HOME', tempfile.gettempdir())):
        path = Path(value)
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=path) as f:
            f.write(b'write-test')
        print('writable=', str(path))
    # Separate temporary profile: never conflict with the running monitor.
    with tempfile.TemporaryDirectory() as profile, sync_playwright() as p:
        context = p.chromium.launch_persistent_context(profile, headless=True)
        try:
            page = context.new_page()
            page.goto('data:text/html,<title>Hollister browser smoke</title>')
            assert page.title() == 'Hollister browser smoke'
            print('chromium_start=ok')
        finally:
            context.close()


if __name__ == '__main__':
    main()
