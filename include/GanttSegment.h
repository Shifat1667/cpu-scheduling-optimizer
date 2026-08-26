#pragma once

#include <string>

struct GanttSegment {
    int pid = -1;             // -1 = IDLE
    std::string processName;  // "IDLE" for idle segments
    double startTime = 0.0;
    double endTime = 0.0;
};
