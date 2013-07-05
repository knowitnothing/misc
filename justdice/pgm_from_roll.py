from fair_check import dice_roll
from justdice_dummy_driver import gen_server_seed

def main(server_seed, user_seed):
    width, height = 1000, 1000

    data = [0] * (width * height)

    roll = dice_roll(server_seed, user_seed)
    for i in xrange(len(data)):
        nonce, result = next(roll)
        r = int(result * 1e4)
        data[r] += 1

    print 'P2'
    print '%d %d %d' % (width, height, max(data))
    for i in xrange(height):
        print ' '.join(map(str, data[i*width:(i+1)*width]))


main(gen_server_seed(), '')
