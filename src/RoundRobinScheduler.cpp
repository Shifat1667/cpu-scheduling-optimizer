#include "RoundRobinScheduler.h"
#include <algorithm>
#include <queue>

RoundRobinScheduler::RoundRobinScheduler(double quantum) : quantum_(quantum) {}

std::string RoundRobinScheduler::getName() const {
    return "Round Robin (Q=" + std::to_string(static_cast<int>(quantum_)) + ")";
}

// Round Robin: Preemptive with configurable time quantum.
// Processes get a time slice; when it expires, they go to the back of the ready queue.
SchedulingResult RoundRobinScheduler::schedule(const std::vector<SchedulingProcess>& processes) {
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
    std::queue<int> readyQueue;
    std::vector<bool> inQueue(n, false);
    std::vector<bool> completed(n, false);
    double currentTime = procs[0].arrivalTime;
    int doneCount = 0;

    // Enqueue all processes that have arrived by startTime
    for (int i = 0; i < n && procs[i].arrivalTime <= currentTime; ++i) {
        readyQueue.push(i);
        inQueue[i] = true;
    }

    while (doneCount < n) {
        if (readyQueue.empty()) {
            // Find next arrival
            double nextArr = 1e18;
            for (int i = 0; i < n; ++i)
                if (!completed[i] && !inQueue[i])
                    nextArr = std::min(nextArr, procs[i].arrivalTime);
            if (nextArr >= 1e18) break;
            result.ganttTimeline.push_back({-1, "IDLE", currentTime, nextArr});
            currentTime = nextArr;
            for (int i = 0; i < n; ++i)
                if (!completed[i] && !inQueue[i] && procs[i].arrivalTime <= currentTime) {
                    readyQueue.push(i);
                    inQueue[i] = true;
                }
            continue;
        }

        int idx = readyQueue.front();
        readyQueue.pop();
        inQueue[idx] = false;

        SchedulingProcess& p = procs[idx];
        if (p.firstStartTime < 0) {
            p.firstStartTime = currentTime;
            p.responseTime = p.firstStartTime - p.arrivalTime;
        }

        double slice = std::min(quantum_, p.remainingTime);
        result.ganttTimeline.push_back({p.pid, p.name, currentTime, currentTime + slice});
        p.remainingTime -= slice;
        currentTime += slice;

        // Enqueue newly arrived processes BEFORE re-enqueueing current
        for (int i = 0; i < n; ++i) {
            if (!completed[i] && !inQueue[i] && i != idx &&
                procs[i].arrivalTime > currentTime - slice &&
                procs[i].arrivalTime <= currentTime) {
                readyQueue.push(i);
                inQueue[i] = true;
            }
        }

        if (p.remainingTime <= 1e-9) {
            p.remainingTime = 0;
            p.completionTime = currentTime;
            p.turnaroundTime = p.completionTime - p.arrivalTime;
            p.waitingTime = p.turnaroundTime - p.burstTime;
            completed[idx] = true;
            ++doneCount;
        } else {
            readyQueue.push(idx);
            inQueue[idx] = true;
        }
    }

    result.processes = procs;
    result.totalTime = currentTime;
    return result;
}
