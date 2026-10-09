"""Temporary entrypoint; original monitor files and image remain unchanged."""
from playwright.sync_api import BrowserType

original = BrowserType.launch_persistent_context


def diagnostic_launch(self, user_data_dir, **options):
    options['args'] = list(options.get('args', [])) + [
        '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=9222']
    return original(self, user_data_dir, **options)


BrowserType.launch_persistent_context = diagnostic_launch

if __name__ == '__main__':
    from manual_browser import main
    main()
