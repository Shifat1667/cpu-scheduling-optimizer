#include "ProcessMonitor.h"
#include <fstream>
#include <sstream>
#include <filesystem>
#include <algorithm>
#include <thread>
#include <chrono>

#ifdef __linux__
#include <dirent.h>
#include <unistd.h>
#endif

#ifdef _WIN32
#include <windows.h>
#include <psapi.h>
#include <tlhelp32.h>
#endif

ProcessMonitor::ProcessMonitor()
    : initialized_(false), prevTotalCpu_(0), prevIdleCpu_(0) {}

bool ProcessMonitor::hasRealProcData() const {
#ifdef __linux__
    return std::filesystem::exists("/proc/stat");
#else
    return false;
#endif
}

// ============================================================
// LINUX IMPLEMENTATION: reads /proc filesystem directly
// ============================================================
#ifdef __linux__

void ProcessMonitor::readLinuxCpuTimes(unsigned long& total, unsigned long& idle) {
    std::ifstream f("/proc/stat");
    std::string line;
    std::getline(f, line);
    std::istringstream iss(line);
    std::string cpu;
    unsigned long user = 0, nice = 0, system = 0, idleTime = 0, iowait = 0, irq = 0, softirq = 0, steal = 0;
    iss >> cpu >> user >> nice >> system >> idleTime >> iowait >> irq >> softirq >> steal;
    total = user + nice + system + idleTime + iowait + irq + softirq + steal;
    idle = idleTime + iowait;
}

ProcessInfo ProcessMonitor::parseLinuxProcStat(int pid) {
    ProcessInfo info;
    info.pid = pid;

    // Read /proc/[pid]/stat
    std::string statPath = "/proc/" + std::to_string(pid) + "/stat";
    std::ifstream f(statPath);
    if (!f.is_open()) return info;

    std::string line;
    if (!std::getline(f, line)) return info;

    // Parse name (inside parentheses) and remaining fields
    size_t openP = line.find('(');
    size_t closeP = line.rfind(')');
    if (openP == std::string::npos || closeP == std::string::npos) return info;

    info.name = line.substr(openP + 1, closeP - openP - 1);
    std::istringstream iss(line.substr(closeP + 2));

    // Fields after the name: 3=state, 4=ppid, 14=utime, 15=stime,
    // 17=nthreads, 18=priority, 19=nice, 22=starttime
    for (int field = 3; field <= 22; ++field) {
        std::string token;
        if (!(iss >> token)) break;
        try {
            switch (field) {
                case 3:  info.state = token[0]; break;
                case 4:  info.parentPid = std::stoi(token); break;
                case 14: info.userTime = std::stoul(token); break;
                case 15: info.kernelTime = std::stoul(token); break;
                case 17: info.threadCount = std::stoi(token); break;
                case 18: info.priority = std::stol(token); break;
                case 19: info.niceValue = std::stol(token); break;
                case 22: info.startTime = std::stoul(token); break;
            }
        } catch (...) {}
    }

    // Read /proc/[pid]/status for memory
    std::string statusPath = "/proc/" + std::to_string(pid) + "/status";
    std::ifstream sf(statusPath);
    if (sf.is_open()) {
        std::string sline;
        while (std::getline(sf, sline)) {
            if (sline.compare(0, 6, "VmSize") == 0) {
                std::istringstream si(sline.substr(6));
                long val; std::string unit;
                si >> val >> unit;
                info.virtualMemory = val * 1024;
            } else if (sline.compare(0, 6, "VmRSS:") == 0) {
                std::istringstream si(sline.substr(6));
                long val; std::string unit;
                si >> val >> unit;
                info.residentMemory = val * 1024;
            }
        }
    }

    return info;
}

std::vector<ProcessInfo> ProcessMonitor::getProcesses() {
    std::vector<ProcessInfo> procs;
    for (const auto& entry : std::filesystem::directory_iterator("/proc")) {
        if (!entry.is_directory()) continue;
        std::string name = entry.path().filename().string();
        bool isPid = true;
        for (char c : name) {
            if (!std::isdigit(c)) { isPid = false; break; }
        }
        if (!isPid) continue;
        try {
            int pid = std::stoi(name);
            ProcessInfo info = parseLinuxProcStat(pid);
            if (info.pid > 0 && !info.name.empty()) {
                procs.push_back(info);
            }
        } catch (...) { continue; } // Process disappeared during read
    }
    return procs;
}

double ProcessMonitor::getSystemCpuUsage() {
    unsigned long total, idle;
    readLinuxCpuTimes(total, idle);

    if (!initialized_) {
        prevTotalCpu_ = total;
        prevIdleCpu_ = idle;
        initialized_ = true;
        return 0.0;
    }

    unsigned long dt = total - prevTotalCpu_;
    unsigned long di = idle - prevIdleCpu_;
    prevTotalCpu_ = total;
    prevIdleCpu_ = idle;

    if (dt == 0) return 0.0;
    return (1.0 - static_cast<double>(di) / dt) * 100.0;
}

double ProcessMonitor::getMemoryUsage() {
    std::ifstream f("/proc/meminfo");
    if (!f.is_open()) return 0.0;
    unsigned long total = 0, available = 0, free = 0;
    std::string key;
    unsigned long val;
    while (f >> key >> val) {
        if (key == "MemTotal:") total = val;
        else if (key == "MemAvailable:") available = val;
        else if (key == "MemFree:") free = val;
    }
    if (total == 0) return 0.0;
    unsigned long used = (available > 0) ? (total - available) : (total - free);
    return (static_cast<double>(used) / total) * 100.0;
}

ProcessInfo ProcessMonitor::getProcessInfo(int pid) {
    return parseLinuxProcStat(pid);
}

int ProcessMonitor::getProcessCount() {
    return static_cast<int>(getProcesses().size());
}

int ProcessMonitor::getTotalThreads() {
    int total = 0;
    for (const auto& p : getProcesses()) total += p.threadCount;
    return total;
}

void ProcessMonitor::takeSnapshot() {
    getSystemCpuUsage(); // just reads and stores current state
}

#endif

// ============================================================
// WINDOWS IMPLEMENTATION: uses WinAPI (for testing on Windows)
// ============================================================
#ifdef _WIN32

std::vector<ProcessInfo> ProcessMonitor::getProcesses() {
    return getWindowsProcesses();
}

std::vector<ProcessInfo> ProcessMonitor::getWindowsProcesses() {
    std::vector<ProcessInfo> procs;
    DWORD pids[2048], cbNeeded;
    if (!EnumProcesses(pids, sizeof(pids), &cbNeeded)) return procs;

    DWORD count = cbNeeded / sizeof(DWORD);
    for (DWORD i = 0; i < count; ++i) {
        HANDLE hProc = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pids[i]);
        if (!hProc) continue;

        ProcessInfo info;
        info.pid = pids[i];

        // FIX: Use wide-character API to handle Unicode process names correctly
        wchar_t nameBuf[MAX_PATH];
        DWORD nameLen = MAX_PATH;
        if (QueryFullProcessImageNameW(hProc, 0, nameBuf, &nameLen)) {
            std::wstring full(nameBuf);
            size_t pos = full.find_last_of(L"\\/");
            std::wstring wname = (pos != std::wstring::npos) ? full.substr(pos + 1) : full;
            // Convert UTF-16 to UTF-8 for storage
            int sz = WideCharToMultiByte(CP_UTF8, 0, wname.c_str(), -1, nullptr, 0, nullptr, nullptr);
            if (sz > 0) {
                std::string narrow(sz - 1, '\0');
                WideCharToMultiByte(CP_UTF8, 0, wname.c_str(), -1, &narrow[0], sz, nullptr, nullptr);
                info.name = narrow;
            } else {
                info.name = "pid_" + std::to_string(pids[i]);
            }
        } else {
            info.name = "pid_" + std::to_string(pids[i]);
        }

        PROCESS_MEMORY_COUNTERS pmc;
        if (GetProcessMemoryInfo(hProc, &pmc, sizeof(pmc))) {
            info.virtualMemory = pmc.PagefileUsage;
            info.residentMemory = pmc.WorkingSetSize;
        }

        FILETIME ct, et, kt, ut;
        if (GetProcessTimes(hProc, &ct, &et, &kt, &ut)) {
            ULARGE_INTEGER ktU, utU;
            ktU.LowPart = kt.dwLowDateTime; ktU.HighPart = kt.dwHighDateTime;
            utU.LowPart = ut.dwLowDateTime; utU.HighPart = ut.dwHighDateTime;
            info.kernelTime = ktU.QuadPart / 10000;
            info.userTime = utU.QuadPart / 10000;
        }

        DWORD exitCode;
        info.state = (GetExitCodeProcess(hProc, &exitCode) && exitCode == STILL_ACTIVE) ? 'R' : 'Z';

        // Get actual thread count from snapshot
        HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
        if (hSnap != INVALID_HANDLE_VALUE) {
            THREADENTRY32 te;
            te.dwSize = sizeof(te);
            int threadCount = 0;
            if (Thread32First(hSnap, &te)) {
                do {
                    if (te.th32OwnerProcessID == pids[i]) ++threadCount;
                } while (Thread32Next(hSnap, &te));
            }
            CloseHandle(hSnap);
            info.threadCount = threadCount > 0 ? threadCount : 1;
        } else {
            info.threadCount = 1;
        }

        info.priority = 0;
        procs.push_back(info);
        CloseHandle(hProc);
    }
    return procs;
}

double ProcessMonitor::getSystemCpuUsage() {
    FILETIME idleTime, kernelTime, userTime;
    if (!GetSystemTimes(&idleTime, &kernelTime, &userTime)) return 0.0;

    auto toUL = [](const FILETIME& ft) -> ULARGE_INTEGER {
        ULARGE_INTEGER u; u.LowPart = ft.dwLowDateTime; u.HighPart = ft.dwHighDateTime; return u;
    };

    ULARGE_INTEGER iIdle = toUL(idleTime), iKernel = toUL(kernelTime), iUser = toUL(userTime);
    unsigned long total = iKernel.QuadPart + iUser.QuadPart;
    unsigned long idle = iIdle.QuadPart;

    if (!initialized_) {
        prevTotalCpu_ = total;
        prevIdleCpu_ = idle;
        initialized_ = true;
        return 0.0;
    }

    unsigned long dt = total - prevTotalCpu_;
    unsigned long di = idle - prevIdleCpu_;
    prevTotalCpu_ = total;
    prevIdleCpu_ = idle;

    if (dt == 0) return 0.0;
    return (1.0 - static_cast<double>(di) / dt) * 100.0;
}

double ProcessMonitor::getMemoryUsage() {
    MEMORYSTATUSEX mem;
    mem.dwLength = sizeof(mem);
    if (GlobalMemoryStatusEx(&mem)) return static_cast<double>(mem.dwMemoryLoad);
    return 0.0;
}

ProcessInfo ProcessMonitor::getProcessInfo(int pid) {
    ProcessInfo info;
    info.pid = pid;
    return info;
}

int ProcessMonitor::getProcessCount() {
    return static_cast<int>(getProcesses().size());
}

int ProcessMonitor::getTotalThreads() {
    int total = 0;
    for (const auto& p : getProcesses()) total += p.threadCount;
    return total;
}

void ProcessMonitor::takeSnapshot() {
    getSystemCpuUsage();
}

#endif
