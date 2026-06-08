# Botafumeiro Measurement Bench - Parametric Excitation of a Pendulum

[![en](https://img.shields.io/badge/English-en-blue.svg?logo=thestorygraph)](README-en.md)
[![fr](https://img.shields.io/badge/Français-fr-green.svg?logo=thestorygraph)](README.md)

## <span style="color:orange"> Table of Contents </span>

1. [Overview](#-overview-)
2. [Theoretical Foundations](#-theoretical-foundations-)
3. [Bench Architecture](#-bench-architecture-)
4. [Hardware Components](#-hardware-components-)
5. [Mechanical Geometry](#-mechanical-geometry-)
6. [System Latency Calibration](#-system-latency-calibration-)
7. [Quick Start](#-quick-start-)
8. [Control System](#-control-system-)
9. [Data Acquisition](#-data-acquisition-)
10. [Experimental Protocols](#-experimental-protocols-)
11. [Results and Validation](#-results-and-validation-)

---

## <span style="color:orange"> Overview </span>

This measurement bench is designed to study the **parametric resonance** of a pendulum by modulating its length periodically, inspired by the physical phenomenon of the *Botafumeiro* of the Cathedral of Santiago de Compostela. The objectives are:

- ✅ Experimentally validate **Floquet-Mathieu** theory for parametric oscillators
- ✅ Determine the **optimal parameters** (pumping frequency and phase) to maximize oscillation amplitude
- ✅ Compare **numerical predictions** and **experimental results**

The system includes:

- ✅ **Software architecture**: GUI, asyncio controller, Bluetooth management, measurement logging
- ✅ **Sensors**: 6-axis IMU and PMU (Power Measurement Unit for measuring motor current, voltage and power)
- ✅ **Pseudo real-time control**: IMU/Motor synchronization

---

## <span style="color:orange"> Theoretical Foundations </span>

### <span style="color:#229DD4"> Mathieu Equation </span>

The system is described by the **complete Mathieu equation**:

$$\ddot{\theta} + 2a \omega_f \cos(\omega_f t) \dot{\theta} + \omega_0^2[1 - A \sin(\omega_f t)]\theta = 0$$

Where:

- **θ**: angle of oscillation of the pendulum
- **ω₀**: natural frequency of the free pendulum
- **ωf**: frequency of modulation (pumping)
- **A**: amplitude of length modulation (A ≈ 0.1)
- **a**: parametric damping coefficient

### <span style="color:#229DD4"> Primary Parametric Resonance </span>

**Floquet** theory predicts instability bands (exponential amplification) at frequencies:

$$\omega_f = \frac{2\omega_0}{n} \quad (n = 1, 2, 3, \ldots)$$

**The primary band (n=1)** at **ωf = 2ω₀** is the most efficient for energy transfer to the pendulum.

### <span style="color:#229DD4"> Mathieu equation solution search </span>

#### <span style="color:#A02B93"> Simplification of Mathieu equation </span>

A being very small (A ≈ 0,1 &rarr; A<sup>2</sup> ≈ 0,01), neglecting the $\dot{\theta}$ term, the equation reduces to :

$$\ddot{\theta} + \omega_0^2[1 - A \sin(\omega_f t)]\theta = 0$$

According to Floquet's theorem, we look for solutions of the form e<sup>(μt)</sup>.p(t) where p(t) is a periodic function of the same period T as the coefficients.

#### <span style="color:#A02B93"> Digital analysis </span>

The digital resolution of the simplified equation yields the instability diagram (Ince-Strutt diagram) :

1. **Digital integration** (scipy.integrate.odeint / LSODA) of the Floquet transition matrix
2. **Construction of the transition matrix** over a complete period T
3. **Computation of eigenvalues** (Floquet multipliers)
4. **Extraction of the characteristic exponent μ** determining growth/decay

The numerical resolution is carried out using the script [digital_ince_strutt.py](doc/theory/scripts/digital_ince_strutt.py) and yields the following instability diagram (Ince-Strutt):

![Stability diagram (Ince-Strutt - Numerical method)](doc/theory/digital_ince_strutt_stability_diagram.png)

#### <span style="color:#A02B93"> Analytical analysis </span>

Alternatively, one can use an analytical approximation that allows a rapid 
**qualitative** verification, at the cost of precision and actual quantification of µ. 
The analytical approximation of the instability bands is obtained by locating the 
parametric resonances predicted by Floquet theory:

1. **Location of resonance bands** at frequencies ωf/ω₀ = 2/n (n = 1, 2, 3...)
2. **Approximation of each band's width** ∆(ωf) ∝ a/n (proportional to amplitude, 
   decreasing with order n)
3. **Construction of the instability domain** for each band n:

$$\left|\frac{\omega_f}{\omega_0} - \frac{2}{n}\right| < \frac{a}{2n}$$

4. **Plotting of boundaries** separating stable (µ < 0) and unstable (µ > 0) regions

The analytical resolution is carried out using the script 
[analytical_ince_strutt.py](doc/theory/scripts/analytical_ince_strutt.py) 
and yields the following instability diagram (Ince-Strutt):

![Stability diagram (Ince-Strutt - Analytical method)](doc/theory/analytical_ince_strutt_stability_diagram.png)

![Stability diagram (Ince-Strutt - Analytical method - Detail)](doc/theory/analytical_ince_strutt_stability_diagram_detail.png)

---

## <span style="color:orange"> Bench Architecture </span>

The bench has the following architecture (see bill of materials for details)

![Botafumeiro System Overview](doc/system/system_overview.png)

1. Massive bob (0.290 kg)
2. Massless inelastic wire
3. Double pulley
4. Servomotor (0° → 180°)
5. Lever (4.5 cm)
6. Power Measurement Unit (PMU): I<sub>motor</sub>, V<sub>motor</sub>, P<sub>motor</sub>
7. Inertial Measurement Unit (IMU) 6-axis to measure the angle of the bob relative to vertical and its angular velocity
8. Raspberry PI4 (LINUX):
   - Real-time IMU data acquisition over Bluetooth link
   - Peak detection of pendulum oscillations
   - PWM-based servomotor angle command
   - GUI
9. Bidirectional Bluetooth link
10. HDMI display
11. Power Supply (0-12V/6A regulated)

### <span style="color:#229DD4"> Software Architecture </span>

#### <span style="color:#A02B93"> Modules and functions </span>

```
┌──────────────────────────────────────────────────────┐
│        USER INTERFACE LAYER (Tkinter GUI)            │
│  ┌────────────────────────────────────────────────┐  │
│  │  gui_app.py                                    │  │
│  │  ├─ Device Pairing and Configuration           │  │
│  │  ├─ Motor Amplitude (slider 0-180°)            │  │
│  │  ├─ Asynchronous Mode Tab                      │  │
│  │  │  └─ Phase Controls                          │  │
│  │  ├─ Synchronous Mode Tab                       │  │
│  │  │  ├─ Motor Period Controls                   │  │
│  │  │  └─ Phase Controls                          │  │
│  │  ├─ Real-time Period Display                   │  │
│  │  └─ Data Recording and Export (CSV)            │  │
│  └────────────────────────────────────────────────┘  │
│  Support Modules:                                    │
│  • gui_dialogs.py - ListBoxSelect, AlarmBox          │
│  • bluetooth_icon.png - UI Resources                 │
└──────────────┬───────────────────────────────────────┘
               │ IPC: stdin/stdout
┌──────────────▼───────────────────────────────────────┐
│      CONTROL LAYER (Python asyncio)                  │
│  ┌────────────────────────────────────────────────┐  │
│  │  app.py - Main Controller                      │  │
│  │  ├─ MotorController Class                      │  │
│  │  │  ├─ Manual Mode (direct angle command)      │  │
│  │  │  ├─ Asynchronous Mode (square wave, strict) │  │
│  │  │  ├─ Absolute Time Synchronization (±5ms)    │  │
│  │  │  └─ Power Monitoring Integration            │  │
│  │  ├─ IMUReader Class                            │  │
│  │  │  └─ Bluetooth UART Stream Processing 100 Hz │  │
│  │  ├─ CurrentMonitor Class (PMU/INA219)          │  │
│  │  │  ├─ Voltage/Current/Power Acquisition       │  │
│  │  │  └─ Servo Health Diagnostics                │  │
│  │  ├─ DataLogger Class                           │  │
│  │  │  └─ CSV Logging (timestamp+sensors)         │  │
│  │  ├─ Error Handling and Recovery                │  │
│  │  └─ Event Loop Management                      │  │
│  └────────────────────────────────────────────────┘  │
└──────────┬────────────────┬──────────────────────────┘
           │                │
    ┌──────▼────────┐  ┌────▼────────────────────────┐
    │  MOTOR LAYER  │  │  SENSOR LAYER               │
    ├───────────────┤  ├─────────────────────────────┤
    │ servomotor.py │  │ device_model.py             │
    │ ├─ Servomotor │  │ ├─ IMU Data Processing      │
    │ │  Class      │  │ ├─ BWT901CL Protocol        │
    │ │             │  │ ├─ Bluetooth Callbacks      │
    │ └─ PWM Control│  │ └─ Angle/Velocity Analysis  │
    │   (GPIO 18)   │  │                             │
    │               │  │ bluetooth_host_controller.py│
    │ app.py        │  │ ├─ Device Scanning          │
    │ └─ Current    │  │ ├─ Device Pairing           │
    │   Monitor     │  │ └─ Bluetooth Management     │
    │   (I2C)       │  │                             │
    └───────┬───────┘  └──────────┬──────────────────┘
            │                     │
    ┌───────▼─────────────────────▼─────────────────┐
    │         HARDWARE LAYER                        │
    ├───────────────────────────────────────────────┤
    │  • Servomotor MG996R (GPIO 18 PWM)            │
    │  • IMU BWT901CL (Bluetooth UART 115200 baud)  │
    │  • PMU INA219 (I2C address 0x40)              │
    │  • Raspberry Pi 4 (asyncio + pigpio)          │
    └───────────────────────────────────────────────┘
```

#### <span style="color:#A02B93"> Architecture multi-threads </span>

The multithreading structure is furthermore described in the document [Multithreading Architecture and Synchronization - Botafumeiro Bench](doc/system/README_SW_threads-en.md)

---

## <span style="color:orange"> Hardware Components </span>

### <span style="color:#229DD4"> Motor and Control </span>

| Component | Model | Specifications |
|-----------|-------|-----------------|
| **Servomotor** | MG996R | 6V, 13 kg·cm torque, speed: ~0.23s/60° |
| **Power Supply** | Lab | 0-12V max 6A (PWM) |
| **Control Signal** | GPIO 18 (Raspberry) | PWM frequency: variable (0.5-2.5 ms for 0-180°) |

### <span style="color:#229DD4"> Sensors </span>

| Sensor | Model | Measurement |
|--------|-------|-------------|
| **9-DOF IMU** | BWT901CL | Angle θ (±180°), angular velocity ω̇, acceleration |
| **Communication** | Bluetooth | 115200 baud, update rate 50 Hz |
| **PMU** | INA219 | Voltage, Current and Power of the servomotor |
| **Communication** | Bluetooth | 115200 baud, update rate 50 Hz |

### <span style="color:#229DD4"> Controller </span>

| Component | Specifications |
|-----------|-----------------|
| **Processor** | Raspberry Pi 4 (ARM Cortex-A72, 1.5 GHz) |
| **RAM** | 4 GB (min 2 GB) |
| **Operating System** | Raspberry Pi OS debian 13 (Python 3.9+) |
| **Core Libraries** | `gpiozero`, `asyncio`, `scipy`, `pigpio` |
| **Sensor Libraries** | `adafruit-circuitpython-ina219` |

### <span style="color:#229DD4"> Power Supply and Safety </span>

- **Power Supply 0-12V**: laboratory (regulated)
- **Fuse**: 10A protection

---

## <span style="color:orange"> Mechanical Geometry </span>

### <span style="color:#229DD4"> Motor Lever Arm </span>

- **Length**: d = 4.5 cm (measured from rotation axis)
- **Rotation angle**: β ∈ [0°, 180°]
- **Neutral position**: β = 0° (arm horizontal to the left)

### <span style="color:#229DD4"> Pulley-Rope System </span>

**Geometry:**

- Arm axis: O = (0, 0)
- Fixed pulley: P = (D, 0) with D = 3 m
- Arm endpoint: A(β) = (-d·cos(β), d·sin(β))

**Rope Length between motor axis and pulley:**

$$L(\beta) = \sqrt{D^2 + d^2 + 2Dd \cos(\beta)}$$

**Extension from initial position (β = 0):**

$$\Delta L(\beta) = \sqrt{D^2 + d^2 + 2Dd \cos(\beta)} - (D + d)$$

**Approximation for small β:**

$$\Delta L(\beta) \approx -\frac{Dd \beta^2}{2(D+d)}$$

*Note:* The rope **shortens** when β increases, which lifts the pendulum.

### <span style="color:#229DD4"> Simple Pendulum </span>

- **Length**: L = 1.175 m for β=0° ↔ L = 1.270 m for β=180°
- **Mass (Bob)**: m ≈ 0.290 kg
- **Natural frequency**: ω₀ = √(g/L) ≈ √(9.81/1.2) ≈ 2.86 rad/s ≈ 0.45 Hz
- **Natural period**: T₀ = 2π/ω₀ ≈ 2.20 s

---

## <span style="color:orange"> System Latency Calibration </span>

### <span style="color:#229DD4"> Overview </span>

The **latency** of the measurement bench is a critical parameter for parametric excitation experiments. It represents the time delay between the detection of θ = 0 (pendulum at lowest point) and the actual activation of the servomotor. This latency directly affects phase synchronization and explains the observed 5% offset between theoretical and experimental optimal phases.

## <span style="color:orange"> Latency Breakdown </span>

The total system latency is the sum of four sequential components:

1. **IMU Sensor Sampling and Processing** (~20-30 ms)
   - BWT901CL samples at 100 Hz (10 ms period)
   - Angle calculation and frame assembly (0x55 protocol)

2. **Bluetooth Transmission** (~20-40 ms)
   - UART to Bluetooth conversion
   - Transmission over Bluetooth UART link (115200 baud)

3. **Raspberry Pi Reception and Angle Detection** (~20-30 ms)
   - Frame reception and CRC validation
   - Zero-crossing detection algorithm
   - GPIO command preparation

4. **Motor Actuation** (~10-20 ms)
   - PWM signal propagation to servo
   - Servo electronic response time

### <span style="color:#229DD4"> Latency mesaurement </span>

The system latency has been estimated according to the methodology that is described in the document [System Latency Calibration](doc/system/README_system_latency-en.md).

#### <span style="color:#A02B93"> Measured Latency </span>

| Measurement | Value | Note |
|-------------|-------|------|
| **Primary latency** | 100 ms | Between θ = 0 detection and first motor movement |
| **Measurement uncertainty** | ±33 ms | One frame period at 30 fps |
| **Confidence interval** | 67-133 ms | ±1 frame (1σ) |

#### <span style="color:#A02B93"> Implication on Phase </span>

   - he motor receives commands with ~100 ms delay after the pendulum reaches θ = 0
   - This causes the effective excitation phase to shift by approximately 5% relative to the ideal theoretical phase
   - For optimal energy transfer, the control algorithm compensates by advancing the phase command

---

## <span style="color:orange"> Quick Start </span>

```bash
# 1. Clone and setup
git clone <repository>
cd botafumeiro

# 2. Install dependencies
pip install gpiozero pigpio scipy numpy matplotlib adafruit-circuitpython-ina219 paho-mqtt

# 3. Start daemon
sudo pigpiod

# 4. Run application
python3 app.py &           # Start asyncio controller

# 5. Access GUI
# → Manual control, asynchronous mode, real-time monitoring
```

---

## <span style="color:orange"> Control System </span>

### <span style="color:#229DD4"> Control GUI </span>

![Graphical User Interface](doc/system/main_gui.png)

### <span style="color:#229DD4"> Operating Modes </span>

#### <span style="color:#A02B93"> Asynchronous Mode </span>

- Periodic oscillation of the arm with rectangular waveform independent from pendulum oscillations
- **Motor amplitude**: β_max (adjustable from 0° to 180°)
- **Period**: T = 2π/ωf (adjustable from 1s)
- **Initial Phase**: φ (adjustable, delay before start)

#### <span style="color:#A02B93"> Synchronous Mode </span>

- Periodic oscillation of the arm with rectangular waveform synchronized with pendulum oscillations
- **Motor amplitude**: β_max (adjustable from 0° to 180°)
- **Period**: non adjustable. Set to half motor period by setting β to 0 when pendulum is at lowest and β to β_max when pendulum reaches highest point
- **Phase**: φ (adjustable, delay after pendulum reaches key positions)

### <span style="color:#229DD4"> Real-time Synchronization Algorithm </span>

**Objective:** Maintain **strictly regular** timing despite system latencies

**Approach:** Synchronization on **absolute time** rather than cumulative delays

```python
cycle_start_time = time.time()

while running:
    # Calculate position in cycle (modulo period)
    time_in_cycle = (time.time() - cycle_start_time) % period
    
    # First half: amplitude
    if time_in_cycle < period / 2:
        set_position(amplitude)
    # Second half: zero
    else:
        set_position(0)
    
    # Calculate next phase change
    next_phase_time = cycle_start_time + (phase_index + 1) * (period / 2)
    sleep_time = next_phase_time - time.time()
    
    # Wait until next change
    await asyncio.sleep(sleep_time)
```

**Outcomes:**

- ✅ Immune to asyncio latencies
- ✅ Regular rectangular waves (T/2, T/2) with ±5 ms precision
- ✅ No accumulation of temporal errors

### <span style="color:#229DD4"> Software Architecture </span>

```
GUI (Tkinter)
    │
    ├─► Communicates via stdin/stdout
    │
APP (Python asyncio)
    │
    ├─► MotorController
    │   ├─ Synchronous mode
    │   └─ Asynchronous mode
    │
    ├─► IMUReader
    │   └─ Bluetooth UART (100 Hz)
    │
    └─► DataLogger
        └─ CSV (timestamp, angle, amplitude, phase)
```

---

## <span style="color:orange"> Data Acquisition </span>

### <span style="color:#229DD4"> IMU Configuration </span>

**BWT901CL Sensor**:

- **Bandwidth**: 256 Hz (can be reduced to 32 Hz)
- **Sample rate**: 100 Hz fixed (10 ms updates)
- **Frame format**: 11 bytes, 0x55 protocol (header)
- **Precision**: ±0.5° angle, ±0.5°/s velocity

**Minimum 32 Hz bandwidth**:

- Pendulum natural frequency: 0.45 Hz
- Parametric excitation harmonics: up to ~5-10 Hz
- Nyquist limit (100 Hz sampling): 50 Hz max
- 20-32 Hz captures all dynamics without noise → **OPTIMAL** ✅

**Acquired Data:**

- θ: pendulum oscillation angle (degrees)
- ω̇: angular velocity (°/s)
- accel: acceleration (m/s²)

### <span style="color:#229DD4"> PMU (INA219) Configuration </span>

**Power Measurement**:

- **Shunt resistance**: 0.1 Ω (default)
- **Current range**: ±3.2 A
- **Voltage range**: 0-26 V
- **Precision**: ±0.8% voltage, ±0.2% current
- **Update rate**: 100-200 Hz (recommended)

**Diagnostic Thresholds** (MG996R):

| Parameter | Normal | Alert | Critical |
|-----------|--------|-------|----------|
| Voltage | 5.5-6.5V | <5.5V | <4.5V |
| Current | 0-1000mA | 1000-2500mA | >3000mA |
| Power | 0-6W | 6-15W | >15W |

### <span style="color:#229DD4"> CSV Logging </span>

**Log files names**:

Log files are named after the current date and are created in the logs directory
```
logs/log_20260604_154424.csv
```

**Format**:

```
time,AccX,AccY,AccZ,AsX,AsY,AsZ,AngleX,AngleY,AngleZ,vMotor,iMotor,pMotor
2026-05-17 22:50:56:224,0.053,-0.009,-0.924,-6.104,22.888,14.282,6.18,-23.99,3.88,6.612,909.400,7.684
```

**Frequency**: 50 Hz (synchronized with IMU)

**Post-processing**:

- Envelope analysis (peak detection)
- FFT (frequency content)
- Exponential decay fitting (Floquet exponent μ)

---

## <span style="color:orange"> Experimental Protocols </span>

⚠️ **WARNING! Prior starting each measurement** ⚠️

- Lock the pendulum in vertical position. Make sure it is still.
- Press **Reset Angles** to reset the IMU (drift risk)

### <span style="color:#229DD4"> Protocol 1: Primary Resonance Validation </span>

**Objective:** Confirm that ωf = 2ω₀ is the optimal frequency

**Procedure:**

1. Fix arm amplitude: β_max = 45°
2. Fix phase: φ = 0° (synchronous)
3. Vary frequency: ωf/ω₀ ∈ [1, 3] in steps of 0.1
4. For each frequency, measure amplitude growth after N cycles
5. Build amplification rate curve vs ωf/ω₀

**Expected Result:** Amplification peak at ωf/ω₀ = 2

### <span style="color:#229DD4"> Protocol 2: Phase Optimization </span>

**Objective:** Find optimal phase φ to maximize growth

**Procedure:**

1. Fix ωf = 2ω₀ (primary frequency)
2. Fix amplitude: β_max = 45°
3. Vary phase: φ ∈ [0°, 360°] in steps of 15°
4. Measure amplitude growth for each phase after N cycles

**Expected Result:** Amplification peak around φ ≈ 90-95°

### <span style="color:#229DD4"> Protocol 3: Theory vs Experiment Comparison </span>

**Objective:** Validate numerical Floquet diagram predictions

**Procedure:**

1. For different combinations (ωf, β_max), measure experimental amplification rate μ_exp
2. Compare to theoretical μ_theo from calculated Floquet diagram
3. Analyze discrepancies (measurement errors, imperfect model, etc.)

---

## <span style="color:orange"> Results and Validation </span>

### <span style="color:#229DD4"> Typical Experimental Results </span>

#### <span style="color:#A02B93"> Amplification Rate vs Frequency </span>

**Observation:** Clear primary band at ωf/ω₀ = 2

```
Amplification (dB/cycle)
        ▲
      5 │        ╱╲
        │      ╱    ╲
      0 │────╱────────╲──────
        │   ╱ ωf/ω₀=2  ╲
     -5 │                
        └─────────────────► ωf/ω₀
         0    1    2    3
```

#### <span style="color:#A02B93"> Phase Optimization </span>

**Observation:** Optimal phase φ_opt ≈ 95°

- Maximum growth: +2.12% per cycle
- Effective phase range: ±30° around optimum

**Amplification rate of pendulum oscillations versus motor excitation phase**

![Influence of Phase on Resonance](doc/experiments/pumping_phase_analysis.png)

### <span style="color:#229DD4"> Numerical vs Experimental Comparison </span>

| Parameter | Theoretical | Experimental | Discrepancy |
|-----------|-----------|--------------|-------------|
| ωf/ω₀ (primary) | 2.00 | 2.00 | ✓ |
| Optimal phase | ~90° | 95° | ±5° |
| μ max (for A=0.1) | 0.18 s⁻¹ | 0.17 s⁻¹ | ~6% |

**The 5% offset between theoretical and experimental phase corresponds to ~110 ms**
**This corresponds to the measured latency between the actual pendulum position and the start of motor actuation.**

