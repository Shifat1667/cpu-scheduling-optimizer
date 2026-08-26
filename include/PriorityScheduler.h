#pragma once
#include "Scheduler.h"

class PriorityScheduler : public Scheduler {
public:
    SchedulingResult schedule(const std::vector<SchedulingProcess>& processes) override;
    std::string getName() const override { return "Priority"; }
};
