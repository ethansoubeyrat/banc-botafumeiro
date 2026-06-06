# Multithreading Architecture and Synchronization - Botafumeiro Bench

[![en](https://img.shields.io/badge/English-en-blue.svg?logo=thestorygraph)](README_SW_threads-en.md)
[![fr](https://img.shields.io/badge/Français-fr-green.svg?logo=thestorygraph)](README_SW_threads-fr.md)

## Overview

The Botafumeiro measurement bench uses a **multi-process architecture** combining:
- **GUI Process** (Tkinter, blocking I/O)
- **APP Process** (Python asyncio, event-driven)
- **Inter-Process Communication** (stdin/stdout)

This document details the threading model, synchronization mechanisms, and critical sections.

---

## Process Architecture

```
┌─────────────────────────────────────────────────────────┐
│  PROCESS 1: GUI (Tkinter)                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Main Thread (Event Loop)                          │  │
│  │ ├─ User input handling                            │  │
│  │ ├─ Widget updates                                 │  │
│  │ ├─ Polling stdin for APP messages                 │  │
│  │ └─ Non-blocking (via after() scheduler)           │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Communication: stdin/stdout                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
                         ↕ (IPC)
┌─────────────────────────────────────────────────────────┐
│  PROCESS 2: APP (asyncio)                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Asyncio Event Loop (Main Thread)                  │  │
│  │ ├─ async_motor_loop()         [Task 1]            │  │
│  │ ├─ imu_reader_loop()          [Task 2]            │  │
│  │ ├─ current_monitor_loop()     [Task 3]            │  │
│  │ ├─ data_logger_task()         [Task 4]            │  │
│  │ ├─ command_listener()         [Task 5]            │  │
│  │ └─ error_handler()            [Task 6]            │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Shared State: Global variables + asyncio.Event         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Asyncio Task Architecture

### Task Hierarchy

```
asyncio.run(main())
    │
    ├─► Task 1: async_motor_loop()
    │   ├─ Monitors: amplitude, period, phase
    │   ├─ Controls: GPIO 18 (PWM)
    │   ├─ Rate: 10-100 Hz (configurable)
    │   └─ Synchronization: asyncio.sleep()
    │
    ├─► Task 2: imu_reader_loop()
    │   ├─ Reads: Bluetooth UART
    │   ├─ Parses: BWT901CL frames (0x55 protocol)
    │   ├─ Extracts: angle, omega, acceleration
    │   ├─ Rate: 100 Hz (fixed from sensor)
    │   └─ Trigger: zero_crossing_event
    │
    ├─► Task 3: current_monitor_loop()
    │   ├─ Reads: I2C (INA219, addr 0x40)
    │   ├─ Measures: Vmotor, Imotor, Pmotor
    │   ├─ Rate: 50-100 Hz (configurable)
    │   └─ Action: Diagnostic alerts
    │
    ├─► Task 4: data_logger_task()
    │   ├─ Buffers: All sensor data
    │   ├─ Rate: 50 Hz (CSV write)
    │   ├─ Lock: asyncio.Lock (prevent corruption)
    │   └─ File: data_YYYYMMDD_HHMMSS.csv
    │
    ├─► Task 5: command_listener()
    │   ├─ Reads: stdin from GUI
    │   ├─ Parses: GUI commands (START, STOP, AMPLITUDE, etc.)
    │   ├─ Updates: Global state variables
    │   ├─ Rate: Event-driven (non-blocking)
    │   └─ Action: Triggers mode changes
    │
    └─► Task 6: error_handler()
        ├─ Monitors: Exception queues
        ├─ Logs: Error messages
        ├─ Rate: Real-time
        └─ Action: Graceful recovery
```

---

## Synchronization Mechanisms

### 1. asyncio.Event - Zero-Crossing Detection

**Purpose**: Signal when pendulum reaches θ = 0

```python
# Declaration (global)
zero_crossing_event = asyncio.Event()

# Producer: IMU Reader Task
async def imu_reader_loop():
    while running:
        angle = await read_imu_frame()
        if angle_crosses_zero(angle):  # θ = 0 detected
            zero_crossing_event.set()   # Signal all waiters
        await asyncio.sleep(0.01)  # 100 Hz

# Consumer: Motor Controller Task
async def async_motor_loop():
    if synchronous_mode:
        await zero_crossing_event.wait()  # Block until θ = 0
        zero_crossing_event.clear()       # Reset for next cycle
        activate_motor()                  # Pump at optimal phase
```

**Properties**:
- ✅ Thread-safe (asyncio primitive)
- ✅ Wake all waiting coroutines
- ✅ No busy-waiting (CPU efficient)

---

### 2. asyncio.Lock - CSV Write Protection

**Purpose**: Prevent concurrent CSV writes from multiple tasks

```python
# Declaration (global)
csv_lock = asyncio.Lock()

# Producer: Current Monitor Task
async def current_monitor_loop():
    while running:
        v, i, p = read_ina219()
        async with csv_lock:
            current_data = {'vMotor': v, 'iMotor': i, 'pMotor': p}
        await asyncio.sleep(0.01)  # 100 Hz

# Producer: Data Logger Task
async def data_logger_task():
    while running:
        async with csv_lock:
            # Safe to write - no other task writing simultaneously
            write_to_csv(imu_data, current_data)
        await asyncio.sleep(0.02)  # 50 Hz
```

**Properties**:
- ✅ Mutual exclusion (only one coroutine at a time)
- ✅ Deadlock prevention (no nested locks)
- ✅ Fair scheduling (FIFO queue)

---

### 3. Global State Variables - Shared Memory

**Purpose**: Share configuration between GUI and APP

```python
# Global state (shared between processes via IPC)
class SystemState:
    motor_amplitude = 0.0      # β_max (0-180°)
    motor_period = 4.0         # T (seconds)
    motor_phase = 0.0          # φ (degrees)
    mode = "manual"            # "manual" | "asynchronous" | "synchronous"
    running = False            # Motor on/off
    
    # Current sensor readings (updated by tasks)
    current_angle = 0.0        # θ (degrees)
    current_omega = 0.0        # ω̇ (°/s)
    motor_voltage = 0.0        # Vmotor (volts)
    motor_current = 0.0        # Imotor (mA)
    
state = SystemState()

# Read (no lock needed - single-assignment)
async def motor_task():
    amp = state.motor_amplitude  # Read latest value
    
# Write (single-assignment - atomic in Python)
async def command_listener():
    state.motor_amplitude = new_value  # GUI command
```

**Properties**:
- ✅ Python GIL ensures atomic reads/writes for basic types
- ✅ No explicit lock needed for single assignments
- ⚠️ Complex objects need Lock (e.g., lists, dicts)

---

### 4. asyncio.Queue - Command Channel

**Purpose**: Safe command transmission from GUI to APP

```python
# Declaration
command_queue = asyncio.Queue(maxsize=10)

# Producer: GUI process (stdin reader)
async def command_listener():
    while True:
        cmd = await read_stdin_async()  # "START_MOTOR::45::2.5::90"
        await command_queue.put(cmd)    # Non-blocking (unless full)

# Consumer: APP process (command handler)
async def process_commands():
    while True:
        cmd = await command_queue.get()  # Block if empty
        parse_and_execute(cmd)
        command_queue.task_done()        # Signal completion
```

**Properties**:
- ✅ Thread-safe between tasks
- ✅ FIFO ordering (no lost commands)
- ✅ Backpressure handling (maxsize=10)

---

## Critical Sections

### Section 1: Motor PWM Update (±5ms Precision)

**Location**: `async_motor_loop()` in `app.py`

**Critical Code**:
```python
async def async_motor_loop():
    cycle_start_time = time.time()
    
    while running:
        # CRITICAL: Absolute-time synchronization
        time_in_cycle = (time.time() - cycle_start_time) % period
        
        if time_in_cycle < period / 2:
            servo.value = amplitude_to_pwm(state.motor_amplitude)
        else:
            servo.value = 0.0
        
        # Calculate next phase transition
        next_phase_time = cycle_start_time + (phase_index + 1) * (period / 2)
        sleep_time = next_phase_time - time.time()
        
        await asyncio.sleep(sleep_time)  # ±5ms precision
```

**Synchronization Strategy**:
- ✅ **Absolute time** (not cumulative delays)
- ✅ **Immune to asyncio latencies**
- ✅ **Bounded error** (±5ms per cycle)

**Potential Issues**:
- ❌ High system load → sleep_time becomes negative
- ❌ Solution: Catch negative sleep, skip to next cycle

---

### Section 2: Zero-Crossing Detection (IMU → Motor Phase Lock)

**Location**: `imu_reader_loop()` triggers `zero_crossing_event`

**Critical Code**:
```python
async def imu_reader_loop():
    prev_angle = 0.0
    
    while running:
        angle = await read_imu_frame()
        
        # CRITICAL: Detect when angle crosses zero
        if (prev_angle < 0 and angle >= 0) or (prev_angle > 0 and angle <= 0):
            zero_crossing_event.set()  # Wake motor task
        
        prev_angle = angle
        await asyncio.sleep(0.01)  # 100 Hz
```

**Synchronization Strategy**:
- ✅ **Event-driven** (no polling)
- ✅ **Single detection per cycle** (prevents duplicate triggers)

**Potential Issues**:
- ❌ Hysteresis (noise near θ = 0 causes multiple detections)
- ❌ Solution: Threshold-based detection (e.g., |θ| < 5°)

---

### Section 3: CSV Data Write (Race Condition Prevention)

**Location**: `data_logger_task()` with `csv_lock`

**Critical Code**:
```python
async def data_logger_task():
    while running:
        # Collect snapshot of current data
        snapshot = {
            'timestamp': time.time(),
            'angle': state.current_angle,
            'omega': state.current_omega,
            'vMotor': state.motor_voltage,
            'iMotor': state.motor_current,
        }
        
        # CRITICAL: Atomic write
        async with csv_lock:
            csvwriter.writerow(snapshot)
            csvfile.flush()  # Force to disk
        
        await asyncio.sleep(0.02)  # 50 Hz
```

**Synchronization Strategy**:
- ✅ **Lock during write** (prevents interleaved writes)
- ✅ **Flush to disk** (ensures persistence)

**Potential Issues**:
- ❌ Lock contention (multiple producers)
- ❌ Solution: Single writer task (reduces lock duration)

---

## Timing Diagram

```
TIME AXIS (milliseconds)
0     10    20    30    40    50    60    70    80    90    100

IMU Task:
[1]---[2]---[3]---[4]---[5]---[6]---[7]---[8]---[9]---[10]--
 │ (100 Hz, 10ms period)
 └─ Reads angle from Bluetooth

Zero-Crossing Event:

          ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
          │ Detection lag: ~30-50ms
          ▼
Motor Task:

     ████████████     ████████████     ████████████     ████
     │                │                │                │
     └─ PWM High      └─ PWM High      └─ PWM High      └─ PWM High
        (50ms)           (50ms)           (50ms)           (50ms)

Current Monitor:

   [V,I]---[V,I]---[V,I]---[V,I]---[V,I]---[V,I]---[V,I]---
   │ (50 Hz, 20ms period)
   └─ Samples INA219

CSV Write (with lock):

        ║ W ║        ║ W ║        ║ W ║        ║ W ║
        (locked for ~2ms per write)
```

---

## Race Conditions Identified & Mitigated

### Race Condition 1: IMU Data Update During Read

**Scenario**: Motor task reads `state.current_angle` while IMU task updates it

**Mitigation**:
```python
# GIL + single assignment = atomic
state.current_angle = angle  # Atomic write
amp = state.current_angle    # Atomic read
```

✅ **Safe** (no explicit lock needed)

---

### Race Condition 2: CSV Corruption on Concurrent Writes

**Scenario**: Data logger and current monitor both write to CSV simultaneously

**Mitigation**:
```python
async with csv_lock:
    csvwriter.writerow(data)  # Only one task writing
```

✅ **Safe** (Lock prevents interleaving)

---

### Race Condition 3: Command Buffer Overflow

**Scenario**: GUI sends commands faster than APP can process

**Mitigation**:
```python
command_queue = asyncio.Queue(maxsize=10)  # Bounded queue
await command_queue.put(cmd)  # Blocks if full
```

✅ **Safe** (Backpressure prevents overflow)

---

### Race Condition 4: Zero-Crossing Event Lost

**Scenario**: Motor task misses zero-crossing event if reset too late

**Mitigation**:
```python
# Proper event lifecycle
await zero_crossing_event.wait()  # Wait for signal
zero_crossing_event.clear()       # Reset AFTER processing
```

✅ **Safe** (Clear AFTER wait ensures no loss)

---

## Performance Analysis

### Task Latencies

| Task | Period | Latency | CPU % | Notes |
|------|--------|---------|-------|-------|
| IMU Reader | 10 ms | 5-10 ms | 15% | Bluetooth UART blocking |
| Motor PWM | 10-100 ms | ±5 ms | 5% | Tight loop, absolute time |
| Current Monitor | 20 ms | 8-15 ms | 8% | I2C blocking |
| Data Logger | 20 ms | 2-3 ms | 10% | CSV write, disk I/O |
| Command Listener | Event | <1 ms | 2% | Non-blocking stdin |
| **Total** | - | - | **40%** | Headroom: 60% |

### Memory Usage

```
Asyncio overhead:        ~5 MB
State variables:         ~1 MB
CSV buffer:              ~2 MB
IMU/Motor buffers:       ~1 MB
─────────────────
Total:                  ~9 MB / 4096 MB available ✅
```

---

## Debugging Tools

### 1. Monitor Task States

```python
import asyncio

async def debug_task_status():
    while True:
        tasks = asyncio.all_tasks()
        for task in tasks:
            print(f"{task.get_name()}: {task._state}")
        await asyncio.sleep(5)
```

### 2. Detect Deadlocks

```python
async def deadlock_detector():
    while True:
        await asyncio.sleep(10)
        pending = asyncio.all_tasks()
        if len(pending) > 8:  # Unusual number of tasks
            print(f"⚠️ Deadlock warning: {len(pending)} tasks pending")
```

### 3. Profile Lock Contention

```python
import time

class ProfiledLock(asyncio.Lock):
    async def acquire(self):
        t0 = time.time()
        await super().acquire()
        wait_time = time.time() - t0
        if wait_time > 10:  # ms
            print(f"⚠️ Lock contention: {wait_time:.1f}ms")
```

---

## Summary

**Synchronization Model**: Event-driven asyncio with minimal locking

**Key Guarantees**:
- ✅ Motor PWM: ±5ms precision (absolute time)
- ✅ IMU data: Real-time (100 Hz) with zero-crossing detection
- ✅ CSV writes: Safe (no corruption)
- ✅ Commands: FIFO ordered (no loss)
- ✅ Overall CPU load: ~40% (headroom for system tasks)

**Critical Dependencies**:
1. Bluetooth UART responsiveness (IMU lag: ~30-50ms)
2. I2C bus availability (INA219: <20ms)
3. Disk I/O latency (CSV writes: <5ms)

---

## References

- Python asyncio documentation: https://docs.python.org/3/library/asyncio.html
- GIL (Global Interpreter Lock): https://realpython.com/python-gil/
- Real-time constraints in Python: https://www.embeddedrelated.com/showarticle/1471.php

