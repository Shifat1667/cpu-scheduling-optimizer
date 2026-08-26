#include "Metrics.h"
#include <cmath>

double Metrics::avgWaitingTime(const std::vector<SchedulingProcess>& procs) {
    if (procs.empty()) return 0.0;
    double sum = 0.0;
    for (const auto& p : procs) sum += p.waitingTime;
    return sum / procs.size();
}

double Metrics::avgTurnaroundTime(const std::vector<SchedulingProcess>& procs) {
    if (procs.empty()) return 0.0;
    double sum = 0.0;
    for (const auto& p : procs) sum += p.turnaroundTime;
    return sum / procs.size();
}

double Metrics::avgResponseTime(const std::vector<SchedulingProcess>& procs) {
    if (procs.empty()) return 0.0;
    double sum = 0.0;
    for (const auto& p : procs) sum += p.responseTime;
    return sum / procs.size();
}

// Jain's Fairness Index: (sum(xi))^2 / (n * sum(xi^2))
// Returns value between 0 (unfair) and 1 (perfectly fair)
double Metrics::fairnessIndex(const std::vector<SchedulingProcess>& procs) {
    if (procs.empty()) return 1.0;
    double sum = 0.0, sumSq = 0.0;
    for (const auto& p : procs) {
        sum += p.waitingTime;
        sumSq += p.waitingTime * p.waitingTime;
    }
    if (sumSq == 0.0) return 1.0;
    return (sum * sum) / (procs.size() * sumSq);
}

double Metrics::throughput(const std::vector<SchedulingProcess>& procs, double totalTime) {
    if (totalTime <= 0.0) return 0.0;
    return procs.size() / totalTime;
}

int Metrics::countContextSwitches(const std::vector<GanttSegment>& timeline) {
    int count = 0;
    for (size_t i = 1; i < timeline.size(); ++i) {
        if (timeline[i].pid != timeline[i - 1].pid && timeline[i].pid != -1)
            ++count;
    }
    return count;
}

double Metrics::cpuUtilization(const std::vector<GanttSegment>& timeline, double totalTime) {
    if (totalTime <= 0.0) return 0.0;
    double busy = 0.0;
    for (const auto& seg : timeline)
        if (seg.pid != -1) busy += (seg.endTime - seg.startTime);
    return (busy / totalTime) * 100.0;
}

void Metrics::calculateAll(SchedulingResult& result) {
    result.avgWaitingTime = avgWaitingTime(result.processes);
    result.avgTurnaroundTime = avgTurnaroundTime(result.processes);
    result.avgResponseTime = avgResponseTime(result.processes);
    result.fairnessIndex = fairnessIndex(result.processes);
    result.throughput = throughput(result.processes, result.totalTime);
    result.contextSwitches = countContextSwitches(result.ganttTimeline);
    result.cpuUtilization = cpuUtilization(result.ganttTimeline, result.totalTime);
}
