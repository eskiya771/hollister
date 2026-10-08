# Hollister availability monitor

## Manual CAPTCHA session on Synology

The optional `manual-browser` service displays Chromium through noVNC using the
same Docker volume and profile as the monitor. It does not solve challenges.
An exclusive file lock prevents both services from opening the profile at once.
This mode is implemented but still requires a Docker build and live test on your NAS.

Keep the existing project directory and Compose project name: a new project name
would create a different `browser-data` volume. Do not run `down -v`.

In the NAS project folder, stop the monitor before starting the manual service:

```sh
docker compose stop hollister
docker compose --profile manual up -d --build manual-browser
docker compose --profile manual logs --tail=50 manual-browser
```

On your PC, open a separate terminal and keep this SSH tunnel running. Replace
`NAS_USER` and `NAS_IP` with your DSM SSH user and NAS address:

```sh
ssh -N -L 127.0.0.1:6080:127.0.0.1:6080 NAS_USER@NAS_IP
```

Open `http://127.0.0.1:6080/vnc.html` on the PC and click Connect.
The browser shown there runs **on the NAS**, not on your PC. Solve any challenge
manually, dismiss cookies and confirm the German shop, Helles Pink and XS.
noVNC has no VNC password in this configuration; its published port binds only
to NAS loopback and SSH provides authentication and encryption. Do not change
the binding to `0.0.0.0`, expose it through a reverse proxy or forward it on your router.
Other local NAS processes can reach the loopback port while the service runs.

Save the browser profile with a graceful stop, then test one automatic check:

```sh
docker compose --profile manual stop manual-browser
docker compose build hollister
docker compose run --rm --no-deps hollister python app.py --once
```

Review the actual Telegram result. If it is correct, start the 15-minute monitor:

```sh
docker compose up -d hollister
docker compose logs --tail=50 hollister
```

Close the SSH tunnel with Ctrl+C. A successful manual challenge does not guarantee
future automatic requests work: session-only cookies, browser restarts or the
change from a visible to a headless browser may trigger a new challenge.
An unknown result must remain unknown; do not treat it as sold out.

Monitors the configured product size and color and sends a Telegram status **on every check**, default every 15 minutes. Configured target: Icon Henley, XS, Helles Pink, requested SKU 673063170.

## Browser check and current test status

The default checker now uses Playwright Chromium, dismisses the cookie banner with Reject All (and German equivalents), switches US redirects to Germany, then selects the configured exact color and size. It reports the visible sold-out message or active add-to-bag button only after confirming the German shop and variant selections. It never solves security challenges. CHECK_MODE=http retains the previous conservative JSON-LD checker.

A separate interactive cloud-browser test confirmed the German shop shows **Helles Pink, XS: ausverkauft**. The application browser could not start inside this Python sandbox: The initial workspace extraction was incomplete. After extracting the complete official Chrome package into a temporary directory, all shared libraries resolved. The verified startup failure is Chrome's local process socket creation: `socket() failed: Operation not permitted (1)` in `process_singleton_posix.cc`, causing SIGABRT / TargetClosedError before opening Hollister. This is a sandbox permission restriction, not a cookie or shop-page failure. The browser adapter has therefore **not passed an end-to-end application test**, and no corrected periodic monitor is currently running here. Telegram delivery was previously tested successfully. Synology browser execution also remains to be verified.

## Synology Container Manager

1. Download this repository into `/volume1/docker/hollister`.
2. Place your filled configuration there with the exact name `.env`. Use the separately provided `hollister.env` and rename it. Keep credentials out of GitHub.
3. Create a Container Manager project using this folder and `compose.yaml`, then build/start it. Alternatively run `docker compose up -d --build` in the folder.
4. Each iteration sends available, unavailable, or not verifiable. Check container logs for delivery failures. No incoming ports are needed.

The `.env.example` is a template without credentials. Send frequency is configured by `CHECK_INTERVAL_SECONDS=900`. Telegram failures are logged without credentials; the next scheduled iteration tries again.

## Local run

Requires Python 3.12 or newer plus Playwright and its Chromium runtime.

```sh
pip install -r requirements.txt
python3 -m playwright install --with-deps chromium
python3 -m unittest -v
python3 app.py --once
python3 app.py
```

The app loads `.env` from the working directory, with existing environment variables taking precedence. It sends immediately on startup, then checks at the configured interval. `--delay-first` waits one interval before the first check. SIGTERM and SIGINT stop it.

## Sandbox trial

The initial HTTP monitor sent one confirmed Telegram status but its terminal session ended later. Detached shell processes also do not survive the execution boundary here. Do not treat this sandbox as an ongoing monitor. The corrected browser application currently cannot launch its browser in this environment. The Synology is the intended persistent host.

BROWSER_PROFILE_DIR configures a persistent profile; compose.yaml uses a writable Docker volume for it. BROWSER_EXECUTABLE_PATH can optionally select an existing official Chrome installation. The Docker image installs Chromium with its operating system dependencies and keeps credentials outside the image.
