import struct, sys, hashlib, curses
from time import sleep
from binascii import hexlify,unhexlify
from ant.core import driver
from ant.core import node
from RowerTx import RowerTx
from iConst import *

rower = None

ROWER_SENSOR_ID = int(int(hashlib.md5(getserial()).hexdigest(), 16) & 0xFFFFfffe) + 1

if  __name__ =='__main__':
    NETKEY = unhexlify(sys.argv[1])
    stick = driver.USB1Driver(device=sys.argv[2], log=None, debug=True)
    antnode = node.Node(stick)
    print("Starting ANT node on network %s" % sys.argv[1])
    antnode.start()
    key = node.NetworkKey('N:ANT+', NETKEY)
    antnode.setNetworkKey(0, key)

    print("Starting power meter with ANT+ ID " + repr(ROWER_SENSOR_ID))
    try:
        # Create the power meter object and open it
        rower = RowerTx(antnode, ROWER_SENSOR_ID)
        rower.open()
    except Exception as e:
        print("power_meter error: " + e.message)
        rower = None

    i = 0
    while True:
        try:
            sleep(1)
        except:
            break
        rower.update(power = 179.2)
        i += 1
        if (i > 200):
            break

    if rower:
        print "Closing power meter"
        rower.close()
        rower.unassign()
    if antnode:
        print "Stopping ANT node"
        antnode.stop()

