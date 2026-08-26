import psutil
import time
import copy
from gui import (
    collect_processes, get_system_stats, detect_bottlenecks,
    classify_workload, build_sched_workload, sched_fcfs,
    sched_sjf, sched_srtf, sched_rr, sched_priority, calc_sched_metrics,
    suggest_optimizations
)

def print_banner(title):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)

def main():
    print_banner("1. Live System Telemetry & Process Monitoring")
    sys_stats = get_system_stats()
    print(f"System CPU Usage : {sys_stats['cpu_percent']:.1f}%")
    print(f"System Memory    : {sys_stats['mem_used_gb']:.2f} GB used / {sys_stats['mem_total_gb']:.2f} GB total ({sys_stats['mem_percent']:.1f}%)")
    print(f"Memory Available : {sys_stats['mem_available_gb']:.2f} GB")

    print("\nScanning OS processes (collecting delta CPU ticks)...")
    procs, cpu_count = collect_processes()
    print(f"Detected {len(procs)} active processes across {cpu_count} logical CPU cores.")

    print("\nTop 5 CPU-Consuming Processes:")
    top_cpu = sorted(procs, key=lambda x: x['cpu'], reverse=True)[:5]
    print(f"{'PID':<8} | {'Process Name':<28} | {'State':<6} | {'CPU%':<8} | {'Memory (MB)':<12} | {'Priority':<12}")
    print("-" * 84)
    for p in top_cpu:
        print(f"{p['pid']:<8} | {p['name']:<28} | {p['state']:<6} | {p['cpu']:<7.1f}% | {p['mem_mb']:<12.1f} | {p['priority_name']:<12}")

    print_banner("2. Workload Classification & Bottleneck Diagnostics")
    workload = classify_workload(procs, sys_stats)
    print(f"Workload Type       : {workload['type']}")
    print(f"Active Processes    : {workload['count']} total (Running: {workload['running']}, Sleeping/Waiting: {workload['sleeping']})")
    print(f"I/O Bound Processes : {workload['io_bound']}")
    print(f"Interactive Procs   : {workload['interactive']}")

    bottlenecks = detect_bottlenecks(procs, sys_stats)
    if bottlenecks:
        print("\nIdentified Bottlenecks:")
        for b in bottlenecks:
            print(f"  * [{b['severity']}] {b['type']}: {b['description']}")
    else:
        print("\nNo critical hardware bottlenecks detected.")

    optimizations = suggest_optimizations(procs, bottlenecks, workload)
    if optimizations:
        print("\nRecommended OS Process Optimizations (Safe):")
        for opt in optimizations[:3]:
            print(f"  * PID {opt['pid']} ({opt['name']}): {opt['action']} -> {opt['recommended']} ({opt['reason']})")

    print_banner("3. Real Process Scheduling Simulation (5 Algorithms)")
    sched_procs = build_sched_workload(procs)
    print(f"Derived {len(sched_procs)} scheduling workloads from active OS processes:")
    print(f"{'PID':<8} | {'Process Name':<28} | {'Arrival':<8} | {'Burst Time':<12} | {'Priority':<8}")
    print("-" * 72)
    for p in sched_procs[:6]:
        print(f"{p['pid']:<8} | {p['name']:<28} | {p['arrival']:<8.1f} | {p['burst']:<12.1f} | {p['priority']:<8}")
    if len(sched_procs) > 6:
        print(f"  ... and {len(sched_procs)-6} more processes.")

    algorithms = [
        ("FCFS", lambda p: sched_fcfs(p)),
        ("SJF (Non-preemptive)", lambda p: sched_sjf(p)),
        ("SRTF (Preemptive)", lambda p: sched_srtf(p)),
        ("Round Robin (Q=2.0)", lambda p: sched_rr(p, 2.0)),
        ("Priority Scheduling", lambda p: sched_priority(p)),
    ]

    results = []
    print("\n" + f"{'Algorithm':<24} | {'Avg Wait':<10} | {'Avg TAT':<10} | {'Avg Resp':<10} | {'CPU Util':<10} | {'Throughput':<12} | {'Switches':<8} | {'Fairness':<8}")
    print("-" * 110)

    for name, fn in algorithms:
        p_copy = copy.deepcopy(sched_procs)
        ps, sw, g, tb, tt = fn(p_copy)
        m = calc_sched_metrics(ps, sw, tb, tt)
        results.append((name, m, g))
        print(f"{name:<24} | {m['avg_wait']:10.2f} | {m['avg_tat']:10.2f} | {m['avg_resp']:10.2f} | {m['cpu_util']:9.1f}% | {m['throughput']:10.3f}/u | {m['switches']:8d} | {m['fairness']:8.4f}")

    print_banner("4. Multi-Criteria Optimization Engine & Winner")
    min_wait = min(r[1]['avg_wait'] for r in results) or 1.0
    min_tat = min(r[1]['avg_tat'] for r in results) or 1.0
    min_resp = min(r[1]['avg_resp'] for r in results) or 1.0
    max_util = max(r[1]['cpu_util'] for r in results) or 1.0
    max_fair = max(r[1]['fairness'] for r in results) or 1.0

    scored = []
    for name, m, g in results:
        score_wait = (min_wait / max(0.01, m['avg_wait'])) * 25
        score_tat = (min_tat / max(0.01, m['avg_tat'])) * 25
        score_resp = (min_resp / max(0.01, m['avg_resp'])) * 20
        score_util = (m['cpu_util'] / max(0.01, max_util)) * 15
        score_fair = (m['fairness'] / max(0.01, max_fair)) * 15
        total_score = score_wait + score_tat + score_resp + score_util + score_fair
        scored.append((name, total_score, m, g))

    scored.sort(key=lambda x: x[1], reverse=True)

    print("Rankings (Score out of 100):")
    for rank, (name, score, m, g) in enumerate(scored, 1):
        star = " * [RECOMMENDED]" if rank == 1 else ""
        print(f"  {rank}. {name:<24} : {score:5.1f} / 100{star}")

    best_name, best_score, best_m, best_g = scored[0]
    print(f"\nRecommendation Analysis:")
    print(f"  -> Selected '{best_name}' as optimal scheduler for the current {workload['type']} workload.")
    print(f"  -> Average Waiting Time  : {best_m['avg_wait']:.2f} time units")
    print(f"  -> Average Turnaround    : {best_m['avg_tat']:.2f} time units")
    print(f"  -> Average Response Time : {best_m['avg_resp']:.2f} time units")
    print(f"  -> Fairness Index        : {best_m['fairness']:.4f}")

    print_banner(f"5. Gantt Timeline Visualization ({best_name})")
    timeline_str = " | ".join(f"[{seg['start']:.1f}-{seg['end']:.1f}: {seg['name'][:10]}]" for seg in best_g[:8])
    if len(best_g) > 8:
        timeline_str += f" ... + {len(best_g)-8} more segments"
    print(timeline_str)
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
