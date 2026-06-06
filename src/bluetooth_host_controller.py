import bluetooth as bt
import subprocess
import select
import time
import re

class BluetoothHostController:

    def __init__(self):
        result = subprocess.run (["bluetoothctl","show"], capture_output=True,text=True)
        power_state_line = re.search ("PowerState:.*",result.stdout)
        power_state = power_state_line.group ().split ()[1]
        self.powered = True if power_state == "on" else False

    # Refresh bluetooth host controller status
    def update (self):
        self.__init__()
    
    # Test if the bluetooth controller of the host is on or not 
    def isOn (self):
        return self.powered

    # Power the bluetooth controller on or off
    def setPower (self, on=True):
        result = subprocess.run (["rfkill","block", "bluetooth"], capture_output=True,text=True)
        result = subprocess.run (["rfkill","unblock", "bluetooth"], capture_output=True,text=True)
        time.sleep (0.2)
        result = subprocess.run (["bluetoothctl","power", "on" if on else "off"], capture_output=True,text=True)
        print (result.stdout)

    # Look for bluetooth devices known by the controller
    # Returns a list of (address,name) tuples of detected bluetooth devices
    def scanDevices (self, duration=5):
        return bt.discover_devices (duration,flush_cache=True,lookup_names=True)

    # Test if the device specified by its mac address is already paired
    def isDevicePaired (self, macAddress):
        paired_state_line=""
        result = subprocess.run (["bluetoothctl","devices","Paired"], capture_output=True, text=True)
        print ("result: ", result.stdout)
        if result and result.stdout:
            paired_state_line = re.search ("Device " + macAddress+":.*", result.stdout)
        return False if paired_state_line == "" else True

    # Pair the specified bluetooth device
    def pairDevice (self, macAddress):
        btctlProcess = subprocess.Popen ("bluetoothctl",stdout=subprocess.PIPE,stdin=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,bufsize=0)
        self._printProcessOutput (btctlProcess)
        btctlProcess.stdin.write("scan on\n")
        time.sleep(1)
        self._printProcessOutput (btctlProcess)
        btctlProcess.stdin.write ("pair " + macAddress+"\n")
        time.sleep(1)
        self._printProcessOutput (btctlProcess)
        btctlProcess.stdin.write ("1234\n")
        self._printProcessOutput (btctlProcess)
        btctlProcess.stdin.write ("exit\n")
        btctlProcess.wait()

    # Print the output to stdout for a given process
    def _printProcessOutput (self, p):
        while True:
            result, *_ = select.select ([p.stdout.fileno()], [], [], 1.0)
            if not result:
                break
            line = p.stdout.readline ()
            print (line, end="")
