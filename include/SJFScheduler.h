#pragma once
#include "Scheduler.h"

class SJFScheduler : public Scheduler {
public:
    SchedulingResult schedule(const std::vector<SchedulingProcess>& processes) override;
    std::string getName() const override { return "SJF"; }
};
