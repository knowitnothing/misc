# Save this as "selenium_base.py"

import sys
import time
from decimal import Decimal
from selenium.common.exceptions import (NoSuchElementException,
                ElementNotVisibleException, StaleElementReferenceException)


URL = 'https://just-dice.com'

# Page elements that if modified will break this program.
def welcome_close_element(driver):
    return driver.find_element_by_css_selector('.fancybox-close')

def btn_randomize(driver): return driver.find_element_by_id('a_random')
def server_seed_hash(driver): return driver.find_element_by_id('new_shash')
def input_seed(driver): return driver.find_element_by_id('new_cseed')
def btn_seed(driver): return driver.find_element_by_xpath(
        "//button[@class='seed_button']")

def lbl_roll_hi(driver): return driver.find_element_by_id('hi')

def tab_account(driver): return driver.find_element_by_link_text('Account')
def input_user(driver): return driver.find_element_by_id('myuser')
def input_password(driver): return driver.find_element_by_id('mypass')
def btn_login(driver): return driver.find_element_by_id('myok')

def tab_mybets(driver): return driver.find_element_by_link_text('My Bets')
def btn_roll_hi(driver): return driver.find_element_by_id('a_hi')
def btn_roll_lo(driver): return driver.find_element_by_id('a_lo')
def playable(elem): return 'invalid' not in elem.get_attribute('class')
def input_winchance(driver): return driver.find_element_by_id('pct_chance')
def input_betsize(driver): return driver.find_element_by_id('pct_bet')
def lbl_losses(driver): return driver.find_element_by_id('losses')
def lucky_number(driver):
    s1 = driver.find_element_by_xpath("//div[@id='me' and @class='results']"
                        "//div[@class='lucky'][1]//span[@class='s1']")
    s2 = driver.find_element_by_xpath("//div[@id='me' and @class='results']"
                        "//div[@class='lucky'][1]//span[@class='s2']")
    s3 = driver.find_element_by_xpath("//div[@id='me' and @class='results']"
                        "//div[@class='lucky'][1]//span[@class='s3']")
    return Decimal('%s%s%s' % (s1.text, s2.text, s3.text))
#


def get_integer(s):
    return int(''.join(si for si in s if si.isdigit()))


class Justdice:

    def __init__(self, driver, house_edge=Decimal('1')):
        self.house_edge = house_edge # %

        self.driver = driver
        # Go to the just-dice site.
        self.driver.get(URL)
        # Wait for a complete page load.

        self.wait_load()
        # Close the "Welcome!" window.
        for _ in xrange(10):
            try:
                close = welcome_close_element(self.driver)
                close.click()
                break
            except NoSuchElementException:
                time.sleep(0.1)

    def wait_load(self, attempts=10):
        """Wait for a complete page load.
        Assumption: the 'roll hi' button will display some digits when
        the page finishes loading."""
        for i in xrange(attempts):
            try:
                text = lbl_roll_hi(self.driver).text
                if text[-2:].isdigit():
                    break
            except NoSuchElementException:
                pass
            sys.stderr.write('Waiting load..\n')
            time.sleep(0.5)

    def wait_reload(self, attempts=15):
        """Wait for a reload. In certain cases (after login, for example)
        we want to wait for a page reload before continuing.
        Assumption: the page is reloaded if the 'roll hi' button
        no longer displays some digits.
        """
        for i in xrange(attempts):
            try:
                text = lbl_roll_hi(self.driver).text
            except (NoSuchElementException, StaleElementReferenceException):
                # That is fine.
                text = ''
            if not text[-2:].isdigit():
                break
            sys.stderr.write('Waiting reload..\n')
            time.sleep(0.5)

    def reload_page(self):
        self.driver.refresh()
        self.wait_reload()
        self.wait_load()


    def login(self, user, pwd):
        # First, go to the 'Account' tab.
        account_tab = tab_account(self.driver)
        account_tab.click()
        # Now enter user and password.
        username = input_user(self.driver)
        password = input_password(self.driver)
        for _ in xrange(5):
            try:
                username.send_keys(user)
                password.send_keys(pwd)
                break
            except ElementNotVisibleException:
                # Page not fully loaded.
                time.sleep(0.5)
        login_btn = btn_login(self.driver)
        login_btn.click()
        # Wait for page reload.
        self.wait_reload()
        self.wait_load()


    def randomize(self, user_seed=None):
        btn_randomize(self.driver).click()
        for _ in xrange(20):
            try:
                server_hash_seed = server_seed_hash(self.driver).text
                break
            except NoSuchElementException:
                time.sleep(0.1)
        else:
            server_hash_seed = None

        for _ in xrange(3):
            try: enter_seed = input_seed(self.driver)
            except NoSuchElementException: time.sleep(0.15)
            else: break
        if user_seed is not None:
            enter_seed.clear()
            enter_seed.send_keys(user_seed)
        user_seed = enter_seed.get_attribute('value')
        btn_seed(self.driver).click()

        return server_hash_seed, user_seed

    def _wait_bet(self, element, attempts=60):
        """Wait for a bet to complete."""
        now = time.time()
        for _ in xrange(attempts):
            # XXX If the class name is modified, the code will not work.
            if 'waiting' in element.get_attribute('class'):
                time.sleep(0.1)
            else:
                sys.stderr.write('Time to complete bet: %s\n' % (
                    time.time() - now))
                break
        else:
            return True


    def bet_prepare(self, new_seed=None):
        # Inputs for betting.
        chance_to_win = input_winchance(self.driver)
        bet_size = input_betsize(self.driver)
        # Grab the element that indicates the amount of losses so far.
        losses_elem = lbl_losses(self.driver)
        # Buttons for rolling.
        roll_btn = [btn_roll_lo(self.driver), btn_roll_hi(self.driver)]

        # Show 'My Bets' tab.
        mybets = tab_mybets(self.driver)
        mybets.click()

        if new_seed is not None:
            sys.stderr.write("sshash: %s, uhash: %s\n" %
                    self.randomize(new_seed))
        sys.stderr.write("Sleeping for half a second, take a deep breath\n")
        time.sleep(0.5)

        def roll(win_chance='50', btc_to_bet='0', high=True):
            """Roll and check the result."""
            # Set the inputs accordingly.
            chance_to_win.clear()
            chance_to_win.send_keys(format(win_chance, '.8f'))
            bet_size.clear()
            bet_size.send_keys(format(btc_to_bet, '.8f'))

            losses = get_integer(losses_elem.text)
            # Roll.
            if not playable(roll_btn[high]):
                raise Exception("No funds @ %s" % time.localtime())
            roll_btn[high].click()
            if self._wait_bet(roll_btn[high]):
                # Bet did not finish in time.
                return (False, False)

            for _ in xrange(3):
                try: result = lucky_number(self.driver)
                except NoSuchElementException: time.sleep(0.35)
                else: break

            if get_integer(losses_elem.text) > losses:
                # You lose!
                return (-1, result)
            else:
                return (1, result)

        return roll

