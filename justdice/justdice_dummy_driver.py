import hmac
import random
import hashlib
import threading
from decimal import Decimal

_chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ._'
def gen_server_seed(size=64):
    return ''.join(random.choice(_chars) for _ in xrange(size))


def _dice_roll(server_seed, client_seed, nonce):
    server_seed = server_seed.encode('utf-8')

    msg = '%s:%d' % (client_seed, nonce)
    h = hmac.new(server_seed, msg.encode('utf-8'), hashlib.sha512)
    digest = h.hexdigest()
    roll = 100
    while roll >= 100:
        roll = int(digest[:5], 16) / 10000.
        digest = digest[5:]
    return roll

def _roll(dummy_justdice, high=True):
    def do_it():
        client_seed = _dummy_elements['new_cseed'].get_attribute('value')
        result = _dice_roll(dummy_justdice._server_seed, client_seed,
                dummy_justdice._nonce)
        dummy_justdice._nonce += 1

        chance_to_win = Decimal(
                _dummy_elements['pct_chance'].get_attribute('value'))
        if ((not high and result > chance_to_win) or
                (high and result < 100 - chance_to_win)):
            # Lose
            l = _dummy_elements['losses'].text
            _dummy_elements['losses'].text = str(int(l) + 1)

        s = format(result, '07.4f')
        _dummy_elements['s1'].text = s[:3]
        _dummy_elements['s2'].text = s[3:5]
        _dummy_elements['s3'].text = s[5:7]

    return do_it

def _new_seed(dummy_justdice):
    def do_it():
        dummy_justdice._server_seed = gen_server_seed()
        dummy_justdice._nonce = 1
        _dummy_elements['new_shash'].text = hashlib.sha256(
                dummy_justdice._server_seed).hexdigest()
    return do_it


_dummy_elements = {}
def _make_dummy_elements(dummy):
    # seeds
    _dummy_elements['new_cseed'] = DummyElement('new_cseed', # User seed
            attrs={'value': dummy._client_seed})
    _dummy_elements['new_shash'] = DummyElement('new_shash', # Server seed hash
            text=hashlib.sha256(dummy._server_seed).hexdigest())
    _dummy_elements['a_random'] = DummyElement('a_random', # Randomize button
            click_func=_new_seed(dummy))
    # clicking on login button causes a page reload
    _dummy_elements['myok'] = DummyElement('myok', '', dummy.refresh)
    # start with 0 losses
    _dummy_elements['losses'] = DummyElement('hi', '0')
    # chance to win input
    _dummy_elements['pct_chance'] = DummyElement('pct_chance', '0')
    # roll hi label
    _dummy_elements['hi'] = DummyElement('hi', '0')
    # buttons for rolling either high or low
    _dummy_elements['a_hi'] = DummyElement('a_hi', '', _roll(dummy))
    _dummy_elements['a_lo'] = DummyElement('a_hi', '', _roll(dummy, high=False))
    # rolling result
    s1 = ("//div[@id='me' and @class='results']"
         "//div[@class='lucky'][1]//span[@class='s1']")
    s2 = ("//div[@id='me' and @class='results']"
          "//div[@class='lucky'][1]//span[@class='s2']")
    s3 = ("//div[@id='me' and @class='results']"
          "//div[@class='lucky'][1]//span[@class='s3']")
    _dummy_elements['s1'] = DummyElement(s1)
    _dummy_elements['s2'] = DummyElement(s2)
    _dummy_elements['s3'] = DummyElement(s3)
    _dummy_elements[s1] = _dummy_elements['s1']
    _dummy_elements[s2] = _dummy_elements['s2']
    _dummy_elements[s3] = _dummy_elements['s3']

class DummyElement(object):
    def __init__(self, name, text='', click_func=None, attrs=None):
        if name in _dummy_elements:
            self.text = _dummy_elements[name].text
            self.click_func = _dummy_elements[name].click_func
            self.attrs = _dummy_elements[name].attrs or {}
        else:
            self.text = text
            self.click_func = click_func
            self.attrs = attrs or {}
        self.name = name

    def text(self): return self.text
    def click(self): return self.click_func() if self.click_func else True
    def get_attribute(self, name):
        return self.attrs.get(name, '')
    def send_keys(self, text):
        if 'value' not in self.attrs:
            self.attrs['value'] = ''
        self.attrs['value'] += text
    def clear(self):
        self.attrs['value'] = ''


class DummyDriver(object):
    def __init__(self):
        self._justdice = False

    def get(self, url):
        if 'just-dice' in url:
            self._justdice = True
            self._server_seed = gen_server_seed()
            self._nonce = 1
            self._client_seed = "0" # Customizable.
            _make_dummy_elements(self)
        return True

    def refresh(self):
        if self._justdice:
            _dummy_elements['hi'].text = ''
            # Set back to some digit after some time.
            t = threading.Timer(0.1,
                    lambda: _dummy_elements['hi'].__setattr__('text', '0'))
            t.start()

    def quit(self):
        pass

    def find_element_by_id(self, name):
        return _dummy_elements.get(name, DummyElement(name))
    find_element_by_xpath = find_element_by_id
    find_element_by_link_text = find_element_by_id
    find_element_by_css_selector = find_element_by_id
