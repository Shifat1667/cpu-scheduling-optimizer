#pragma once
// ProcessInfo.h
// Stores REAL OS process data collected from /proc (Linux) or WinAPI (Windows).
// This is NOT scheduling-analysis data. It represents actual kernel information.

#include <string>

struct ProcessInfo {
    int pid = 0;
    int parentPid = 0;

    std::string name;
    char state = 'S'; // R=Running, S=Sleeping, D=Uninterruptible, Z=Zombie, T=Stopped

    long priority = 0;   // Kernel priority
    long niceValue = 0;  // Nice value (-20 to 19), lower = higher priority

    // CPU time in clock ticks (typically 100 ticks/sec on Linux)
    unsigned long userTime = 0;
    unsigned long kernelTime = 0;

    // Process start time (clock ticks since boot)
    unsigned long startTime = 0;

    // Memory information
    unsigned long virtualMemory = 0; // Virtual memory size in bytes
    long residentMemory = 0;         // Resident Set Size in bytes (physical memory)

    int threadCount = 1;

    // CPU usage is MEASURED by comparing two samples, not obtained from /proc directly.
    // Label: MEASURED (not direct kernel value)
    double cpuUsage = 0.0; // percentage
};
