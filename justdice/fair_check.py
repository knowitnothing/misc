import sys
import hmac
import hashlib


def fair_server(seed, seed_hash):
    digest = hashlib.sha256(seed.encode('utf-8')).hexdigest()
    return True if digest == seed_hash else False

def dice_roll(server_seed, client_seed, num=float('inf')):
    server_seed = server_seed.encode('utf-8')
    i = 0
    while i < num:
        i += 1
        msg = '%s:%d' % (client_seed, i)
        h = hmac.new(server_seed, msg.encode('utf-8'), hashlib.sha512)
        digest = h.hexdigest()
        roll = 100
        while roll >= 100:
            roll = int(digest[:5], 16) / 10000.
            digest = digest[5:]
        yield i, roll



def main(server_seed, server_seed_hash, client_seed, number_of_rolls):
    # All arguments are assumed to be of string type.
    if not fair_server(server_seed, server_seed_hash):
        sys.stderr.write("**** Unfair! ****\n")
        return 1

    sys.stderr.write("Rolls\n")
    digits = len(number_of_rolls)
    number_of_rolls = int(number_of_rolls)
    for roll in dice_roll(server_seed, client_seed, number_of_rolls):
        sys.stdout.write('%*d\t%07.4f\n' % (digits, roll[0], roll[1]))

    return 0

if __name__ == "__main__":
    # The following data is directly available on the "randomize" window
    # at just-dice.com. Ideally, you should write down the new
    # server seed hash produced in order to correctly check the server's
    # fairness.
    data = ("K8TWYVpwy_k2V4tkwL3cN5dCOEJ6Ppr7BFPJ8hJtmM81r8DErO26cAqCwCWvnf4.",
            "d12d0ae6f4b762223170b1dba218d67734091778870271929934cd5a4dc7e8c6",
            "220525942783254573895367", "5")

    sys.exit(main(*data))
