# coding:UTF-8
import socket
import time
from gui_dialogs import AlarmBox, ListBoxSelect
import bluetooth_host_controller

# Device instance
class DeviceModel:
    def __init__(self):
        self.isReady = False
        self.mac = ""
        self.name = ""
        self.isOpened = False
        self.socket = None
        # Device Data Dictionary
        self.deviceData = {}
        self._tempBytes = []
    
    def connect(self, callback_method):
        # If needed, pair device. Set the usReady flag if ready to proceed to further steps
        hostCtrlr = bluetooth_host_controller.BluetoothHostController()
        if (not hostCtrlr.isOn ()):
            hostCtrlr.setPower (True)
            hostCtrlr.update ()
        if (not hostCtrlr.isOn ()):
            AlarmBox ("Can't start host bluetooth controller", "error")
        else:
            nearby_devices = hostCtrlr.scanDevices(5)
            if not nearby_devices:
                AlarmBox ("No bluetooth device found", "error")
            else:
                deviceID = ListBoxSelect ("Select bluetooth device", "400x200", nearby_devices).select_item ()
                if (not deviceID):
                    AlarmBox ("No bluetooth device selected", "error")
                else:
                    self.mac = deviceID[0]
                    self.name = deviceID[1]
                    if (not hostCtrlr.isDevicePaired (deviceID[0])):
                        hostCtrlr.pairDevice (self.mac)
                    if (hostCtrlr.isDevicePaired (deviceID[0])):
                        self.port = 1
                        self.callback_method = callback_method
                        self.isReady = True

    # Set device data
    def set(self, key, value):
        # Saving device data to key values
        self.deviceData[key] = value

    # Obtain device data
    def get(self, key):
        # Obtaining data from key values
        if key in self.deviceData:
            return self.deviceData[key]
        else:
            return None

    # Delete device data
    def remove(self, key):
        del self.deviceData[key]
    
    # open Device
    async def openDevice(self):
        self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.socket.connect((self.mac, 1))
        self.isOpened = True
        return self.socket

    # close Device
    def closeDevice(self):
        self.socket.close()
        self.isOpened = False

    # Serial port data processing
    def onDataReceived(self, sender, data):
        tempdata = bytes.fromhex(data.hex())
        for var in tempdata:
            self._tempBytes.append(var)
            # Must start with 0x55
            if self._tempBytes[0] != 0x55:
                del self._tempBytes[0]
                continue
            if len(self._tempBytes) == 11:
                # Checksum
                if (sum(self._tempBytes[:10]) & 0xff) == self._tempBytes[10]:
                    self.processData(self._tempBytes)
                    self._tempBytes.clear()
                else:
                    del self._tempBytes[0]
                    continue

    # data analysis
    def processData(self, Bytes):
        # Time
        if Bytes[1] == 0x50:
            year = Bytes[2] + 2000
            mon = Bytes[3]
            day = Bytes[4]
            hour = Bytes[5]
            minute = Bytes[6]
            sec = Bytes[7]
            mils = Bytes[9] << 8 | Bytes[8]
            self.set("time", "{}-{}-{} {}:{}:{}:{}".format(year, mon, day, hour, minute, sec, mils))
        # Acceleration
        elif Bytes[1] == 0x51:
            Ax = self.getSignInt16(Bytes[3] << 8 | Bytes[2]) / 32768 * 16
            Ay = self.getSignInt16(Bytes[5] << 8 | Bytes[4]) / 32768 * 16
            Az = self.getSignInt16(Bytes[7] << 8 | Bytes[6]) / 32768 * 16
            self.set("AccX", round(Ax, 3))
            self.set("AccY", round(Ay, 3))
            self.set("AccZ", round(Az, 3))
            # self.callback_method(self)
        # Angular velocity
        elif Bytes[1] == 0x52:
            Gx = self.getSignInt16(Bytes[3] << 8 | Bytes[2]) / 32768 * 2000
            Gy = self.getSignInt16(Bytes[5] << 8 | Bytes[4]) / 32768 * 2000
            Gz = self.getSignInt16(Bytes[7] << 8 | Bytes[6]) / 32768 * 2000
            self.set("AsX", round(Gx, 3))
            self.set("AsY", round(Gy, 3))
            self.set("AsZ", round(Gz, 3))
        # Angle
        elif Bytes[1] == 0x53:
            AngX = self.getSignInt16(Bytes[3] << 8 | Bytes[2]) / 32768 * 180
            AngY = self.getSignInt16(Bytes[5] << 8 | Bytes[4]) / 32768 * 180
            AngZ = self.getSignInt16(Bytes[7] << 8 | Bytes[6]) / 32768 * 180
            self.set("AngleX", round(AngX, 2))
            self.set("AngleY", round(AngY, 2))
            self.set("AngleZ", round(AngZ, 2))
            self.callback_method(self)
        # Magnetic field
        elif Bytes[1] == 0x54:
            Hx = self.getSignInt16(Bytes[3] << 8 | Bytes[2]) / 120
            Hy = self.getSignInt16(Bytes[5] << 8 | Bytes[4]) / 120
            Hz = self.getSignInt16(Bytes[7] << 8 | Bytes[6]) / 120
            self.set("HX", round(Hx, 3))
            self.set("HY", round(Hy, 3))
            self.set("HZ", round(Hz, 3))
        else:
            pass

    # Obtain int16 signed number
    @staticmethod
    def getSignInt16(num):
        if num >= pow(2, 15):
            num -= pow(2, 16)
        return num

    # End of sensor data processing section

    # Sending serial port data
    async def sendData(self, data):
        try:
            self.socket.send(bytes(data))
        except Exception as ex:
            print(ex)

    # read register
    async def readReg(self, regAddr):
        # Encapsulate read instructions and send data to the serial port
        await self.sendData(self.get_readBytes(regAddr))

    # Write Register
    async def writeReg(self, regAddr, sValue):
        # unlock
        await self.unlock()
        # Delay 100ms
        time.sleep(0.1)
        cmd = self.get_writeBytes(regAddr, sValue)
        await self.sendData(cmd)
        # Delay 100ms
        time.sleep(0.1)
        # save
        await self.save()

    # Reset angles
    async def resetAngles(self):
        await self.writeReg(0x01, 0x0008)

    # Read instruction encapsulation
    @staticmethod
    def get_readBytes(regAddr):
        tempBytes = [None] * 5
        tempBytes[0] = 0xff
        tempBytes[1] = 0xaa
        tempBytes[2] = 0x27
        tempBytes[3] = regAddr
        tempBytes[4] = 0
        return tempBytes

    # Write instruction encapsulation
    @staticmethod
    def get_writeBytes(regAddr, rValue):
        tempBytes = [None] * 5
        tempBytes[0] = 0xff
        tempBytes[1] = 0xaa
        tempBytes[2] = regAddr
        tempBytes[3] = rValue & 0xff
        tempBytes[4] = rValue >> 8
        return tempBytes

    async def unlock(self):
        cmd = self.get_writeBytes(0x69, 0xb588)
        await self.sendData(cmd)

    async def save(self):
        cmd = self.get_writeBytes(0x00, 0x0000)
        await self.sendData(cmd)
        await self.sendData(cmd)