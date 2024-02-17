#!/bin/python3

import argparse
import re
import urllib
import random
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import staleness_of

def slide_loader(url: str, is_redirect: bool = False, is_kiosk: bool = False, chrome_debug_port: int = 12345, is_unique: bool = False):
    """ Setup browser specific options, execute  """
    options = webdriver.ChromeOptions()
    options.page_load_strategy = 'normal'
    options.accept_insecure_certs = True
    options.add_argument('no-default-browser-check')
    options.add_argument('no-first-run')
    options.add_argument('ash-no-nudges')
    options.add_argument('disable-search-engine-choice-screen')
    options.add_argument('aggressive-cache-discard')
    options.add_argument('deny-permission-prompts')
    options.add_argument('disable-notifications')
    options.add_argument('disk-cache-size=0')
    options.add_argument('disable-background-networking')
    options.add_argument('disable-component-update')
    options.add_argument('disable-domain-reliability')
    options.add_argument('disable-sync')
    options.add_argument('no-pings')
    # stops this error => "DevToolsActivePort file doesn't exist"
    options.add_argument(f'remote-debugging-port={chrome_debug_port}')
    if is_kiosk:
        options.add_argument('kiosk')
    # Removes the "Chrome is being controlled by automated test software" banner
    options.add_experimental_option('excludeSwitches', ['enable-automation'])

    # service = webdriver.ChromeService(port=12346) service=service, 
    with webdriver.Chrome(options=options) as driver:
        slide_repeater(url, is_redirect, is_unique, driver)

def slide_repeater(url: str, is_redirect: bool = False, is_unique: bool = False, driver = None):
    """ Logic for reloading the presentation """
    re_pattern = re.compile(r'^Slide (\d+) of (\d+):')
    wait = WebDriverWait(driver, timeout=30.0)
    data_loaded_url = None
    data_redirect_url = None
    data_latest_aria = None
    print(f'Loading {url}')
    while True:
        # reload loop
        try:
            if is_redirect:
                data_redirect_url = urllib.request.urlopen(url).geturl()
                if is_unique:
                    data_redirect_url = unique_url(data_redirect_url)
                driver.get(data_redirect_url)
            else:
                driver.get(url)
            data_loaded_url = driver.current_url

            while True:
                # slide loop
                slide_aria = driver.find_element(By.CSS_SELECTOR, "div.punch-viewer-svgpage-a11yelement")
                data_latest_aria = slide_aria.get_attribute('aria-label')
                re_matches = re_pattern.match(data_latest_aria)

                if len(re_matches.groups()) > 1 and re_matches.group(1) == re_matches.group(2):
                    latest_groups = f'{re_matches.group(1)} of {re_matches.group(2)}'
                    break
                elif len(re_matches.groups()) > 1:
                    latest_groups = f'{re_matches.group(1)} of {re_matches.group(2)}'
                else:
                    latest_groups = None
                wait.until(staleness_of(slide_aria))
            # clear page data
            driver.delete_all_cookies()
            execute_script(driver, 'window.localStorage.clear()')
            execute_script(driver, 'window.sessionStorage.clear()')
        except Exception as e:
            if str(e).find('target window already closed') > 0:
                print(f'No window found, exiting loaded={data_loaded_url} redirect={data_redirect_url} aria={data_latest_aria}')
                break
            if str(e).find('stale element not found') > 0:
                print(f'Stale element not found, reloading loaded={data_loaded_url} redirect={data_redirect_url} aria={data_latest_aria}')
                continue
            print(f'Exception loaded={data_loaded_url} redirect={data_redirect_url} aria={data_latest_aria} error={e}')

def execute_script(driver, script: str):
    try:
        driver.execute_script(script)
    except Exception as e:
        print(f'Script "{script}" failed')

def unique_url(url: str):
    params = {'my_unique': str(random.random())}
    url_parts = list(urllib.parse.urlparse(url))
    query = dict(urllib.parse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib.parse.urlencode(query)
    return urllib.parse.urlunparse(url_parts)

def main():
    parser = argparse.ArgumentParser(description='Reload and cycle a presentation')
    parser.add_argument('--url', required=True)
    parser.add_argument('--redirect', action='store_true')
    parser.add_argument('--kiosk', action='store_true')
    parser.add_argument('--unique', action='store_true')
    parser.add_argument('--chrome-debug-port', default=12345)
    args = parser.parse_args()

    slide_loader(url=args.url, is_redirect=args.redirect, is_kiosk=args.kiosk, chrome_debug_port=args.chrome_debug_port, is_unique=args.unique)

if __name__ == "__main__":
    main()
