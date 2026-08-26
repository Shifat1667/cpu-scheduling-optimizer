#pragma once

#include "SchedulingResult.h"
#include <vector>

// Calculates all performance metrics from a completed SchedulingResult.
// All formulas follow standard OS textbook definitions.
class Metrics {
public:
    // Recalculates all metrics in-place on the given result
    static void calculateAll(SchedulingResult& result);

    static double avgWaitingTime(const std::vector<SchedulingProcess>& procs);
    static double avgTurnaroundTime(const std::vector<SchedulingProcess>& procs);
    static double avgResponseTime(const std::vector<SchedulingProcess>& procs);
    static double fairnessIndex(const std::vector<SchedulingProcess>& procs);
    static double throughput(const std::vector<SchedulingProcess>& procs, double totalTime);
    static int countContextSwitches(const std::vector<GanttSegment>& timeline);
    static double cpuUtilization(const std::vector<GanttSegment>& timeline, double totalTime);
};
