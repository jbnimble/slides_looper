# Slides Looper

Refresh and loop a Google Slides presentation after reaching the last slide

## Install and Run

```bash
# On a managed system
sudo apt update
sudo apt install -y pip python3-selenium chromium chromium-driver

# On a non-managed system
pip3 install --requirement requirements.txt

# redirect URL to a Google Slides presentation
./app.py --redirect --url="https://example.com/my-presentation-redirect"

# Direct URL to a Google Slides presentation in Kiosk mode
./app.py --kiosk --url="https://docs.google.com/presentation/d/e/foo/pub?start=true&loop=true&delayms=1000&slide=id.bar"
```

## Errors

Any error during the looping flow will reload and restart the URL load and slide loop

## Future Enhancements

- Find better or more ways to know what slide is active and when the last slide is reached
- Logging
- detect `delayms` in URL and set timeout based on slide delay
