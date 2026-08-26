# Architecture

## Overview

This system has a clean separation between **data collection** (real OS processes) and **scheduling analysis** (derived scheduling processes). The optimization engine sits on top, evaluating all algorithms and recommending the best one for the detected workload type.

## Core Data Structures

### ProcessInfo (Real Data)
```
ProcessInfo
├── pid                    (from OS)
├── name                   (from OS)
├── state                  (from OS: R=running, S=sleeping, Z=zombie, ...)
├── cpuUsage               (computed: delta CPU ticks / delta total ticks)
├── virtualMemory          (from OS)
├── residentMemory         (from OS)
├── userTime               (from OS: user-mode CPU ticks)
├── kernelTime             (from OS: kernel-mode CPU ticks)
├── threadCount            (from OS)
├── priority               (from OS)
├── niceValue              (from OS, Linux only)
├── startTime              (from OS)
└── parentPid              (from OS)
```

### SchedulingProcess (Derived for Analysis)
```
SchedulingProcess
├── pid                    (assigned by system, 1-N)
├── name                   (from ProcessInfo)
├── arrivalTime            (set to 0.0, all available at analysis start)
├── burstTime              (estimated: userTime + kernelTime or CPU%)
├── remainingTime          (for preemptive algorithms)
└── priority               (from ProcessInfo or nice value)
```

### SchedulingResult
```
SchedulingResult
├── algorithmName
├── processes[]            (each with completion, turnaround, waiting, response times)
├── avgWaitingTime
├── avgTurnaroundTime
├── avgResponseTime
├── cpuUtilization
├── throughput
├── contextSwitches
├── totalTime
├── fairnessIndex          (Jain's fairness index)
└── ganttTimeline[]        (GanttSegment objects for visualization)
```

## Module Responsibilities

### ProcessMonitor
- **Linux**: reads `/proc/[pid]/stat`, `/proc/[pid]/status`, `/proc/stat`, `/proc/meminfo`
- **Windows**: `EnumProcesses()`, `OpenProcess()`, `GetProcessTimes()`, `GetProcessMemoryInfo()`
- CPU usage: two-sample delta measurement
- Does NOT modify, kill, or suspend any process

### Scheduling Algorithms
Each scheduler implements the `Scheduler` interface:
```cpp
class Scheduler {
    virtual SchedulingResult schedule(const std::vector<SchedulingProcess>&) = 0;
};
```

- **FCFS**: Simple FIFO queue
- **SJF**: Sort by burst time, non-preemptive
- **SRTF**: Preemptive SJF — at each arrival, check if new process has shorter remaining time
- **Round Robin**: Circular queue with configurable time quantum
- **Priority**: Non-preemptive, sorted by priority value (lower = higher priority)

### Metrics
Calculates all scheduling metrics from a completed `SchedulingResult`:
- Avg turnaround time = sum(CT - AT) / n
- Avg waiting time = sum(WT) / n
- Avg response time = sum(RT) / n
- CPU utilization = (totalBurst / totalTime) * 100
- Throughput = n / totalTime
- Fairness index = Jain's fairness index based on individual throughputs

### WorkloadAnalyzer
Classifies the workload based on:
- Process count
- CPU/memory usage ratio
- Average priority/nice values
- Thread density

Returns one of: `CPU_BOUND`, `IO_BOUND`, `MIXED`, `INTERACTIVE`, `BATCH`

### OptimizationEngine
1. Runs all 5 algorithms on the same workload
2. For each metric, identifies the best-performing algorithm
3. Normalizes each algorithm's score against the best for that metric
4. Applies weighted combination (weights from `OptimizationWeights`)
5. Checks for Pareto dominance
6. Generates human-readable explanation

**Normalization**:
- Lower-is-better metrics: `bestValue / currentValue` (capped at 1.0)
- Higher-is-better metrics: `currentValue / bestValue` (capped at 1.0)

**Single weight configuration**:
```cpp
struct OptimizationWeights {
    double waitingWeight   = 0.25;
    double responseWeight  = 0.25;
    double turnaroundWeight = 0.15;
    double cpuUtilWeight   = 0.15;
    double fairnessWeight  = 0.10;
    double contextSwitchWeight = 0.10;
};
```

## Key Design Decisions

### Data Separation
`ProcessInfo` (real) and `SchedulingProcess` (derived) are strictly separate types. This prevents confusion between observed data and analysis assumptions.

### Burst Time Estimation
Burst times are labeled "MEASURED CPU ACTIVITY" — derived from accumulated CPU ticks. The actual burst time a process will use in the future is unknowable from user space. All scheduling analysis is based on observed activity, not predictions.

### No Kernel Modification
This system observes and analyzes. It never:
- Modifies process priorities
- Kills or suspends processes
- Replaces the kernel scheduler
- Uses `nice()`, `sched_setscheduler()`, or similar syscalls

### Optimization Weights
A single configuration in `OptimizationWeights` controls all scoring. No per-workload weight tables — the workload type affects algorithm *selection* logic in `chooseBestForWorkload()`, but not the base scoring weights.

## File Dependencies

```
ProcessInfo.h ← ProcessMonitor.h, SchedulingProcess.h
SchedulingProcess.h ← all schedulers
SchedulingResult.h ← Metrics.h, all schedulers
GanttSegment.h ← SchedulingResult.h
Scheduler.h ← all scheduler headers
Metrics.h ← OptimizationEngine.h
WorkloadAnalyzer.h ← OptimizationEngine.h
OptimizationEngine.h ← main.cpp
```
