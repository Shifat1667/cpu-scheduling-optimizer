# CPU Scheduling Optimization & Process Monitoring System

A C++17 academic project that collects **real process data** from the operating system and uses it to analyze, compare, and optimize CPU scheduling strategies. Built for a university OS course.

## Key Design Principle

> **No simulation. Real data.**

This system reads actual process information from `/proc` (Linux) or WinAPI (Windows), then uses that data to *analyze* scheduling strategies — not to control the kernel scheduler.

## Features

- **Real Process Monitoring** — reads `/proc/[pid]/stat`, `/proc/[pid]/status`, `/proc/stat`, `/proc/meminfo` on Linux; uses `EnumProcesses`, `GetProcessTimes`, `GetProcessMemoryInfo` on Windows
- **5 Scheduling Algorithms** — FCFS, SJF, SRTF, Round Robin, Priority
- **Workload Classification** — automatically categorizes workloads as CPU-bound, I/O-bound, mixed, interactive, or batch
- **Optimization Engine** — weighted multi-criteria scoring across 6 metrics with Pareto dominance analysis
- **Gantt Timeline** — visual timeline of analyzed schedules
- **35 Unit Tests** — covering all algorithms, metrics, edge cases, and optimization logic

## Project Structure

```
cpu-scheduling-optimizer/
├── include/                    # Headers
│   ├── ProcessInfo.h           # OS process data structure
│   ├── SchedulingProcess.h     # Derived scheduling process (from real data)
│   ├── SchedulingResult.h      # Algorithm output container
│   ├── GanttSegment.h          # Gantt chart segment
│   ├── ProcessMonitor.h        # Real OS data collector
│   ├── Scheduler.h             # Base class for all algorithms
│   ├── FCFScheduler.h          # First-Come First-Served
│   ├── SJFScheduler.h          # Shortest Job First
│   ├── SRTFScheduler.h         # Shortest Remaining Time First
│   ├── RoundRobinScheduler.h   # Round Robin
│   ├── PriorityScheduler.h     # Priority Scheduling
│   ├── Metrics.h               # Scheduling metric calculator
│   ├── WorkloadAnalyzer.h      # Workload type classifier
│   └── OptimizationEngine.h    # Multi-criteria optimization
├── src/                        # Implementations
│   ├── main.cpp                # Terminal UI application
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
│   └── test_all.cpp            # 35 unit tests
├── CMakeLists.txt              # Build configuration
└── README.md                   # This file
```

## Data Flow

```
OS Kernel (/proc or WinAPI)
    ↓
ProcessMonitor (collects real process info)
    ↓
ProcessInfo (PID, name, state, CPU%, memory, priority)
    ↓
WorkloadAnalyzer (classifies workload type)
    ↓
SchedulingProcess (derived from real data for scheduling analysis)
    ↓
5 Schedulers (FCFS, SJF, SRTF, RR, Priority)
    ↓
Metrics (turnaround, waiting, response, CPU util, throughput, fairness)
    ↓
OptimizationEngine (weighted scoring → recommendation)
    ↓
User (terminal display, Gantt timeline)
```

## Building

### Prerequisites

- **C++17 compiler** (g++ 8+ or MSVC 2019+)
- **CMake 3.16+**

### Build Commands

```bash
# Linux
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# Windows (MSYS2 MinGW)
cmake -S . -B build -G "MinGW Makefiles"
cmake --build build

# Windows (MSVC)
cmake -S . -B build
cmake --build build --config Release
```

### Run

```bash
./build/cpu_scheduler    # Main application
./build/test_runner      # Test suite
```

## Algorithms

| Algorithm | Type | Best For |
|-----------|------|----------|
| FCFS | Non-preemptive | Simple, predictable workloads |
| SJF | Non-preemptive | Minimizing average waiting time |
| SRTF | Preemptive | Responsive short-process handling |
| Round Robin | Preemptive | Fair time-sharing (configurable quantum) |
| Priority | Non-preemptive | Priority-driven systems |

## Optimization Engine

The optimization engine evaluates all 5 algorithms against 6 metrics using weighted scoring:

| Metric | Weight | Direction |
|--------|--------|-----------|
| Avg Waiting Time | 25% | Lower is better |
| Avg Response Time | 25% | Lower is better |
| Avg Turnaround Time | 15% | Lower is better |
| CPU Utilization | 15% | Higher is better |
| Fairness Index | 10% | Higher is better |
| Context Switches | 10% | Lower is better |

Each metric is normalized against the best-performing algorithm for that metric, then combined using the weights. The engine also performs Pareto dominance analysis and generates a human-readable explanation.

## Scheduling Processes: Derived, Not Real

**Important distinction:**

- `ProcessInfo` = Real OS data (from `/proc` or WinAPI)
- `SchedulingProcess` = Derived from real data, used for scheduling analysis

Burst times are **estimated** from accumulated CPU ticks (`userTime + kernelTime`). The system does NOT know the actual burst time a process will use — no user-space program can know this. The analysis is based on *observed CPU activity*.

## Testing

35 unit tests covering:
- All 5 scheduling algorithms (correctness, ordering, preemption)
- Metric calculations (turnaround, waiting, response, utilization, throughput, fairness)
- Optimization scoring and ranking
- Edge cases (idle periods, same arrival times, preemption, quantum variation, priority ties, single process, empty input)

```bash
cd build && ./test_runner
```

## Platform Support

| Platform | Data Source | Status |
|----------|------------|--------|
| Linux | `/proc` filesystem | Primary |
| Windows | WinAPI (`EnumProcesses`, `GetProcessTimes`) | Testing/development |

## License

Academic use.
