import sys
import time
from decimal import Decimal

def main(play, user=None, pwd=None, new_seed=True, dummy=True):
    if dummy:
        from browserless_dummy import load_justdice, JustDiceSocket
    else:
        from browserless_driver import load_justdice, JustDiceSocket

    print "Connecting..."
    response = load_justdice()
    login_info = {'user': user, 'pwd': pwd} if user is not None else None
    justdice = JustDiceSocket(response, login=login_info)
    sys.stdout.write("Logging in...")
    sys.stdout.flush()
    while not justdice.logged_in:
        if justdice.logged_in is None:
            # Could not login.
            justdice.sock.emit('disconnect')
            return
        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(0.75)
    print

    if new_seed:
        print "Generating new server seed.."
        justdice.randomize()
        print

    win, total = play(justdice)
    print "\nWin ratio: %d/%d = %s" % (win, total, Decimal(win) / total)

    justdice.sock.emit('disconnect')

def roll_dice(justdice, win_chance, amount, roll_hi):
    roll_for = Decimal('99.9999') - win_chance if roll_hi else win_chance
    sys.stdout.write("Rolling dice for %s %s ..." % (
        ">" if roll_hi else "<", format(roll_for, '07.4f')))
    sys.stdout.flush()
    justdice.bet(win_chance=win_chance, amount=amount, roll_hi=roll_hi)
    while justdice.waiting_bet_result:
        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(0.1)
    print " %s %s" % (format(justdice.last_bet["lucky_number"], '07.4f'),
        "win!" if justdice.last_bet['win'] else "lose :/")

    return justdice.last_bet['win']
