# CPU Scheduling Optimizer — GUI User Guide

## Overview

The Python/Tkinter GUI (`gui.py`) provides an interactive interface for:
1. Live OS process monitoring, sorting, searching, and context-based process tuning.
2. Custom workload simulation (Simulation Mode).
3. System analysis and bottleneck detection.
4. Classical CPU scheduling algorithm evaluation and multi-metric visual comparison.
5. Live optimization review and before/after verification.
6. Diagnostic activity logging and data export.

---

## Tabs & Capabilities

### 1. Processes Tab
- **Search Bar**: Instant filter by process name or PID.
- **Column Sorting**: Click any column header (`PID`, `Name`, `State`, `CPU%`, `Memory MB`, `Priority`, `Threads`, `Ctx Switches`) to sort ascending/descending.
- **Right-Click Context Menu**:
  - Copy PID to clipboard
  - Change process priority (High, Normal, Below Normal, Low/Idle)
  - Terminate process
- **Export CSV Button**: Exports the complete process table and system snapshot to a `.csv` file.

### 2. Simulation Mode Tab
- **Manual Process Builder**:
  - Add processes with custom **Name**, **Arrival Time**, **Burst Time**, and **Priority**.
  - Configure **Round Robin Time Quantum**.
- **Preset Scenarios**:
  - *Textbook Classic (4 processes)*: Demonstrates standard arrival and burst trade-offs.
  - *Convoy Effect (FCFS worst case)*: Demonstrates how a long CPU burst stalls short jobs in FCFS.
  - *Priority Mix (High vs Low)*: Analyzes priority-driven preemption and tie-breaking.
  - *Preemption Stress (SRTF vs RR)*: Evaluates rapid context switching and interactive latency.
- **Execute Simulation**: Evaluates all 5 scheduling algorithms on the custom workload and automatically opens the Scheduling comparison view.

### 3. Analysis Tab
- **Workload Classification**: Classifies current load as CPU-Bound, I/O-Bound, Mixed, Interactive, or Batch.
- **Bottleneck Diagnostics**: Highlights high-severity CPU, memory, and context-switching bottlenecks with top offending processes.
- **Optimization Suggestions**: Provides concrete priority adjustments to alleviate system stress.

### 4. Scheduling Tab
- **Decision Banner**: Shows the recommended algorithm and weighted score.
- **Algorithm Comparison Table**: Displays 7 columns: Algorithm, Score, Avg Wait, Response Time, Turnaround Time, CPU Utilization, and Context Switches.
- **Radar / Spider Chart**: Multi-metric polar plot visualizing trade-offs across all 6 normalized metrics simultaneously.
- **Preemptive Gantt Timeline**: Displays true execution segments, slices, and idle periods across time.

### 5. Optimization Tab
- **Before vs After Benchmark**: Measures real system utilization across sampling intervals before and after applying optimizations.
- **Resource Pressure Banner**: Summarizes whether resource consumption decreased measurably.
- **Action Record**: Tracks which priority modifications were applied vs skipped (e.g. system-protected processes when un-elevated).

### 6. Log Tab
- **Diagnostic Activity Feed**: Timestamped stream of system scans, simulations, priority adjustments, and errors.
- **Clear & Export Log**: Save diagnostics to `.txt` for reporting and grading.

---

## Keyboard Shortcuts

| Shortcut | Description |
|:---|:---|
| **F5** | Refresh System Scan (collects real OS processes) |
| **F6** | Run Scheduling Analysis (on live process workload) |
| **Ctrl + O** | Run System Optimization |
| **Ctrl + E** | Export Process & Scheduling Data to CSV |
| **Ctrl + W** | Open Optimization Weights Editor Dialog |
| **Ctrl + Q** | Quit Application |

---

## Customizing Optimization Weights (`Ctrl + W`)

The Optimization Weights Dialog allows users to adjust how the 6 metrics are prioritized:
- Waiting Time (default 25%)
- Response Time (default 25%)
- Turnaround Time (default 15%)
- CPU Utilization (default 15%)
- Jain's Fairness Index (default 10%)
- Context Switch Overhead (default 10%)

*The dialog enforces that weights sum to 1.0 (100%) and provides a one-click "Reset Defaults" option.*
