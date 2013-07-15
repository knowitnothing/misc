import sys
import time

from browserless_driver import JustDiceSocket, load_justdice, current_secreturl

def main(user, pwd, google_2fa=None):
    print "Connecting.."
    response, _ = load_justdice()
    print "Logging in.."
    justdice = JustDiceSocket(response,
            login={'user': user, 'pwd': pwd, '2fa': google_2fa})
    now = time.time()
    max_login_wait = 15 # seconds
    while not justdice.logged_in:
        if time.time() - now > max_login_wait:
            # Timed out.
            justdice.logged_in = None
        if justdice.logged_in is None:
            # Could not login.
            print "Couldn't log in"
            break
        time.sleep(0.75)
    else:
        print "Secret url: %s" % current_secreturl()
    justdice.sock.emit('disconnect')


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "Usage: %s user password [2fa]" % sys.argv[0]
    main(*sys.argv[1:])
