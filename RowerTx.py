from ant.core import message
from ant.core.constants import *
from ant.core.exceptions import ChannelError
import thread
# from binascii import hexlify
import struct

CHANNEL_PERIOD = 8182

# Transmitter for Rower Power ANT+ sensor
class RowerTx(object):
    data_lock = thread.allocate_lock()

    class RowerData:
        def __init__(self):
            self.instantaneousPower = 0
            self.distance = 0
            self.i = 0

    def __init__(self, antnode, sensor_id):
        self.antnode = antnode
        self.power = 0
        self.sensor_id = sensor_id

        # Get the channel
        self.channel = antnode.getFreeChannel()
        try:
            self.channel.name = 'C:POWER'
            self.channel.assign('N:ANT+', CHANNEL_TYPE_TWOWAY_TRANSMIT)
            self.channel.setID(0x11, sensor_id & 0xFFFF, 5)
            self.channel.setPeriod(8182)
            self.channel.setFrequency(57)
        except ChannelError as e:
            print "Channel config error: " + e.message
        self.powerData = RowerTx.RowerData()
        self.channel.registerCallback(self)

    def open(self):
        self.channel.open()

    def close(self):
        self.channel.close()

    def unassign(self):
        self.channel.unassign()

    def update(self, power):
        self.data_lock.acquire()
        self.power = power
        self.data_lock.release()

    def process(self, msg):
        if isinstance(msg, message.ChannelEventMessage) and \
                msg.getMessageID() == 1 and \
                msg.getMessageCode() == EVENT_TX:
            self.broadcast()
        elif isinstance(msg, message.ChannelAcknowledgedDataMessage):
            payload = msg.getPayload()
            a, page, id_ = struct.unpack('BBB', payload[:3])
            if a == 0 and page == 1 and id_ == 0xAA:
                # print ("ChannelAcknowledgedDataMessage: " + hexlify(payload))
                payload = chr(0x01)
                payload += chr(0xAC)
                payload += chr(0xFF)
                payload += chr(0xFF)
                payload += chr(0xFF)
                payload += chr(0xFF)
                payload += chr(0x00)
                payload += chr(0x00)
                ant_msg = message.ChannelBroadcastDataMessage(self.channel.number, data=payload)
                self.antnode.driver.write(ant_msg.encode())
        else:
            print("Message ID %d Code %d" % (msg.getMessageID(), msg.getMessageCode()))

    # Power was updated, so send out an ANT+ message
    def broadcast(self):
        self.powerData.i += 1

        self.data_lock.acquire()
        power = self.power
        self.data_lock.release()

        if power == 0:
            speed_bytes = 0
            distance_delta = 0
        else:
            pace = pow(2.80/float(power), 1.0/3.0)
            speed = 1.0 / pace
            speed_bytes = int(1000.0 / pace)
            distance_delta = speed / 4.0

        self.powerData.distance += distance_delta

        if self.powerData.i % 132 == 64 or self.powerData.i % 132 == 65:
            # page 80
            payload = chr(0x50)   # Manufacturer's Info
            payload += chr(0xFF)
            payload += chr(0xFF)
            payload += chr(0x01)  # HW Rev
            payload += chr(0xFF)  # MID LSB
            payload += chr(0x00)  # MID MSB
            payload += chr(0x01)  # Model LSB
            payload += chr(0x00)  # Model MSB
        elif self.powerData.i % 132 == 130 or self.powerData.i % 132 == 131:
            # page 81
            payload = chr(0x51)   # Product Info
            payload += chr(0xFF)
            payload += chr(0xFF)  # SW Rev Supp
            payload += chr(0x01)  # SW Rev Main
            payload += chr((self.sensor_id >> 0) & 0xFF)   # Serial 0-7
            payload += chr((self.sensor_id >> 8) & 0xFF)   # Serial 8-15
            payload += chr((self.sensor_id >> 16) & 0xFF)  # Serial 16-23
            payload += chr((self.sensor_id >> 24) & 0xFF)  # Serial 24-31
        elif self.powerData.i % 4 == 0 or self.powerData.i % 4 == 1:
            # page 16
            payload = chr(0x10)   # standard fitness equipment page
            payload += chr(22)    # equipment type field / rower
            payload += chr(self.powerData.i % 0xFF)  # Elapsed Time
            payload += chr(int(self.powerData.distance) % 0xFF)     # Distance travelled accumulated
            payload += chr(speed_bytes % 0xFF)  # Speed LSB
            payload += chr(speed_bytes >> 8)  # Speed MSB
            payload += chr(0xFF)  # Heart rate
            payload += chr((1<<2) | (1<<3))     # capabilities / FE state (transmit distance | virtual speed)
        elif self.powerData.i % 4 == 2 or self.powerData.i % 4 == 3:
            # page 22
            self.powerData.instantaneousPower = int(power)

            payload = chr(0x16)   # specific rower data
            payload += chr(0xFF)
            payload += chr(0xFF)
            payload += chr(0)     # stroke count
            payload += chr(0xFF)  # stroke cadence
            payload += chr(self.powerData.instantaneousPower & 0xff)
            payload += chr(self.powerData.instantaneousPower >> 8)
            payload += chr(0)     # capabilities / FE state

        ant_msg = message.ChannelBroadcastDataMessage(self.channel.number, data=payload)
        self.antnode.driver.write(ant_msg.encode())
