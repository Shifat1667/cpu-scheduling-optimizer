// tests/test_all.cpp
// Algorithm test suite. Uses controlled test data, NOT real process data.
// These tests verify that each scheduling algorithm and metric is correct.

#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <memory>

#include "FCFSScheduler.h"
#include "SJFScheduler.h"
#include "SRTFScheduler.h"
#include "RoundRobinScheduler.h"
#include "PriorityScheduler.h"
#include "Metrics.h"
#include "OptimizationEngine.h"

static int passed = 0, failed = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { std::cerr << "  FAIL: " << msg << "\n"; ++failed; } \
    else { ++passed; } \
} while(0)

#define CHECK_NEAR(a, b, eps, msg) CHECK(std::abs((a)-(b)) < (eps), msg)

std::vector<SchedulingProcess> testProcs() {
    return {
        {1, "P1", 0.0, 8.0, 8.0, 2},
        {2, "P2", 1.0, 4.0, 4.0, 1},
        {3, "P3", 2.0, 2.0, 2.0, 3},
        {4, "P4", 3.0, 1.0, 1.0, 2}
    };
}

// ===== FCFS Tests =====
void testFCFS() {
    std::cout << "\n--- FCFS ---\n";
    FCFSScheduler sched;
    auto r = sched.schedule(testProcs());
    Metrics::calculateAll(r);

    CHECK(r.processes.size() == 4, "FCFS: 4 processes");
    CHECK_NEAR(r.processes[0].completionTime, 8.0, 0.01, "FCFS: P1 CT=8");
    CHECK_NEAR(r.processes[1].completionTime, 12.0, 0.01, "FCFS: P2 CT=12");
    CHECK_NEAR(r.processes[2].completionTime, 14.0, 0.01, "FCFS: P3 CT=14");
    CHECK_NEAR(r.processes[3].completionTime, 15.0, 0.01, "FCFS: P4 CT=15");
    CHECK_NEAR(r.avgWaitingTime, 7.0, 0.01, "FCFS: avgWT=7");
    CHECK(r.contextSwitches >= 3, "FCFS: switches >= 3");
    CHECK_NEAR(r.cpuUtilization, 100.0, 0.01, "FCFS: CPU=100%");
}

// ===== SJF Tests =====
void testSJF() {
    std::cout << "\n--- SJF ---\n";
    SJFScheduler sched;
    auto r = sched.schedule(testProcs());
    Metrics::calculateAll(r);

    CHECK(r.processes.size() == 4, "SJF: 4 processes");
    CHECK(r.avgWaitingTime <= 7.0, "SJF: avgWT <= FCFS");
    std::cout << "  SJF avgWT=" << r.avgWaitingTime << "\n";
}

// ===== SRTF Tests =====
void testSRTF() {
    std::cout << "\n--- SRTF ---\n";
    SRTFScheduler sched;
    auto r = sched.schedule(testProcs());
    Metrics::calculateAll(r);

    CHECK(r.processes.size() == 4, "SRTF: 4 processes");
    CHECK(r.avgWaitingTime <= 7.0, "SRTF: avgWT <= FCFS");
    CHECK(r.contextSwitches >= 1, "SRTF: preemptions detected");
    std::cout << "  SRTF avgWT=" << r.avgWaitingTime << " switches=" << r.contextSwitches << "\n";
}

// ===== Round Robin Tests =====
void testRoundRobin() {
    std::cout << "\n--- Round Robin ---\n";
    RoundRobinScheduler rr(2.0);
    auto r = rr.schedule(testProcs());
    Metrics::calculateAll(r);

    CHECK(r.processes.size() == 4, "RR: 4 processes");
    CHECK(r.contextSwitches >= 2, "RR: context switches");
    std::cout << "  RR avgWT=" << r.avgWaitingTime << " switches=" << r.contextSwitches << "\n";
}

// ===== Priority Tests =====
void testPriority() {
    std::cout << "\n--- Priority ---\n";
    PriorityScheduler sched;
    auto r = sched.schedule(testProcs());
    Metrics::calculateAll(r);

    CHECK(r.processes.size() == 4, "Priority: 4 processes");
    CHECK(r.avgWaitingTime >= 0, "Priority: valid WT");
    std::cout << "  Priority avgWT=" << r.avgWaitingTime << "\n";
}

// ===== Metrics Tests =====
void testMetrics() {
    std::cout << "\n--- Metrics ---\n";
    std::vector<SchedulingProcess> p = {{1,"A",0,5,5,1},{2,"B",0,3,3,2}};
    FCFSScheduler sched;
    auto r = sched.schedule(p);
    Metrics::calculateAll(r);

    CHECK(r.avgWaitingTime >= 0, "Metrics: WT >= 0");
    CHECK(r.avgTurnaroundTime >= 0, "Metrics: TAT >= 0");
    CHECK(r.cpuUtilization >= 0 && r.cpuUtilization <= 100, "Metrics: CPU 0-100");
    CHECK(r.throughput > 0, "Metrics: throughput > 0");
    CHECK(r.fairnessIndex > 0, "Metrics: fairness > 0");
}

// ===== Optimization Tests =====
void testOptimization() {
    std::cout << "\n--- Optimization ---\n";
    auto procs = testProcs();
    std::vector<std::unique_ptr<Scheduler>> scheds;
    scheds.push_back(std::make_unique<FCFSScheduler>());
    scheds.push_back(std::make_unique<SJFScheduler>());
    scheds.push_back(std::make_unique<SRTFScheduler>());
    scheds.push_back(std::make_unique<RoundRobinScheduler>(2.0));
    scheds.push_back(std::make_unique<PriorityScheduler>());

    std::vector<SchedulingResult> results;
    for (auto& s : scheds) { auto r = s->schedule(procs); Metrics::calculateAll(r); results.push_back(r); }

    WorkloadAnalysis wl;
    wl.type = WorkloadType::MIXED;
    wl.processCount = 4;

    OptimizationEngine engine;
    auto opt = engine.optimize(results, wl);

    CHECK(!opt.recommendedAlgorithm.empty(), "Opt: has recommendation");
    CHECK(opt.recommendedScore >= 0 && opt.recommendedScore <= 100, "Opt: score 0-100");
    CHECK(opt.rankings.size() == 5, "Opt: 5 rankings");
    CHECK(!opt.explanation.empty(), "Opt: has explanation");

    std::cout << "  Recommended: " << opt.recommendedAlgorithm << " (" << opt.recommendedScore << ")\n";
    for (const auto& r : opt.rankings)
        std::cout << "    " << r.name << ": " << r.score << "\n";
}

// ===== Original Edge Case Tests =====

void testIdlePeriods() {
    std::cout << "\n--- Idle Periods ---\n";
    FCFSScheduler sched;
    std::vector<SchedulingProcess> p = {{1,"A",0,2,2,1},{2,"B",5,2,2,1}};
    auto r = sched.schedule(p);
    bool hasIdle = false;
    for (const auto& seg : r.ganttTimeline)
        if (seg.pid == -1) hasIdle = true;
    CHECK(hasIdle, "Idle: has IDLE segment");
}

void testSameArrival() {
    std::cout << "\n--- Same Arrival ---\n";
    FCFSScheduler sched;
    std::vector<SchedulingProcess> p = {{1,"A",0,5,5,1},{2,"B",0,3,3,1},{3,"C",0,1,1,1}};
    auto r = sched.schedule(p);
    Metrics::calculateAll(r);
    CHECK(r.avgWaitingTime >= 0, "Same arrival: valid WT");
}

void testPreemption() {
    std::cout << "\n--- Preemption ---\n";
    SRTFScheduler sched;
    std::vector<SchedulingProcess> p = {{1,"A",0,10,10,1},{2,"B",2,2,2,1}};
    auto r = sched.schedule(p);
    Metrics::calculateAll(r);
    CHECK(r.contextSwitches >= 1, "Preemption: SRTF preempts");
}

void testRRQuantum() {
    std::cout << "\n--- RR Quantum ---\n";
    std::vector<SchedulingProcess> p = {{1,"A",0,6,6,1},{2,"B",0,4,4,1}};
    RoundRobinScheduler rr1(1.0), rr4(4.0);
    auto r1 = rr1.schedule(p), r4 = rr4.schedule(p);
    Metrics::calculateAll(r1);
    Metrics::calculateAll(r4);
    CHECK(r1.contextSwitches >= r4.contextSwitches, "RR: smaller Q = more switches");
    std::cout << "  Q=1 switches=" << r1.contextSwitches << " Q=4 switches=" << r4.contextSwitches << "\n";
}

void testPriorityTies() {
    std::cout << "\n--- Priority Ties ---\n";
    PriorityScheduler sched;
    std::vector<SchedulingProcess> p = {{1,"A",0,3,3,1},{2,"B",0,2,2,1},{3,"C",0,4,4,1}};
    auto r = sched.schedule(p);
    CHECK(r.processes.size() == 3, "Priority ties: 3 scheduled");
}

void testSingleProcess() {
    std::cout << "\n--- Single Process ---\n";
    FCFSScheduler sched;
    std::vector<SchedulingProcess> p = {{1,"Solo",0,5,5,1}};
    auto r = sched.schedule(p);
    Metrics::calculateAll(r);
    CHECK_NEAR(r.avgWaitingTime, 0.0, 0.01, "Single: WT=0");
    CHECK_NEAR(r.cpuUtilization, 100.0, 0.01, "Single: CPU=100%");
}

void testEmptyInput() {
    std::cout << "\n--- Empty Input ---\n";
    FCFSScheduler sched;
    auto r = sched.schedule({});
    CHECK(r.processes.empty(), "Empty: no processes");
    CHECK(r.totalTime == 0.0, "Empty: totalTime=0");
}

// ===== NEW EDGE CASE TESTS (10 additional) =====

void testLargeWorkload() {
    std::cout << "\n--- Large Workload (20 processes) ---\n";
    std::vector<SchedulingProcess> procs;
    for (int i = 1; i <= 20; ++i)
        procs.push_back({i, "P" + std::to_string(i), (double)(i-1)*0.5, (double)i, (double)i, i % 5 + 1});
    FCFSScheduler sched;
    auto r = sched.schedule(procs);
    Metrics::calculateAll(r);
    CHECK(r.processes.size() == 20, "Large: 20 processes scheduled");
    CHECK(r.avgWaitingTime >= 0, "Large: valid waiting time");
    CHECK(r.cpuUtilization > 0 && r.cpuUtilization <= 100.0 + 1e-6, "Large: valid CPU util");
}

void testFractionalBurstTimes() {
    std::cout << "\n--- Fractional Burst Times ---\n";
    std::vector<SchedulingProcess> p = {
        {1, "A", 0.0, 2.5, 2.5, 1},
        {2, "B", 0.5, 1.5, 1.5, 1},
        {3, "C", 1.0, 0.7, 0.7, 1}
    };
    SRTFScheduler sched;
    auto r = sched.schedule(p);
    Metrics::calculateAll(r);
    CHECK(r.processes.size() == 3, "Fractional: 3 processes");
    CHECK(r.avgWaitingTime >= 0, "Fractional: valid WT");
    // Total burst = 4.7
    double totalBurst = 2.5 + 1.5 + 0.7;
    CHECK_NEAR(r.totalTime, totalBurst, 0.01, "Fractional: totalTime == sum of bursts");
    CHECK(r.avgTurnaroundTime > 0, "Fractional: positive TAT");
    std::cout << "  Fractional avgWT=" << r.avgWaitingTime << "\n";
}

void testZeroBurstGuard() {
    std::cout << "\n--- Zero / Very Small Burst Time ---\n";
    // A process with near-zero burst must not cause division by zero
    std::vector<SchedulingProcess> p = {{1, "Tiny", 0.0, 0.001, 0.001, 1}, {2, "Big", 0.0, 5.0, 5.0, 1}};
    FCFSScheduler sched;
    auto r = sched.schedule(p);
    Metrics::calculateAll(r);
    CHECK(r.processes.size() == 2, "Zero-burst guard: 2 scheduled");
    CHECK(r.fairnessIndex >= 0.0, "Zero-burst guard: fairness non-negative");
}

void testAllSamePriority() {
    std::cout << "\n--- All Same Priority ---\n";
    std::vector<SchedulingProcess> p = {
        {1, "A", 0.0, 4.0, 4.0, 2},
        {2, "B", 0.0, 4.0, 4.0, 2},
        {3, "C", 0.0, 4.0, 4.0, 2}
    };
    PriorityScheduler sched;
    auto r = sched.schedule(p);
    Metrics::calculateAll(r);
    CHECK(r.processes.size() == 3, "Same priority: 3 scheduled");
    // All arrive at 0 with equal burst/priority; order is FIFO tiebreak → waiting ≥ 0
    CHECK(r.avgWaitingTime >= 0, "Same priority: valid WT");
    std::cout << "  avgWT=" << r.avgWaitingTime << "\n";
}

void testRRLargeQuantum() {
    std::cout << "\n--- RR with Very Large Quantum (behaves like FCFS) ---\n";
    std::vector<SchedulingProcess> procs = {
        {1, "P1", 0.0, 3.0, 3.0, 1},
        {2, "P2", 0.0, 5.0, 5.0, 1},
        {3, "P3", 0.0, 2.0, 2.0, 1}
    };
    RoundRobinScheduler rr_big(1000.0);  // quantum >> burst → each runs to completion once
    FCFSScheduler fcfs;
    auto r_rr  = rr_big.schedule(procs);
    auto r_fc  = fcfs.schedule(procs);
    Metrics::calculateAll(r_rr);
    Metrics::calculateAll(r_fc);
    // With huge quantum every process runs once → same TAT as FCFS (or very close)
    CHECK_NEAR(r_rr.avgTurnaroundTime, r_fc.avgTurnaroundTime, 0.1,
               "RR(huge Q) avgTAT ≈ FCFS avgTAT");
}

void testSRTFManyShortArrivals() {
    std::cout << "\n--- SRTF: Many Short Arrivals ---\n";
    std::vector<SchedulingProcess> procs;
    // Long process that should be preempted by each short arrival
    procs.push_back({1, "Long", 0.0, 20.0, 20.0, 1});
    for (int i = 2; i <= 6; ++i)
        procs.push_back({i, "S" + std::to_string(i), (double)i, 1.0, 1.0, 1});
    SRTFScheduler sched;
    auto r = sched.schedule(procs);
    Metrics::calculateAll(r);
    CHECK(r.processes.size() == 6, "SRTF many short: 6 processes");
    CHECK(r.contextSwitches >= 5, "SRTF many short: at least 5 preemptions");
    std::cout << "  switches=" << r.contextSwitches << " avgWT=" << r.avgWaitingTime << "\n";
}

void testFairnessIndexRange() {
    std::cout << "\n--- Fairness Index in [0,1] ---\n";
    // Jain's fairness index must be in (0, 1]
    auto procs = testProcs();
    std::vector<std::unique_ptr<Scheduler>> scheds;
    scheds.push_back(std::make_unique<FCFSScheduler>());
    scheds.push_back(std::make_unique<RoundRobinScheduler>(2.0));
    scheds.push_back(std::make_unique<SRTFScheduler>());
    for (auto& s : scheds) {
        auto r = s->schedule(procs);
        Metrics::calculateAll(r);
        CHECK(r.fairnessIndex >= 0.0 && r.fairnessIndex <= 1.0 + 1e-6,
              r.algorithmName + ": fairness in [0,1]");
    }
}

void testThroughputSanity() {
    std::cout << "\n--- Throughput Sanity ---\n";
    // throughput = N / total_time → must equal processes / completion of last
    std::vector<SchedulingProcess> p = {{1, "A", 0.0, 4.0, 4.0, 1}, {2, "B", 0.0, 6.0, 6.0, 1}};
    FCFSScheduler sched;
    auto r = sched.schedule(p);
    Metrics::calculateAll(r);
    double expected_throughput = 2.0 / 10.0; // 2 procs / 10 time units
    CHECK_NEAR(r.throughput, expected_throughput, 0.01, "Throughput = N/total_time");
}

void testPriorityInversionDetection() {
    std::cout << "\n--- Priority Scheduling: High Priority Runs First ---\n";
    // P1 has lower priority number (= higher priority in most OS conventions)
    std::vector<SchedulingProcess> p = {
        {1, "LowP",  0.0, 5.0, 5.0, 5},   // low priority
        {2, "HighP", 0.0, 3.0, 3.0, 1}    // high priority (lower number = higher prio)
    };
    PriorityScheduler sched;
    auto r = sched.schedule(p);
    // High-priority process should complete first (completion ≤ its burst time from t=0)
    // Find the high-priority process in result
    bool highRanFirst = false;
    for (const auto& rp : r.processes) {
        if (rp.name == "HighP" && rp.completionTime <= 3.0 + 1e-6)
            highRanFirst = true;
    }
    CHECK(highRanFirst, "Priority: high-priority process completes first");
}

void testDeterminism() {
    std::cout << "\n--- Determinism: Same Input = Same Output ---\n";
    auto procs = testProcs();
    SJFScheduler sched;
    auto r1 = sched.schedule(procs);
    auto r2 = sched.schedule(procs);
    Metrics::calculateAll(r1);
    Metrics::calculateAll(r2);
    CHECK_NEAR(r1.avgWaitingTime, r2.avgWaitingTime, 1e-9, "Determinism: same avgWT");
    CHECK_NEAR(r1.avgTurnaroundTime, r2.avgTurnaroundTime, 1e-9, "Determinism: same avgTAT");
    CHECK(r1.contextSwitches == r2.contextSwitches, "Determinism: same context switches");
}

int main() {
    std::cout << "========================================\n";
    std::cout << "  CPU SCHEDULING - TEST SUITE\n";
    std::cout << "========================================\n";

    testFCFS();
    testSJF();
    testSRTF();
    testRoundRobin();
    testPriority();
    testMetrics();
    testOptimization();
    testIdlePeriods();
    testSameArrival();
    testPreemption();
    testRRQuantum();
    testPriorityTies();
    testSingleProcess();
    testEmptyInput();

    // New edge case tests
    testLargeWorkload();
    testFractionalBurstTimes();
    testZeroBurstGuard();
    testAllSamePriority();
    testRRLargeQuantum();
    testSRTFManyShortArrivals();
    testFairnessIndexRange();
    testThroughputSanity();
    testPriorityInversionDetection();
    testDeterminism();

    std::cout << "\n========================================\n";
    std::cout << "  RESULTS: " << passed << " passed, " << failed << " failed\n";
    std::cout << "========================================\n";

    return failed > 0 ? 1 : 0;
}
