import tkinter as tk
from tkinter import ttk
import sys
import os


flash_colors = ("black", "lightblue")
afterID = None
previousAmplitudeValue = 90
previousPeriodValue = 2
previousPhasePercentValue = 0
previousPhaseSecondsValue = 0

def flash_color(object, color_index, stop=False):
    global afterID
    if not stop:
        object.config (disabledforeground = flash_colors[color_index])
        afterID = root.after (500, flash_color, object, 1 - color_index, stop)
    elif afterID:
        object.config (disabledforeground = flash_colors[0])
        root.after_cancel (afterID)
        afterID = None
    

def connect_requested (root):
    print ("GUI::BT_CONNECT_REQUEST", flush=True)
    buttonCnx.config (state="disabled")
    buttonCnx.config (text="Scanning...")
    flash_color (buttonCnx, 0)

def show_device_selector (devices):
    """Show a Toplevel dialog to select a BT device. Sends GUI::DEVICE_SELECTED::MAC on selection."""
    top = tk.Toplevel(root)
    top.title("Select bluetooth device")
    top.geometry("400x200")
    top.attributes("-topmost", True)
    top.grab_set()  # Make it modal

    listbox = tk.Listbox(top, font=("Arial", 18))
    listbox.pack(fill="both", expand=True, padx=10, pady=10)

    # Store (mac, name) pairs alongside display strings
    device_map = {}
    for mac, name in devices:
        display = "{} ({})".format(name, mac)
        listbox.insert(tk.END, display)
        device_map[display] = mac

    def on_select():
        sel = listbox.get(tk.ANCHOR)
        if sel and sel in device_map:
            print("GUI::DEVICE_SELECTED::{}".format(device_map[sel]), flush=True)
            top.destroy()

    def on_cancel():
        # Notify app.py that no device was selected
        print("GUI::DEVICE_SELECTED::NONE", flush=True)
        buttonCnx.config(state="normal", text="Connect")
        flash_color(buttonCnx, 0, stop=True)
        top.destroy()

    top.protocol("WM_DELETE_WINDOW", on_cancel)
    listbox.bind('<Double-1>', lambda e: on_select())

    btn_frame = tk.Frame(top)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Select", font=("Arial", 18), command=on_select).pack(side=tk.LEFT, padx=10)
    tk.Button(btn_frame, text="Cancel", font=("Arial", 18), command=on_cancel).pack(side=tk.LEFT, padx=10)

def reset_angles_requested (root):
    print ("GUI::RESET_ANGLES_REQUEST", flush=True)

def start_log_requested (root):
    print ("GUI::START_LOG_REQUEST", flush=True)
    buttonStartLog.config (text="Stop logging", command=lambda : stop_log_requested(root))

def stop_log_requested (root):
    print ("GUI::STOP_LOG_REQUEST", flush=True)
    buttonStartLog.config (text="Start logging", command=lambda : start_log_requested(root))

def start_motor_requested (root):
    print ("GUI::START_MOTOR_REQUEST", flush=True)
    buttonStartMotor.config (text="Stop motor", command=lambda : stop_motor_requested(root))
    labelAmplitude.config (state="disabled")
    entryAmplitude.config (state="disabled")
    checkSyncMode.config(state="disabled")
    labelMotorPeriod.config (state="disabled")
    entryMotorPeriod.config (state="disabled")
    labelMotorPhasePercent.config (state="disabled")
    entryMotorPhasePercent.config (state="disabled")
    labelMotorPhaseSeconds.config (state="disabled")
    entryMotorPhaseSeconds.config (state="disabled")

def stop_motor_requested (root):
    print ("GUI::STOP_MOTOR_REQUEST", flush=True)
    buttonStartMotor.config (text="Start motor", command=lambda : start_motor_requested(root))
    labelAmplitude.config (state="normal")
    entryAmplitude.config (state="normal")
    checkSyncMode.config(state="normal")
    is_async = syncMode.get()
    if is_async:
        # Mode asynchrone : afficher period et phase en secondes
        labelMotorPeriod.config (state="normal")
        entryMotorPeriod.config (state="normal")
        labelMotorPhaseSeconds.config (state="normal")
        entryMotorPhaseSeconds.config (state="normal")
        # Masquer phase en %
        labelMotorPhasePercent.config (state="disabled")
        entryMotorPhasePercent.config (state="disabled")
    else:
        # Mode synchrone : afficher seulement phase en %
        labelMotorPeriod.config (state="disabled")
        entryMotorPeriod.config (state="disabled")
        labelMotorPhasePercent.config (state="normal")
        entryMotorPhasePercent.config (state="normal")
        # Masquer phase en secondes
        labelMotorPhaseSeconds.config (state="disabled")
        entryMotorPhaseSeconds.config (state="disabled")

def motor_amplitude_changed (root):
    global previousAmplitudeValue
    value = motorAmplitude.get()

    if value <= 0 or value > 180:
        entryAmplitude.config(bg="red")
        root.after(200, lambda: entryAmplitude.config(bg="white"))
        root.after(10, lambda: motorAmplitude.set(previousAmplitudeValue))
        return False
    
    try:
        float_value = float(value)
        previousAmplitudeValue = value
        print ("GUI::MOTOR_AMPLITUDE_CHANGED::{}".format(float_value), flush=True)
    except ValueError:
        entryAmplitude.config(bg="red")
        root.after(200, lambda: entryAmplitude.config(bg="white"))
        root.after(10, lambda: motorAmplitude.set(previousAmplitudeValue))
        return False
    
    return True

def on_motor_amplitude_entered (event):
    motor_amplitude_changed(root)
    root.focus()
    return "break"

def motor_phase_percent_changed (root):
    global previousPhasePercentValue
    value = motorPhasePercent.get()

    if value < 0 or value > 100:
        entryMotorPhasePercent.config(bg="red")
        root.after(200, lambda: entryMotorPhasePercent.config(bg="white"))
        root.after(10, lambda: motorPhasePercent.set(previousPhasePercentValue))
        return False
    
    try:
        float_value = float(value)
        previousPhasePercentValue = value
        print ("GUI::MOTOR_DELAY_PERCENT_CHANGED::{}".format(float_value), flush=True)
    except ValueError:
        entryMotorPhasePercent.config(bg="red")
        root.after(200, lambda: entryMotorPhasePercent.config(bg="white"))
        root.after(10, lambda: motorPhasePercent.set(previousPhasePercentValue))
        return False
    return True

def on_motor_phase_percent_entered (event):
    motor_phase_percent_changed(root)
    root.focus()
    return "break"

def motor_phase_seconds_changed (root):
    global previousPhaseSecondsValue
    value = motorPhaseSeconds.get()

    if value < 0:
        entryMotorPhaseSeconds.config(bg="red")
        root.after(200, lambda: entryMotorPhaseSeconds.config(bg="white"))
        root.after(10, lambda: motorPhaseSeconds.set(previousPhaseSecondsValue))
        return False
    
    try:
        float_value = float(value)
        previousPhaseSecondsValue = value
        print ("GUI::MOTOR_PHASE_CHANGED::{}".format(float_value), flush=True)
    except ValueError:
        entryMotorPhaseSeconds.config(bg="red")
        root.after(200, lambda: entryMotorPhaseSeconds.config(bg="white"))
        root.after(10, lambda: motorPhaseSeconds.set(previousPhaseSecondsValue))
        return False
    return True

def on_motor_phase_seconds_entered (event):
    motor_phase_seconds_changed(root)
    root.focus()
    return "break"

def motor_period_changed (root):
    global previousPeriodValue
    value = motorPeriod.get()

    if value <= 0:
        entryMotorPeriod.config(bg="red")
        root.after(200, lambda: entryMotorPeriod.config(bg="white"))
        root.after(10, lambda: motorPeriod.set(previousPeriodValue))
        return False

    try:
        float_value = float(value)
        previousPeriodValue = value
        print ("GUI::MOTOR_PERIOD_CHANGED::{}".format(float_value), flush=True)
    except ValueError:
        return False
    return True

def on_motor_period_entered (event):
    motor_period_changed(root)
    root.focus()
    return "break"

def sync_mode_changed():
    is_async = syncMode.get()
    mode_str = "asynchronous" if is_async else "synchronous"
    print("GUI::SYNC_MODE_CHANGED::{}".format(mode_str), flush=True)
    
    if is_async:
        # Mode async : afficher period et phase (en secondes)
        labelMotorPeriod.config(state="normal")
        entryMotorPeriod.config(state="normal")
        labelMotorPhaseSeconds.config(state="normal")
        entryMotorPhaseSeconds.config(state="normal")
        # Masquer phase en %
        labelMotorPhasePercent.config(state="disabled")
        entryMotorPhasePercent.config(state="disabled")
    else:
        # Mode sync : afficher seulement phase delay en %
        labelMotorPeriod.config(state="disabled")
        entryMotorPeriod.config(state="disabled")
        labelMotorPhasePercent.config(state="normal")
        entryMotorPhasePercent.config(state="normal")
        # Masquer phase en secondes
        labelMotorPhaseSeconds.config(state="disabled")
        entryMotorPhaseSeconds.config(state="disabled")

def on_input_received(file, mask):
    data = file.readline()
    if data.startswith ("APP::"):
        match data.strip():
            case "APP::BT_CONNECTED":
                flash_color (buttonCnx, 0, stop=True)
                buttonCnx.config (state="disabled")
                buttonCnx.config (disabledforeground="gray")
                buttonCnx.config (text="Connected")
                buttonResetAngles.config (state="normal")
                buttonStartLog.config (state="normal")
                labelPendulumPeriod.config (state="normal")
                labelMotion.config (state="normal")
                buttonStartMotor.config (state="normal")
                labelAmplitude.config (state="normal")
                entryAmplitude.config (state="normal")
                checkSyncMode.config(state="normal")
                # Mode sync par défaut : afficher phase en %
                labelMotorPeriod.config (state="disabled")
                entryMotorPeriod.config (state="disabled")
                labelMotorPhasePercent.config (state="normal")
                entryMotorPhasePercent.config (state="normal")
                labelMotorPhaseSeconds.config (state="disabled")
                entryMotorPhaseSeconds.config (state="disabled")
            case "APP::BT_DISCONNECTED":
                flash_color (buttonCnx, 0, stop=True)
                buttonCnx.config (state="normal")
                buttonCnx.config (text="Connect")
                buttonCnx.config (foreground="black")
                buttonStartLog.config (state="disabled")
                buttonResetAngles.config (state="disabled")
                labelMotion.config (text="disabled")
                labelMotionValue.config (text="disabled")
                labelPendulumPeriod.config (state="disabled")
                labelPendulumPeriodValue.config (state="disabled")
            case _:
                if data.strip().startswith ("APP::DEVICE_LIST::"):
                    # Parse device list and show selector dialog
                    device_list_str = data.strip().split("::")[2]
                    devices = []
                    for item in device_list_str.split(";"):
                        parts = item.split(",", 1)
                        if len(parts) == 2:
                            devices.append((parts[0], parts[1]))
                    show_device_selector(devices)
                elif data.strip().startswith ("APP::MOTION_STATE_UPDATE::"):
                    state_value = data.strip().split ("::")[2]
                    labelMotionValue.config (text=state_value)
                elif data.strip().startswith ("APP::LOG_FILE_NAME::"):
                    log_file_name = data.strip().split ("::")[2]
                    labelLogFile.config (text="Logging to: {}".format(log_file_name))
                elif data.strip().startswith ("APP::PERIOD_UPDATE::"):
                    period_value = data.strip().split ("::")[2]
                    labelPendulumPeriodValue.config (text=period_value)
                else:
                    print ("GUI::unknown_message:", data.strip())

                       
if __name__ == '__main__':
    if os.environ.get('DISPLAY','') == '':
        os.environ.__setitem__('DISPLAY', ':0')
    root = tk.Tk()
    root.title ("Botabench")

    cnxFrame = tk.Frame (root, pady=20)
    logFrame = tk.Frame (root, relief = "groove" , bd = 2 , bg = "Aqua", pady=20)
    motorFrame = tk.Frame (root, pady=20)
    statusFrame = tk.Frame (root, relief = "groove" , bd = 2 , bg = "Aqua", pady=20)

    motorAmplitude = tk.IntVar (value=90)
    motorPeriod = tk.IntVar (value=2)
    motorPhasePercent = tk.IntVar (value=0)
    motorPhaseSeconds = tk.DoubleVar (value=0)
    syncMode = tk.BooleanVar(value=False)

    cnxFrame.rowconfigure (0, weight=1)
    cnxFrame.columnconfigure (0, weight=1)
    cnxFrame.columnconfigure (1, weight=1)
    logFrame.rowconfigure (0, weight=1)
    logFrame.columnconfigure (0, weight=1)
    logFrame.columnconfigure (1, weight=3)
    motorFrame.rowconfigure (0, weight=1)
    motorFrame.rowconfigure (1, weight=1)
    motorFrame.rowconfigure (2, weight=1)
    motorFrame.columnconfigure (0, weight=1)
    motorFrame.columnconfigure (1, weight=3)
    motorFrame.columnconfigure (2, weight=1)
    statusFrame.rowconfigure (0, weight=1)
    statusFrame.columnconfigure (0, weight=1)
    statusFrame.columnconfigure (1, weight=1)
    statusFrame.columnconfigure (2, weight=1)
    statusFrame.columnconfigure (3, weight=1)

    btIcon = tk.PhotoImage (file="bluetooth_icon.png")
    btIcon = btIcon.subsample(2, 2)
    buttonCnx = tk.Button (cnxFrame, text="Connect", width=240, compound=tk.LEFT, foreground=flash_colors[0], image=btIcon, font=("Arial", 24), command=lambda : connect_requested(root))
    buttonResetAngles = tk.Button (cnxFrame, text="Reset angles", width=14, state="disabled", foreground="black", font=("Arial", 24), command=lambda : reset_angles_requested(root))
    buttonStartLog = tk.Button (logFrame, text="Start logging", width=14, foreground="black", state="disabled", font=("Arial", 24), command=lambda : start_log_requested(root))
    labelLogFile = tk.Label (logFrame, text="Logging to: None", anchor='e', state="disabled", bg = "Aqua", font=("Arial", 24))
    buttonStartMotor = tk.Button (motorFrame, text="Start motor", width=14, foreground="black", state="disabled", font=("Arial", 24), command=lambda : start_motor_requested(root))
    labelAmplitude = tk.Label (motorFrame, text="Amplitude (°)", state="disabled", font=("Arial", 24))
    entryAmplitude = tk.Entry (motorFrame, textvariable=motorAmplitude, width=10, state="disabled", font=("Arial", 24))
    entryAmplitude.config (validate="focusout", validatecommand=lambda: motor_amplitude_changed(root))
    entryAmplitude.bind("<Return>", on_motor_amplitude_entered)
    separator = ttk.Separator(motorFrame, orient='horizontal')
    checkSyncMode = tk.Checkbutton(motorFrame, text="Asynchronous mode", variable=syncMode, state="disabled", font=("Arial", 24), command=sync_mode_changed)
    labelMotorPeriod = tk.Label (motorFrame, text="Period (s)", state="disabled", font=("Arial", 24))
    entryMotorPeriod = tk.Entry (motorFrame, textvariable=motorPeriod, width=10, state="disabled", font=("Arial", 24))
    entryMotorPeriod.bind("<Return>", on_motor_period_entered)
    entryMotorPeriod.config (validate="focusout", validatecommand=lambda: motor_period_changed(root))
    labelMotorPhasePercent = tk.Label (motorFrame, text="Phase delay (%)", state="disabled", font=("Arial", 24))
    entryMotorPhasePercent = tk.Entry (motorFrame, textvariable=motorPhasePercent, width=10, state="disabled", font=("Arial", 24))
    entryMotorPhasePercent.bind("<Return>", on_motor_phase_percent_entered)
    entryMotorPhasePercent.config (validate="focusout", validatecommand=lambda: motor_phase_percent_changed(root))
    labelMotorPhaseSeconds = tk.Label (motorFrame, text="Phase (s)", state="disabled", font=("Arial", 24))
    entryMotorPhaseSeconds = tk.Entry (motorFrame, textvariable=motorPhaseSeconds, width=10, state="disabled", font=("Arial", 24))
    entryMotorPhaseSeconds.bind("<Return>", on_motor_phase_seconds_entered)
    entryMotorPhaseSeconds.config (validate="focusout", validatecommand=lambda: motor_phase_seconds_changed(root))
    labelPendulumPeriod = tk.Label (statusFrame, text="Period (s)", state="disabled", bg = "Aqua", font=("Arial", 24))
    labelPendulumPeriodValue = tk.Label (statusFrame, text="", state="disabled", width=8, relief=tk.SUNKEN, bd=1, font=("Arial", 24))
    labelMotion = tk.Label (statusFrame, text="Motion", state="disabled", bg = "Aqua", font=("Arial", 24))
    labelMotionValue = tk.Label (statusFrame, text="", state="disabled", width=8, relief=tk.SUNKEN, bd=1, font=("Arial", 24))
    root.createfilehandler (sys.stdin, tk.READABLE, on_input_received)

    buttonCnx.grid (row=0, column=0, padx=(20, 30), sticky="w")
    buttonResetAngles.grid (row=0, column=1, padx=(0, 20), sticky="e")
    buttonStartLog.grid(row=0, column=0, padx=(20, 10), sticky="w")
    labelLogFile.grid(row=0, column=1, padx=(0, 20), sticky="e")
    buttonStartMotor.grid(row=0, column=0, padx=(20, 40), sticky="w")
    labelAmplitude.grid(row=0, column=1, padx=(0, 10), sticky="e")
    entryAmplitude.grid(row=0, column=2, padx=(0, 20), sticky="e")
    separator.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 10))
    checkSyncMode.grid(row=2, column=0, columnspan=3, sticky="w", padx=(20, 0))
    labelMotorPeriod.grid(row=3, column=0, padx=(0, 10), sticky="e")
    entryMotorPeriod.grid(row=3, column=1, padx=(0, 20), sticky="e")
    labelMotorPhasePercent.grid(row=4, column=0, padx=(0, 10), sticky="e")
    entryMotorPhasePercent.grid(row=4, column=1, padx=(0, 20), sticky="e")
    labelMotorPhaseSeconds.grid(row=5, column=0, padx=(0, 10), sticky="e")
    entryMotorPhaseSeconds.grid(row=5, column=1, padx=(0, 20), sticky="e")
    labelPendulumPeriod.grid(row=0, column=0, padx=(20, 10), sticky="w")
    labelPendulumPeriodValue.grid(row=0, column=1, padx=(0, 100), sticky="w")
    labelMotion.grid(row=0, column=2, padx=(0, 10), sticky="e")
    labelMotionValue.grid(row=0, column=3, padx=(0, 20), sticky="e")
 
    cnxFrame.pack (fill='x')
    logFrame.pack (fill='x')
    motorFrame.pack (fill='x')
    statusFrame.pack (fill='x')

root.mainloop ()