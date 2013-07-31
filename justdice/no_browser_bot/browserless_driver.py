import random
import urllib
import urllib2
import cookielib
from decimal import Decimal

import websocket
from socketio import SocketIO

BASE_DOMAIN = 'just-dice.com'
BASE_URL = 'https://%s' % BASE_DOMAIN

cj = cookielib.CookieJar()
def load_justdice(secret_url=None, proxy=None, headers=None, debug=False):
    """
    "proxy" is expected to be a map from protocol to a proxy server.
        e.g., proxy={'https': 'myproxy:port'} would use a proxy
        for https requests.

    "headers" should be a sequence of tuples to be added in each
    request. e.g, headers=[('User-Agent', 'bot')]
    """
    handler = []
    if debug:
        websocket.enableTrace(True)
        handler.append(urllib2.HTTPSHandler(debuglevel=1))
    cookie_handler = urllib2.HTTPCookieProcessor(cj)
    handler.append(cookie_handler)
    if proxy is not None:
        proxy_handler = urllib2.ProxyHandler(proxy)
        handler.append(proxy_handler)
    opener = urllib2.build_opener(*handler)

    headers = headers or []
    headers.append(('Origin', BASE_URL))
    opener.addheaders = headers

    if secret_url is not None:
        opener.open('%s/%s' % (BASE_URL, secret_url))
    else:
        opener.open(BASE_URL)
    req = opener.open('%s/socket.io/1' % BASE_URL)
    # Grab the session in order to allow the websocket connection.
    response = req.read()
    return response

def login_on_secret_url(options):
    # When using the secretl url with user/pwd defined,
    # we need to POST login data to a different page.
    data = urllib.urlencode({'password': options.password,
        'username': options.user, 'code': options.gauth})
    request = urllib2.Request('%s/%s' % (BASE_URL, options.secret), data)
    cookie_handler = urllib2.HTTPCookieProcessor(cj)
    handler = [cookie_handler]
    if options.proxy is not None:
        proxy_handler = urllib2.ProxyHandler(options.proxy)
        handler.append(proxy_handler)
    opener = urllib2.build_opener(*handler)
    opener.addheaders = [('Origin', BASE_URL)]
    opener.open(request)

    req = opener.open('%s/socket.io/1' % BASE_URL)
    # Grab the new session in order to allow the websocket connection.
    response = req.read()
    return response

def current_secreturl():
    for cookie in cj:
        if cookie.name == 'hash':
            return cookie.value


class JustDiceSocket(object):
    def __init__(self, response, login, params=None):
        self.login = login
        self._setup_sock(response)

    def _setup_sock(self, response):
        self.csrf = None
        self.user_id = None
        self.logged_in = False
        self.waiting_bet_result = False
        self.last_bet = None
        self.house_edge = 1 # %
        self.waiting_seed = False

        origin = BASE_URL
        self.sock = SocketIO(BASE_DOMAIN, origin, response, secure=True)

        self.sock.on('init', self.on_init)
        self.sock.on('set_hash', self.on_set_hash)
        self.sock.on('reload', self.on_reload)
        self.sock.on('result', self.on_result)
        self.sock.on('login_error', self.on_login_error)
        self.sock.on('jderror', self.on_jderror)
        self.sock.on('new_client_seed', self.on_new_seed)

        self.sock.on('invest', self.on_invest)
        self.sock.on('invest_error', self.on_invest_error)
        self.sock.on('divest_error', self.on_divest_error)
        self.sock.on('balance', self.on_balance)
        self.sock.on('chat', self.on_chat)

    # Override if needed.
    def on_invest(self, *args):
        # Expected args: invest, invest_pct, profit
        pass
    def on_invest_error(self, msg):
        pass
    def on_divest_error(self, msg):
        pass
    def on_balance(self, data):
        pass
    def on_chat(self, *args):
        # Expected args: msg, timestamp
        pass
    #

    def bet(self, win_chance, amount, roll_hi):
        if self.waiting_bet_result:
            raise Exception("Still waiting for last bet result")
        which = 'hi' if roll_hi else 'lo'
        self.sock.emit('bet', self.csrf, {'chance': '%s' % str(win_chance),
            'bet': format(amount, '.8f'), 'which': '%s' % which})
        self.waiting_bet_result = True

    def randomize(self, user_seed=None):
        # user_seed must be a string.
        if self.waiting_seed:
            return
        self.sock.emit('random', self.csrf)
        if user_seed is None:
            user_seed = str(random.randint(0, int('9' * 24)))
        self.sock.emit('seed', self.csrf, user_seed, True)
        self.waiting_seed = True

    def on_new_seed(self, o_sseed, o_sshash, o_useed, old_nonce, new_sshash):
        self.waiting_seed = False

    def on_result(self, result):
        if result['uid'] == self.user_id:
            self.last_bet = {
                    'win': result['win'],
                    'roll_high': result['high'],
                    'lucky_number': Decimal(result['lucky']) / 10000}
            self.waiting_bet_result = False
            return True

    def on_reload(self):
        self.sock.emit('disconnect')
        response = load_justdice()
        self._setup_sock(response)

    def on_set_hash(self, new_cookie_hash):
        for cookie in cj:
            if cookie.name == 'hash':
                cookie.value = new_cookie_hash
                break

    def on_init(self, data):
        self.csrf = data[u'csrf']
        self.user_id = data[u'uid']
        self.house_edge = data[u'edge']

        if data['username'] is None and self.login:
            google_2fa = self.login.get('2fa', '')
            self.sock.emit('login', self.csrf,
                    self.login['user'], self.login['pwd'], google_2fa)
        else:
            self.logged_in = True

    def on_login_error(self, msg):
        msg = msg.lower()
        if msg.startswith('incorrect') or msg.endswith('no such user'):
            self.logged_in = None
            raise Exception("Invalid credentials")
        elif 'google' in msg or 'phone' in msg:
            self.logged_in = None
            raise Exception("2FA failed")
        elif 'wrong too many' in msg:
            self.logged_in = None
            raise Exception("Blocked by 2FA, contact just-dice")

    def on_jderror(self, msg):
        msg = msg.lower()
        if 'minimum allowed' in msg or 'maximum allowed' in msg:
            self.waiting_bet_result = None
            raise Exception("Invalid win chance")
        elif 'google-auth' in msg:
            self.waiting_bet_result = None
            raise Exception("2FA locked")
        elif 'can not bet' in msg:
            raise Exception("Could not place bet, check your balance")
