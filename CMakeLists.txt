cmake_minimum_required(VERSION 3.16)
project(cpu_scheduler LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(HEADERS
    include/ProcessInfo.h
    include/SchedulingProcess.h
    include/SchedulingResult.h
    include/GanttSegment.h
    include/ProcessMonitor.h
    include/Scheduler.h
    include/FCFSScheduler.h
    include/SJFScheduler.h
    include/SRTFScheduler.h
    include/RoundRobinScheduler.h
    include/PriorityScheduler.h
    include/Metrics.h
    include/WorkloadAnalyzer.h
    include/OptimizationEngine.h
)

set(SCHEDULER_SOURCES
    src/FCFSScheduler.cpp
    src/SJFScheduler.cpp
    src/SRTFScheduler.cpp
    src/RoundRobinScheduler.cpp
    src/PriorityScheduler.cpp
    src/Metrics.cpp
    src/OptimizationEngine.cpp
    src/WorkloadAnalyzer.cpp
)

add_executable(cpu_scheduler
    src/main.cpp
    src/ProcessMonitor.cpp
    ${SCHEDULER_SOURCES}
    ${HEADERS}
)
target_include_directories(cpu_scheduler PRIVATE include)

add_executable(test_runner
    tests/test_all.cpp
    ${SCHEDULER_SOURCES}
    src/ProcessMonitor.cpp
    ${HEADERS}
)
target_include_directories(test_runner PRIVATE include)
