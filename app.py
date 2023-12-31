#!/bin/python3

import argparse
import re
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import staleness_of

def slide_loader(url: str, is_redirect: bool = False, is_kiosk: bool = False, chrome_debug_port: int = 12345):
    """ Setup browser specific options, execute  """
    options = webdriver.ChromeOptions()
    options.page_load_strategy = 'normal'
    options.accept_insecure_certs = True
    # stops this error => "DevToolsActivePort file doesn't exist"
    options.add_argument(f'remote-debugging-port={chrome_debug_port}')
    if is_kiosk:
        options.add_argument('kiosk')
    # Removes the "Chrome is being controlled by automated test software" banner
    options.add_experimental_option('excludeSwitches', ['enable-automation'])

    # service = webdriver.ChromeService(port=12346) service=service, 
    with webdriver.Chrome(options=options) as driver:
        slide_repeater(url, is_redirect, driver)

def slide_repeater(url: str, is_redirect: bool = False, driver = None):
    """ Logic for reloading the presentation """
    re_pattern = re.compile(r'^Slide (\d+) of (\d+):')
    wait = WebDriverWait(driver, timeout=30.0)
    data_loaded_url = None
    data_redirect_url = None
    data_latest_aria = None
    data_latest_groups = None
    while True:
        try:
            driver.get(url)
            data_loaded_url = driver.current_url
            if is_redirect:
                wait.until_not(lambda driver: driver.current_url == url)
                data_redirect_url = driver.current_url

            while True:
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
        except Exception as e:
            print(f'Exception loaded={data_loaded_url} redirect={data_redirect_url} aria={data_latest_aria} groups={data_latest_groups} error={e}')

def main():
    parser = argparse.ArgumentParser(description='Reload and cycle a presentation')
    parser.add_argument('--url', required=True)
    parser.add_argument('--redirect', action='store_true')
    parser.add_argument('--kiosk', action='store_true')
    parser.add_argument('--chrome-debug-port', default=12345)
    args = parser.parse_args()

    slide_loader(url=args.url, is_redirect=args.redirect, is_kiosk=args.kiosk, chrome_debug_port=args.chrome_debug_port)

if __name__ == "__main__":
    main()
