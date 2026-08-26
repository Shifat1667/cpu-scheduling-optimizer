#include "SJFScheduler.h"
#include <algorithm>
#include <limits>

// SJF: Shortest Job First
// Non-preemptive. Selects shortest available burst among arrived processes.
SchedulingResult SJFScheduler::schedule(const std::vector<SchedulingProcess>& processes) {
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
        // Find shortest available job
        int best = -1;
        double bestBurst = std::numeric_limits<double>::max();
        for (int i = 0; i < n; ++i) {
            if (!done[i] && procs[i].arrivalTime <= currentTime) {
                if (procs[i].burstTime < bestBurst ||
                    (procs[i].burstTime == bestBurst && procs[i].arrivalTime < procs[best].arrivalTime)) {
                    bestBurst = procs[i].burstTime;
                    best = i;
                }
            }
        }

        // No process available -> advance to next arrival
        if (best == -1) {
            double nextArrival = std::numeric_limits<double>::max();
            for (int i = 0; i < n; ++i)
                if (!done[i] && procs[i].arrivalTime > currentTime)
                    nextArrival = std::min(nextArrival, procs[i].arrivalTime);
            result.ganttTimeline.push_back({-1, "IDLE", currentTime, nextArrival});
            currentTime = nextArrival;
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
