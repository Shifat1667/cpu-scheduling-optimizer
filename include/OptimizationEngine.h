#pragma once

#include "SchedulingResult.h"
#include "WorkloadAnalyzer.h"
#include <vector>
#include <string>

// === CONFIGURABLE WEIGHTS (single location) ===
// All optimization weights are defined here. Do NOT scatter magic numbers elsewhere.
struct OptimizationWeights {
    double waitingTime = 0.25;        // 25%
    double responseTime = 0.25;       // 25%
    double turnaroundTime = 0.15;     // 15%
    double cpuUtilization = 0.15;     // 15%
    double fairness = 0.10;           // 10%
    double contextSwitchOverhead = 0.10; // 10%
};

struct AlgorithmRanking {
    std::string name;
    double score = 0.0;
};

struct OptimizationResult {
    std::string recommendedAlgorithm;
    double recommendedScore = 0.0;
    std::vector<AlgorithmRanking> rankings;
    std::string explanation;
    WorkloadAnalysis workloadAnalysis;
};

// OptimizationEngine: The CORE module of the project.
//
// Pipeline:
//   1. Takes real workload data
//   2. Runs all five scheduling algorithms
//   3. Collects metrics from each
//   4. Normalizes metrics (lower-is-better vs higher-is-better)
//   5. Calculates weighted optimization score
//   6. Ranks algorithms
//   7. Recommends the best one with dynamic explanation
//
// The recommendation is NEVER hardcoded. It depends entirely on the current workload.
class OptimizationEngine {
public:
    OptimizationResult optimize(const std::vector<SchedulingResult>& results,
                                const WorkloadAnalysis& workload);

    void setWeights(const OptimizationWeights& w) { weights_ = w; }
    OptimizationWeights getWeights() const { return weights_; }

private:
    OptimizationWeights weights_;

    // Normalization: protects against zero and division by zero
    double normalizeLowerBetter(double value, double best);
    double normalizeHigherBetter(double value, double best);

    // Dynamic explanation generation based on actual metric results
    std::string generateExplanation(const AlgorithmRanking& best,
                                    const WorkloadAnalysis& workload,
                                    const std::vector<SchedulingResult>& results);
};
