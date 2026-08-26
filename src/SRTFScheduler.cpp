#include "SRTFScheduler.h"
#include <algorithm>
#include <limits>

// SRTF: Shortest Remaining Time First
// Preemptive. Selects process with minimum remaining time.
// Records preemptions and context switches.
SchedulingResult SRTFScheduler::schedule(const std::vector<SchedulingProcess>& processes) {
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
    double currentTime = procs[0].arrivalTime;
    int completed = 0;
    std::vector<bool> done(n, false);

    while (completed < n) {
        int best = -1;
        double bestRem = std::numeric_limits<double>::max();
        for (int i = 0; i < n; ++i) {
            if (!done[i] && procs[i].arrivalTime <= currentTime && procs[i].remainingTime > 0) {
                if (procs[i].remainingTime < bestRem) {
                    bestRem = procs[i].remainingTime;
                    best = i;
                }
            }
        }

        // No available process -> advance to next arrival
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
        if (p.firstStartTime < 0) {
            p.firstStartTime = currentTime;
            p.responseTime = p.firstStartTime - p.arrivalTime;
        }

        // Find when next process arrives (potential preemption point)
        double nextArr = std::numeric_limits<double>::max();
        for (int i = 0; i < n; ++i) {
            if (!done[i] && i != best && procs[i].arrivalTime > currentTime)
                nextArr = std::min(nextArr, procs[i].arrivalTime);
        }

        // Run until either finished or preempted
        double sliceEnd = std::min(currentTime + p.remainingTime, nextArr);
        result.ganttTimeline.push_back({p.pid, p.name, currentTime, sliceEnd});

        p.remainingTime -= (sliceEnd - currentTime);
        currentTime = sliceEnd;

        if (p.remainingTime <= 1e-9) {
            p.remainingTime = 0;
            p.completionTime = currentTime;
            p.turnaroundTime = p.completionTime - p.arrivalTime;
            p.waitingTime = p.turnaroundTime - p.burstTime;
            done[best] = true;
            ++completed;
        }
    }

    result.processes = procs;
    result.totalTime = currentTime;
    return result;
}
