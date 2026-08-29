# CPU Scheduling Optimization & Real-Time Process Analysis System

[![C++ Standard](https://img.shields.io/badge/C%2B%2B-17-blue.svg?style=flat-square&logo=c%2B%2B)](https://en.cppreference.com/w/cpp/17)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg?style=flat-square&logo=python)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg?style=flat-square)]()
[![Tests](https://img.shields.io/badge/Unit%20Tests-57%20Passed-success.svg?style=flat-square)]()
[![License](https://img.shields.io/badge/License-Academic%20Use-orange.svg?style=flat-square)]()

A high-performance, dual-architecture system for **real OS process monitoring**, **dynamic workload analysis**, and **multi-criteria CPU scheduling optimization**. Built for Operating Systems research and engineering analysis.

---

## 🌟 Key Highlights

- **Real Operating System Telemetry**: Reads actual live process statistics from `/proc` (Linux) and WinAPI / Toolhelp32 (Windows) — no synthetic-only limitations.
- **5 Classical Scheduling Algorithms**: First-Come First-Served (**FCFS**), Shortest Job First (**SJF**), Shortest Remaining Time First (**SRTF**), Round Robin (**RR** with configurable quantum), and **Priority Scheduling**.
- **Dynamic Optimization Engine**: Evaluates schedules across 6 normalized metrics with customizable weights (Waiting Time, Response Time, Turnaround Time, CPU Utilization, Jain's Fairness Index, and Context Switches).
- **Interactive Modern GUI (Python/Tkinter + Matplotlib)**:
  - Live process table with instantaneous search, sorting, and context actions.
  - **Simulation Mode**: Interactive workload builder with presets, custom arrival/burst/priority settings, and configurable RR quantum.
  - Multi-metric **Radar/Spider Chart** comparing algorithm trade-offs.
  - **True Preemptive Gantt Timeline** showing execution slices and idle gaps.
  - Optimization weight editor dialog (`Ctrl+W`).
  - One-click CSV and activity log export (`Ctrl+E`).
- **High-Performance C++17 Core & CLI**: Native, memory-safe backend with comprehensive test suite (57 unit tests, 0 failures).

---

## 🎥 Project Video Presentation & Live Demonstration

> **Faculty & Reviewer Quick Link:** Click the banner below or use the direct link to watch the complete video presentation and live system demonstration.

[![Watch Live Demonstration Video](https://img.shields.io/badge/GitHub-Watch%20Demo%20Video-blue?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Shifat1667/cpu-scheduling-optimizer/releases/tag/v1.0.0)

### 🔗 Direct Video Link

👉 **[Click Here to Download / Watch the Full Video](https://github.com/Shifat1667/cpu-scheduling-optimizer/releases/tag/v1.0.0)**

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Operating System Kernel                         │
│             Linux (/proc/stat, /proc/[pid])  │  Windows (WinAPI/PSAPI) │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ Raw OS Telemetry
                                     ▼
                     ┌───────────────────────────────┐
                     │    ProcessMonitor Module      │
                     │  • CPU & Memory Delta Sampling│
                     │  • Thread & State Extraction  │
                     └───────────────┬───────────────┘
                                     │ ProcessInfo Records
                                     ▼
                     ┌───────────────────────────────┐
                     │    WorkloadAnalyzer Module    │
                     │  • CPU-Bound vs I/O-Bound     │
                     │  • Interactive vs Batch Mix   │
                     └───────────────┬───────────────┘
                                     │ Workload Classification
                                     ▼
       ┌───────────────────────────────────────────────────────────┐
       │               5 CPU Scheduling Algorithms                 │
       │   FCFS  │  SJF  │  SRTF (Preemptive)  │  RR  │  Priority  │
       └─────────────────────────────┬─────────────────────────────┘
                                     │ Scheduling Results & Timeline
                                     ▼
                     ┌───────────────────────────────┐
                     │         Metrics Engine        │
                     │  • Avg Waiting Time           │
                     │  • Avg Turnaround Time        │
                     │  • Avg Response Time          │
                     │  • CPU Utilization %          │
                     │  • Jain's Fairness Index      │
                     │  • Context Switch Count       │
                     └───────────────┬───────────────┘
                                     │ Normalized Metric Vectors
                                     ▼
                     ┌───────────────────────────────┐
                     │      Optimization Engine      │
                     │  • Weighted Multi-Criteria    │
                     │  • Workload-Aware Ranking     │
                     │  • Recommendation & Narrative │
                     └───────────────┬───────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
    ┌─────────────────────────┐             ┌─────────────────────────┐
    │     Interactive GUI     │             │     Terminal CLI UI     │
    │  • Radar & Gantt Charts │             │  • Menu-driven monitor  │
    │  • Simulation Mode      │             │  • ASCII Gantt charts   │
    │  • Process Filtering    │             │  • Diagnostic summaries │
    └─────────────────────────┘             └─────────────────────────┘
```

---

## 📁 Project Structure

```
cpu-scheduling-optimizer/
├── include/                    # C++ Header Interfaces
│   ├── ProcessInfo.h           # Raw OS process representation
│   ├── SchedulingProcess.h     # Normalized scheduling unit
│   ├── SchedulingResult.h      # Complete algorithm evaluation container
│   ├── GanttSegment.h          # Preemptive timeline segment
│   ├── ProcessMonitor.h        # Cross-platform OS telemetry collector
│   ├── Scheduler.h             # Abstract base scheduler interface
│   ├── FCFSScheduler.h         # First-Come First-Served
│   ├── SJFScheduler.h          # Shortest Job First
│   ├── SRTFScheduler.h         # Shortest Remaining Time First
│   ├── RoundRobinScheduler.h   # Round Robin (configurable quantum)
│   ├── PriorityScheduler.h     # Priority Scheduling
│   ├── Metrics.h               # Formal scheduling metric calculator
│   ├── WorkloadAnalyzer.h      # Workload type classification engine
│   └── OptimizationEngine.h    # Multi-criteria optimization & decision engine
├── src/                        # C++ Implementation Files
│   ├── main.cpp                # Terminal CLI Application
│   ├── ProcessMonitor.cpp      # Linux & Windows system monitors
│   ├── FCFSScheduler.cpp
│   ├── SJFScheduler.cpp
│   ├── SRTFScheduler.cpp
│   ├── RoundRobinScheduler.cpp
│   ├── PriorityScheduler.cpp
│   ├── Metrics.cpp
│   ├── WorkloadAnalyzer.cpp
│   └── OptimizationEngine.cpp
├── tests/
│   └── test_all.cpp            # 57 comprehensive unit and edge-case tests
├── docs/
│   ├── architecture.md         # Detailed architectural documentation
│   └── gui_guide.md            # GUI user guide & workflow reference
├── gui.py                      # Interactive Python/Tkinter GUI Application
├── requirements.txt            # Python dependencies (psutil, matplotlib)
├── CMakeLists.txt              # CMake build configuration with CTest
├── run.bat                     # Windows automatic dependency & launcher script
└── README.md                   # Project documentation
```

---

## 🚀 Quickstart

### 1. Launching the GUI (Recommended)

#### Using `run.bat` (Windows):
Double click `run.bat` or run from terminal:
```bat
run.bat
```
*(Automatically verifies Python, installs dependencies if needed, and launches the application.)*

#### Manual Python Execution:
```bash
pip install -r requirements.txt
python gui.py
```

#### GUI Keyboard Shortcuts:
| Shortcut | Action |
|----------|--------|
| **F5** | Refresh System Scan |
| **F6** | Run Scheduling Analysis |
| **Ctrl + O** | Run System Optimization |
| **Ctrl + E** | Export Process & Scheduling Data (CSV) |
| **Ctrl + W** | Open Optimization Weights Editor |
| **Ctrl + Q** | Quit Application |

---

### 2. Building & Running the C++ Backend

#### Prerequisites:
- **C++17 compiler** (`g++`, `clang++`, or `MSVC`)
- **CMake 3.16+**

#### Linux / macOS:
```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)

# Run CLI application
./build/cpu_scheduler

# Run unit test suite
./build/test_runner
```

#### Windows (MinGW / MSYS2 / PowerShell):
```powershell
cmake -S . -B build -G "MinGW Makefiles"
cmake --build build

# Run CLI application
.\build\cpu_scheduler.exe

# Run unit test suite
.\build\test_runner.exe
```

---

## 📊 Scheduling Algorithms Matrix

| Algorithm | Preemption | Strategy | Primary Advantage | Trade-Off |
|:---|:---:|:---|:---|:---|
| **FCFS** | Non-preemptive | First arrival served first | Zero scheduling overhead, deterministic | Vulnerable to Convoy Effect |
| **SJF** | Non-preemptive | Shortest burst runs first | Mathematically minimizes average wait | Can starve long jobs |
| **SRTF** | Preemptive | Shortest remaining burst runs | Optimal responsiveness for short arrivals | Higher context-switch frequency |
| **Round Robin** | Preemptive | Time-sliced circular queue | Fair CPU allocation, responsive UI | Quantum selection sensitive |
| **Priority** | Non-preemptive | Highest priority (lowest index) first | Strict policy enforcement | Priority inversion / starvation risk |

---

## ⚖️ Optimization Scoring Weights

The Optimization Engine ranks algorithms using a normalized multi-criteria scoring model:

$$\text{Score} = \sum_{i=1}^{6} w_i \cdot \text{NormalizedMetric}_i \times 100$$

| Metric | Direction | Default Weight | Optimization Rationale |
|:---|:---:|:---:|:---|
| **Waiting Time** | Lower is better | **25%** | Minimizes process delay in ready queue |
| **Response Time** | Lower is better | **25%** | Maximizes interactive application responsiveness |
| **Turnaround Time** | Lower is better | **15%** | Minimizes total time from arrival to completion |
| **CPU Utilization** | Higher is better | **15%** | Keeps execution units maximally busy |
| **Fairness Index** | Higher is better | **10%** | Jain's Fairness Index ($\in [0, 1]$) avoids starvation |
| **Context Switches** | Lower is better | **10%** | Minimizes cache-thrashing & kernel context-switch overhead |

*Note: Weights can be customized interactively in the GUI via `Ctrl+W` or programmatically via `OptimizationEngine::setWeights()`.*

---

## 🧪 Test Suite & Validation

The test suite (`tests/test_all.cpp`) validates 57 test scenarios across:
1. **Algorithm Correctness**: Burst consumption, FIFO tie-breaking, preemption triggers.
2. **Metric Integrity**: Turnaround time, waiting time, throughput sanity, and Jain's index bounds.
3. **Edge Cases**:
   - Zero and fractional burst times.
   - Idle intervals between arrivals.
   - Large workloads ($20+$ processes).
   - Preemption stress tests with rapid short arrivals.
   - Round Robin quantum degradation (large $Q \to \text{FCFS}$).
   - Deterministic execution guarantees (same input produces identical metrics).

```text
========================================
  CPU SCHEDULING - TEST SUITE
========================================
  RESULTS: 57 passed, 0 failed
========================================
```

---

## 📄 License & Course Information

Developed as an academic Operating Systems course project. Designed for educational, research, and benchmarking use.

