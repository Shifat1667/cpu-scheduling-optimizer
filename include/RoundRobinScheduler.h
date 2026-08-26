#pragma once
#include "Scheduler.h"

class RoundRobinScheduler : public Scheduler {
public:
    explicit RoundRobinScheduler(double quantum = 2.0);
    SchedulingResult schedule(const std::vector<SchedulingProcess>& processes) override;
    std::string getName() const override;

private:
    double quantum_;
};
