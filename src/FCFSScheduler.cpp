#include "FCFSScheduler.h"
#include <algorithm>

// FCFS: First Come First Serve
// Non-preemptive. Processes execute in arrival order.
SchedulingResult FCFSScheduler::schedule(const std::vector<SchedulingProcess>& processes) {
    SchedulingResult result;
    result.algorithmName = getName();
    if (processes.empty()) return result;

    std::vector<SchedulingProcess> procs = processes;
    std::sort(procs.begin(), procs.end(),
        [](const SchedulingProcess& a, const SchedulingProcess& b) {
            return (a.arrivalTime != b.arrivalTime)
                ? a.arrivalTime < b.arrivalTime
                : a.pid < b.pid;
        });

    double currentTime = 0.0;

    for (size_t i = 0; i < procs.size(); ++i) {
        SchedulingProcess& p = procs[i];

        // Handle idle period: no process has arrived yet
        if (currentTime < p.arrivalTime) {
            GanttSegment idle{-1, "IDLE", currentTime, p.arrivalTime};
            result.ganttTimeline.push_back(idle);
            currentTime = p.arrivalTime;
        }

        p.firstStartTime = currentTime;
        p.responseTime = p.firstStartTime - p.arrivalTime;

        GanttSegment seg{p.pid, p.name, currentTime, currentTime + p.burstTime};
        result.ganttTimeline.push_back(seg);

        currentTime += p.burstTime;
        p.completionTime = currentTime;
        p.turnaroundTime = p.completionTime - p.arrivalTime;
        p.waitingTime = p.turnaroundTime - p.burstTime;
        p.remainingTime = 0;
    }

    result.processes = procs;
    result.totalTime = currentTime;
    return result;
}
