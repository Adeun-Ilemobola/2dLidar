# 2D LiDAR Prototype

A compact LiDAR-style scanning prototype that combines sensing, motion control, calibration, and real-time visualization into a single system.

This project is a proof-of-concept for controlled **2-axis scanning** using custom hardware, custom software, and iterative CAD-designed 3D-printed parts.

---

## Project Overview

This prototype is designed to:

- Perform controlled 2-axis scanning
- Use a ToF distance sensor for real-time ranging
- Drive mirror positioning with servo-controlled motion
- Automatically calibrate safe scan limits before scanning
- Visualize scan output in a desktop UI

The system is built around:

- **Raspberry Pi 5**
- **VL53L1X ToF sensor**
- **Servo drivers for Motor X and Motor Y**
- **Python desktop UI**
- **Custom 3D-printed enclosure system**

---

## Core Features

- **2-axis scan control**
  - Motor X and Motor Y coordinate mirror motion for scanning

- **Automatic calibration**
  - Finds usable scan width and height before scanning
  - Uses repeated calibration passes to reduce noise
  - Detects scan aperture boundaries with spike detection

- **Real-time operator UI**
  - Separate control panels for X axis, Y axis, and scan controls
  - Displays sensor feedback and scan progress
  - Sends completed scan data to a visualization canvas

- **Adaptive scan visualization**
  - Each scan point stores:
    - X angle
    - Y angle
    - Measured distance
  - Uses a snake-pattern scan path for efficiency
  - Updates visualization based on calibrated limits

- **Depth color mapping**
  - Distance is visualized using **50 cm color intervals**

- **Iterative CAD enclosure design**
  - Multiple enclosure versions developed and optimized for size, print time, and material use

---

## System Architecture

### 1. Operator UI
The desktop UI is the main control layer for the system.

It:
- Sends commands
- Starts calibration
- Starts scans
- Receives live system events
- Updates the visualization

### 2. Hardware Worker
The hardware worker handles the low-level system logic, including:

- VL53L1X sensor ranging
- Motor X control
- Motor Y control
- Calibration logic
- Scan execution
- Event packaging

### 3. Event / Command Flow

- UI sends commands into the **command queue**
- Hardware worker processes commands
- Hardware worker sends results into the **event queue**
- UI listens for those events and updates the display

---

## Calibration Workflow

Before scanning begins, the system automatically calibrates the usable scan range.

### Calibration process
1. Calibrate **X-axis** first to determine usable scan width
2. Calibrate **Y-axis** second to determine usable scan height
3. Run multiple calibration cycles for reliability
4. Detect scan aperture start/end points
5. Send final calibrated min/max values back to the UI

This allows the scan to stay inside a safe and useful operating area.

---

## Scan Workflow

Once calibration is complete:

1. The system uses the calibrated limits
2. It steps through the scan point by point
3. Each point records:
   - X angle
   - Y angle
   - Distance
4. Data is sent to the visualization layer
5. The SmartCanvas updates using the current scan data

---

## Depth Color Mapping

The prototype uses **50 cm depth intervals** for distance visualization.

| Distance Range | Color |
|---|---|
| 0–49 cm | `#440154` |
| 50–99 cm | `#46327E` |
| 100–149 cm | `#365C8D` |
| 150–199 cm | `#277F8E` |
| 200–249 cm | `#1FA187` |
| 250–299 cm | `#4AC16D` |
| 300–349 cm | `#A0DA39` |
| 350–399 cm | `#FDE725` |

---

## CAD / Mechanical Design

The enclosure was developed through multiple iterations to improve:

- physical size
- print efficiency
- material usage
- overall practicality

### CAD Link
[View the Onshape CAD model](https://cad.onshape.com/documents/98702c16ff76be94589c1516/w/66e35b99acd07c5ac5382f90/e/7541bd26da950092198af327?renderMode=0&uiState=69d83b6cbdc4726745c18e9c)

### Design Optimization Example
A later enclosure revision significantly improved print time and material efficiency compared to an earlier version.

---

## Hardware

Current prototype components include:

- Raspberry Pi 5
- VL53L1X ToF distance sensor
- Servo driver hardware
- 50 mm mirrors
- 3D-printed enclosure parts

---

## Software

Main software responsibilities include:

- sensor ranging
- servo positioning
- calibration logic
- scan generation
- event handling
- UI updates
- scan visualization

The desktop software uses a **multi-threaded Python UI architecture** to keep the interface responsive while background hardware tasks continue running.

---

## Repository Structure

Example structure:

```text
.
├── README.md
├── images/
│   ├── XX.png
│   └── enclosure-v15.png
├
├── src/
│   └── ...
