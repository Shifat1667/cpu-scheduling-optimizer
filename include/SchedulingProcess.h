#pragma once
// SchedulingProcess.h
// Derived data model for scheduling algorithm analysis.
//
// IMPORTANT: These fields are NOT directly available from the OS kernel.
// They are derived/measured from real ProcessInfo data using documented methods:
//
//   arrivalTime  -> Derived from ProcessInfo::startTime (normalized to first process)
//   burstTime    -> MEASURED CPU ACTIVITY: sum of userTime + kernelTime, or
//                   sampled CPU activity between two measurements
//   remainingTime -> Updated during scheduling simulation
//   priority     -> Derived from ProcessInfo::niceValue (mapped to scheduling range)
//
// Do NOT confuse this with actual kernel scheduling data.

#include <string>

struct SchedulingProcess {
    int pid = 0;
    std::string name;

    // --- Derived from real OS data (see labels above) ---
    double arrivalTime = 0.0;   // Derived from /proc/[pid]/stat field 22 (starttime)
    double burstTime = 0.0;     // MEASURED CPU ACTIVITY (userTime + kernelTime)
    double remainingTime = 0.0; // Updated by scheduling algorithms

    int priority = 0;           // Derived from nice value

    // --- Calculated during scheduling analysis ---
    double firstStartTime = -1.0; // First time process gets CPU
    double completionTime = 0.0;
    double turnaroundTime = 0.0;  // CT - AT
    double waitingTime = 0.0;     // TAT - BT
    double responseTime = 0.0;    // FirstStart - AT
};
