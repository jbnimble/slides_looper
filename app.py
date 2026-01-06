#!/bin/python3

import argparse
import re
import urllib
import random
import time
import logging
from logging.handlers import RotatingFileHandler
from selenium import webdriver
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.common.exceptions import InvalidSessionIdException, NoSuchWindowException, StaleElementReferenceException, TimeoutException

# 5MB rotating log file
log_format = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
log_handler = RotatingFileHandler('slides_looper.log', mode='a', maxBytes=5*1024*1024, backupCount=2, encoding='UTF-8', delay=0)
log_handler.setFormatter(log_format)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

class AppOptions:
    def __init__(self, url, is_redirect, is_kiosk, is_f11, is_unique, is_maximize, is_loop_new_window, last_slide_wait_sec, chrome_debug_port, driver_path):
        self.url = url
        self.is_redirect = is_redirect
        self.is_kiosk = is_kiosk
        self.is_f11 = is_f11
        self.is_unique = is_unique
        self.is_maximize = is_maximize
        self.is_loop_new_window = is_loop_new_window
        self.last_slide_wait_sec = last_slide_wait_sec
        self.chrome_debug_port = chrome_debug_port
        self.driver_path = driver_path

def slide_loader(appOptions: AppOptions):
    """ Setup browser specific options, execute  """
    webOptions = webdriver.ChromeOptions()
    webOptions.page_load_strategy = 'normal'
    webOptions.accept_insecure_certs = True
    webOptions.add_argument('no-default-browser-check')
    webOptions.add_argument('no-first-run')
    webOptions.add_argument('ash-no-nudges')
    webOptions.add_argument('disable-search-engine-choice-screen')
    webOptions.add_argument('aggressive-cache-discard')
    webOptions.add_argument('deny-permission-prompts')
    webOptions.add_argument('disable-notifications')
    webOptions.add_argument('disk-cache-size=0')
    webOptions.add_argument('disable-background-networking')
    webOptions.add_argument('disable-component-update')
    webOptions.add_argument('disable-domain-reliability')
    webOptions.add_argument('disable-sync')
    webOptions.add_argument('no-pings')
    # stops this error => "DevToolsActivePort file doesn't exist"
    webOptions.add_argument(f'remote-debugging-port={appOptions.chrome_debug_port}')
    if appOptions.is_kiosk:
        webOptions.add_argument('kiosk')
    # Removes the "Chrome is being controlled by automated test software" banner
    webOptions.add_experimental_option('excludeSwitches', ['enable-automation'])

    if appOptions.driver_path:
        service = webdriver.ChromeService(executable_path=appOptions.driver_path)
    else:
        service = webdriver.ChromeService()
    logger.info(f'Create WebDriver with options')
    repeater_result = False
    with webdriver.Chrome(options=webOptions, service=service) as driver:
        logger.info(f'Begin slide_repeater')
        repeater_result = slide_repeater(appOptions, driver)
    return repeater_result

def slide_repeater(appOptions: AppOptions, driver) -> bool:
    """ Logic for reloading the presentation, return false to not loop again """
    re_pattern = re.compile(r'^Slide (\d+) of (\d+):')
    wait = WebDriverWait(driver, timeout=30.0)
    data_loaded_url = None
    data_redirect_url = None
    data_latest_aria = None
    logger.info(f'Loading {appOptions.url}')

    if appOptions.is_maximize:
        driver.maximize_window() # Maximize window

    while True:
        # reload loop
        try:
            data_loaded_url = driver.current_url

            if appOptions.is_redirect:
                data_redirect_url = urllib.request.urlopen(appOptions.url).geturl()
                if appOptions.is_unique:
                    data_redirect_url = unique_url(data_redirect_url)
                driver.get(data_redirect_url)
            else:
                driver.get(appOptions.url)

            if appOptions.is_f11:
                ActionChains(driver).send_keys(Keys.F11).perform() # make fullscreen by pressing F11

            while True:
                # slide loop
                slide_aria = driver.find_element(By.CSS_SELECTOR, "div.punch-viewer-svgpage-a11yelement")
                data_latest_aria = slide_aria.get_attribute('aria-label')
                re_matches = re_pattern.match(data_latest_aria)

                if len(re_matches.groups()) > 1 and re_matches.group(1) == re_matches.group(2):
                    time_to_wait = float(appOptions.last_slide_wait_sec)
                    if time_to_wait >= 1:
                        time.sleep(time_to_wait) # pause before breaking to reload loop
                    latest_groups = f'{re_matches.group(1)} of {re_matches.group(2)}'
                    if appOptions.is_loop_new_window:
                        logger.info(f'Exiting due to is_loop_new_window={appOptions.is_loop_new_window}')
                        return True
                    else:
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
        except (InvalidSessionIdException, NoSuchWindowException) as e:
            logger.warning(f'Exiting due to {type(e)}')
            break
        except (StaleElementReferenceException, TimeoutException) as e:
            logger.warning(f'Reloading due to {type(e)}')
        except Exception as e:
            logger.error(f'Reloading due to unknown exception={type(e)}\n\turl={data_loaded_url}\n\tredirect_url={data_redirect_url}\n\taria_data={data_latest_aria}\n\terror={e}')
    return False

def execute_script(driver, script: str):
    try:
        driver.execute_script(script)
    except Exception as e:
        logger.error(f'Script "{script}" failed')

def unique_url(url: str):
    params = {'my_unique': str(random.random())}
    url_parts = list(urllib.parse.urlparse(url))
    query = dict(urllib.parse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib.parse.urlencode(query)
    return urllib.parse.urlunparse(url_parts)

def main():
    parser = argparse.ArgumentParser(description='Reload and cycle a presentation')
    parser.add_argument('--url', required=True, help='presentation URL')
    parser.add_argument('--redirect', action='store_true', help='Query for potential redirect URL')
    parser.add_argument('--kiosk', action='store_true', help='Enable kiosk mode')
    parser.add_argument('--f11', action='store_true', help='Press F11 key when after loading URL')
    parser.add_argument('--unique', action='store_true', help='Add unique parameter with random value to URL')
    parser.add_argument('--maximize', action='store_true', help='Start browser window maximized')
    parser.add_argument('--loop-new-window', action='store_true', help='Start new browser for each loop')
    parser.add_argument('--last-slide-wait-sec', default="0", help='Wait number of seconds on last slide')
    parser.add_argument('--chrome-debug-port', default=12345, help='Chrome debug port')
    parser.add_argument('--driverpath', default='/usr/bin/chromedriver', help='Filesystem path to Chrome driver executable')
    args = parser.parse_args()
    appOptions = AppOptions(url=args.url, 
        is_redirect = args.redirect, 
        is_kiosk = args.kiosk, 
        is_f11 = args.f11, 
        is_unique = args.unique, 
        is_maximize = args.maximize, 
        is_loop_new_window = args.loop_new_window, 
        last_slide_wait_sec = args.last_slide_wait_sec, 
        chrome_debug_port=args.chrome_debug_port, 
        driver_path=args.driverpath)

    if appOptions.is_loop_new_window:
        loop_again = True
        while loop_again:
            loop_again = slide_loader(appOptions)
        logger.info(f'Exiting due to loop_again={loop_again}')
    else:
        slide_loader(appOptions)

if __name__ == "__main__":
    main()
