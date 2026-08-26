// main.cpp
// CPU Scheduling Optimization and Real Process Analysis System
//
// Terminal UI for:
//   1. Collecting real OS process data
//   2. Analyzing workload characteristics
//   3. Running all 5 scheduling algorithms
//   4. Comparing and optimizing scheduling strategies
//   5. Displaying Gantt timeline of analyzed schedule
//
// IMPORTANT: This system OBSERVES real processes and ANALYZES scheduling strategies.
// It does NOT control, modify, or replace the Linux kernel scheduler.

#include <iostream>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>
#include <limits>
#include <thread>
#include <chrono>
#include <memory>

#include "ProcessMonitor.h"
#include "FCFSScheduler.h"
#include "SJFScheduler.h"
#include "SRTFScheduler.h"
#include "RoundRobinScheduler.h"
#include "PriorityScheduler.h"
#include "Metrics.h"
#include "WorkloadAnalyzer.h"
#include "OptimizationEngine.h"

static const char* LINE = "============================================================";
static const char* THIN = "------------------------------------------------------------";

// ===== UI Helpers =====
void printHeader() {
    std::cout << "\n" << LINE << "\n";
    std::cout << "    CPU SCHEDULING OPTIMIZATION & REAL PROCESS ANALYSIS\n";
    std::cout << LINE << "\n\n";
}

void printSystemStatus(ProcessMonitor& mon) {
    std::cout << "SYSTEM STATUS\n" << THIN << "\n";
    std::cout << "CPU Usage:     " << std::fixed << std::setprecision(1) << mon.getSystemCpuUsage() << "%\n";
    std::cout << "Memory Usage:  " << std::fixed << std::setprecision(1) << mon.getMemoryUsage() << "%\n";
    std::cout << "Processes:     " << mon.getProcessCount() << "\n";
    std::cout << "Platform:      " << (mon.hasRealProcData() ? "Linux (/proc)" : "Windows (WinAPI)") << "\n\n";
}

void printProcessTable(const std::vector<ProcessInfo>& procs) {
    std::cout << "PROCESS MONITOR (first 20)\n" << THIN << "\n";
    std::cout << std::left
              << std::setw(8) << "PID"
              << std::setw(20) << "NAME"
              << std::setw(8) << "STATE"
              << std::setw(10) << "CPU%"
              << std::setw(12) << "MEM(KB)"
              << std::setw(8) << "PRIO"
              << "\n" << THIN << "\n";

    int shown = 0;
    for (const auto& p : procs) {
        if (shown >= 20) { std::cout << "  ... and " << (procs.size() - 20) << " more\n"; break; }
        std::string name = p.name.length() > 19 ? p.name.substr(0, 18) + "." : p.name;
        std::cout << std::left
                  << std::setw(8) << p.pid
                  << std::setw(20) << name
                  << std::setw(8) << p.state
                  << std::setw(10) << std::fixed << std::setprecision(1) << p.cpuUsage
                  << std::setw(12) << p.residentMemory
                  << std::setw(8) << p.priority
                  << "\n";
        ++shown;
    }
    std::cout << "\n";
}

void printSchedulingResult(const SchedulingResult& r) {
    std::cout << "\nSCHEDULING RESULT: " << r.algorithmName << "\n" << THIN << "\n";
    std::cout << std::left
              << std::setw(6)  << "PID"
              << std::setw(10) << "NAME"
              << std::setw(10) << "ARRIVAL"
              << std::setw(10) << "BURST"
              << std::setw(12) << "COMPLETE"
              << std::setw(12) << "TAT"
              << std::setw(10) << "WAIT"
              << std::setw(10) << "RESP"
              << "\n" << THIN << "\n";

    for (const auto& p : r.processes) {
        std::cout << std::left
                  << std::setw(6)  << p.pid
                  << std::setw(10) << p.name
                  << std::setw(10) << std::fixed << std::setprecision(1) << p.arrivalTime
                  << std::setw(10) << std::fixed << std::setprecision(1) << p.burstTime
                  << std::setw(12) << std::fixed << std::setprecision(1) << p.completionTime
                  << std::setw(12) << std::fixed << std::setprecision(1) << p.turnaroundTime
                  << std::setw(10) << std::fixed << std::setprecision(1) << p.waitingTime
                  << std::setw(10) << std::fixed << std::setprecision(1) << p.responseTime
                  << "\n";
    }

    std::cout << THIN << "\n";
    std::cout << "Avg Waiting:     " << std::fixed << std::setprecision(2) << r.avgWaitingTime << "\n";
    std::cout << "Avg Turnaround:  " << std::fixed << std::setprecision(2) << r.avgTurnaroundTime << "\n";
    std::cout << "Avg Response:    " << std::fixed << std::setprecision(2) << r.avgResponseTime << "\n";
    std::cout << "CPU Utilization: " << std::fixed << std::setprecision(1) << r.cpuUtilization << "%\n";
    std::cout << "Throughput:      " << std::fixed << std::setprecision(3) << r.throughput << " proc/unit\n";
    std::cout << "Context Switches:" << r.contextSwitches << "\n";
    std::cout << "Fairness Index:  " << std::fixed << std::setprecision(4) << r.fairnessIndex << "\n";
}

void printGantt(const std::vector<GanttSegment>& timeline) {
    std::cout << "\nPROPOSED / ANALYZED SCHEDULE (Gantt)\n" << THIN << "\n";
    for (const auto& seg : timeline)
        std::cout << "| " << std::setw(8) << std::left
                  << (seg.pid == -1 ? "IDLE" : seg.processName) << " ";
    "|\n";
    for (const auto& seg : timeline)
        std::cout << std::setw(10) << std::left << seg.startTime;
    std::cout << std::setw(10) << std::left
              << (timeline.empty() ? 0.0 : timeline.back().endTime) << "\n" << THIN << "\n";
}

void printOptimizationResult(const OptimizationResult& opt) {
    std::cout << "\n" << LINE << "\n";
    std::cout << "            OPTIMIZATION RESULT\n";
    std::cout << LINE << "\n\n";

    std::cout << "Current Workload:  " << workloadTypeToString(opt.workloadAnalysis.type) << "\n\n";
    std::cout << "Recommended Algorithm:\n  " << opt.recommendedAlgorithm << "\n\n";
    std::cout << "Optimization Score:\n  " << opt.recommendedScore << " / 100\n\n";

    std::cout << THIN << "\n";
    std::cout << "ALGORITHM RANKING\n";
    std::cout << THIN << "\n";
    int rank = 1;
    for (const auto& r : opt.rankings) {
        std::cout << rank << ". " << std::left << std::setw(22) << r.name
                  << std::fixed << std::setprecision(1) << r.score << "\n";
        ++rank;
    }

    std::cout << "\n" << THIN << "\n";
    std::cout << "WHY " << opt.recommendedAlgorithm << "?\n";
    std::cout << THIN << "\n";
    std::cout << opt.explanation << "\n";
}

// ===== Test Mode =====
std::vector<SchedulingProcess> getTestProcesses() {
    return {
        {1, "P1", 0.0, 8.0, 8.0, 2},
        {2, "P2", 1.0, 4.0, 4.0, 1},
        {3, "P3", 2.0, 2.0, 2.0, 3},
        {4, "P4", 3.0, 1.0, 1.0, 2}
    };
}

// ===== Core Logic =====
std::vector<SchedulingProcess> buildSchedulingWorkload(const std::vector<ProcessInfo>& monProcs) {
    std::vector<SchedulingProcess> schedProcs;
    int id = 1;
    for (const auto& mp : monProcs) {
        // Only schedule processes with measurable CPU activity
        if (mp.cpuUsage > 0.01 || mp.state == 'R' || mp.state == 'r') {
            SchedulingProcess sp;
            sp.pid = id++;
            sp.name = mp.name;
            sp.arrivalTime = 0.0; // All available at analysis start
            sp.burstTime = std::max(1.0, mp.cpuUsage * 0.5 + (mp.kernelTime % 10));
            sp.remainingTime = sp.burstTime;
            sp.priority = static_cast<int>(std::abs(mp.niceValue) % 5) + 1;
            schedProcs.push_back(sp);
        }
        if (id > 15) break; // Keep analysis manageable
    }
    return schedProcs;
}

std::vector<SchedulingResult> runAllAlgorithms(const std::vector<SchedulingProcess>& procs) {
    std::vector<std::unique_ptr<Scheduler>> schedulers;
    schedulers.push_back(std::make_unique<FCFSScheduler>());
    schedulers.push_back(std::make_unique<SJFScheduler>());
    schedulers.push_back(std::make_unique<SRTFScheduler>());
    schedulers.push_back(std::make_unique<RoundRobinScheduler>(2.0));
    schedulers.push_back(std::make_unique<PriorityScheduler>());

    std::vector<SchedulingResult> results;
    for (auto& sched : schedulers) {
        SchedulingResult r = sched->schedule(procs);
        Metrics::calculateAll(r);
        results.push_back(r);
    }
    return results;
}

void runFullAnalysis(const std::vector<SchedulingProcess>& procs, const WorkloadAnalysis& workload) {
    auto results = runAllAlgorithms(procs);
    for (const auto& r : results) printSchedulingResult(r);

    OptimizationEngine engine;
    OptimizationResult opt = engine.optimize(results, workload);
    printOptimizationResult(opt);
}

// ===== Main Menu =====
int main() {
    ProcessMonitor monitor;
    std::vector<ProcessInfo> cachedProcesses;
    WorkloadAnalysis cachedWorkload;
    std::vector<SchedulingResult> cachedResults;
    bool dataCollected = false;

    while (true) {
        printHeader();
        printSystemStatus(monitor);
        if (dataCollected) printProcessTable(cachedProcesses);

        std::cout << "MENU\n" << THIN << "\n";
        std::cout << "[1] Refresh Processes\n";
        std::cout << "[2] Analyze Workload\n";
        std::cout << "[3] Run Scheduling Analysis (from real data)\n";
        std::cout << "[4] Algorithm Test Mode (textbook data)\n";
        std::cout << "[5] Optimization Recommendation\n";
        std::cout << "[6] View Gantt Timeline\n";
        std::cout << "[7] Exit\n\n";
        std::cout << "Choice: ";

        int choice;
        if (!(std::cin >> choice)) {
            if (std::cin.eof()) break;
            std::cin.clear();
            std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
            continue;
        }

        switch (choice) {
            case 1: {
                std::cout << "\nCollecting real process data...\n";
                cachedProcesses = monitor.getProcesses();
                monitor.takeSnapshot();
                std::this_thread::sleep_for(std::chrono::seconds(1));
                double cpu = monitor.getSystemCpuUsage();
                for (auto& p : cachedProcesses)
                    p.cpuUsage = cpu / std::max(1, static_cast<int>(cachedProcesses.size()));
                dataCollected = true;
                cachedWorkload = WorkloadAnalyzer().analyze(
                    cachedProcesses, monitor.getSystemCpuUsage(), monitor.getMemoryUsage());
                std::cout << "Collected " << cachedProcesses.size() << " processes.\n";
                break;
            }
            case 2: {
                if (!dataCollected) { std::cout << "\nCollect data first [1].\n"; break; }
                std::cout << "\nWORKLOAD ANALYSIS\n" << THIN << "\n";
                std::cout << cachedWorkload.description << "\n";
                break;
            }
            case 3: {
                if (!dataCollected) { std::cout << "\nCollect data first [1].\n"; break; }
                auto schedProcs = buildSchedulingWorkload(cachedProcesses);
                if (schedProcs.empty()) { std::cout << "\nNo active processes.\n"; break; }
                std::cout << "\nGenerated " << schedProcs.size() << " scheduling processes from real data.\n";
                runFullAnalysis(schedProcs, cachedWorkload);
                cachedResults = runAllAlgorithms(schedProcs);
                break;
            }
            case 4: {
                std::cout << "\n  ALGORITHM TEST MODE\n" << THIN << "\n";
                std::cout << "P1: AT=0, BT=8, Priority=2\n";
                std::cout << "P2: AT=1, BT=4, Priority=1\n";
                std::cout << "P3: AT=2, BT=2, Priority=3\n";
                std::cout << "P4: AT=3, BT=1, Priority=2\n";
                std::cout << "Quantum = 2\n\n";

                auto procs = getTestProcesses();
                WorkloadAnalysis wl;
                wl.type = WorkloadType::MIXED;
                wl.processCount = 4;
                runFullAnalysis(procs, wl);
                break;
            }
            case 5: {
                std::vector<SchedulingProcess> procs;
                WorkloadAnalysis wl;
                if (dataCollected && !cachedResults.empty()) {
                    procs = buildSchedulingWorkload(cachedProcesses);
                    wl = cachedWorkload;
                } else {
                    procs = getTestProcesses();
                    wl.type = WorkloadType::MIXED;
                    wl.processCount = 4;
                }
                auto results = runAllAlgorithms(procs);
                OptimizationEngine engine;
                OptimizationResult opt = engine.optimize(results, wl);
                printOptimizationResult(opt);
                break;
            }
            case 6: {
                if (cachedResults.empty()) {
                    std::cout << "\nRun analysis first [3] or [4].\n";
                    break;
                }
                printGantt(cachedResults[0].ganttTimeline);
                break;
            }
            case 7:
                return 0;
            default:
                std::cout << "\nInvalid choice.\n";
        }

        std::cout << "\nPress Enter to continue...";
        std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
        if (std::cin.eof()) break;
        std::cin.get();
    }
    return 0;
}
