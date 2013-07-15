import hmac
import hashlib
try:
    from Crypto.Random import random
except ImportError:
    # Cryptographically strong random numbers not available.
    import random

_chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ._'
def gen_server_seed(size=64):
    return ''.join(random.choice(_chars) for _ in xrange(size))

def dice_roll(server_seed, client_seed, nonce):
    server_seed = server_seed.encode('utf-8')

    msg = '%s:%d' % (client_seed, nonce)
    h = hmac.new(server_seed, msg.encode('utf-8'), hashlib.sha512)
    digest = h.hexdigest()
    roll = 100
    while roll >= 100:
        roll = int(digest[:5], 16) / 10000.
        digest = digest[5:]
    return roll


def load_justdice(*no_args, **no_kwargs):
    return 'a:1:1:websocket', ''

class _Dummy(object):
    def emit(*args): pass

class JustDiceSocket(object):
    def __init__(self, response, login):
        self.login = login
        self._setup_sock(response)

    def _setup_sock(self, response):
        self.csrf = 'x'
        self.user_id = 1
        self.logged_in = True
        self.waiting_bet_result = False
        self.last_bet = None
        self.house_edge = 1 # %
        self.waiting_seed = False

        self.sock = _Dummy()

        self.server_seed = gen_server_seed()
        self.nonce = 0
        self.user_seed = str(random.randint(0, int('9' * 24)))


    def bet(self, win_chance, amount, roll_hi):
        which = 'hi' if roll_hi else 'lo'

        self.nonce += 1
        result = dice_roll(self.server_seed, self.user_seed, self.nonce)
        win = True
        if ((not roll_hi and result > win_chance) or
                (roll_hi and result < 100 - win_chance)):
            # Lose
            win = False

        self.last_bet = {
                'win': win,
                'roll_high': roll_hi,
                'lucky_number': result}

    def randomize(self, user_seed=None):
        self.server_seed = gen_server_seed()
        self.nonce = 0
        if user_seed is None:
            user_seed = str(random.randint(0, int('9' * 24)))
        self.user_seed = user_seed


    def on_reload(self):
        pass
