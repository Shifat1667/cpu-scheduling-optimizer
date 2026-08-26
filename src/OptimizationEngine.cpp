#include "OptimizationEngine.h"
#include <algorithm>
#include <sstream>
#include <cmath>
#include <limits>

// === NORMALIZATION FUNCTIONS ===
// Lower-is-better: score = best / current (closer to 1 = better)
double OptimizationEngine::normalizeLowerBetter(double value, double best) {
    if (best <= 1e-9) return 1.0;  // If best is zero, all are equally good
    if (value <= 1e-9) return 1.0;  // If value is zero, perfect score
    return std::min(best / value, 1.0);
}

// Higher-is-better: score = current / best (closer to 1 = better)
double OptimizationEngine::normalizeHigherBetter(double value, double best) {
    if (best <= 1e-9) return 0.0;
    if (value <= 1e-9) return 0.0;
    return std::min(value / best, 1.0);
}

OptimizationResult OptimizationEngine::optimize(
    const std::vector<SchedulingResult>& results,
    const WorkloadAnalysis& workload)
{
    OptimizationResult opt;
    opt.workloadAnalysis = workload;
    if (results.empty()) return opt;

    // === STEP 1: Find best value for each metric across all algorithms ===
    double bestWait = std::numeric_limits<double>::max();
    double bestTurn = std::numeric_limits<double>::max();
    double bestResp = std::numeric_limits<double>::max();
    double bestCpu = 0.0;
    double bestFair = 0.0;
    double bestCs = std::numeric_limits<double>::max();

    for (const auto& r : results) {
        bestWait = std::min(bestWait, r.avgWaitingTime);
        bestTurn = std::min(bestTurn, r.avgTurnaroundTime);
        bestResp = std::min(bestResp, r.avgResponseTime);
        bestCpu  = std::max(bestCpu,  r.cpuUtilization);
        bestFair = std::max(bestFair, r.fairnessIndex);
        double cs = (r.contextSwitches > 0) ? r.contextSwitches : 1.0;
        bestCs = std::min(bestCs, cs);
    }

    // === STEP 2: Score each algorithm ===
    for (const auto& r : results) {
        double score = 0.0;

        // Lower is better: waiting, turnaround, response
        score += weights_.waitingTime   * normalizeLowerBetter(r.avgWaitingTime,    bestWait) * 100.0;
        score += weights_.responseTime  * normalizeLowerBetter(r.avgResponseTime,   bestResp) * 100.0;
        score += weights_.turnaroundTime* normalizeLowerBetter(r.avgTurnaroundTime, bestTurn) * 100.0;

        // Higher is better: CPU utilization, fairness
        score += weights_.cpuUtilization * normalizeHigherBetter(r.cpuUtilization,  bestCpu)  * 100.0;
        score += weights_.fairness       * normalizeHigherBetter(r.fairnessIndex,   bestFair) * 100.0;

        // Lower is better: context switches (overhead)
        double cs = (r.contextSwitches > 0) ? static_cast<double>(r.contextSwitches) : 1.0;
        score += weights_.contextSwitchOverhead * normalizeLowerBetter(cs, bestCs) * 100.0;

        AlgorithmRanking rank;
        rank.name = r.algorithmName;
        rank.score = std::round(score * 10.0) / 10.0;
        opt.rankings.push_back(rank);
    }

    // === STEP 3: Sort by score (descending) ===
    std::sort(opt.rankings.begin(), opt.rankings.end(),
        [](const AlgorithmRanking& a, const AlgorithmRanking& b) {
            return a.score > b.score;
        });

    // === STEP 4: Select winner and generate explanation ===
    opt.recommendedAlgorithm = opt.rankings[0].name;
    opt.recommendedScore = opt.rankings[0].score;
    opt.explanation = generateExplanation(opt.rankings[0], workload, results);

    return opt;
}

std::string OptimizationEngine::generateExplanation(
    const AlgorithmRanking& best,
    const WorkloadAnalysis& workload,
    const std::vector<SchedulingResult>& results)
{
    std::ostringstream oss;

    // Find the result matching the best algorithm
    const SchedulingResult* bestResult = nullptr;
    for (const auto& r : results) {
        if (r.algorithmName == best.name) {
            bestResult = &r;
            break;
        }
    }

    // Find second-best for comparison
    const SchedulingResult* secondBest = nullptr;
    if (results.size() >= 2) {
        for (const auto& r : results) {
            if (r.algorithmName != best.name) {
                if (!secondBest || r.avgWaitingTime < secondBest->avgWaitingTime)
                    secondBest = &r;
            }
        }
    }

    // === WORKLOAD PROFILE ===
    oss << "=== WORKLOAD ANALYSIS ===\n\n";
    oss << "Workload type: " << workloadTypeToString(workload.type) << "\n";
    oss << "Processes analyzed: " << workload.processCount << "\n";
    oss << "System CPU usage: " << workload.systemCpuUsage << "%\n";
    oss << "System memory usage: " << workload.systemMemoryUsage << "%\n";
    oss << "Process breakdown: " << workload.cpuBoundCount << " CPU-bound, "
        << workload.ioBoundCount << " I/O-bound, "
        << workload.interactiveCount << " interactive\n";
    oss << "Running: " << workload.runningCount << ", Sleeping: " << workload.sleepingCount << "\n";
    oss << "Burst time distribution: avg=" << workload.avgBurstTime
        << " min=" << workload.minBurstTime
        << " max=" << workload.maxBurstTime
        << " variance=" << workload.burstVariance << "\n";

    // === WHY THIS ALGORITHM WINS ===
    oss << "\n=== WHY " << best.name << " IS OPTIMAL ===\n\n";

    if (bestResult) {
        oss << "Metric comparison (" << best.name << " vs others):\n\n";

        // Find worst for each metric for contrast
        double worstWait = 0, worstTat = 0, worstResp = 0;
        for (const auto& r : results) {
            worstWait = std::max(worstWait, r.avgWaitingTime);
            worstTat  = std::max(worstTat, r.avgTurnaroundTime);
            worstResp = std::max(worstResp, r.avgResponseTime);
        }

        // Waiting time analysis
        oss << "  Waiting time: " << bestResult->avgWaitingTime;
        if (secondBest)
            oss << " (vs " << secondBest->avgWaitingTime << " for " << secondBest->algorithmName << ")";
        oss << "\n";

        // Response time analysis
        oss << "  Response time: " << bestResult->avgResponseTime;
        if (secondBest)
            oss << " (vs " << secondBest->avgResponseTime << " for " << secondBest->algorithmName << ")";
        oss << "\n";

        // Turnaround analysis
        oss << "  Turnaround time: " << bestResult->avgTurnaroundTime;
        if (secondBest)
            oss << " (vs " << secondBest->avgTurnaroundTime << " for " << secondBest->algorithmName << ")";
        oss << "\n";

        oss << "  CPU utilization: " << bestResult->cpuUtilization << "%\n";
        oss << "  Fairness index: " << bestResult->fairnessIndex << "\n";
        oss << "  Context switches: " << bestResult->contextSwitches << "\n";

        // === ALGORITHM-SPECIFIC THEORETICAL JUSTIFICATION ===
        oss << "\n=== THEORETICAL JUSTIFICATION ===\n\n";

        if (best.name.find("SJF") != std::string::npos && best.name.find("SRTF") == std::string::npos) {
            oss << "SJF (Shortest Job First) is provably optimal for minimizing\n";
            oss << "average waiting time among non-preemptive algorithms.\n\n";
            oss << "This workload has " << workload.ioBoundCount << " I/O-bound processes\n";
            oss << "with short burst times (avg=" << workload.avgBurstTime << "). SJF schedules\n";
            oss << "these short jobs first, reducing their waiting time significantly\n";
            oss << "while long-running CPU-bound processes (count=" << workload.cpuBoundCount << ")\n";
            oss << "are deferred. This is the optimal strategy when burst times are known\n";
           oss << "or can be estimated from observed CPU activity.\n\n";
            if (workload.burstVariance > 100.0) {
                oss << "High burst variance (" << workload.burstVariance << ") means jobs have\n";
                oss << "very different lengths — SJF benefits most in this scenario.\n";
            }
        }
        else if (best.name.find("SRTF") != std::string::npos) {
            oss << "SRTF (Shortest Remaining Time First) is the preemptive version of SJF\n";
            oss << "and is provably optimal for minimizing average waiting time.\n\n";
            oss << "With " << workload.processCount << " processes where " << workload.ioBoundCount
                << " are I/O-bound, SRTF can interrupt a long CPU-bound process\n";
            oss << "whenever a shorter job arrives, ensuring minimal waiting for\n";
            oss << "responsive I/O-bound tasks.\n\n";
            oss << "Context switches: " << bestResult->contextSwitches << " — acceptable\n";
            oss << "overhead given the waiting time improvement.\n";
        }
        else if (best.name.find("Round Robin") != std::string::npos) {
            oss << "Round Robin provides the best fairness (" << bestResult->fairnessIndex
                << ") and response time (" << bestResult->avgResponseTime << ").\n\n";
            oss << "With " << workload.interactiveCount << " interactive processes and "
                << workload.processCount << " total, fair time-sharing is critical.\n";
            oss << "Each process gets a time quantum, preventing starvation and\n";
            oss << "ensuring responsive interactive behavior.\n\n";
            oss << "The tradeoff: " << bestResult->contextSwitches << " context switches\n";
            oss << "increase overhead, but the fairness gain justifies it for this workload.\n";
        }
        else if (best.name.find("FCFS") != std::string::npos) {
            oss << "FCFS (First Come First Served) is optimal when:\n";
            oss << "  1. Burst times are similar (low variance=" << workload.burstVariance << ")\n";
            oss << "  2. Few processes (=" << workload.processCount << ") — convoy effect minimal\n";
            oss << "  3. Predictable arrival pattern\n\n";
            oss << "With similar burst times, FCFS avoids context switch overhead\n";
            oss << "while providing predictable, FIFO-ordered execution.\n";
        }
        else if (best.name.find("Priority") != std::string::npos) {
            oss << "Priority scheduling is optimal when the workload has clear\n";
            oss << "priority distinctions. Average priority: " << workload.avgPriority << "\n";
            oss << "Average nice value: " << workload.avgNiceValue << "\n\n";
            oss << "This workload benefits from prioritizing important system processes\n";
            oss << "over background tasks, reducing effective waiting time for\n";
            oss << "high-priority work.\n";
        }

        // === WHY OTHERS LOSE ===
        oss << "\n=== WHY OTHER ALGORITHMS ARE LESS OPTIMAL ===\n\n";
        for (const auto& r : results) {
            if (r.algorithmName == best.name) continue;
            oss << r.algorithmName << ":\n";

            double waitDiff = r.avgWaitingTime - bestResult->avgWaitingTime;
            double respDiff = r.avgResponseTime - bestResult->avgResponseTime;
            double tatDiff = r.avgTurnaroundTime - bestResult->avgTurnaroundTime;

            if (waitDiff > 0.1)
                oss << "  + " << waitDiff << " higher avg waiting time";
            if (respDiff > 0.1)
                oss << "  + " << respDiff << " higher avg response time";
            if (tatDiff > 0.1)
                oss << "  + " << tatDiff << " higher avg turnaround time";
            if (r.contextSwitches > bestResult->contextSwitches)
                oss << "  + " << (r.contextSwitches - bestResult->contextSwitches) << " more context switches";
            if (r.fairnessIndex < bestResult->fairnessIndex)
                oss << "  + Lower fairness (" << r.fairnessIndex << " vs " << bestResult->fairnessIndex << ")";
            oss << "\n";
        }
    }

    return oss.str();
}
