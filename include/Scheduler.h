#pragma once

#include "SchedulingProcess.h"
#include "SchedulingResult.h"
#include <vector>
#include <string>

// Abstract base class for all scheduling algorithms.
// Each algorithm takes a list of SchedulingProcess and produces a SchedulingResult
// containing the analyzed schedule, metrics, and Gantt timeline.
class Scheduler {
public:
    virtual ~Scheduler() = default;
    virtual SchedulingResult schedule(const std::vector<SchedulingProcess>& processes) = 0;
    virtual std::string getName() const = 0;
};
