#!/usr/bin/env python2

import sys
import serial, hashlib
from time import sleep
from binascii import unhexlify
from ant.core import driver
from ant.core import node
from RowerTx import RowerTx
from antConst import *

DEBUG = False
LOG = None
rower_trainer = None
antnode = None

ROWER_SENSOR_ID = int(int(hashlib.md5(getserial()).hexdigest(), 16) & 0xfffe) + 7

if  __name__ =='__main__':
    while True:
        try:
            with serial.Serial('/dev/serial0', 9600, timeout=1) as ser:
                ser.write(b"st\n")
                line = ser.readline()
                fields = line.split()
                power = fields[7]
                power = int(power)
        except:
            sleep(1)
            print("Waiting for serial line!")
            continue
        break        
       


    NETKEY = unhexlify(sys.argv[1])
    stick = driver.USB1Driver(device=sys.argv[2], log=LOG, debug=DEBUG)
    antnode = node.Node(stick)
    print("Starting ANT node on network %s" % sys.argv[1])
    antnode.start()
    key = node.NetworkKey('N:ANT+', NETKEY)
    antnode.setNetworkKey(0, key)

    print("Starting power meter with ANT+ ID " + repr(ROWER_SENSOR_ID))
    try:
        # Create the power meter object and open it
        rower_trainer = RowerTx(antnode, ROWER_SENSOR_ID)
        rower_trainer.open()
    except Exception as e:
        print("power_meter error: " + e.message)
        rower_trainer = None

    try:
        with serial.Serial('/dev/serial0', 9600, timeout=1) as ser:
            i = 0
            while True:
                i += 1
                sleep(0.2)
                ser.write(b"st\n")
                line = ser.readline()
                fields = line.split()
                power = fields[7]
                rower_trainer.update(power = int(power))
    except:
        pass

    if rower_trainer:
        print "Closing power meter"
        rower_trainer.close()
        rower_trainer.unassign()
    if antnode:
        print "Stopping ANT node"
        antnode.stop()

