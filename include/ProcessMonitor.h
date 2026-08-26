#pragma once

#include "ProcessInfo.h"
#include <vector>
#include <string>

// ProcessMonitor: Collects REAL process information from the operating system.
//
// On Linux: reads /proc/[pid]/stat, /proc/[pid]/status, /proc/stat, /proc/meminfo
// On Windows: uses EnumProcesses, GetProcessMemoryInfo, GetProcessTimes (for testing)
//
// IMPORTANT: This module is READ-ONLY. It never modifies, kills, or suspends processes.
//
// CPU usage measurement methodology:
//   1. Take sample 1: record CPU times for each process and system total
//   2. Wait for sampling interval (default 1 second)
//   3. Take sample 2: record CPU times again
//   4. CPU% = (delta_process_cpu / delta_system_cpu) * 100
//
// Burst time estimation (for scheduling analysis):
//   burstTime is estimated as (userTime + kernelTime) accumulated CPU ticks,
//   or as the measured CPU activity between two samples.
//   This is labeled as "MEASURED CPU ACTIVITY" - not actual kernel burst time.

class ProcessMonitor {
public:
    ProcessMonitor();

    // Collects all active processes. Returns only valid, readable processes.
    std::vector<ProcessInfo> getProcesses();

    // Get info for a specific PID. Returns empty ProcessInfo if not found.
    ProcessInfo getProcessInfo(int pid);

    // System-wide CPU usage (percentage). Requires two samples to compute.
    double getSystemCpuUsage();

    // System-wide memory usage (percentage).
    double getMemoryUsage();

    // Total number of active processes.
    int getProcessCount();

    // Total thread count across all processes.
    int getTotalThreads();

    // Take a snapshot for CPU measurement. Call twice with interval.
    void takeSnapshot();

    // Check if real /proc data is available
    bool hasRealProcData() const;

private:
    bool initialized_;
    unsigned long prevTotalCpu_;
    unsigned long prevIdleCpu_;

#ifdef __linux__
    ProcessInfo parseLinuxProcStat(int pid);
    void readLinuxCpuTimes(unsigned long& total, unsigned long& idle);
#endif

#ifdef _WIN32
    std::vector<ProcessInfo> getWindowsProcesses();
#endif
};
