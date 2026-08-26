from fpdf import FPDF

class ProjectReport(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 8, "CPU Scheduling Optimization and Process Monitoring System", align="C")
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def stitle(self, title, num=""):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(41, 98, 255)
        self.cell(0, 10, f"{num}  {title}" if num else title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(41, 98, 255)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def sub(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(60, 60, 60)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def txt(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def blt(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.set_x(self.l_margin)
        self.multi_cell(0, 5.5, "  - " + text)

    def code(self, text):
        self.set_font("Courier", "", 9)
        self.set_fill_color(240, 240, 245)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, text, fill=True)
        self.ln(3)

    def th(self, headers, widths):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(41, 98, 255)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()

    def tr(self, data, widths, hl=False):
        self.set_font("Helvetica", "", 9)
        self.set_fill_color(230, 240, 255) if hl else self.set_fill_color(255, 255, 255)
        self.set_text_color(40, 40, 40)
        for i, d in enumerate(data):
            self.cell(widths[i], 6, str(d), border=1, fill=True, align="C")
        self.ln()


pdf = ProjectReport()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)

# TITLE PAGE
pdf.add_page()
pdf.ln(40)
pdf.set_font("Helvetica", "B", 28)
pdf.set_text_color(41, 98, 255)
pdf.multi_cell(0, 12, "CPU Scheduling Optimization\nand Process Monitoring System", align="C")
pdf.ln(10)
pdf.set_draw_color(41, 98, 255)
pdf.line(50, pdf.get_y(), 160, pdf.get_y())
pdf.ln(10)
pdf.set_font("Helvetica", "", 13)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 8, "Operating Systems Course Project", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(5)
pdf.set_font("Helvetica", "", 11)
pdf.cell(0, 7, "C++ Implementation with CMake Build System", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 7, "C++17 Standard", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(20)
pdf.set_font("Helvetica", "I", 10)
pdf.set_text_color(120, 120, 120)
pdf.cell(0, 7, "Built with GCC 16.1.0 via MSYS2 on Windows", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 7, "Target Platform: Linux (primary) / Windows (compatibility)", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(30)
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(60, 60, 60)
pdf.cell(0, 7, "Project Location: C:\\Users\\foysa\\cpu-scheduling-optimizer", align="C", new_x="LMARGIN", new_y="NEXT")

# TABLE OF CONTENTS
pdf.add_page()
pdf.stitle("Table of Contents")
toc = [
    ("1", "Introduction and Problem Statement"),
    ("2", "Project Objectives"),
    ("3", "System Architecture"),
    ("4", "Linux Process Monitoring via /proc"),
    ("5", "C++ System Calls and OS Interfaces"),
    ("6", "Data Models"),
    ("7", "Scheduling Algorithms"),
    ("8", "Performance Metrics"),
    ("9", "Optimization Engine"),
    ("10", "Workload Classification"),
    ("11", "Algorithm Test Results"),
    ("12", "Real System Test Results"),
    ("13", "Build Instructions"),
    ("14", "Limitations"),
    ("15", "Viva Preparation - Key OS Concepts"),
]
for num, title in toc:
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(10, 7, num + ".")
    pdf.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")

# 1. INTRODUCTION
pdf.add_page()
pdf.stitle("Introduction and Problem Statement", "1")
pdf.txt(
    "Operating systems use CPU scheduling algorithms to determine which process runs "
    "on the CPU at any given time. The choice of algorithm significantly impacts system "
    "performance metrics such as waiting time, turnaround time, response time, CPU "
    "utilization, and fairness."
)
pdf.txt(
    "This project implements a CPU Scheduling Optimization and Process Monitoring System that:"
)
pdf.blt("Collects actual process information from the OS using C++ system calls")
pdf.blt("Analyzes the real workload and classifies its characteristics")
pdf.blt("Runs five classical CPU scheduling algorithms against the workload")
pdf.blt("Calculates comprehensive performance metrics for each algorithm")
pdf.blt("Normalizes and scores each algorithm using a weighted optimization model")
pdf.blt("Recommends the best scheduling strategy with a dynamic explanation")
pdf.ln(3)
pdf.txt(
    "IMPORTANT: This system monitors actual OS processes but does NOT replace or "
    "modify the Linux kernel CPU scheduler. The scheduling algorithms are used for "
    "analysis, comparison, and optimization only."
)

# 2. OBJECTIVES
pdf.stitle("Project Objectives", "2")
pdf.blt("Demonstrate practical knowledge of system calls and OS interfaces")
pdf.blt("Implement all five classical CPU scheduling algorithms")
pdf.blt("Calculate and compare scheduling metrics (7 metrics)")
pdf.blt("Build an optimization engine that scores and recommends the best algorithm")
pdf.blt("Monitor real system processes safely (read-only)")
pdf.blt("Provide a terminal UI for interaction")
pdf.blt("Use C++17 with CMake build system")
pdf.blt("Write comprehensive tests (35 test cases)")

# 3. ARCHITECTURE
pdf.add_page()
pdf.stitle("System Architecture", "3")
pdf.sub("Module Overview")
pdf.txt(
    "The system consists of six major modules:\n\n"
    "1. ProcessMonitor - Collects real process information from the OS\n"
    "2. Scheduling Algorithms (5 classes) - FCFS, SJF, SRTF, RR, Priority\n"
    "3. Metrics Calculator - Computes 7 performance metrics\n"
    "4. Workload Analyzer - Classifies the system workload type\n"
    "5. Optimization Engine - Scores, ranks, and recommends algorithms\n"
    "6. Terminal UI / GUI - User interface for interaction"
)

pdf.sub("Data Flow")
pdf.code(
    "OS Processes -> ProcessMonitor -> ProcessInfo[]\n"
    "                                        |\n"
    "                              WorkloadAnalyzer\n"
    "                                        |\n"
    "                         SchedulingProcess[]\n"
    "                          |    |    |    |    |\n"
    "                        FCFS SJF SRTF  RR  Priority\n"
    "                          |    |    |    |    |\n"
    "                       SchedulingResult[]\n"
    "                                        |\n"
    "                              Metrics.calculateAll()\n"
    "                                        |\n"
    "                              OptimizationEngine\n"
    "                                        |\n"
    "                              OptimizationResult"
)

pdf.sub("File Structure (28 files)")
pdf.code(
    "include/          14 header files\n"
    "src/              10 source files (incl. main.cpp)\n"
    "tests/            1 test file (35 test cases)\n"
    "docs/             1 architecture document\n"
    "CMakeLists.txt    Build configuration"
)

# 4. /proc
pdf.add_page()
pdf.stitle("Linux Process Monitoring via /proc", "4")
pdf.txt(
    "Linux provides direct access to process information through the /proc virtual "
    "filesystem. This is a pseudo-filesystem that exists only in memory and provides "
    "an interface to kernel data structures."
)

pdf.sub("Key /proc Files")
w = [50, 140]
pdf.th(["File", "Purpose"], w)
pdf.tr(["/proc/[pid]/stat", "Process status: CPU times, priority, state"], w)
pdf.tr(["/proc/[pid]/status", "Process memory and thread info"], w, True)
pdf.tr(["/proc/[pid]/cmdline", "Command line arguments"], w)
pdf.tr(["/proc/stat", "System-wide CPU statistics"], w, True)
pdf.tr(["/proc/meminfo", "System memory information"], w)
pdf.ln(3)

pdf.sub("Parsing /proc/[pid]/stat")
pdf.txt(
    "The stat file contains a single line with space-separated fields. Fields 14 "
    "and 15 contain user and kernel CPU time in clock ticks. Field 18 is priority, "
    "field 19 is nice value, field 21 is start time. The process name is in parentheses."
)

pdf.sub("Process Disappearance Handling")
pdf.txt(
    "Processes can terminate during collection. The system handles this gracefully:"
)
pdf.code(
    "try {\n"
    "    ProcessInfo info = parseLinuxProcStat(pid);\n"
    "    if (info.pid > 0 && !info.name.empty())\n"
    "        processes.push_back(info);\n"
    "} catch (...) {\n"
    "    continue;  // Skip disappeared process\n"
    "}"
)

# 5. SYSTEM CALLS
pdf.add_page()
pdf.stitle("C++ System Calls and OS Interfaces", "5")

pdf.sub("Linux Interfaces")
w2 = [55, 135]
pdf.th(["Interface", "Purpose"], w2)
pdf.tr(["/proc/[pid]/stat", "Read process CPU times, priority, state"], w2)
pdf.tr(["/proc/[pid]/status", "Read process memory usage"], w2, True)
pdf.tr(["/proc/stat", "Read system-wide CPU times"], w2)
pdf.tr(["/proc/meminfo", "Read system memory info"], w2, True)
pdf.tr(["std::filesystem", "Discover /proc/[pid] directories"], w2)
pdf.tr(["getpid() / getppid()", "Get process/parent IDs"], w2, True)
pdf.tr(["sysconf()", "Get system configuration"], w2)
pdf.tr(["clock_gettime()", "High-resolution timing"], w2, True)
pdf.ln(3)

pdf.sub("Windows Interfaces")
pdf.th(["Interface", "Purpose"], w2)
pdf.tr(["EnumProcesses()", "Discover running process IDs"], w2)
pdf.tr(["OpenProcess()", "Get handle to a process"], w2, True)
pdf.tr(["GetProcessMemoryInfo()", "Read process memory usage"], w2)
pdf.tr(["GetProcessTimes()", "Read process CPU times"], w2, True)
pdf.tr(["QueryFullProcessImageNameA()", "Read process name"], w2)
pdf.tr(["GlobalMemoryStatusEx()", "Read system memory"], w2, True)

# 6. DATA MODELS
pdf.add_page()
pdf.stitle("Data Models", "6")
pdf.sub("ProcessInfo (Real OS Data)")
pdf.txt(
    "This struct stores actual data collected from the operating system. It contains "
    "fields that correspond directly to /proc or WinAPI data."
)
pdf.code(
    "struct ProcessInfo {\n"
    "    int pid;                    // Process ID\n"
    "    int parentPid;              // Parent process ID\n"
    "    std::string name;           // Process name\n"
    "    char state;                 // R=Running, S=Sleeping\n"
    "    long priority;              // Kernel priority\n"
    "    long niceValue;             // Nice value (-20 to 19)\n"
    "    unsigned long userTime;     // User CPU time (ticks)\n"
    "    unsigned long kernelTime;   // Kernel CPU time (ticks)\n"
    "    unsigned long startTime;    // Process start time\n"
    "    unsigned long virtualMemory;// Virtual memory size\n"
    "    long residentMemory;        // Physical memory (RSS)\n"
    "    int threadCount;            // Number of threads\n"
    "    double cpuUsage;            // CPU utilization %\n"
    "};"
)

pdf.sub("SchedulingProcess (Textbook Model)")
pdf.txt(
    "This struct represents a process for scheduling analysis. Real OS processes "
    "do not have clean 'arrival time' and 'burst time' values, so these are estimated."
)
pdf.code(
    "struct SchedulingProcess {\n"
    "    int pid;\n"
    "    std::string name;\n"
    "    double arrivalTime;  // Estimated from start time\n"
    "    double burstTime;    // Estimated from CPU time\n"
    "    double remainingTime;// For preemptive algorithms\n"
    "    int priority;        // From OS priority/nice\n"
    "    double firstStartTime;\n"
    "    double completionTime;\n"
    "    double turnaroundTime; // CT - AT\n"
    "    double waitingTime;    // TAT - BT\n"
    "    double responseTime;   // First start - AT\n"
    "};"
)

# 7. SCHEDULING ALGORITHMS
pdf.add_page()
pdf.stitle("Scheduling Algorithms", "7")

pdf.sub("7.1 FCFS (First Come First Serve)")
pdf.txt("Non-preemptive. Processes executed in arrival order. Simple but can cause convoy effect.")
pdf.blt("Sort processes by arrival time")
pdf.blt("Execute each process to completion")
pdf.blt("Handle idle periods when no process has arrived")
pdf.ln(2)

pdf.sub("7.2 SJF (Shortest Job First)")
pdf.txt("Non-preemptive. Selects shortest burst time. Optimal for minimizing average waiting time.")
pdf.blt("At each step, select shortest burst among available")
pdf.blt("Handle ties using arrival time")
pdf.blt("Skip idle periods")
pdf.ln(2)

pdf.sub("7.3 SRTF (Shortest Remaining Time First)")
pdf.txt("Preemptive SJF. Minimum remaining execution time. Records preemptions.")
pdf.blt("At each time unit, check for newly arrived processes")
pdf.blt("Preempt if shorter process arrives")
pdf.blt("Track context switches")
pdf.ln(2)

pdf.sub("7.4 Round Robin")
pdf.txt("Preemptive with configurable quantum (default Q=2). Each process gets a time slice.")
pdf.blt("Use a FIFO ready queue")
pdf.blt("Execute min(quantum, remainingTime) per turn")
pdf.blt("Smaller quantum = more context switches, better response time")
pdf.ln(2)

pdf.sub("7.5 Priority Scheduling")
pdf.txt("Non-preemptive. Lower numerical priority = higher priority. Ties broken by arrival time.")
pdf.blt("Select highest priority (lowest number) available process")
pdf.blt("Handle ties using arrival time")

# 8. METRICS
pdf.add_page()
pdf.stitle("Performance Metrics", "8")

w3 = [40, 55, 95]
pdf.th(["Metric", "Formula", "Purpose"], w3)
pdf.tr(["Completion", "When process finishes", "Total execution time"], w3)
pdf.tr(["Turnaround", "CT - AT", "Total time in system"], w3, True)
pdf.tr(["Waiting", "TAT - BT", "Time spent waiting"], w3)
pdf.tr(["Response", "First start - AT", "Time to first response"], w3, True)
pdf.tr(["CPU Util", "Busy/Total x 100", "CPU efficiency %"], w3)
pdf.tr(["Throughput", "Count / Total time", "Work completion rate"], w3, True)
pdf.tr(["Fairness", "Jain's index (0-1)", "Equity of service"], w3)
pdf.ln(3)

pdf.sub("Jain's Fairness Index")
pdf.code(
    "Fairness = (sum)^2 / (n * sum_of_squares)\n"
    "Example: waiting = [0, 7, 10, 11]\n"
    "  sum=28, sum_sq=270\n"
    "  Fairness = 784 / 1080 = 0.7259"
)

# 9. OPTIMIZATION
pdf.add_page()
pdf.stitle("Optimization Engine", "9")
pdf.txt(
    "The optimization engine compares all five algorithms and recommends the best "
    "one based on measurable performance metrics."
)

pdf.sub("Weighting Configuration")
w4 = [80, 50, 60]
pdf.th(["Metric", "Weight", "Direction"], w4)
pdf.tr(["Average Waiting Time", "25%", "Lower=Better"], w4)
pdf.tr(["Average Response Time", "25%", "Lower=Better"], w4, True)
pdf.tr(["Average Turnaround Time", "15%", "Lower=Better"], w4)
pdf.tr(["CPU Utilization", "15%", "Higher=Better"], w4, True)
pdf.tr(["Fairness", "10%", "Higher=Better"], w4)
pdf.tr(["Context Switch Overhead", "10%", "Lower=Better"], w4, True)
pdf.ln(3)

pdf.sub("Normalization")
pdf.code(
    "Lower-is-better: score = bestValue / currentValue\n"
    "Higher-is-better: score = currentValue / bestValue\n"
    "Protected against division by zero."
)

pdf.sub("Final Score")
pdf.code(
    "Final = (wait*ws + resp*rs + turn*ts + cpu*cs + fair*fs + swt*ss) * 100\n"
    "Result: 0-100 scale. Highest score recommended.\n"
    "Explanation generated dynamically from metrics."
)

# 10. WORKLOAD
pdf.add_page()
pdf.stitle("Workload Classification", "10")

w5 = [40, 150]
pdf.th(["Type", "Condition"], w5)
pdf.tr(["Light", "< 20 processes"], w5)
pdf.tr(["Medium", "20-100 processes"], w5, True)
pdf.tr(["Heavy", "> 100 processes"], w5)
pdf.tr(["CPU-Bound", "> 50% high CPU usage"], w5, True)
pdf.tr(["I/O-Bound", "> 50% low CPU usage"], w5)
pdf.tr(["Interactive", "> 40% moderate CPU"], w5, True)
pdf.tr(["Mixed", "Active + sleeping"], w5)

# 11. TEST RESULTS
pdf.add_page()
pdf.stitle("Algorithm Test Results", "11")
pdf.txt("Test processes:")
pdf.code(
    "P1: Arrival=0, Burst=8, Priority=2\n"
    "P2: Arrival=1, Burst=4, Priority=1\n"
    "P3: Arrival=2, Burst=2, Priority=3\n"
    "P4: Arrival=3, Burst=1, Priority=2"
)

pdf.sub("Results")
w6 = [32, 28, 30, 28, 25, 27]
pdf.th(["Algo", "Avg Wait", "Avg TAT", "Avg Resp", "CPU%", "Switch"], w6)
pdf.tr(["FCFS", "7.00", "10.75", "7.00", "100", "3"], w6)
pdf.tr(["SJF", "5.50", "9.25", "5.50", "100", "3"], w6, True)
pdf.tr(["SRTF", "2.75", "6.50", "0.25", "100", "5"], w6)
pdf.tr(["RR(Q=2)", "5.00", "8.75", "2.00", "100", "6"], w6, True)
pdf.tr(["Priority", "6.75", "10.50", "6.75", "100", "3"], w6)
pdf.ln(5)

pdf.sub("Optimization Scores")
w7 = [60, 50]
pdf.th(["Algorithm", "Score"], w7)
pdf.tr(["SRTF", "91.8 / 100"], w7, True)
pdf.tr(["Round Robin", "58.0 / 100"], w7)
pdf.tr(["SJF", "57.1 / 100"], w7, True)
pdf.tr(["Priority", "53.7 / 100"], w7)
pdf.tr(["FCFS", "53.1 / 100"], w7, True)
pdf.ln(3)
pdf.txt("Recommended: SRTF (91.8/100)")

# 12. REAL SYSTEM RESULTS
pdf.add_page()
pdf.stitle("Real System Test Results", "12")
pdf.txt(
    "Tested on a real Windows machine with 98 active processes."
)

pdf.sub("Results on Real Data")
w8 = [32, 28, 28, 28, 25, 27]
pdf.th(["Algo", "Avg Wait", "Avg TAT", "Avg Resp", "CPU%", "Switch"], w8)
pdf.tr(["FCFS", "24.15", "28.37", "24.15", "100", "14"], w8)
pdf.tr(["SJF", "18.07", "22.30", "18.07", "100", "14"], w8, True)
pdf.tr(["SRTF", "18.07", "22.30", "18.07", "100", "14"], w8)
pdf.tr(["RR(Q=2)", "33.87", "38.10", "10.97", "100", "40"], w8, True)
pdf.tr(["Priority", "24.15", "28.37", "24.15", "100", "14"], w8)
pdf.ln(3)
pdf.txt("Recommended: SJF (87.2/100)")

# 13. BUILD
pdf.add_page()
pdf.stitle("Build Instructions", "13")
pdf.sub("Prerequisites")
pdf.blt("C++17 compiler (GCC, Clang, or MSVC)")
pdf.blt("CMake 3.16+")
pdf.ln(2)

pdf.sub("Build Commands")
pdf.code(
    "cmake -S . -B build\n"
    "cmake --build build\n\n"
    "./build/cpu_scheduler      # Linux\n"
    ".\\build\\cpu_scheduler.exe  # Windows\n\n"
    "./build/test_runner        # Run tests"
)

pdf.sub("Build Outputs")
w9 = [60, 130]
pdf.th(["File", "Description"], w9)
pdf.tr(["cpu_scheduler.exe", "Main application"], w9)
pdf.tr(["test_runner.exe", "Test suite (35 tests)"], w9, True)
pdf.tr(["*.dll (x3)", "MSYS2 runtime deps"], w9)

# 14. LIMITATIONS
pdf.add_page()
pdf.stitle("Limitations", "14")
pdf.blt("/proc reading only works on Linux; Windows uses alternative APIs")
pdf.blt("Real OS does not expose textbook burst times directly")
pdf.blt("Analyzes workload but does not control the kernel scheduler")
pdf.blt("CPU usage accuracy depends on measurement interval")
pdf.blt("Short-lived processes may disappear during collection")
pdf.blt("Single snapshot approximation on non-Linux systems")

# 15. VIVA
pdf.add_page()
pdf.stitle("Viva Preparation - Key OS Concepts", "15")

pdf.sub("CPU Scheduling")
pdf.blt("Why scheduling? CPU is shared; scheduler decides who runs when")
pdf.blt("Preemptive vs Non-preemptive: Can OS interrupt a running process?")
pdf.blt("Context Switch: Save/restore state when switching processes")
pdf.blt("Turnaround Time: Submission to completion")
pdf.blt("Waiting Time: Time in ready queue")
pdf.blt("Response Time: Submission to first execution")
pdf.ln(2)

pdf.sub("Process Management")
pdf.blt("PCB: Kernel data structure storing process state")
pdf.blt("Process States: Running, Ready, Blocked, Terminated")
pdf.blt("System Calls: Interface between user and kernel")
pdf.blt("/proc: Virtual filesystem exposing kernel data")
pdf.ln(2)

pdf.sub("Memory Management")
pdf.blt("Virtual Memory: Each process has own address space")
pdf.blt("RSS: Physical memory currently used")
pdf.blt("Virtual Size: Total address space including swap")
pdf.ln(2)

pdf.sub("Optimization")
pdf.blt("Jain's Fairness Index: Equity of resource distribution")
pdf.blt("Normalization: Scale metrics to comparable ranges")
pdf.blt("Multi-criteria optimization: Weighted scoring")

# SAVE
output_path = r"C:\Users\foysa\cpu-scheduling-optimizer\CPU_Scheduling_Project_Report.pdf"
pdf.output(output_path)
print(f"PDF saved to: {output_path}")
print(f"Total pages: {pdf.page_no()}")
