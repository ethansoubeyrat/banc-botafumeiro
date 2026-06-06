#!/usr/bin/env python3
# coding:UTF-8
import os
import signal
import atexit
import sys

import device_model
from servomotor import Servomotor
import select
import socket
import asyncio
import subprocess
import threading
import time
from datetime import datetime
import queue

import board
from adafruit_ina219 import INA219
import bluetooth_host_controller

class Logger:
    def __init__ (self):
        self.logFile = None
        self.logFileName = None
        self._logEnabled = False
        if not os.path.exists ("logs"):
            os.makedirs ("logs")

    def open (self):
        self.logFileName = "logs/log_{}.csv".format (datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.logFile = open (self.logFileName, "w")
        self.logFile.write ("time,AccX,AccY,AccZ,AsX,AsY,AsZ,AngleX,AngleY,AngleZ,vMotor,iMotor,pMotor\n")
        return self.logFile
    
    def enable (self, enabled):
        self._logEnabled = enabled
    
    def log (self, time, accX, accY, accZ, asX, asY, asZ, angleX, angleY, angleZ, vMotor, iMotor, pMotor):
        if self.logFile is not None and self._logEnabled:
            self.logFile.write ("{},{},{},{},{},{},{},{},{},{},{:.3f},{:.3f},{:.3f}\n".format (
                time, accX, accY, accZ, asX, asY, asZ,
                angleX, angleY, angleZ,
                vMotor, iMotor, pMotor
            ))

    def close (self):
        if (self.logFile is not None):
            self.logFile.close ()
        self.logFile = None
        try:
            gui_process.stdin.write ("APP::LOG_FILE_NAME::None\n".encode ("utf-8"))
            gui_process.stdin.flush ()
        except:
            pass

class MotorController:
    def __init__ (self):
        self._mode = "synchronous"
        self._amplitude = 90
        self._period = 2.0
        self._phase = 0
        self._servo = Servomotor()
        self._async_task = None
        self._running = False
        self._delay_percent = 0  # Délai en pourcentage de la période
    
    def set_mode (self, mode):
        self._mode = mode

    def get_mode (self):
        return self._mode

    def set_amplitude (self, amplitude):
        self._amplitude = amplitude

    def get_amplitude (self):
        return self._amplitude
    
    def set_period (self, period):
        self._period = period

    def get_period (self):
        return self._period

    def set_phase (self, phase):
        self._phase = phase

    def get_phase (self):
        return self._phase

    def set_delay_percent (self, delay_percent):
        """Définir le délai en pourcentage de la période (0-100)"""
        self._delay_percent = max(0, min(100, delay_percent))  # Limiter entre 0 et 100

    def get_delay_percent (self):
        return self._delay_percent

    def set_position (self, angle):
        self._servo.servo.value = self._servo.angle_to_position(angle)

    def get_position (self):
        return self._position
    
    async def async_motor_loop(self):
        """Periodic motor control with strict timing synchronization"""
        try:
            # Apply initial phase delay (phase is in seconds)
            if self._phase > 0:
                try:
                    await asyncio.sleep(self._phase)
                except asyncio.CancelledError:
                    print("Motor: Initial phase delay cancelled", flush=True)
                    return

            # Start time for the first cycle
            cycle_start_time = time.time()

            while self._running:
                try:
                    current_time = time.time()
                    time_in_cycle = (current_time - cycle_start_time) % self._period
                    
                    # First half of period: go to amplitude
                    if time_in_cycle < self._period / 2.0:
                        try:
                            self.set_position(self._amplitude)
                        except Exception as e:
                            print(f"Motor ERROR: Failed to set amplitude position: {e}", flush=True)
                    # Second half of period: go to zero
                    else:
                        try:
                            self.set_position(0)
                        except Exception as e:
                            print(f"Motor ERROR: Failed to set zero position: {e}", flush=True)
                    
                    # Calculate time until next phase change
                    next_phase_time = cycle_start_time + (int(time_in_cycle / (self._period / 2.0)) + 1) * (self._period / 2.0)
                    sleep_time = next_phase_time - time.time()
                    
                    # Only sleep if there's time left (with small safety margin)
                    if sleep_time > 0.01:
                        try:
                            await asyncio.sleep(sleep_time)
                        except asyncio.CancelledError:
                            print("Motor: Sleep cancelled", flush=True)
                            raise
                    else:
                        # Very short sleep to avoid busy-waiting
                        await asyncio.sleep(0.001)
                        
                except asyncio.CancelledError:
                    print("Motor loop cancelled", flush=True)
                    break
                except Exception as e:
                    print(f"Motor ERROR in cycle: {e}", flush=True)
                    await asyncio.sleep(0.01)  # Short pause before retry
                    
        except asyncio.CancelledError:
            print("Motor: Main loop cancelled", flush=True)
        except Exception as e:
            print(f"Motor FATAL ERROR: {e}", flush=True)
        finally:
            try:
                self.set_position(0)  # Safety: return to 0 at end
                print("Motor: Safely stopped at position 0", flush=True)
            except Exception as e:
                print(f"Motor ERROR on final stop: {e}", flush=True)
    
    def start_async_motor(self, loop):
        """Start asynchronous motor control with error handling"""
        if self._mode == "asynchronous" and not self._running:
            self._running = True
            try:
                self._async_task = asyncio.run_coroutine_threadsafe(self.async_motor_loop(), loop)
                print("Motor: Async motor started successfully", flush=True)
            except Exception as e:
                print(f"Motor ERROR: Failed to start async motor: {e}", flush=True)
                self._running = False
                self._async_task = None
    
    def stop_async_motor(self):
        """Stop asynchronous motor control"""
        self._running = False
        if self._async_task:
            self._async_task.cancel()
            self._async_task = None
        self.set_position(0)

    def close (self):
        self.stop_async_motor()
        self._servo.close()    


class MotorWorker:
    """Worker thread dédié pour contrôle moteur"""
    
    def __init__(self, motor_controller):
        self.motor = motor_controller
        self._running = False
        self._thread = None
        self.cmd_queue = queue.Queue(maxsize=50)
        self.reaction_times = []
    
    def start(self):
        """Démarrer le worker thread"""
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=False, name="MotorWorker")
        self._thread.start()
        print("Motor worker started")
    
    def schedule_position_change(self, position, delay_seconds):
        """Ajouter une commande moteur à la queue"""
        try:
            execute_at = time.perf_counter() + delay_seconds
            self.cmd_queue.put_nowait((position, execute_at))
        except queue.Full:
            print("Motor queue full")
    
    def _worker_loop(self):
        """Boucle principale du worker"""
        pending = {}
        
        while self._running:
            now = time.perf_counter()
            
            # Récupérer nouvelles commandes
            try:
                while True:
                    position, execute_at = self.cmd_queue.get_nowait()
                    pending[execute_at] = position
            except queue.Empty:
                pass
            
            # Exécuter les commandes prêtes
            to_execute = [t for t in pending if t <= now]
            for execute_at in sorted(to_execute):
                position = pending.pop(execute_at)
                self.motor.set_position(position)
            
            # Sleep court
            if pending:
                next_time = min(pending.keys())
                sleep_time = max(0.001, (next_time - time.perf_counter()))
                time.sleep(min(sleep_time, 0.01))
            else:
                time.sleep(0.005)
    
    def stop(self):
        """Arrêter le worker"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

class PendulumState:
    def __init__ (self):
        self.theta = 0.0
        self.lastTheta = 0.0
        self.thetaDot = 0.0
        self.lastThetaDot = 0.0
        self.time = 0.0
        self.theta0Time = -1.0
        self.lastMotionState = "moving"
        self.motionState = "moving"
        self.stillCntr = 0
        self.period = -1.0
        # Period state:
        # 0 (uninitialized), 1 (1st crossing of theta0), 2 (crossing of thetaH1),
        # 3 (2nd crossing of theta0), 4 (crossing of thetaH2)
        self.periodState = 0
        self.lastPeriodStateTime = 0.0
        self.MIN_STATE_CHANGE_DELAY = 0.10  # temps (s) minimum entre changements d'état
        self.debugMode = False
        self.debugFile = None
        self.openDebugFile ()

    def openDebugFile (self):
        if not self.debugMode:
            return
        if not os.path.exists("logs"):
            os.makedirs("logs")
        self.debugFile = open("logs/state_debug.csv", "w", encoding="utf-8")
        self.debugFile.write("time,theta,thetaDot,current_state,detected_condition,new_state,time_since_last_change,accepted\n")
        self.debugFile.flush()

    def logState(self, time, theta, thetaDot, current_state, condition, new_state, time_since_change, accepted):
        if not self.debugMode:
            return
        if self.debugFile:
            self.debugFile.write(f"{time:.4f},{theta:.2f},{thetaDot:.2f},{current_state},'{condition}',{new_state},{time_since_change:.4f},{accepted}\n")
            self.debugFile.flush()

    def closeDebugFile (self):
        if not self.debugMode:
            return
        if self.debugFile:
            self.debugFile.close()
            self.debugFile = None

    def parseImuTimestamp(self, timeStr):
        """Parser le format bizarre de l'IMU"""
        parts = timeStr.split()  # ['2026-5-17', '20:19:5:284']
        dateParts = parts[0].split('-')  # ['2026', '5', '17']
        timeParts = parts[1].split(':')  # ['20', '19', '5', '284']
        
        year = int(dateParts[0])
        month = int(dateParts[1])
        day = int(dateParts[2])
        hour = int(timeParts[0])
        minute = int(timeParts[1])
        second = int(timeParts[2])
        milliseconds = int(timeParts[3])
        
        # Créer un datetime
        dt = datetime(year, month, day, hour, minute, second, milliseconds * 1000)
        return dt.timestamp()

    def update (self, sensorData):
        if "AsY" in sensorData and "AngleY" in sensorData and "time" in sensorData:
            self.theta = sensorData["AngleY"]
            self.thetaDot = sensorData["AsY"]
            newTime = self.parseImuTimestamp (sensorData["time"])

            if newTime < self.time:
                # Temps invalide car inférieur au temps précédent - ignorer cette mesure
                print(f"Timestamp IMU invalide: {newTime} < {self.time} (retard: {self.time - newTime:.3f}s)")
                return

            self.time = newTime

            # Update motion state
            if abs(self.thetaDot) > 5.0:
                self.motionState = "moving"
                self.stillCntr = 0
            else:
                self.stillCntr += 1
                if self.stillCntr >= 10:
                    self.motionState = "stationary"
            if (self.motionState != self.lastMotionState):
                try:
                    gui_process.stdin.write ("APP::MOTION_STATE_UPDATE::{}\n".format (self.motionState).encode ("utf-8"))
                    gui_process.stdin.flush ()
                except:
                    pass
                self.lastMotionState = self.motionState
            
            # Update period state if in synchronous mode
            if motor.get_mode() == "synchronous" and self.motionState == "moving":
                new_period_state = self.periodState
                conditionName = "none"
                
                if (self.periodState == 0 or self.periodState == 4) and (self.theta * self.lastTheta) < 0.0 and self.thetaDot > 0.0:
                    if (self.periodState == 0):
                        self.theta0Time = self.time
                    elif self.periodState == 4:
                        self.period = self.time - self.theta0Time
                        try:
                            gui_process.stdin.write ("APP::PERIOD_UPDATE::{:.3f}\n".format (self.period).encode ("utf-8"))
                            gui_process.stdin.flush ()
                        except:
                            pass
                        self.theta0Time = self.time
                    new_period_state = 1
                    conditionName = "θ crossing, θ̇>0"
                elif self.periodState == 1 and (self.thetaDot * self.lastThetaDot) <= 0.0 and self.theta < -5.0:
                    new_period_state = 2
                    conditionName = "θ̇ zero, θ<-5"
                elif self.periodState == 2 and (self.theta * self.lastTheta) <= 0.0 and self.thetaDot < 0.0:
                    new_period_state = 3
                    conditionName = "θ crossing, θ̇<0"
                elif self.periodState == 3 and (self.thetaDot * self.lastThetaDot) <= 0.0 and self.theta > 5.0:
                    new_period_state = 4
                    conditionName = "θ̇ positive, θ>5"
                elif self.periodState != 0 and self.time - self.theta0Time > 10.0:
                    new_period_state = 0
                    conditionName = "timeout"

                # Appliquer le changement seulement si délai respecté
                accepted = False
                if new_period_state != self.periodState:
                    time_since_last_change = self.time - self.lastPeriodStateTime
                    if time_since_last_change >= self.MIN_STATE_CHANGE_DELAY:
                        self.periodState = new_period_state
                        self.lastPeriodStateTime = self.time
                        accepted = True

                    # Logger TOUS les changements (acceptés ou bloqués)
                    self.logState(self.time, self.theta, self.thetaDot, 
                                  self.periodState, conditionName, new_period_state, 
                                  time_since_last_change, accepted)


                self.lastTheta = self.theta
                self.lastThetaDot = self.thetaDot

class SingleAxisAttitudeMonitor:
    def __init__ (self, axis="x"):
        self.period = -1.0
        self._tsAngle0 = None   
        self.lastAngle = None
        self.lastMotionState = "moving"
        self._axisData = dict (time = "time")
        match axis:
            case "x":
                self._axisData["Acc"] = "AccX"
                self._axisData["As"] = "AsX"
                self._axisData["Angle"] = "AngleX"
                self._axisData["AngleYaw"] = "AngleZ"
                self._axisData["AngleRoll"] = "AngleY"
                self._axisData["H"] = "HX"
            case "y":
                self._axisData["Acc"] = "AccY"
                self._axisData["As"] = "AsY"
                self._axisData["Angle"] = "AngleY"
                self._axisData["AngleYaw"] = "AngleZ"
                self._axisData["AngleRoll"] = "AngleX"
                self._axisData["H"] = "HY"
            case "z":
                self._axisData["Acc"] = "AccZ"
                self._axisData["As"] = "AsZ"
                self._axisData["Angle"] = "AngleZ"
                self._axisData["AngleYaw"] = "AngleX"
                self._axisData["AngleRoll"] = "AngleY"
                self._axisData["H"] = "HZ"
            case _:
                raise ValueError("Invalid axis. Choose from \"x\", \"y\", or \"z\".")
        self.pendulum = PendulumState()
    
    def updateIMUMeasures (self, sensorData):
        if states["device-ready"] == False:
            return
        self.pendulum.update (sensorData)


# Planifier les appels motor.set_position avec délai
def schedule_motor_position_change(position, delay_seconds):
    """Planifier un changement de position du moteur après un délai"""
    motor_worker.schedule_position_change(position, delay_seconds)

# This method will be called when sensor data is updated
def updateData (deviceModel):
    _imuData = deviceModel.deviceData

    if not hasattr(updateData, 'currPeriodState'):
        updateData.currPeriodState = 0

    _motorPower = ina219.power
    _motorVoltage = ina219.bus_voltage
    _motorCurrent = ina219.current

    mon.updateIMUMeasures(_imuData)

    # Only control motor position in SYNCHRONOUS mode
    if motor.get_mode() == "synchronous":
        if updateData.currPeriodState != mon.pendulum.periodState:
            if states["motor-running"]:
                # Calculer le délai en secondes basé sur le pourcentage de la période mesurée
                if mon.pendulum.period > 0:
                    delay_seconds = (motor.get_delay_percent() / 100.0) * mon.pendulum.period
                else:
                    delay_seconds = 0
                
                if mon.pendulum.periodState == 1 or mon.pendulum.periodState == 3:
                    # Planifier le mouvement vers 0 avec délai
                    schedule_motor_position_change(0, delay_seconds)
                elif mon.pendulum.periodState == 2 or mon.pendulum.periodState == 4:
                    # Planifier le mouvement vers amplitude avec délai
                    schedule_motor_position_change(motor.get_amplitude(), delay_seconds)
            
            updateData.currPeriodState = mon.pendulum.periodState

    log.log (
        _imuData.get("time", ""),
        _imuData.get("AccX", ""),
        _imuData.get("AccY", ""),
        _imuData.get("AccZ", ""),
        _imuData.get("AsX", ""),
        _imuData.get("AsY", ""),
        _imuData.get("AsZ", ""),
        _imuData.get("AngleX", ""),
        _imuData.get("AngleY", ""),
        _imuData.get("AngleZ", ""),
        _motorVoltage,
        _motorCurrent,
        _motorPower
    )

# Check for user input from stdin
async def receive_user_input ():
    try:
        result = select.select ([sys.stdin], [], [], 0)
        if result[0]:
            return True
        return False
    except Exception:
        return True
    
# Poll for receiving sensor data
async def receive_sensor_data (sock):
    result = select.select ([sock], [], [], 0.1)
    if result[0]:
        res = sock.recv (1024)
        device.onDataReceived (None, res)

# Main event loop: read sensor data and check for user input
async def app_loop(sock):
    exit_loop = False
    while not exit_loop and not states.get("shutdown", False):
        read_stdin_task = asyncio.create_task (receive_user_input())
        read_sensor_task = asyncio.create_task (receive_sensor_data(sock))
        await read_sensor_task
        exit_loop = await read_stdin_task

    
def do_bt_connect ():
    """Scan BT devices and send list to GUI for selection."""
    print ("Trying to connect")
    hostCtrlr = bluetooth_host_controller.BluetoothHostController()
    if not hostCtrlr.isOn():
        hostCtrlr.setPower(True)
        hostCtrlr.update()
    if not hostCtrlr.isOn():
        try:
            gui_process.stdin.write (b"APP::BT_DISCONNECTED\n")
            gui_process.stdin.flush ()
        except:
            pass
        return

    nearby_devices = hostCtrlr.scanDevices(5)
    if not nearby_devices:
        try:
            gui_process.stdin.write (b"APP::BT_DISCONNECTED\n")
            gui_process.stdin.flush ()
        except:
            pass
        return

    # Send device list to GUI — format: "MAC1,Name1;MAC2,Name2;..."
    device_list_str = ";".join(["{},{}".format(mac, name) for mac, name in nearby_devices])
    try:
        gui_process.stdin.write ("APP::DEVICE_LIST::{}\n".format (device_list_str).encode ("utf-8"))
        gui_process.stdin.flush ()
    except:
        pass


def do_device_selected (mac):
    """Finalize BT connection once GUI has selected a device."""
    hostCtrlr = bluetooth_host_controller.BluetoothHostController()

    if not hostCtrlr.isDevicePaired(mac):
        hostCtrlr.pairDevice(mac)

    if hostCtrlr.isDevicePaired(mac):
        device.mac = mac
        device.callback_method = updateData
        device.port = 1
        device.isReady = True
        try:
            gui_process.stdin.write (b"APP::BT_CONNECTED\n")
            states["device-ready"] = True
        except:
            pass
    else:
        try:
            gui_process.stdin.write (b"APP::BT_DISCONNECTED\n")
            states["device-ready"] = False
        except:
            pass
    try:
        gui_process.stdin.flush ()
    except:
        pass


def gui_worker (device, states, loop):
    """Worker thread that reads GUI commands"""
    print("GUI worker thread started")
    while not states.get("shutdown", False):
        try:
            for l in gui_process.stdout:
                ls = l.rstrip()
                ls = ls.decode ("utf-8")
                if ls.startswith ("GUI::"):
                    match ls.strip():
                        case "GUI::BT_CONNECT_REQUEST":
                            do_bt_connect ()
                        case _ if ls.strip().startswith("GUI::DEVICE_SELECTED::"):
                            mac = ls.strip().split("::")[2]
                            do_device_selected (mac)
                        case "GUI::RESET_ANGLES_REQUEST":
                            future = asyncio.run_coroutine_threadsafe(device.resetAngles(), loop)
                            try:
                                future.result(timeout=2.0)
                            except Exception as e:
                                print(f"resetAngles failed: {e}")
                        case "GUI::START_LOG_REQUEST":
                            if states["device-ready"]:
                                states["file-logging"] = True
                                log.enable (True)
                                log.open ()
                                try:
                                    gui_process.stdin.write ("APP::LOG_FILE_NAME::{}\n".format (log.logFileName).encode ("utf-8"))
                                    gui_process.stdin.flush ()
                                except:
                                    pass
                        case "GUI::STOP_LOG_REQUEST":
                            if states["file-logging"]:
                                states["file-logging"] = False
                                log.enable (False)
                                log.close ()
                        case "GUI::START_MOTOR_REQUEST":
                            if states["device-ready"]:
                                states["motor-running"] = True
                                if motor.get_mode() == "asynchronous":
                                    motor.start_async_motor(loop)
                                else:
                                    motor.set_position(0)
                        case "GUI::STOP_MOTOR_REQUEST":
                            if states["motor-running"]:
                                states["motor-running"] = False
                                if motor.get_mode() == "asynchronous":
                                    motor.stop_async_motor()
                                else:
                                    motor.set_position(0)
                        case _ if ls.strip().startswith("GUI::MOTOR_AMPLITUDE_CHANGED"):
                            if states["device-ready"]:
                                try:
                                    amplitude = float(ls.strip().split("::")[2])
                                    motor.set_amplitude(amplitude)
                                except ValueError:
                                    print(f"Invalid amplitude value: {ls.strip().split('::')[2]}")
                        case _ if ls.strip().startswith("GUI::SYNC_MODE_CHANGED"):
                            if states["device-ready"]:
                                mode = ls.strip().split("::")[2]
                                was_running = states["motor-running"]
                                
                                # Stop current mode
                                if was_running:
                                    if motor.get_mode() == "asynchronous":
                                        motor.stop_async_motor()
                                
                                # Change mode
                                motor.set_mode(mode)
                                
                                # Restart if was running
                                if was_running:
                                    if mode == "asynchronous":
                                        motor.start_async_motor(loop)
                        case _ if ls.strip().startswith("GUI::MOTOR_PERIOD_CHANGED"):
                            if states["device-ready"]:
                                try:
                                    period = float(ls.strip().split("::")[2])
                                    motor.set_period(period)
                                except ValueError:
                                    print(f"Invalid period value: {ls.strip().split('::')[2]}")
                        case _ if ls.strip().startswith("GUI::MOTOR_PHASE_CHANGED"):
                            if states["device-ready"]:
                                try:
                                    phase = float(ls.strip().split("::")[2])
                                    motor.set_phase(phase)
                                except ValueError:
                                    print(f"Invalid phase value: {ls.strip().split('::')[2]}")
                        case _ if ls.strip().startswith("GUI::MOTOR_DELAY_PERCENT_CHANGED"):
                            if states["device-ready"]:
                                try:
                                    delay_percent = float(ls.strip().split("::")[2])
                                    motor.set_delay_percent(delay_percent)
                                except ValueError:
                                    print(f"Invalid delay percent value: {ls.strip().split('::')[2]}")
        except Exception as e:
            print(f"GUI worker error: {e}")
            break
    
    print("GUI worker exiting")

def cleanup():
    """Called on exit - cleanup resources"""
    states["shutdown"] = True
    
    # Stop motor
    if motor:
        try:
            motor.close()
            print("Motor stopped")
        except:
            pass
    if motor_worker:
        try:
            motor_worker.stop()
            print("Motor worker stopped")
        except:
            pass
    
    # Close GUI
    if gui_process:
        try:
            gui_process.terminate()
            gui_process.wait(timeout=2)
            print("GUI closed")
        except subprocess.TimeoutExpired:
            gui_process.kill()
            gui_process.wait()
            print("GUI killed")
        except:
            pass
    
    # Close event loop
    if loop:
        try:
            loop.close()
            print("Event loop closed")
        except:
            pass
    
    # Close logger
    if log:
        try:
            log.close()
            print("Logger closed")
        except:
            pass

    if mon and mon.pendulum:
        try:
            mon.pendulum.closeDebugFile()
            if mon.pendulum.debugMode:
                print("Debug file closed")
        except:
            pass
    
    print("=== Cleanup complete ===\n")

def signal_handler(sig, frame):
    """Handle Ctrl+C and termination signals"""
    print(f"\n[Signal {sig}] Received, exiting gracefully...")
    cleanup()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup)

mon = SingleAxisAttitudeMonitor ("y")
motor = None
gui_process = None
loop = None
log = None

if __name__ == '__main__':
    print("=== Botafumeiro Application Started ===\n")
    
    device = device_model.DeviceModel()
    motor = MotorController()
    motor_worker = MotorWorker(motor)
    motor_worker.start()

    i2c = board.I2C()
    ina219 = INA219(i2c)
    log = Logger()
    
    states = {"file-logging": False,
              "device-ready": False,
              "motor-running": False,
              "shutdown": False}

    gui_process = subprocess.Popen(["python3", "gui_app.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    gui_worker_thread = threading.Thread(target=gui_worker, args=(device, states, loop), daemon=True)
    gui_worker_thread.start()

    try:
        while not device.isReady and not states.get("shutdown", False):
            time.sleep(0.1)

        if device.isReady and not states.get("shutdown", False):
            socket = loop.run_until_complete(device.openDevice())
            loop.run_until_complete(app_loop(socket))
    
    except KeyboardInterrupt:
        print("\nKeyboard interrupt")
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        cleanup()