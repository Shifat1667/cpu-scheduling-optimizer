#pragma once
#include "Scheduler.h"

class FCFSScheduler : public Scheduler {
public:
    SchedulingResult schedule(const std::vector<SchedulingProcess>& processes) override;
    std::string getName() const override { return "FCFS"; }
};
