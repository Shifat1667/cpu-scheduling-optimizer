#include "WorkloadAnalyzer.h"
#include "SchedulingProcess.h"
#include <sstream>
#include <algorithm>
#include <cmath>

std::string workloadTypeToString(WorkloadType type) {
    switch (type) {
        case WorkloadType::LIGHT:       return "Light";
        case WorkloadType::MEDIUM:      return "Medium";
        case WorkloadType::HEAVY:       return "Heavy";
        case WorkloadType::CPU_BOUND:   return "CPU-Bound";
        case WorkloadType::IO_BOUND:    return "I/O-Bound";
        case WorkloadType::MIXED:       return "Mixed";
        case WorkloadType::INTERACTIVE: return "Interactive";
    }
    return "Unknown";
}

WorkloadAnalysis WorkloadAnalyzer::analyze(const std::vector<ProcessInfo>& processes,
                                           double systemCpu, double systemMemory) {
    WorkloadAnalysis a;
    a.processCount = static_cast<int>(processes.size());
    a.systemCpuUsage = systemCpu;
    a.systemMemoryUsage = systemMemory;

    if (processes.empty()) {
        a.type = WorkloadType::LIGHT;
        a.description = "No processes detected.";
        return a;
    }

    double totalCpu = 0.0;
    double totalPriority = 0.0;
    double totalNice = 0.0;
    double totalBurst = 0.0;
    double maxBurst = 0.0;
    double minBurst = 1e9;
    double burstSqSum = 0.0;
    int burstCount = 0;

    for (const auto& p : processes) {
        totalCpu += p.cpuUsage;
        if (p.state == 'R' || p.state == 'r') ++a.runningCount;
        if (p.state == 'S' || p.state == 's') ++a.sleepingCount;

        if (p.cpuUsage > 50.0)     ++a.cpuBoundCount;
        else if (p.cpuUsage < 5.0) ++a.ioBoundCount;
        else if (p.cpuUsage > 0.0 && p.cpuUsage <= 50.0) ++a.interactiveCount;

        totalPriority += std::abs(p.priority);
        totalNice += std::abs(p.niceValue);

        // Estimate burst time from CPU ticks (userTime + kernelTime)
        double burst = static_cast<double>(p.userTime + p.kernelTime);
        if (burst > 0.0) {
            totalBurst += burst;
            burstSqSum += burst * burst;
            maxBurst = std::max(maxBurst, burst);
            minBurst = std::min(minBurst, burst);
            ++burstCount;
        }
    }

    a.avgCpuUsage = totalCpu / processes.size();
    a.avgPriority = totalPriority / processes.size();
    a.avgNiceValue = totalNice / processes.size();

    if (burstCount > 0) {
        a.avgBurstTime = totalBurst / burstCount;
        a.maxBurstTime = maxBurst;
        a.minBurstTime = (minBurst < 1e9) ? minBurst : 0.0;
        double mean = a.avgBurstTime;
        a.burstVariance = (burstSqSum / burstCount) - (mean * mean);
        if (a.burstVariance < 0.0) a.burstVariance = 0.0;
    }

    // Classification
    if (a.processCount < 20)       a.type = WorkloadType::LIGHT;
    else if (a.processCount < 100) a.type = WorkloadType::MEDIUM;
    else                           a.type = WorkloadType::HEAVY;

    if (systemCpu > 70.0) {
        a.type = WorkloadType::CPU_BOUND;
    } else if (a.ioBoundCount > a.processCount * 0.5) {
        a.type = WorkloadType::IO_BOUND;
    } else if (a.interactiveCount > a.processCount * 0.4) {
        a.type = WorkloadType::INTERACTIVE;
    } else if (a.runningCount > 0 && a.sleepingCount > 0) {
        a.type = WorkloadType::MIXED;
    }

    // Process count distribution
    for (const auto& p : processes) {
        double b = static_cast<double>(p.userTime + p.kernelTime);
        if (b < 5.0)        ++a.processCountSmall;
        else if (b < 50.0)  ++a.processCountMedium;
        else                 ++a.processCountLarge;
    }

    std::ostringstream oss;
    oss << "Workload: " << workloadTypeToString(a.type) << "\n";
    oss << "Processes: " << a.processCount
        << " (small:" << a.processCountSmall
        << " medium:" << a.processCountMedium
        << " large:" << a.processCountLarge << ")\n";
    oss << "System CPU: " << systemCpu << "%  Memory: " << systemMemory << "%\n";
    oss << "CPU-bound: " << a.cpuBoundCount
        << "  I/O-bound: " << a.ioBoundCount
        << "  Interactive: " << a.interactiveCount << "\n";
    oss << "Running: " << a.runningCount << "  Sleeping: " << a.sleepingCount << "\n";
    oss << "Burst times: avg=" << a.avgBurstTime
        << " min=" << a.minBurstTime
        << " max=" << a.maxBurstTime
        << " variance=" << a.burstVariance;
    a.description = oss.str();

    return a;
}
