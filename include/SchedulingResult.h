#pragma once

#include "SchedulingProcess.h"
#include "GanttSegment.h"
#include <vector>
#include <string>

struct SchedulingResult {
    std::string algorithmName;
    std::vector<SchedulingProcess> processes;
    std::vector<GanttSegment> ganttTimeline;

    double avgWaitingTime = 0.0;
    double avgTurnaroundTime = 0.0;
    double avgResponseTime = 0.0;
    double cpuUtilization = 0.0;  // percentage
    double throughput = 0.0;      // processes per time unit
    int contextSwitches = 0;
    double fairnessIndex = 0.0;   // Jain's fairness index (0 to 1)
    double totalTime = 0.0;       // total makespan
};
