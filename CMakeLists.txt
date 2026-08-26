cmake_minimum_required(VERSION 3.16)
project(cpu_scheduler VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ── Build type defaults ──────────────────────────────────────────────────────
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Release" CACHE STRING "Build type" FORCE)
endif()

# ── Compiler warning flags ───────────────────────────────────────────────────
if(MSVC)
    add_compile_options(/W4 /WX- /permissive-)
else()
    add_compile_options(
        -Wall -Wextra -Wpedantic
        -Wno-unused-parameter    # suppress common false positives in headers
    )
    if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        add_compile_options(-fsanitize=address,undefined)
        add_link_options(-fsanitize=address,undefined)
    endif()
endif()

# ── Release optimisation ─────────────────────────────────────────────────────
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    add_compile_definitions(NDEBUG)
endif()

# ── Source lists ─────────────────────────────────────────────────────────────
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

# ── Main application ─────────────────────────────────────────────────────────
add_executable(cpu_scheduler
    src/main.cpp
    src/ProcessMonitor.cpp
    ${SCHEDULER_SOURCES}
    ${HEADERS}
)
target_include_directories(cpu_scheduler PRIVATE include)

# Link psapi on Windows (required for GetProcessMemoryInfo)
if(WIN32)
    target_link_libraries(cpu_scheduler PRIVATE psapi)
endif()

# ── Test runner ──────────────────────────────────────────────────────────────
add_executable(test_runner
    tests/test_all.cpp
    ${SCHEDULER_SOURCES}
    src/ProcessMonitor.cpp
    ${HEADERS}
)
target_include_directories(test_runner PRIVATE include)

if(WIN32)
    target_link_libraries(test_runner PRIVATE psapi)
endif()

# ── CTest integration ────────────────────────────────────────────────────────
enable_testing()
add_test(NAME AllTests COMMAND test_runner)
set_tests_properties(AllTests PROPERTIES TIMEOUT 30)

