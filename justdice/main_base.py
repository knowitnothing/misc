import sys

from justdice_selenium import Justdice

def main(args, func):
    if len(args) < 3:
        sys.stderr.write('Usage: %s username password [-dummy]\n' % args[0])
        raise SystemExit

    user, pwd = args[1:3]

    if len(sys.argv) == 4 and args[3].startswith('-d'):
        from justdice_dummy_driver import DummyDriver
        driver = DummyDriver()
    else:
        from selenium import webdriver
        driver = webdriver.Firefox()

    try:
        justdice = Justdice(driver)
        justdice.login(user, pwd)

        roll = justdice.bet_prepare(new_seed='1')
        func(justdice, roll)
    finally:
        sys.stderr.write('Leaving..\n')
        driver.quit()
