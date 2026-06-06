# System Latency Calibration

[![en](https://img.shields.io/badge/English-en-blue.svg?logo=thestorygraph)](README_system_latency-en.md)
[![fr](https://img.shields.io/badge/Français-fr-green.svg?logo=thestorygraph)](README_system_latency-fr.md)

## <span style="color:orange"> Overview </span>

The **latency** of the measurement bench represents the delay between the detection of θ = 0 (bob at lowest point) and the actual activation of the servomotor. This latency directly affects phase synchronization and explains the observed 5% offset between theoretical and experimental optimal phases.

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

**Total Estimated Latency: ~100 ms**

## <span style="color:orange"> Measurement Methodology </span>

### <span style="color:#229DD4"> Experimental Protocol </span>

To measure the actual system latency, we used a **video analysis approach**:

1. **Recording Setup**
   - Smartphone camera (30 fps = 33 ms per frame)
   - Positioned to capture both the pendulum wire and the servomotor
   - Horizontal alignment for visual angle reference
   - File format: MP4 video

2. **Frame Extraction**
   - Used `ffmpeg` tool to decompose video frame-by-frame
   - Output: PNG sequence (frame_0001.png, frame_0002.png, etc.)
   - Frame interval: 33 ms (1/30 second)

3. **Visual Landmark Detection**
   - **Frame A**: Identify θ = 0 (pendulum wire vertical)
   - **Frame B**: Identify first visible motor movement
   - **Latency**: (Frame B - Frame A) × 33 ms

### <span style="color:#229DD4"> Example Timeline </span>

```
Frame 0001: θ = 0 (pendulum vertical, no motor movement)
Frame 0002: No motor movement (33 ms elapsed)
Frame 0003: No motor movement (66 ms elapsed)
Frame 0004: First visible motor movement (99 ms elapsed)
            → Latency ≈ 100 ms
```

## <span style="color:orange"> Results and Conclusions </span>

### <span style="color:#229DD4"> Measured Latency </span>

| Measurement | Value | Note |
|-------------|-------|------|
| **Primary latency** | 100 ms | Between θ = 0 detection and first motor movement |
| **Measurement uncertainty** | ±33 ms | One frame period at 30 fps |
| **Confidence interval** | 67-133 ms | ±1 frame (1σ) |

### <span style="color:#229DD4"> Physical Interpretation </span>

The 100 ms latency means:

1. **Implication on Phase**
   - The motor receives commands with ~100 ms delay after the pendulum reaches θ = 0
   - This causes the effective excitation phase to shift by approximately 5% relative to the ideal theoretical phase
   - For optimal energy transfer, the control algorithm compensates by advancing the phase command

2. **Impact on Synchronous Mode**
   - In synchronous mode (pumping synchronized with pendulum), the latency must be compensated
   - The phase controller accounts for this by predicting the pendulum position ahead by ~100 ms

3. **Implications on System Performance**
   - ✅ **Acceptable**: 100 ms << 2200 ms (pendulum period)
   - ✅ **Manageable**: Latency is predictable and constant
   - ✅ **Compensatable**: Can be calibrated in software

### <span style="color:#229DD4"> Dominant Contributors (Ranked by Impact) </span>

| Source | Estimated | Reduction Potential |
|--------|-----------|---------------------|
| Bluetooth transmission | ~30-40 ms | ⭐⭐ Use direct UART |
| IMU processing | ~20-30 ms | ⭐ Hardware limitation |
| Pi angle detection | ~20-30 ms | ⭐⭐⭐ Algorithm optimization |
| Motor response | ~10-20 ms | ⭐ Hardware limitation |

