#include "PriorityScheduler.h"
#include <algorithm>
#include <limits>

// Priority Scheduling: Non-preemptive.
// Lower numerical priority = higher priority (1 = highest, 5 = lower).
// Ties broken by arrival time, then by PID.
SchedulingResult PriorityScheduler::schedule(const std::vector<SchedulingProcess>& processes) {
    SchedulingResult result;
    result.algorithmName = getName();
    if (processes.empty()) return result;

    std::vector<SchedulingProcess> procs = processes;
    for (auto& p : procs) p.remainingTime = p.burstTime;
    std::sort(procs.begin(), procs.end(),
        [](const SchedulingProcess& a, const SchedulingProcess& b) {
            return a.arrivalTime < b.arrivalTime;
        });

    int n = static_cast<int>(procs.size());
    double currentTime = 0.0;
    int completed = 0;
    std::vector<bool> done(n, false);

    while (completed < n) {
        int best = -1;
        int bestPrio = std::numeric_limits<int>::max();
        for (int i = 0; i < n; ++i) {
            if (!done[i] && procs[i].arrivalTime <= currentTime) {
                int p = static_cast<int>(procs[i].priority);
                if (p < bestPrio ||
                    (p == bestPrio && procs[i].arrivalTime < procs[best].arrivalTime)) {
                    bestPrio = p;
                    best = i;
                }
            }
        }

        if (best == -1) {
            double nextArr = std::numeric_limits<double>::max();
            for (int i = 0; i < n; ++i)
                if (!done[i] && procs[i].arrivalTime > currentTime)
                    nextArr = std::min(nextArr, procs[i].arrivalTime);
            if (nextArr >= std::numeric_limits<double>::max()) break;
            result.ganttTimeline.push_back({-1, "IDLE", currentTime, nextArr});
            currentTime = nextArr;
            continue;
        }

        SchedulingProcess& p = procs[best];
        p.firstStartTime = currentTime;
        p.responseTime = p.firstStartTime - p.arrivalTime;

        result.ganttTimeline.push_back({p.pid, p.name, currentTime, currentTime + p.burstTime});
        currentTime += p.burstTime;
        p.completionTime = currentTime;
        p.turnaroundTime = p.completionTime - p.arrivalTime;
        p.waitingTime = p.turnaroundTime - p.burstTime;
        p.remainingTime = 0;
        done[best] = true;
        ++completed;
    }

    result.processes = procs;
    result.totalTime = currentTime;
    return result;
}
