# CPU Scheduling Optimization & Process Monitoring System

A comprehensive C++17 & Python real-time process monitoring, CPU scheduling simulation, and optimization suite. Built to analyze live operating system processes, detect resource bottlenecks, evaluate 5 fundamental CPU scheduling algorithms, and apply process optimizations with before/after measurement reporting.

---

## Key Design Principle

> **No simulation. Real OS data.**

This system collects real OS process telemetry from WinAPI (Windows) or `/proc` (Linux). It derives execution metrics, analyzes CPU scheduling strategies, identifies bottlenecks, and allows safe process optimization.

---

## Highlights & Features

### 🖥️ Real-Time Python GUI Suite (`gui.py`)
- **Enterprise Obsidian Theme** — Polished, dark-mode desktop user interface built with Tkinter & Matplotlib.
- **Live System Telemetry** — Monitor live CPU utilization, RAM usage, thread counts, system context switches, handle counts, and process status.
- **Process Manager** — Interactive table showing running processes, PIDs, CPU %, memory usage, thread/handle counts, priorities, and context switches.
- **Bottleneck Analysis Engine** — Automated detection of CPU/Memory hogs and high context-switching processes with action recommendations.
- **Safe Process Optimization** — Adjust process priorities safely (supports elevated Administrator privileges for system processes).
- **CPU Scheduling Visualizer** — Run 5 scheduling algorithms (FCFS, SJF, SRTF, Round Robin, Priority) on live process snapshots with interactive Gantt timelines and algorithm comparison charts.
- **Before / After Optimization Review** — Compare CPU/RAM resource usage before and after priority adjustments with real-time trend charts.

### ⚙️ C++17 High-Performance Core Engine
- **Real OS Process Collector** — Direct interface with WinAPI (`EnumProcesses`, `GetProcessTimes`, `GetProcessMemoryInfo`) and Linux `/proc`.
- **5 CPU Scheduling Algorithms** — FCFS, SJF (Non-preemptive), SRTF (Preemptive), Round Robin (Configurable quantum), Priority Scheduling.
- **Workload Classification** — Categorizes workloads as CPU-bound, I/O-bound, mixed, interactive, or batch.
- **Multi-Criteria Optimization Engine** — Evaluates algorithms across 6 weighted metrics (Avg Wait Time, Response Time, Turnaround Time, CPU Util, Fairness Index, Context Switches) with Pareto dominance analysis.
- **35 Unit Tests** — Comprehensive verification suite using C++ testing framework.

---

## Quick Start

### Running the Graphical Application (Windows)

Simply run the batch file:

```cmd
run.bat
```

Or run directly with Python:

```bash
python gui.py
```

*Note: For full process optimization capabilities (modifying process priorities), right-click `run.bat` and select **Run as administrator**.*

---

## Project Structure

```
cpu-scheduling-optimizer/
├── run.bat                     # One-click launcher for GUI
├── gui.py                      # Enterprise Python Tkinter + Matplotlib GUI
├── run_analysis.py             # CLI analysis script
├── generate_pdf.py             # Automated PDF project report generator
├── CPU_Scheduling_Project_Report.pdf # Generated PDF project report
├── include/                    # C++ Header files
│   ├── ProcessInfo.h           # OS process data structure
│   ├── SchedulingProcess.h     # Derived scheduling process
│   ├── SchedulingResult.h      # Algorithm output container
│   ├── GanttSegment.h          # Gantt chart segment
│   ├── ProcessMonitor.h        # Real OS data collector
│   ├── Scheduler.h             # Base class for schedulers
│   ├── FCFSScheduler.h         # First-Come First-Served
│   ├── SJFScheduler.h          # Shortest Job First
│   ├── SRTFScheduler.h         # Shortest Remaining Time First
│   ├── RoundRobinScheduler.h   # Round Robin
│   ├── PriorityScheduler.h     # Priority Scheduling
│   ├── Metrics.h               # Scheduling metric calculator
│   ├── WorkloadAnalyzer.h      # Workload type classifier
│   └── OptimizationEngine.h    # Multi-criteria optimization
├── src/                        # C++ Source files
│   ├── main.cpp                # Terminal C++ application
│   ├── ProcessMonitor.cpp      # OS data collection (Linux + Windows)
│   ├── FCFSScheduler.cpp
│   ├── SJFScheduler.cpp
│   ├── SRTFScheduler.cpp
│   ├── RoundRobinScheduler.cpp
│   ├── PriorityScheduler.cpp
│   ├── Metrics.cpp
│   ├── WorkloadAnalyzer.cpp
│   └── OptimizationEngine.cpp
├── tests/
│   └── test_all.cpp            # 35 C++ unit tests
├── CMakeLists.txt              # CMake build configuration
└── README.md                   # Project documentation
```

---

## C++ Core Building & Execution

### Prerequisites
- **C++17 Compiler** (g++ 8+ or MSVC 2019+)
- **CMake 3.16+**

### Building

```bash
# Windows (MinGW / MSYS2)
cmake -S . -B build -G "MinGW Makefiles"
cmake --build build

# Windows (MSVC)
cmake -S . -B build
cmake --build build --config Release

# Linux
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

### Running C++ Binaries

```bash
# Run C++ terminal application
./build/cpu_scheduler

# Run test suite (35 unit tests)
./build/test_runner
```

---

## Scheduling Algorithms & Evaluation

| Algorithm | Type | Description | Best For |
|-----------|------|-------------|----------|
| **FCFS** | Non-preemptive | First-Come First-Served based on process arrival | Simple, low overhead workloads |
| **SJF** | Non-preemptive | Shortest Job First based on estimated burst time | Minimizing average waiting time |
| **SRTF** | Preemptive | Shortest Remaining Time First with dynamic preemption | Minimizing response time for short processes |
| **Round Robin** | Preemptive | Time-slice sharing (configurable quantum) | Fair multi-user / interactive systems |
| **Priority** | Non-preemptive | Priority-driven queue scheduling | Systems with explicit process priorities |

---

## Multi-Criteria Optimization Scoring

The optimization engine evaluates scheduling strategies across 6 weighted metrics:

| Metric | Weight | Direction |
|--------|--------|-----------|
| **Avg Waiting Time** | 25% | Lower is better |
| **Avg Response Time** | 25% | Lower is better |
| **Avg Turnaround Time** | 15% | Lower is better |
| **CPU Utilization** | 15% | Higher is better |
| **Fairness Index** | 10% | Higher is better |
| **Context Switches** | 10% | Lower is better |

---

## License

Academic & Educational Use.
