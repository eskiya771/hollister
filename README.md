# Hollister availability monitor

Monitors the configured product size and color and sends a Telegram status **on every check**, default every 15 minutes. Configured target: Icon Henley, XS, Helles Pink, requested SKU 673063170.

## Current limitation

The live Hollister request from the sandbox returned a JavaScript protection page. The checker therefore reports **Status nicht prüfbar**. Successful Telegram delivery does not establish product availability. The parser supports exact size/color variants in JSON-LD Product data; the current live shop structure and correspondence to the requested SKU have not been verified. A shop-specific adapter may be needed. Generic product-level stock and HTML words such as “available” never trigger an availability alert.

## Synology Container Manager

1. Download this repository into `/volume1/docker/hollister`.
2. Place your filled configuration there with the exact name `.env`. Use the separately provided `hollister.env` and rename it. Keep credentials out of GitHub.
3. Create a Container Manager project using this folder and `compose.yaml`, then build/start it. Alternatively run `docker compose up -d --build` in the folder.
4. Each iteration sends available, unavailable, or not verifiable. Check container logs for delivery failures. No incoming ports are needed.

The `.env.example` is a template without credentials. Send frequency is configured by `CHECK_INTERVAL_SECONDS=900`. Telegram failures are logged without credentials; the next scheduled iteration tries again.

## Local run

Requires Python 3.12 or newer; no additional Python packages.

```sh
python3 -m unittest -v
python3 app.py --once
python3 app.py
```

The app loads `.env` from the working directory, with existing environment variables taking precedence. It sends immediately on startup, then checks at the configured interval. `--delay-first` waits one interval before the first check. SIGTERM and SIGINT stop it.

## Sandbox trial

Started as a background Python process because Docker is unavailable in this sandbox. It runs only while this environment and process remain active; it is not a permanent hosted service. The Synology is the intended persistent host.
