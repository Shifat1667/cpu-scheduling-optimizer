#pragma once

#include "ProcessInfo.h"
#include <vector>
#include <string>

enum class WorkloadType {
    LIGHT,
    MEDIUM,
    HEAVY,
    CPU_BOUND,
    IO_BOUND,
    MIXED,
    INTERACTIVE
};

std::string workloadTypeToString(WorkloadType type);

struct WorkloadAnalysis {
    WorkloadType type = WorkloadType::LIGHT;
    int processCount = 0;
    double avgCpuUsage = 0.0;
    double systemCpuUsage = 0.0;
    double systemMemoryUsage = 0.0;
    int cpuBoundCount = 0;
    int ioBoundCount = 0;
    int interactiveCount = 0;
    int sleepingCount = 0;
    int runningCount = 0;

    // Burst time distribution (derived from CPU ticks)
    double avgBurstTime = 0.0;
    double maxBurstTime = 0.0;
    double minBurstTime = 0.0;
    double burstVariance = 0.0;

    // Priority distribution
    double avgPriority = 0.0;
    double avgNiceValue = 0.0;

    // Arrival pattern
    double avgArrivalInterval = 0.0;

    // Size classification
    int processCountSmall = 0;   // < 5
    int processCountMedium = 0;  // 5-20
    int processCountLarge = 0;   // > 20

    std::string description;
};

// WorkloadAnalyzer: Classifies the real system workload using rule-based logic.
// No machine learning. All thresholds are configurable.
class WorkloadAnalyzer {
public:
    WorkloadAnalysis analyze(const std::vector<ProcessInfo>& processes,
                             double systemCpu, double systemMemory);
};
