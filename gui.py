"""
Real-Time CPU Scheduling & Process Optimization System  v1.0
=============================================================
Collects real OS process data, detects bottlenecks, applies safe
optimizations (priority adjustment), and measures Before/After results.

Features
--------
- Live process table with search/filter
- 5 scheduling algorithms: FCFS, SJF, SRTF, Round Robin, Priority
- Gantt chart with actual preemptive segments
- Multi-metric radar chart for algorithm comparison
- Algorithm weight editor (customize optimization scoring)
- Simulation mode (custom process input)
- CSV/JSON export
- Keyboard shortcuts: F5=Scan, F6=Schedule, Ctrl+O=Optimize, Ctrl+Q=Quit

Keyboard shortcuts
------------------
  F5          Refresh System Scan
  F6          Run Scheduling Analysis
  Ctrl+O      Optimize System
  Ctrl+E      Export results (CSV)
  Ctrl+Q      Quit
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import threading
import ctypes
import os
import csv
import json
import datetime
import math
import time
import sys

import psutil

import matplotlib
matplotlib.use("TkAgg")

# Enable high-DPI awareness on Windows to prevent canvas blur/clipping
try:
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# ── Colour Palette (Enterprise Obsidian Edition) ──────────────────────────────
BG_DARK      = "#05050a"
BG_PANEL     = "#0f0f1a"
BG_CARD      = "#161625"
BG_INPUT     = "#1d1d33"
FG_PRIMARY   = "#ffffff"
FG_SECONDARY = "#a0a0c0"
FG_DIM       = "#606080"
ACCENT_BLUE  = "#3b82f6"
ACCENT_CYAN  = "#06b6d4"
ACCENT_GREEN = "#10b981"
ACCENT_PINK  = "#ec4899"
ACCENT_AMBER = "#f59e0b"
ACCENT_PURPLE= "#8b5cf6"
ACCENT_RED   = "#ef4444"
BORDER       = "#25253d"

ALGO_COLORS = {"FCFS":"#4fc3f7","SJF":"#69f0ae","SRTF":"#ff4081",
               "Round Robin":"#ffd740","Priority Scheduling":"#b388ff"}

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ── Windows API for priority adjustment ──────────────────────────────────
PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_INFORMATION = 0x0400
HIGH_PRIORITY_CLASS    = 0x00000080
ABOVE_NORMAL_PRIORITY  = 0x00008000
NORMAL_PRIORITY_CLASS  = 0x00000020
BELOW_NORMAL_PRIORITY  = 0x00004000
IDLE_PRIORITY_CLASS    = 0x00000040

PRIORITY_MAP = {
    "High":           HIGH_PRIORITY_CLASS,
    "Above Normal":   ABOVE_NORMAL_PRIORITY,
    "Normal":         NORMAL_PRIORITY_CLASS,
    "Below Normal":   BELOW_NORMAL_PRIORITY,
    "Low (Idle)":     IDLE_PRIORITY_CLASS,
}
PRIORITY_NAMES = list(PRIORITY_MAP.keys())

kernel32 = ctypes.windll.kernel32

def is_admin():
    """Check if running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def set_process_priority(pid, priority_name):
    """Set a process priority via Windows API. Returns True on success."""
    if priority_name not in PRIORITY_MAP:
        return False
    try:
        handle = kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)
        if not handle:
            return False
        result = kernel32.SetPriorityClass(handle, PRIORITY_MAP[priority_name])
        kernel32.CloseHandle(handle)
        return bool(result)
    except Exception:
        return False

# System/service processes that always need admin
ADMIN_REQUIRED_NAMES = {
    'memcompression', 'msmpeng.exe', 'officeclicktorun.exe', 'searchindexer.exe',
    'spoolsv.exe', 'wmiprvse.exe', 'dllhost.exe', 'wudfhost.exe',
    'trustedinstaller.exe', 'tiworker.exe', 'sppsvc.exe', 'tokenserver.exe',
    'audiodg.exe', 'dashost.exe', 'hpcommhelper.exe', 'hp cm status server',
}

def get_process_priority_name(pid):
    """Read current priority class name of a process."""
    try:
        p = psutil.Process(pid)
        nice = p.nice()
        if nice <= -8:   return "High"
        if nice <= -2:   return "Above Normal"
        if nice <= 2:    return "Normal"
        if nice <= 7:    return "Below Normal"
        return "Low (Idle)"
    except Exception:
        return "Normal"


# ══════════════════════════════════════════════════════════════════════════
#  DATA COLLECTION
# ══════════════════════════════════════════════════════════════════════════

def collect_processes():
    """Collect real OS processes with normalized CPU%."""
    cpu_count = psutil.cpu_count(logical=True) or 1
    # Prime cpu_percent counter, then wait for real delta
    for p in psutil.process_iter(['cpu_percent']):
        try: p.cpu_percent()
        except: pass
    time.sleep(0.8)
    procs = []
    attrs = ['pid','name','status','cpu_percent','memory_info','nice','num_threads']
    for p in psutil.process_iter(attrs):
        try:
            info = p.info
            mem = info.get('memory_info')
            raw_cpu = info.get('cpu_percent') or 0.0
            normalized_cpu = min(raw_cpu / cpu_count, 100.0)
            mem_bytes = mem.rss if mem else 0
            nice = info.get('nice') or 0
            if nice <= -8: pname = "High"
            elif nice <= -2: pname = "Above Normal"
            elif nice <= 2: pname = "Normal"
            elif nice <= 7: pname = "Below Normal"
            else: pname = "Low (Idle)"
            try:
                switches = p.num_ctx_switches()
                ctx_switches = switches.voluntary + switches.involuntary
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                ctx_switches = 0
            procs.append({
                'pid': info['pid'],
                'name': (info.get('name') or 'unknown')[:40],
                'state': (info.get('status') or 'R')[0],
                'cpu_raw': raw_cpu,
                'cpu': normalized_cpu,
                'mem_bytes': mem_bytes,
                'mem_mb': mem_bytes / 1048576,
                'priority_name': pname,
                'nice': nice,
                'threads': info.get('num_threads') or 1,
                'ctx_switches': ctx_switches,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return procs, cpu_count

def get_system_stats():
    """Get system-wide CPU and memory stats."""
    cpu = psutil.cpu_percent(interval=0.2)
    mem = psutil.virtual_memory()
    return {
        'cpu_percent': cpu,
        'mem_percent': mem.percent,
        'mem_used_gb': mem.used / (1024**3),
        'mem_total_gb': mem.total / (1024**3),
        'mem_available_gb': mem.available / (1024**3),
    }

def detect_bottlenecks(procs, sys_stats):
    """Identify system bottlenecks."""
    bottlenecks = []

    # CPU bottleneck
    if sys_stats['cpu_percent'] > 70:
        top_cpu = sorted(procs, key=lambda x: x['cpu'], reverse=True)[:3]
        bottlenecks.append({
            'type': 'CPU',
            'severity': 'HIGH' if sys_stats['cpu_percent'] > 85 else 'MEDIUM',
            'value': sys_stats['cpu_percent'],
            'top_processes': top_cpu,
            'description': f"System CPU at {sys_stats['cpu_percent']:.1f}%"
        })

    # Memory bottleneck
    if sys_stats['mem_percent'] > 75:
        top_mem = sorted(procs, key=lambda x: x['mem_mb'], reverse=True)[:3]
        bottlenecks.append({
            'type': 'MEMORY',
            'severity': 'HIGH' if sys_stats['mem_percent'] > 90 else 'MEDIUM',
            'value': sys_stats['mem_percent'],
            'top_processes': top_mem,
            'description': f"System memory at {sys_stats['mem_percent']:.1f}%"
        })

    # High-context-switch processes
    high_ctx = [p for p in procs if p['ctx_switches'] > 10000]
    if high_ctx:
        high_ctx.sort(key=lambda x: x['ctx_switches'], reverse=True)
        bottlenecks.append({
            'type': 'CONTEXT_SWITCHES',
            'severity': 'MEDIUM',
            'value': high_ctx[0]['ctx_switches'],
            'top_processes': high_ctx[:3],
            'description': f"{len(high_ctx)} processes with excessive context switches"
        })

    return bottlenecks

def classify_workload(procs, sys_stats):
    n = len(procs)
    if n == 0: return {'type':'Empty','count':0}
    cpu_b = sum(1 for p in procs if p['cpu'] > 30)
    io_b = sum(1 for p in procs if p['cpu'] < 1)
    inter = sum(1 for p in procs if 1 <= p['cpu'] <= 30)
    running = sum(1 for p in procs if p['state'] == 'R')

    if sys_stats['cpu_percent'] > 70: wtype = "CPU-Bound"
    elif io_b > n * 0.5: wtype = "I/O-Bound"
    elif inter > n * 0.4: wtype = "Interactive"
    elif running > 0 and (n - running) > 0: wtype = "Mixed"
    elif n < 20: wtype = "Light"
    elif n < 100: wtype = "Medium"
    else: wtype = "Heavy"

    return {
        'type': wtype, 'count': n,
        'cpu_bound': cpu_b, 'io_bound': io_b, 'interactive': inter,
        'running': running, 'sleeping': n - running,
        'sys_cpu': sys_stats['cpu_percent'], 'sys_mem': sys_stats['mem_percent'],
    }

def suggest_optimizations(procs, bottlenecks, workload):
    """Suggest safe OS-level optimizations. Never touch protected processes."""
    PROTECTED_PIDS = {0, 1, 2, 3, 4}
    PROTECTED_NAMES = {
        'system', 'system idle process', 'registry', 'smss.exe', 'csrss.exe',
        'wininit.exe', 'winlogon.exe', 'lsass.exe', 'services.exe',
        'svchost.exe', 'svchost', 'dcomlaunch', 'rpcss', 'plugplay',
        'conhost.exe', 'dwm.exe', 'fontdrvhost', 'sihost.exe',
        'taskhostw.exe', 'dashost.exe', 'spoolsv.exe', 'searchindexer.exe',
        'applicationframehost.exe', 'shellexperiencehost.exe',
        'startmenuexperiencehost.exe', 'textinputhost.exe', 'runtimebroker.exe',
        'ctfmon.exe', 'securityhealthservice.exe', 'securityhealthsystray.exe',
    }
    suggestions = []
    has_mem_bottleneck = any(b['type'] == 'MEMORY' for b in bottlenecks)

    for p in procs:
        if p['pid'] in PROTECTED_PIDS: continue
        if p['name'].lower() in PROTECTED_NAMES: continue
        if p['name'].lower().startswith('svchost'): continue
        if p['name'].lower() in ADMIN_REQUIRED_NAMES: continue

        cpu = p['cpu']
        mem_mb = p['mem_mb']
        prio = p['priority_name']
        threads = p['threads']

        if cpu > 15 and prio in ('Normal', 'Above Normal', 'High'):
            target = 'Below Normal' if cpu < 40 else 'Low (Idle)'
            suggestions.append({
                'pid': p['pid'], 'name': p['name'],
                'action': 'Lower priority (CPU)', 'current': prio, 'recommended': target,
                'reason': f"CPU {cpu:.1f}% — reducing priority frees CPU for interactive tasks",
                'expected_effect': f"Lower CPU contention",
            })
        elif has_mem_bottleneck and mem_mb > 200 and prio in ('Normal', 'Above Normal'):
            suggestions.append({
                'pid': p['pid'], 'name': p['name'],
                'action': 'Lower priority (Memory)', 'current': prio, 'recommended': 'Below Normal',
                'reason': f"Using {mem_mb:.0f} MB — reducing priority reduces pressure on memory manager",
                'expected_effect': f"Better memory scheduling",
            })
        elif threads > 15 and cpu < 1.0 and prio == 'Normal':
            suggestions.append({
                'pid': p['pid'], 'name': p['name'],
                'action': 'Lower priority (Threads)', 'current': prio, 'recommended': 'Below Normal',
                'reason': f"{threads} threads but idle — background process should yield",
                'expected_effect': f"Free thread scheduler capacity",
            })
        elif prio == 'Above Normal' and cpu < 10:
            suggestions.append({
                'pid': p['pid'], 'name': p['name'],
                'action': 'Normalize priority', 'current': prio, 'recommended': 'Normal',
                'reason': f"Above Normal but only {cpu:.1f}% CPU — unnecessary priority elevation",
                'expected_effect': f"Fairer scheduling",
            })

    suggestions.sort(key=lambda x: (
        0 if 'CPU' in x['action'] else 1 if 'Memory' in x['action'] else 2,
        -next((p['cpu'] for p in procs if p['pid']==x['pid']), 0)
    ))
    return suggestions[:15]

def apply_optimization(pid, recommended):
    """Apply priority change via Windows API."""
    return set_process_priority(pid, recommended)

def measure_improvement(num_samples=3, interval=1.0):
    """Take multiple CPU/memory samples and return averages."""
    samples = []
    for _ in range(num_samples):
        cpu = psutil.cpu_percent(interval=interval)
        mem = psutil.virtual_memory().percent
        samples.append({'cpu': cpu, 'mem': mem})
    avg_cpu = sum(s['cpu'] for s in samples) / len(samples)
    avg_mem = sum(s['mem'] for s in samples) / len(samples)
    return {'cpu': avg_cpu, 'mem': avg_mem}

# ── Scheduling Algorithms ────────────────────────────────────────────────
def _sched_reset(procs):
    for p in procs:
        p['remaining'] = p['burst']
        p['first_start'] = -1.0
        p['completion'] = 0.0

def sched_fcfs(procs):
    _sched_reset(procs)
    ps = sorted(procs, key=lambda x: x['arrival'])
    t = 0.0; sw = 0; g = []
    for p in ps:
        if t < p['arrival']:
            g.append({'pid':-1,'name':'IDLE','start':t,'end':p['arrival']})
            t = p['arrival']
        if p['first_start'] < 0: p['first_start'] = t
        g.append({'pid':p['pid'],'name':p['name'],'start':t,'end':t+p['burst']})
        t += p['burst']; p['completion'] = t; sw += 1
    for p in ps:
        p['turnaround'] = p['completion'] - p['arrival']
        p['waiting'] = p['turnaround'] - p['burst']
        p['response'] = (p['first_start'] if p['first_start']>=0 else 0) - p['arrival']
    tb = sum(p['burst'] for p in ps); tt = max((p['completion'] for p in ps), default=0)
    return ps, sw, g, tb, tt

def sched_sjf(procs):
    _sched_reset(procs)
    ps = list(procs); t = 0.0; done = []; sw = 0; g = []
    while len(done) < len(ps):
        avail = [p for p in ps if p['arrival'] <= t and p not in done]
        if not avail:
            nxt = min((p for p in ps if p not in done), key=lambda x: x['arrival'])
            g.append({'pid':-1,'name':'IDLE','start':t,'end':nxt['arrival']})
            t = nxt['arrival']; continue
        pick = min(avail, key=lambda x: (x['burst'], x['arrival']))
        if pick['first_start'] < 0: pick['first_start'] = t
        g.append({'pid':pick['pid'],'name':pick['name'],'start':t,'end':t+pick['burst']})
        t += pick['burst']; pick['completion'] = t; done.append(pick); sw += 1
    for p in ps:
        p['turnaround'] = p['completion'] - p['arrival']
        p['waiting'] = p['turnaround'] - p['burst']
        p['response'] = (p['first_start'] if p['first_start']>=0 else 0) - p['arrival']
    tb = sum(p['burst'] for p in ps); tt = max((p['completion'] for p in ps), default=0)
    return ps, sw, g, tb, tt

def sched_srtf(procs):
    _sched_reset(procs)
    ps = list(procs); t = 0.0; done = []; sw = 0; g = []; last = None
    while len(done) < len(ps):
        avail = [p for p in ps if p['arrival'] <= t and p not in done]
        if not avail:
            nxt = min((p for p in ps if p not in done), key=lambda x: x['arrival'])
            g.append({'pid':-1,'name':'IDLE','start':t,'end':nxt['arrival']})
            t = nxt['arrival']; continue
        pick = min(avail, key=lambda x: (x['remaining'], x['arrival']))
        if pick['first_start'] < 0: pick['first_start'] = t
        if last != pick['pid']: sw += 1; last = pick['pid']
        nxt_arr = [p for p in ps if p['arrival'] > t and p not in done]
        run = min(pick['remaining'], (min(p['arrival'] for p in nxt_arr) - t) if nxt_arr else pick['remaining'])
        g.append({'pid':pick['pid'],'name':pick['name'],'start':t,'end':t+run})
        pick['remaining'] -= run; t += run
        if pick['remaining'] <= 1e-9: pick['completion'] = t; done.append(pick)
    for p in ps:
        p['turnaround'] = p['completion'] - p['arrival']
        p['waiting'] = p['turnaround'] - p['burst']
        p['response'] = (p['first_start'] if p['first_start']>=0 else 0) - p['arrival']
    tb = sum(p['burst'] for p in ps); tt = max((p['completion'] for p in ps), default=0)
    return ps, sw, g, tb, tt

def sched_rr(procs, quantum=2.0):
    _sched_reset(procs)
    ps = list(procs); t = 0.0; sw = 0; g = []; rem = list(ps)
    q = [p for p in sorted(rem, key=lambda x: x['arrival']) if p['arrival'] <= t]
    for p in q: rem.remove(p)
    while q or rem:
        if not q:
            nxt = rem.pop(0)
            g.append({'pid':-1,'name':'IDLE','start':t,'end':nxt['arrival']})
            t = nxt['arrival']; q.append(nxt); continue
        cur = q.pop(0)
        if cur['first_start'] < 0: cur['first_start'] = t
        run = min(quantum, cur['remaining'])
        g.append({'pid':cur['pid'],'name':cur['name'],'start':t,'end':t+run})
        cur['remaining'] -= run; t += run; sw += 1
        new_arr = [p for p in rem if p['arrival'] <= t]
        for p in new_arr:
            if p not in q and p['remaining'] > 1e-9: q.append(p)
            if p in rem: rem.remove(p)
        if cur['remaining'] > 1e-9: q.append(cur)
        else: cur['completion'] = t
    for p in ps:
        p['turnaround'] = p['completion'] - p['arrival']
        p['waiting'] = p['turnaround'] - p['burst']
        p['response'] = (p['first_start'] if p['first_start']>=0 else 0) - p['arrival']
    tb = sum(p['burst'] for p in ps); tt = max((p['completion'] for p in ps), default=0)
    return ps, sw, g, tb, tt

def sched_priority(procs):
    _sched_reset(procs)
    ps = list(procs); t = 0.0; done = []; sw = 0; g = []
    while len(done) < len(ps):
        avail = [p for p in ps if p['arrival'] <= t and p not in done]
        if not avail:
            nxt = min((p for p in ps if p not in done), key=lambda x: x['arrival'])
            g.append({'pid':-1,'name':'IDLE','start':t,'end':nxt['arrival']})
            t = nxt['arrival']; continue
        pick = min(avail, key=lambda x: (x['priority'], x['arrival']))
        if pick['first_start'] < 0: pick['first_start'] = t
        g.append({'pid':pick['pid'],'name':pick['name'],'start':t,'end':t+pick['burst']})
        t += pick['burst']; pick['completion'] = t; done.append(pick); sw += 1
    for p in ps:
        p['turnaround'] = p['completion'] - p['arrival']
        p['waiting'] = p['turnaround'] - p['burst']
        p['response'] = (p['first_start'] if p['first_start']>=0 else 0) - p['arrival']
    tb = sum(p['burst'] for p in ps); tt = max((p['completion'] for p in ps), default=0)
    return ps, sw, g, tb, tt

def calc_sched_metrics(ps, sw, tb, tt):
    n = len(ps)
    if n == 0 or tt == 0:
        return {'avg_wait':0,'avg_tat':0,'avg_resp':0,'cpu_util':0,'throughput':0,'switches':0,'fairness':0}
    aw = sum(p['waiting'] for p in ps)/n
    at = sum(p['turnaround'] for p in ps)/n
    ar = sum(p['response'] for p in ps)/n
    cu = (tb/tt)*100; th = n/tt
    vals = [max(0.001, p['burst']/max(0.001, p['turnaround'])) for p in ps]
    s = sum(vals); ss = sum(v*v for v in vals)
    fair = (s*s)/(n*ss) if ss > 0 else 0
    return {'avg_wait':aw,'avg_tat':at,'avg_resp':ar,'cpu_util':cu,
            'throughput':th,'switches':sw,'fairness':fair}

def build_sched_workload(procs):
    """Build scheduling workload from real processes."""
    # Include any process with measurable CPU or in running state
    active = [p for p in procs if p['cpu'] > 0.0 or p['state'] in ('R', 'r')]
    if not active:
        # Fallback: take top 15 by memory if no CPU data
        active = sorted(procs, key=lambda x: x['mem_mb'], reverse=True)[:15]
    active.sort(key=lambda x: x['cpu'], reverse=True)
    sched = []
    for i, p in enumerate(active[:15]):
        burst = max(1.0, p['cpu'] * 2 + (p['pid'] % 10))
        sched.append({
            'pid': i+1, 'name': p['name'][:16], 'arrival': 0.0,
            'burst': burst, 'remaining': burst,
            'priority': max(1, abs(p['nice']) % 5 + 1),
            'first_start': -1.0, 'completion': 0.0,
            'turnaround': 0.0, 'waiting': 0.0, 'response': 0.0,
        })
    return sched

def run_scheduling_analysis(sched_procs):
    import copy
    fns = {'FCFS':sched_fcfs,'SJF':sched_sjf,'SRTF':sched_srtf,
           'Round Robin (Q=2)':lambda p:sched_rr(copy.deepcopy(p),2.0),'Priority Scheduling':sched_priority}
    results = {}
    for name, fn in fns.items():
        ps, sw, g, tb, tt = fn(copy.deepcopy(sched_procs))
        m = calc_sched_metrics(ps, sw, tb, tt)
        results[name] = {'rows':ps,'metrics':m,'gantt':g}
    return results


# ══════════════════════════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════════════════════════

class SchedulingGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CPU Scheduling Optimizer PRO")
        self.geometry("1440x900")
        self.minsize(1200, 700)
        self.configure(bg=BG_DARK)

        self.processes = []
        self.sys_stats = {}
        self.bottlenecks = []
        self.workload = {}
        self.suggestions = []
        self.sched_results = {}
        self.before_stats = {}
        self.after_stats = {}
        self.optimized_pids = set()
        self.history = []
        self.top_metric = "memory"
        self.opt_event_index = None
        self.trend_data = {"xs": [], "cpu": [], "mem": [], "times": []}
        self.before_snapshot = None
        self.actions_record = []

        self._styles()
        self._build_ui()
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass
        self.after(2000, self._sample_loop)
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # ── Keyboard shortcuts ────────────────────────────────────────────────
        self.bind("<F5>",          lambda _: self._scan())
        self.bind("<F6>",          lambda _: self._sched())
        self.bind("<Control-o>",   lambda _: self._optimize())
        self.bind("<Control-e>",   lambda _: self._export_csv())
        self.bind("<Control-q>",   lambda _: self.quit())
        self.bind("<Control-w>",   lambda _: self._edit_weights())

        self.log("System initialized. Ready for workload analysis.", "info")
        self.log("Shortcuts: F5=Scan  F6=Schedule  Ctrl+O=Optimize  Ctrl+E=Export  Ctrl+W=Weights", "debug")

    def _styles(self):
        s = ttk.Style(self); s.theme_use("clam")
        s.configure(".", background=BG_DARK, foreground=FG_PRIMARY, borderwidth=0)
        s.configure("TFrame", background=BG_DARK)
        s.configure("TLabel", background=BG_DARK, foreground=FG_PRIMARY, font=("Segoe UI", 11))
        s.configure("Header.TLabel", font=("Segoe UI", 20, "bold"), foreground=ACCENT_CYAN, background=BG_DARK)
        s.configure("Sub.TLabel", font=("Segoe UI", 12), foreground=FG_SECONDARY, background=BG_DARK)
        s.configure("Eyebrow.TLabel", font=("Segoe UI", 10, "bold"), foreground=ACCENT_PURPLE, background=BG_DARK)
        s.configure("Custom.Treeview", background=BG_CARD, foreground=FG_PRIMARY,
                     fieldbackground=BG_CARD, borderwidth=0, rowheight=34, font=("Consolas", 11))
        s.configure("Custom.Treeview.Heading", background=BG_PANEL, foreground=ACCENT_CYAN,
                     font=("Segoe UI", 10, "bold"), borderwidth=0)
        s.map("Custom.Treeview", background=[("selected", ACCENT_BLUE)], foreground=[("selected", "#000")])
        s.configure("Custom.TNotebook", background=BG_DARK, borderwidth=0)
        s.configure("Custom.TNotebook.Tab", background=BG_PANEL, foreground=FG_PRIMARY,
                     font=("Segoe UI", 11, "bold"), padding=(20, 10))
        s.map("Custom.TNotebook.Tab", background=[("selected", BG_CARD)], foreground=[("selected", ACCENT_CYAN)])

    def _build_ui(self):
        # Main Container
        main_container = tk.Frame(self, bg=BG_DARK)
        main_container.pack(fill="both", expand=True)

        # Top Header — fluid height so titles and the status note can never be clipped
        header = tk.Frame(main_container, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill="x", side="top")

        header_inner = tk.Frame(header, bg=BG_PANEL)
        header_inner.pack(fill="both", expand=True, padx=24, pady=14)
        header_inner.columnconfigure(1, weight=1)
        header_inner.rowconfigure(0, weight=1)

        title_f = tk.Frame(header_inner, bg=BG_PANEL)
        title_f.grid(row=0, column=0, sticky="w")
        ttk.Label(title_f, text="CPU SCHEDULING OPTIMIZER PRO", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(title_f, text="System Resource Optimization Tool", style="Header.TLabel").pack(anchor="w")
        ttk.Label(title_f, text="Real-time process telemetry  ·  Scheduling simulation  ·  Safe priority optimization",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 0))
        
        status_wrap = tk.Frame(header_inner, bg=BG_PANEL)
        status_wrap.grid(row=0, column=1, sticky="nsew")
        status_wrap.columnconfigure(0, weight=1)
        self.status_lbl = ttk.Label(status_wrap, text="● System Ready", style="Sub.TLabel", anchor="e")
        self.status_lbl.grid(row=0, column=0, sticky="ew")

        # Body Layout
        body = tk.Frame(main_container, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        # Sidebar
        sidebar = tk.Frame(body, bg=BG_PANEL, width=310, highlightbackground=BORDER, highlightthickness=1)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        sb_canvas = tk.Canvas(sidebar, bg=BG_PANEL, highlightthickness=0)
        sb_vsb = ttk.Scrollbar(sidebar, orient="vertical", command=sb_canvas.yview)
        sb_canvas.pack(side="left", fill="both", expand=True)
        sb_content = tk.Frame(sb_canvas, bg=BG_PANEL, padx=16, pady=16)
        sb_win = sb_canvas.create_window((0, 0), window=sb_content, anchor="nw")
        sb_canvas.configure(yscrollcommand=sb_vsb.set)

        def sync_sb(e=None):
            if e is not None and getattr(e, "widget", None) is sb_canvas and e.width > 1:
                sb_canvas.itemconfigure(sb_win, width=max(278, e.width - 14))
            sb_canvas.configure(scrollregion=sb_canvas.bbox("all"))
            if sb_content.winfo_reqheight() <= sb_canvas.winfo_height():
                sb_vsb.pack_forget()
            else:
                sb_vsb.pack(side="right", fill="y")
        sb_content.bind("<Configure>", sync_sb)
        sb_canvas.bind("<Configure>", sync_sb)

        def on_wheel_sb(e):
            node = sb_canvas.winfo_containing(e.x_root, e.y_root)
            while node is not None:
                if node is sb_canvas:
                    sb_canvas.yview_scroll(-1 * (e.delta // 120), "units")
                    return
                node = getattr(node, "master", None)
        self.bind_all("<MouseWheel>", on_wheel_sb, add="+")

        def sect(parent, text, color=ACCENT_CYAN):
            tk.Label(parent, text=text, bg=BG_PANEL, fg=color,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")

        def rule(parent):
            tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=(6, 0))

        # HUD
        sect(sb_content, "SYSTEM STATUS")
        rule(sb_content)
        hud = tk.Frame(sb_content, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1,
                       padx=14, pady=12)
        hud.pack(fill="x", pady=(10, 18))
        self.cpu_lbl = tk.Label(hud, text="CPU: ---%", bg=BG_CARD, fg=FG_SECONDARY,
                                font=("Consolas", 15, "bold"), anchor="w")
        self.cpu_lbl.pack(fill="x")
        self.mem_lbl = tk.Label(hud, text="MEM: ---%", bg=BG_CARD, fg=FG_SECONDARY,
                                font=("Consolas", 11, "bold"), anchor="w")
        self.mem_lbl.pack(fill="x", pady=(2, 8))
        self.proc_lbl = tk.Label(hud, text="Processes: --", bg=BG_CARD, fg=FG_SECONDARY,
                                 font=("Segoe UI", 10), anchor="w", wraplength=265)
        self.proc_lbl.pack(fill="x")
        self.core_lbl = tk.Label(hud, text="Cores: --", bg=BG_CARD, fg=FG_SECONDARY,
                                 font=("Segoe UI", 10), anchor="w", wraplength=265)
        self.core_lbl.pack(fill="x")
        self.admin_lbl = tk.Label(hud, text="Admin: checking...", bg=BG_CARD, fg=FG_SECONDARY,
                                  font=("Segoe UI", 10), anchor="w", wraplength=265,
                                  justify="left")
        self.admin_lbl.pack(fill="x")

        # Controls
        sect(sb_content, "ACTIONS", ACCENT_PURPLE)
        rule(sb_content)
        actions = tk.Frame(sb_content, bg=BG_PANEL)
        actions.pack(fill="x", pady=(10, 18))

        def hover(button, enter_bg, leave_bg):
            def on_enter(_):
                if str(button["state"]) != "disabled":
                    button.configure(bg=enter_bg)
            def on_leave(_):
                button.configure(bg=leave_bg)
            button.bind("<Enter>", on_enter)
            button.bind("<Leave>", on_leave)

        self.btn_scan = tk.Button(actions, text="Refresh System Scan", command=self._scan,
            bg=ACCENT_BLUE, fg="#ffffff", activebackground="#2f6fe4", activeforeground="#ffffff",
            disabledforeground="#7d8bb0", font=("Segoe UI", 10, "bold"), relief="flat",
            bd=0, cursor="hand2", padx=16, pady=10, anchor="w")
        self.btn_scan.pack(fill="x", pady=(0, 8))
        hover(self.btn_scan, "#2f6fe4", ACCENT_BLUE)

        self.btn_sched = tk.Button(actions, text="Run Scheduling Analysis", command=self._sched,
            bg=BG_INPUT, fg=ACCENT_GREEN, activebackground="#20203a", activeforeground=ACCENT_GREEN,
            disabledforeground="#4d4d66", font=("Segoe UI", 10, "bold"), relief="flat",
            bd=0, cursor="hand2", padx=16, pady=10, anchor="w", state="disabled")
        self.btn_sched.pack(fill="x", pady=(0, 8))
        hover(self.btn_sched, "#20203a", BG_INPUT)

        self.btn_optimize = tk.Button(actions, text="Optimize System", command=self._optimize,
            bg=BG_INPUT, fg=ACCENT_PINK, activebackground="#20203a", activeforeground=ACCENT_PINK,
            disabledforeground="#4d4d66", font=("Segoe UI", 10, "bold"), relief="flat",
            bd=0, cursor="hand2", padx=16, pady=10, anchor="w", state="disabled")
        self.btn_optimize.pack(fill="x")
        hover(self.btn_optimize, "#20203a", BG_INPUT)

        if not is_admin():
            rule(actions)
            self.btn_admin = tk.Button(actions, text="Run as Admin", command=self._run_as_admin,
                bg=ACCENT_AMBER, fg="#0b0b12", activebackground="#e0940f", activeforeground="#0b0b12",
                disabledforeground="#4d4d66", font=("Segoe UI", 10, "bold"), relief="flat",
                bd=0, cursor="hand2", padx=16, pady=9, anchor="w")
            self.btn_admin.pack(fill="x", pady=(12, 0))
            hover(self.btn_admin, "#e0940f", ACCENT_AMBER)

        # Risk analysis
        sect(sb_content, "RISK ANALYSIS", ACCENT_RED)
        rule(sb_content)
        self.bn_card = tk.Frame(sb_content, bg=BG_CARD, highlightbackground=BORDER,
                                highlightthickness=1, padx=14, pady=12)
        self.bn_card.pack(fill="x", pady=(10, 16))
        self.bn_level = tk.Label(self.bn_card, text="--", bg=BG_CARD, fg=FG_DIM,
                                 font=("Segoe UI", 18, "bold"))
        self.bn_level.pack(anchor="w")

        def bn_row(label):
            row = tk.Frame(self.bn_card, bg=BG_CARD)
            row.pack(fill="x", pady=(6, 0))
            tk.Label(row, text=label, bg=BG_CARD, fg=FG_DIM,
                     font=("Segoe UI", 9)).pack(side="left")
            val = tk.Label(row, text="--", bg=BG_CARD, fg=FG_SECONDARY,
                           font=("Segoe UI", 9, "bold"), anchor="e")
            val.pack(side="right", anchor="e")
            return val

        self.bn_primary = bn_row("Primary risk")
        self.bn_current = bn_row("Current")
        tk.Label(self.bn_card, text="TOP CONSUMER", bg=BG_CARD, fg=FG_DIM,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(8, 0))
        self.bn_top = tk.Label(self.bn_card, text="--", bg=BG_CARD, fg=FG_SECONDARY,
                               font=("Segoe UI", 9, "bold"), wraplength=240,
                               justify="left", anchor="w")
        self.bn_top.pack(fill="x")
        tk.Frame(self.bn_card, bg=BORDER, height=1).pack(fill="x", pady=(8, 6))
        tk.Label(self.bn_card, text="REASON", bg=BG_CARD, fg=FG_DIM,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.bn_detail = tk.Label(self.bn_card, text="Run Refresh System Scan to assess current risk.",
                                  bg=BG_CARD, fg=FG_SECONDARY, font=("Segoe UI", 9),
                                  wraplength=240, justify="left", anchor="w")
        self.bn_detail.pack(fill="x")
        self.bn_card.bind("<Configure>",
            lambda e: (self.bn_detail.configure(wraplength=max(170, e.width - 36)),
                       self.bn_top.configure(wraplength=max(170, e.width - 36))))

        self.nb = ttk.Notebook(body, style="Custom.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=20, pady=20)
        self._tab_processes()
        self._tab_simulation()
        self._tab_analysis()
        self._tab_scheduling()
        self._tab_optimization()
        self._tab_log()

    def _build_control(self, parent):
        pass

    # ── Tabs ───────────────────────────────────────────────────────────────
    def _tab_processes(self):
        f = tk.Frame(self.nb, bg=BG_DARK); self.nb.add(f, text="  Processes  ")

        # ── Toolbar row ──────────────────────────────────────────────────────
        toolbar = tk.Frame(f, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        toolbar.pack(fill="x", padx=8, pady=(8, 0))

        tk.Label(toolbar, text="Search:", bg=BG_PANEL, fg=FG_SECONDARY,
                 font=("Segoe UI", 10)).pack(side="left", padx=(10, 4), pady=6)
        self._proc_search_var = tk.StringVar()
        self._proc_search_var.trace_add("write", lambda *_: self._filter_tree())
        search_entry = tk.Entry(toolbar, textvariable=self._proc_search_var,
                                bg=BG_INPUT, fg=FG_PRIMARY, insertbackground=FG_PRIMARY,
                                relief="flat", font=("Segoe UI", 10), width=24)
        search_entry.pack(side="left", padx=(0, 8), pady=6, ipady=3)

        tk.Button(toolbar, text="✕ Clear", command=lambda: self._proc_search_var.set(""),
                  bg=BG_INPUT, fg=FG_SECONDARY, relief="flat", font=("Segoe UI", 9),
                  padx=6, pady=4, cursor="hand2").pack(side="left")

        self._proc_count_lbl = tk.Label(toolbar, text="", bg=BG_PANEL, fg=FG_DIM,
                                        font=("Segoe UI", 9))
        self._proc_count_lbl.pack(side="left", padx=12)

        tk.Button(toolbar, text="⬇ Export CSV", command=self._export_csv,
                  bg=BG_INPUT, fg=ACCENT_GREEN, relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=10, pady=4, cursor="hand2").pack(side="right", padx=8, pady=5)

        # ── Treeview ─────────────────────────────────────────────────────────
        cols = ("PID", "Name", "State", "CPU%", "Memory MB", "Priority", "Threads", "Ctx Switches")
        headers = {"PID": "PID", "Name": "Name", "State": "State", "CPU%": "CPU %",
                   "Memory MB": "Mem (MB)", "Priority": "Priority",
                   "Threads": "Threads", "Ctx Switches": "Ctx Sw"}
        widths = {"PID": 70, "State": 64, "CPU%": 80, "Memory MB": 100,
                  "Priority": 110, "Threads": 84, "Ctx Switches": 92}

        tf = tk.Frame(f, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        tf.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.ptree = ttk.Treeview(tf, columns=cols, show="headings", style="Custom.Treeview")
        for c in cols:
            self.ptree.heading(c, text=headers[c], anchor="w",
                               command=lambda col=c: self._sort_tree(col))
            if c == "Name":
                self.ptree.column(c, width=230, minwidth=180, anchor="w", stretch=True)
            else:
                w = widths[c]
                self.ptree.column(c, width=w, minwidth=w, anchor="center", stretch=False)
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.ptree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self.ptree.xview)
        self.ptree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x")
        vsb.pack(side="right", fill="y")
        self.ptree.pack(side="left", fill="both", expand=True)
        self._sort_col = "CPU%"
        self._sort_reverse = True

    def _tab_simulation(self):
        """Simulation Mode tab: allows manual process definition and benchmark execution."""
        f = tk.Frame(self.nb, bg=BG_DARK)
        self.nb.add(f, text="  Simulation Mode  ")
        f.rowconfigure(1, weight=1)
        f.columnconfigure(0, weight=1)

        # Header banner
        head_card = tk.Frame(f, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        head_card.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        tk.Label(head_card, text="CUSTOM WORKLOAD SIMULATOR", bg=BG_PANEL, fg=ACCENT_CYAN,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=12, pady=8)
        tk.Label(head_card, text="Define custom processes to analyze and compare scheduling algorithms without scanning live OS processes.",
                 bg=BG_PANEL, fg=FG_DIM, font=("Segoe UI", 9)).pack(side="left", padx=8, pady=8)

        # Main layout
        body_frame = tk.Frame(f, bg=BG_DARK)
        body_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        body_frame.columnconfigure(0, weight=1, minsize=350)
        body_frame.columnconfigure(1, weight=2)
        body_frame.rowconfigure(0, weight=1)

        # Left panel: Input form & Presets
        left_box = tk.Frame(body_frame, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        tk.Label(left_box, text="PROCESS INPUT", bg=BG_CARD, fg=ACCENT_GREEN,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(12, 6))

        form = tk.Frame(left_box, bg=BG_CARD)
        form.pack(fill="x", padx=14, pady=4)
        form.columnconfigure(1, weight=1)

        self._sim_name_var = tk.StringVar(value="P1")
        self._sim_arr_var  = tk.DoubleVar(value=0.0)
        self._sim_burst_var= tk.DoubleVar(value=5.0)
        self._sim_prio_var = tk.IntVar(value=1)
        self._sim_quantum_var = tk.DoubleVar(value=2.0)

        inputs = [
            ("Process Name:", self._sim_name_var, "entry"),
            ("Arrival Time:", self._sim_arr_var,  "spin_float"),
            ("Burst Time:",   self._sim_burst_var,"spin_float"),
            ("Priority (1=High):", self._sim_prio_var, "spin_int"),
        ]

        for r, (lbl, var, typ) in enumerate(inputs):
            tk.Label(form, text=lbl, bg=BG_CARD, fg=FG_SECONDARY,
                     font=("Segoe UI", 9)).grid(row=r, column=0, sticky="w", pady=4)
            if typ == "entry":
                e = tk.Entry(form, textvariable=var, bg=BG_INPUT, fg=FG_PRIMARY,
                             insertbackground=FG_PRIMARY, relief="flat", font=("Segoe UI", 10))
            elif typ == "spin_float":
                e = tk.Spinbox(form, textvariable=var, from_=0.0, to=999.0, increment=0.5,
                               bg=BG_INPUT, fg=FG_PRIMARY, buttonbackground=BG_PANEL, relief="flat", font=("Segoe UI", 10))
            else:
                e = tk.Spinbox(form, textvariable=var, from_=1, to=99, increment=1,
                               bg=BG_INPUT, fg=FG_PRIMARY, buttonbackground=BG_PANEL, relief="flat", font=("Segoe UI", 10))
            e.grid(row=r, column=1, sticky="ew", padx=(8, 0), pady=4)

        # RR Quantum input
        q_frame = tk.Frame(left_box, bg=BG_CARD)
        q_frame.pack(fill="x", padx=14, pady=8)
        tk.Label(q_frame, text="Round Robin Quantum:", bg=BG_CARD, fg=ACCENT_AMBER,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Spinbox(q_frame, textvariable=self._sim_quantum_var, from_=0.5, to=50.0, increment=0.5,
                   width=6, bg=BG_INPUT, fg=FG_PRIMARY, buttonbackground=BG_PANEL, relief="flat", font=("Segoe UI", 10)).pack(side="right")

        # Action buttons row
        btn_row = tk.Frame(left_box, bg=BG_CARD)
        btn_row.pack(fill="x", padx=14, pady=(6, 10))
        tk.Button(btn_row, text="+ Add Process", command=self._sim_add_proc,
                  bg=ACCENT_BLUE, fg="#ffffff", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=10, pady=5, cursor="hand2").pack(side="left")
        tk.Button(btn_row, text="✕ Remove", command=self._sim_remove_proc,
                  bg=BG_INPUT, fg=ACCENT_RED, relief="flat", font=("Segoe UI", 9),
                  padx=8, pady=5, cursor="hand2").pack(side="left", padx=4)
        tk.Button(btn_row, text="↺ Clear All", command=self._sim_clear_procs,
                  bg=BG_INPUT, fg=FG_SECONDARY, relief="flat", font=("Segoe UI", 9),
                  padx=8, pady=5, cursor="hand2").pack(side="left")

        # Presets Section
        tk.Label(left_box, text="PRESET SCENARIOS", bg=BG_CARD, fg=ACCENT_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(8, 4))
        presets_frame = tk.Frame(left_box, bg=BG_CARD)
        presets_frame.pack(fill="x", padx=14, pady=(0, 10))

        presets = [
            ("⚡ Textbook Classic (4 processes)", self._load_preset_textbook),
            ("⚡ Convoy Effect (FCFS worst case)", self._load_preset_convoy),
            ("⚡ Priority Mix (High vs Low)",      self._load_preset_priority),
            ("⚡ Preemption Stress (SRTF vs RR)", self._load_preset_preemption),
        ]
        for name, cmd in presets:
            tk.Button(presets_frame, text=name, command=cmd,
                      bg=BG_INPUT, fg=FG_PRIMARY, relief="flat", font=("Segoe UI", 9),
                      anchor="w", padx=8, pady=4, cursor="hand2").pack(fill="x", pady=2)

        # Right panel: Process List Table & Run Button
        right_box = tk.Frame(body_frame, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right_box.rowconfigure(1, weight=1)
        right_box.columnconfigure(0, weight=1)

        rtop = tk.Frame(right_box, bg=BG_CARD)
        rtop.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        tk.Label(rtop, text="SIMULATION PROCESS QUEUE", bg=BG_CARD, fg=ACCENT_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self._sim_queue_count = tk.Label(rtop, text="0 processes", bg=BG_CARD, fg=FG_DIM, font=("Segoe UI", 9))
        self._sim_queue_count.pack(side="right")

        cols = ("PID", "Name", "Arrival", "Burst", "Priority")
        self.sim_tree = ttk.Treeview(right_box, columns=cols, show="headings", style="Custom.Treeview")
        for c in cols:
            self.sim_tree.heading(c, text=c, anchor="center")
            self.sim_tree.column(c, width=70, anchor="center")
        self.sim_tree.column("Name", width=180, anchor="w")
        self.sim_tree.grid(row=1, column=0, sticky="nsew", padx=14, pady=4)

        # Bottom execute bar
        rbot = tk.Frame(right_box, bg=BG_CARD)
        rbot.grid(row=2, column=0, sticky="ew", padx=14, pady=12)
        tk.Button(rbot, text="▶  RUN SIMULATION ON ALL 5 ALGORITHMS", command=self._run_custom_simulation,
                  bg=ACCENT_GREEN, fg="#0b0b12", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=16, pady=8, cursor="hand2").pack(fill="x")

        self.custom_procs = []
        self._load_preset_textbook()

    def _sim_add_proc(self):
        name = self._sim_name_var.get().strip() or f"P{len(self.custom_procs)+1}"
        try:
            arr = float(self._sim_arr_var.get())
            burst = max(0.1, float(self._sim_burst_var.get()))
            prio = max(1, int(self._sim_prio_var.get()))
        except Exception as e:
            messagebox.showerror("Invalid Input", f"Please check process values: {e}")
            return
        pid = len(self.custom_procs) + 1
        self.custom_procs.append({
            'pid': pid, 'name': name, 'arrival': arr, 'burst': burst, 'priority': prio
        })
        self._refresh_sim_tree()
        self._sim_name_var.set(f"P{len(self.custom_procs)+1}")

    def _sim_remove_proc(self):
        sel = self.sim_tree.selection()
        if not sel:
            return
        idx = self.sim_tree.index(sel[0])
        if 0 <= idx < len(self.custom_procs):
            del self.custom_procs[idx]
            for i, p in enumerate(self.custom_procs):
                p['pid'] = i + 1
            self._refresh_sim_tree()

    def _sim_clear_procs(self):
        self.custom_procs.clear()
        self._refresh_sim_tree()

    def _refresh_sim_tree(self):
        for i in self.sim_tree.get_children():
            self.sim_tree.delete(i)
        for p in self.custom_procs:
            self.sim_tree.insert("", "end", values=(
                p['pid'], p['name'], f"{p['arrival']:.1f}", f"{p['burst']:.1f}", p['priority']
            ))
        if hasattr(self, '_sim_queue_count'):
            self._sim_queue_count.configure(text=f"{len(self.custom_procs)} processes")

    def _load_preset_textbook(self):
        self.custom_procs = [
            {'pid': 1, 'name': 'P1 (Compute)', 'arrival': 0.0, 'burst': 8.0, 'priority': 2},
            {'pid': 2, 'name': 'P2 (Web Svc)', 'arrival': 1.0, 'burst': 4.0, 'priority': 1},
            {'pid': 3, 'name': 'P3 (Worker)',  'arrival': 2.0, 'burst': 2.0, 'priority': 3},
            {'pid': 4, 'name': 'P4 (UI Task)', 'arrival': 3.0, 'burst': 1.0, 'priority': 2},
        ]
        self._sim_quantum_var.set(2.0)
        self._refresh_sim_tree()

    def _load_preset_convoy(self):
        self.custom_procs = [
            {'pid': 1, 'name': 'Heavy Batch', 'arrival': 0.0, 'burst': 28.0, 'priority': 3},
            {'pid': 2, 'name': 'Quick Task 1', 'arrival': 1.0, 'burst': 2.0,  'priority': 1},
            {'pid': 3, 'name': 'Quick Task 2', 'arrival': 2.0, 'burst': 1.5,  'priority': 1},
            {'pid': 4, 'name': 'Quick Task 3', 'arrival': 3.0, 'burst': 1.0,  'priority': 1},
        ]
        self._sim_quantum_var.set(2.0)
        self._refresh_sim_tree()

    def _load_preset_priority(self):
        self.custom_procs = [
            {'pid': 1, 'name': 'Background Sync', 'arrival': 0.0, 'burst': 6.0, 'priority': 4},
            {'pid': 2, 'name': 'Critical Audio',   'arrival': 1.0, 'burst': 3.0, 'priority': 1},
            {'pid': 3, 'name': 'Renderer',         'arrival': 2.0, 'burst': 5.0, 'priority': 2},
            {'pid': 4, 'name': 'Indexing Daemon',  'arrival': 3.0, 'burst': 8.0, 'priority': 5},
        ]
        self._sim_quantum_var.set(2.0)
        self._refresh_sim_tree()

    def _load_preset_preemption(self):
        self.custom_procs = [
            {'pid': 1, 'name': 'Long Job',     'arrival': 0.0, 'burst': 12.0, 'priority': 3},
            {'pid': 2, 'name': 'Short Burst 1', 'arrival': 2.0, 'burst': 2.0,  'priority': 2},
            {'pid': 3, 'name': 'Short Burst 2', 'arrival': 4.0, 'burst': 1.0,  'priority': 1},
            {'pid': 4, 'name': 'Short Burst 3', 'arrival': 6.0, 'burst': 3.0,  'priority': 2},
        ]
        self._sim_quantum_var.set(2.0)
        self._refresh_sim_tree()

    def _run_custom_simulation(self):
        if not self.custom_procs:
            messagebox.showwarning("No Processes", "Add at least one process to the simulation queue.")
            return

        import copy
        q = max(0.1, self._sim_quantum_var.get())
        sched = []
        for i, p in enumerate(self.custom_procs):
            sched.append({
                'pid': i + 1,
                'name': p['name'],
                'arrival': float(p['arrival']),
                'burst': float(p['burst']),
                'remaining': float(p['burst']),
                'priority': int(p['priority']),
                'first_start': -1.0,
                'completion': 0.0,
                'turnaround': 0.0,
                'waiting': 0.0,
                'response': 0.0,
            })

        fns = {
            'FCFS': sched_fcfs,
            'SJF': sched_sjf,
            'SRTF': sched_srtf,
            f'Round Robin (Q={q:g})': lambda procs: sched_rr(copy.deepcopy(procs), q),
            'Priority Scheduling': sched_priority
        }
        results = {}
        for name, fn in fns.items():
            ps, sw, g, tb, tt = fn(copy.deepcopy(sched))
            m = calc_sched_metrics(ps, sw, tb, tt)
            results[name] = {'rows': ps, 'metrics': m, 'gantt': g}

        self.sched_results = results
        self._render_sched_review()
        self.log(f"Simulated {len(self.custom_procs)} custom processes across all algorithms (RR Q={q:g})", "ok")
        self.nb.select(3)


    def _refit_all_charts(self):
        """Corrective second pass: re-fit charts after layout/scrollbars settle.

        Axes artists persist across set_size_inches, so a plain re-fit
        re-renders the same content at the correct size.
        """
        for canvas, fig, tight in (
                (self.opt_canvas, self.opt_fig, False),
                (self.trend_canvas, self.trend_fig, False),
                (self.top_canvas, self.top_fig, True),
                (self.comparison_canvas, self.comparison_fig, False),
                (self.gantt_canvas, self.gantt_fig, True)):
            try:
                self._fit_figure(canvas, fig, 0, 0, tight)
            except Exception:
                pass

    def _on_tab_changed(self, _e=None):
        """Self-healing: re-fit every chart to its live widget size on tab switch."""
        self.after(150, self._refit_all_charts)

    def _progress_canvas(self, parent):
        c = tk.Canvas(parent, bg=BG_CARD, height=6, highlightthickness=0, bd=0)
        c.pack(fill="x", pady=(6, 2))
        c.pct = 0.0
        c.color = ACCENT_CYAN

        def redraw(_e=None):
            c.delete("bar")
            w = max(2, int(c.winfo_width() * min(100.0, c.pct) / 100.0))
            c.create_rectangle(0, 1, w, 5, fill=c.color, width=0, tags="bar")

        def setv(pct, color):
            c.pct = float(pct)
            c.color = color
            redraw()

        c.bind("<Configure>", redraw)
        c.setv = setv
        return c

    def _tab_analysis(self):
        f = tk.Frame(self.nb, bg=BG_DARK)
        self.nb.add(f, text="  Analysis  ")
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

        outer = tk.Frame(f, bg=BG_DARK)
        outer.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(outer, orient="vertical")
        vsb.pack(side="right", fill="y")
        view = tk.Canvas(outer, bg=BG_DARK, highlightthickness=0, yscrollcommand=vsb.set)
        view.pack(side="left", fill="both", expand=True)
        vsb.configure(command=view.yview)
        inner = tk.Frame(view, bg=BG_DARK)
        win = view.create_window((0, 0), window=inner, anchor="nw")

        def sync(e=None):
            if e is not None and getattr(e, "widget", None) is view and e.width > 1:
                view.itemconfigure(win, width=e.width)
            view.configure(scrollregion=view.bbox("all"))
            if inner.winfo_reqheight() <= view.winfo_height():
                vsb.pack_forget()
            else:
                vsb.pack(side="right", fill="y")
        inner.bind("<Configure>", sync)
        view.bind("<Configure>", sync)

        def on_wheel(e):
            node = view.winfo_containing(e.x_root, e.y_root)
            while node is not None:
                if node is view:
                    view.yview_scroll(-1 * (e.delta // 120), "units")
                    return
                node = getattr(node, "master", None)
        self.bind_all("<MouseWheel>", on_wheel, add="+")

        # Banner
        banner = tk.Frame(inner, bg=BG_CARD, highlightbackground=BORDER,
                          highlightthickness=1)
        banner.pack(fill="x", padx=12, pady=(12, 0))
        brow = tk.Frame(banner, bg=BG_CARD)
        brow.pack(fill="both", expand=True, padx=16, pady=12)
        tk.Label(brow, text="SYSTEM ANALYSIS", bg=BG_CARD, fg=ACCENT_PURPLE,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.an_verdict = tk.Label(brow,
            text="Awaiting first scan \u2014 press 'Refresh System Scan' to collect live OS data.",
            bg=BG_CARD, fg=ACCENT_AMBER, font=("Segoe UI", 11), wraplength=900,
            justify="left", anchor="w")
        self.an_verdict.pack(fill="x", pady=(4, 0))
        banner.bind("<Configure>",
            lambda e: self.an_verdict.configure(wraplength=max(360, e.width - 120)))

        # Live metric cards with utilization bars
        row = tk.Frame(inner, bg=BG_DARK)
        row.pack(fill="x", pady=(10, 0), padx=12)
        for i in range(4):
            row.columnconfigure(i, weight=1, uniform="acard")
        self.an_vals = {}
        self.an_bars = {}
        an_defs = [("cpu", "CPU UTILIZATION", ACCENT_CYAN),
                   ("mem", "MEMORY UTILIZATION", ACCENT_AMBER),
                   ("procs", "PROCESSES", ACCENT_BLUE),
                   ("wtype", "WORKLOAD TYPE", ACCENT_PURPLE)]
        for i, (key, label, color) in enumerate(an_defs):
            c = tk.Frame(row, bg=BG_CARD, highlightbackground=BORDER,
                         highlightthickness=1)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            tk.Label(c, text=label, bg=BG_CARD, fg=FG_DIM,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12,
                                                        pady=(10, 2))
            val = tk.Label(c, text="--", bg=BG_CARD, fg=color,
                           font=("Consolas", 16, "bold"), anchor="w")
            val.pack(anchor="w", padx=12)
            self.an_vals[key] = val
            if key in ("cpu", "mem"):
                self.an_bars[key] = self._progress_canvas(c)
            else:
                tk.Frame(c, bg=BG_CARD, height=8).pack()

        # Two-column info cards
        gridf = tk.Frame(inner, bg=BG_DARK)
        gridf.pack(fill="x", padx=12, pady=(10, 0))
        gridf.columnconfigure(0, weight=1, uniform="ag")
        gridf.columnconfigure(1, weight=1, uniform="ag")

        wl_card = tk.Frame(gridf, bg=BG_CARD, highlightbackground=BORDER,
                           highlightthickness=1)
        wl_card.grid(row=0, column=0, sticky="nsew")
        tk.Label(wl_card, text="WORKLOAD CLASSIFICATION", bg=BG_CARD, fg=ACCENT_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14,
                                                     pady=(12, 4))
        self.wl_frame = tk.Frame(wl_card, bg=BG_CARD)
        self.wl_frame.pack(fill="x", padx=14, pady=(0, 10))

        bn_card = tk.Frame(gridf, bg=BG_CARD, highlightbackground=BORDER,
                           highlightthickness=1)
        bn_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        tk.Label(bn_card, text="BOTTLENECKS", bg=BG_CARD, fg=ACCENT_RED,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14,
                                                     pady=(12, 4))
        self.bottles_frame = tk.Frame(bn_card, bg=BG_CARD)
        self.bottles_frame.pack(fill="x", padx=14, pady=(0, 10))

        sug_card = tk.Frame(inner, bg=BG_CARD, highlightbackground=BORDER,
                            highlightthickness=1)
        sug_card.pack(fill="x", padx=12, pady=(10, 14))
        tk.Label(sug_card, text="OPTIMIZATION SUGGESTIONS", bg=BG_CARD,
                 fg=ACCENT_PINK, font=("Segoe UI", 10, "bold")).pack(anchor="w",
                                                                     padx=14,
                                                                     pady=(12, 4))
        self.sug_admin_note = tk.Label(sug_card, text="", bg=BG_CARD,
                                       fg=ACCENT_AMBER, font=("Segoe UI", 9,
                                                              "italic"),
                                       wraplength=900, justify="left")
        self.sug_admin_note.pack(fill="x", padx=14)
        self.sugg_frame = tk.Frame(sug_card, bg=BG_CARD)
        self.sugg_frame.pack(fill="x", padx=14, pady=(6, 12))

        self._set_empty(self.wl_frame, "Scan to classify the workload.")
        self._set_empty(self.bottles_frame, "Scan to detect bottlenecks.")
        self._set_empty(self.sugg_frame, "Scan to generate optimization suggestions.")

    def _tab_scheduling(self):
        f = tk.Frame(self.nb, bg=BG_DARK)
        self.nb.add(f, text="  Scheduling  ")
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

        outer = tk.Frame(f, bg=BG_DARK)
        outer.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(outer, orient="vertical")
        vsb.pack(side="right", fill="y")
        view = tk.Canvas(outer, bg=BG_DARK, highlightthickness=0, yscrollcommand=vsb.set)
        view.pack(side="left", fill="both", expand=True)
        vsb.configure(command=view.yview)
        inner = tk.Frame(view, bg=BG_DARK)
        win = view.create_window((0, 0), window=inner, anchor="nw")

        def sync(e=None):
            if e is not None and getattr(e, "widget", None) is view and e.width > 1:
                view.itemconfigure(win, width=e.width)
            view.configure(scrollregion=view.bbox("all"))
            if inner.winfo_reqheight() <= view.winfo_height():
                vsb.pack_forget()
            else:
                vsb.pack(side="right", fill="y")
        inner.bind("<Configure>", sync)
        view.bind("<Configure>", sync)

        def on_wheel(e):
            node = view.winfo_containing(e.x_root, e.y_root)
            while node is not None:
                if node is view:
                    view.yview_scroll(-1 * (e.delta // 120), "units")
                    return
                node = getattr(node, "master", None)
        self.bind_all("<MouseWheel>", on_wheel, add="+")

        # Decision banner
        sb = tk.Frame(inner, bg=BG_CARD, highlightbackground=BORDER,
                      highlightthickness=1)
        sb.pack(fill="x", padx=12, pady=(12, 0))
        srow = tk.Frame(sb, bg=BG_CARD)
        srow.pack(fill="both", expand=True, padx=16, pady=12)
        tk.Label(srow, text="SCHEDULING DECISION", bg=BG_CARD, fg=ACCENT_PURPLE,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.sched_verdict = tk.Label(srow,
            text="Awaiting analysis \u2014 press 'Run Scheduling Analysis' to simulate "
                 "FCFS, SJF, SRTF, Round Robin and Priority on the live workload.",
            bg=BG_CARD, fg=ACCENT_AMBER, font=("Segoe UI", 11), wraplength=900,
            justify="left", anchor="w")
        self.sched_verdict.pack(fill="x", pady=(4, 0))
        self.sched_detail = tk.Label(srow, text="", bg=BG_CARD, fg=FG_DIM,
                                     font=("Segoe UI", 9), wraplength=900,
                                     justify="left", anchor="w")
        self.sched_detail.pack(fill="x", pady=(2, 0))
        sb.bind("<Configure>",
            lambda e: (self.sched_verdict.configure(wraplength=max(360, e.width - 120)),
                       self.sched_detail.configure(wraplength=max(360, e.width - 120))))

        # Comparison table + notes side by side
        mid = tk.Frame(inner, bg=BG_DARK)
        mid.pack(fill="x", padx=12, pady=(10, 0))
        mid.columnconfigure(0, weight=3, uniform="smid")
        mid.columnconfigure(1, weight=2, uniform="smid")
        ct = tk.Frame(mid, bg=BG_CARD, highlightbackground=BORDER,
                      highlightthickness=1)
        ct.grid(row=0, column=0, sticky="nsew")
        tk.Label(ct, text="ALGORITHM COMPARISON", bg=BG_CARD, fg=ACCENT_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14,
                                                     pady=(12, 4))
        self.sched_table = tk.Frame(ct, bg=BG_CARD)
        self.sched_table.pack(fill="x", padx=14, pady=(0, 10))
        nt = tk.Frame(mid, bg=BG_CARD, highlightbackground=BORDER,
                      highlightthickness=1)
        nt.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        tk.Label(nt, text="DECISION NOTES", bg=BG_CARD, fg=ACCENT_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14,
                                                     pady=(12, 4))
        self.sched_notes_frame = tk.Frame(nt, bg=BG_CARD)
        self.sched_notes_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._set_empty(self.sched_table, "Run the analysis to compare algorithms.")
        self._set_empty(self.sched_notes_frame, "Notes appear after analysis.")

        # Card 1: Algorithm Performance & Ranking (Full Width)
        comp_card = tk.Frame(inner, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        comp_card.pack(fill="x", padx=12, pady=(10, 0))
        comp_hdr = tk.Frame(comp_card, bg=BG_CARD)
        comp_hdr.pack(fill="x", padx=14, pady=(10, 2))
        tk.Label(comp_hdr, text="ALGORITHM PERFORMANCE & RANKING", bg=BG_CARD, fg=ACCENT_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        comp_body = tk.Frame(comp_card, bg=BG_CARD, height=220)
        comp_body.pack(fill="x", padx=8, pady=(2, 6))
        comp_body.pack_propagate(False)
        self.comparison_fig = Figure(figsize=(7, 2.2), dpi=100, facecolor=BG_CARD)
        self.comparison_ax = self.comparison_fig.add_subplot(111)
        self.comparison_ax.set_facecolor(BG_CARD)
        self.comparison_canvas = FigureCanvasTkAgg(self.comparison_fig, comp_body)
        self.comparison_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._responsive_figure(self.comparison_canvas, self.comparison_fig, use_tight=False)

        # Card 2: Recommended Schedule Timeline (Full Width)
        gantt_card = tk.Frame(inner, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        gantt_card.pack(fill="x", padx=12, pady=(10, 14))
        gantt_hdr = tk.Frame(gantt_card, bg=BG_CARD)
        gantt_hdr.pack(fill="x", padx=14, pady=(10, 2))
        tk.Label(gantt_hdr, text="RECOMMENDED SCHEDULE TIMELINE (GANTT)", bg=BG_CARD, fg=ACCENT_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        gantt_body = tk.Frame(gantt_card, bg=BG_CARD, height=280)
        gantt_body.pack(fill="x", padx=8, pady=(2, 6))
        gantt_body.pack_propagate(False)
        self.gantt_fig = Figure(figsize=(8, 2.7), dpi=100, facecolor=BG_CARD)
        self.gantt_ax = self.gantt_fig.add_subplot(111)
        self.gantt_ax.set_facecolor(BG_CARD)
        for sp in self.gantt_ax.spines.values(): sp.set_color(BORDER)
        self.gantt_ax.tick_params(colors=FG_SECONDARY, labelsize=8)
        self.gantt_canvas = FigureCanvasTkAgg(self.gantt_fig, gantt_body)
        self.gantt_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._responsive_figure(self.gantt_canvas, self.gantt_fig, use_tight=True)

    def _tab_optimization(self):
        f = tk.Frame(self.nb, bg=BG_DARK)
        self.nb.add(f, text="  Optimization  ")
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

        # Scrollable dashboard surface
        outer = tk.Frame(f, bg=BG_DARK)
        outer.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(outer, orient="vertical")
        vsb.pack(side="right", fill="y")
        self.opt_view = tk.Canvas(outer, bg=BG_DARK, highlightthickness=0,
                                  yscrollcommand=vsb.set)
        self.opt_view.pack(side="left", fill="both", expand=True)
        vsb.configure(command=self.opt_view.yview)
        inner = tk.Frame(self.opt_view, bg=BG_DARK)
        win = self.opt_view.create_window((0, 0), window=inner, anchor="nw")

        def sync_scroll(e=None):
            if e is not None and getattr(e, "widget", None) is self.opt_view and e.width > 1:
                self.opt_view.itemconfigure(win, width=e.width)
            self.opt_view.configure(scrollregion=self.opt_view.bbox("all"))
            if inner.winfo_reqheight() <= self.opt_view.winfo_height():
                vsb.pack_forget()
            else:
                vsb.pack(side="right", fill="y")
        inner.bind("<Configure>", sync_scroll)
        self.opt_view.bind("<Configure>", sync_scroll)

        def on_wheel(e):
            node = self.opt_view.winfo_containing(e.x_root, e.y_root)
            while node is not None:
                if node is self.opt_view:
                    self.opt_view.yview_scroll(-1 * (e.delta // 120), "units")
                    return
                node = getattr(node, "master", None)
        self.bind_all("<MouseWheel>", on_wheel, add="+")

        # Verdict banner
        self.opt_banner = tk.Frame(inner, bg=BG_CARD, highlightbackground=BORDER,
                                   highlightthickness=1)
        self.opt_banner.pack(fill="x", padx=12, pady=(12, 0))
        banner_row = tk.Frame(self.opt_banner, bg=BG_CARD)
        banner_row.pack(fill="both", expand=True, padx=16, pady=12)
        tk.Label(banner_row, text="OPTIMIZATION REVIEW", bg=BG_CARD, fg=ACCENT_PURPLE,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.opt_verdict = tk.Label(banner_row,
            text="Awaiting first run \u2014 press 'Optimize System' to sample resources and apply safe priority adjustments.",
            bg=BG_CARD, fg=ACCENT_AMBER, font=("Segoe UI", 11), wraplength=900,
            justify="left", anchor="w")
        self.opt_verdict.pack(fill="x", pady=(4, 0))
        self.opt_banner.bind("<Configure>",
            lambda e: self.opt_verdict.configure(wraplength=max(360, e.width - 120)))

        # Metric cards
        cards_row = tk.Frame(inner, bg=BG_DARK)
        cards_row.pack(fill="x", pady=(10, 0), padx=12)
        for i in range(5):
            cards_row.columnconfigure(i, weight=1, uniform="mcard")
        card_defs = [
            ("cpu",   "CPU",          ACCENT_CYAN),
            ("mem",   "MEMORY",       ACCENT_AMBER),
            ("procs", "PROCESSES",    ACCENT_BLUE),
            ("optim", "OPTIMIZATION", ACCENT_PINK),
            ("risk",  "RISK",         ACCENT_GREEN),
        ]
        self.metric_vals = {}
        self.metric_subs = {}
        for i, (key, label, color) in enumerate(card_defs):
            c = tk.Frame(cards_row, bg=BG_CARD, highlightbackground=BORDER,
                         highlightthickness=1)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            tk.Label(c, text=label, bg=BG_CARD, fg=FG_DIM,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
            val = tk.Label(c, text="--", bg=BG_CARD, fg=color,
                           font=("Consolas", 17, "bold"), anchor="w")
            val.pack(anchor="w", padx=12)
            sub = tk.Label(c, text="--", bg=BG_CARD, fg=FG_SECONDARY,
                           font=("Segoe UI", 9), anchor="w")
            sub.pack(anchor="w", padx=12, pady=(2, 10))
            self.metric_vals[key] = val
            self.metric_subs[key] = sub

        def section(title, right_text="", height=240, subtitle=""):
            card = tk.Frame(inner, bg=BG_CARD, highlightbackground=BORDER,
                            highlightthickness=1)
            card.pack(fill="x", padx=12, pady=(10, 0))
            hdr = tk.Frame(card, bg=BG_CARD)
            hdr.pack(fill="x", padx=14, pady=(12, 0))
            tk.Label(hdr, text=title, bg=BG_CARD, fg=ACCENT_CYAN,
                     font=("Segoe UI", 10, "bold")).pack(side="left")
            if right_text:
                tk.Label(hdr, text=right_text, bg=BG_CARD, fg=FG_DIM,
                         font=("Segoe UI", 9, "italic")).pack(side="right")
            if subtitle:
                tk.Label(hdr, text=subtitle, bg=BG_CARD, fg=FG_DIM,
                         font=("Segoe UI", 8, "italic")).pack(anchor="w", pady=(2, 0))
            body = tk.Frame(card, bg=BG_CARD, height=height)
            body.pack(fill="x", padx=8, pady=(4, 6))
            body.pack_propagate(False)
            return card, hdr, body

        # Chart 1 — Before vs After resource utilization
        ba_card, _ba_hdr, ba_body = section("BEFORE VS AFTER RESOURCE UTILIZATION",
                                            "real measured averages", 265,
                                            subtitle="Measured system utilization before and after the optimization attempt")
        self.opt_fig = Figure(figsize=(6, 2.6), dpi=100, facecolor=BG_CARD)
        self.opt_ax = self.opt_fig.add_subplot(111)
        self.opt_ax.set_facecolor(BG_CARD)
        for sp in self.opt_ax.spines.values():
            sp.set_color(BORDER)
        self.opt_ax.set_xticks([])
        self.opt_ax.set_yticks([])
        self.opt_canvas = FigureCanvasTkAgg(self.opt_fig, ba_body)
        self.opt_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._responsive_figure(self.opt_canvas, self.opt_fig, use_tight=False)
        self.opt_chart_note = tk.Label(ba_card,
            text="Samples are captured directly before and after optimization.",
            bg=BG_CARD, fg=FG_DIM, font=("Segoe UI", 8, "italic"))
        self.opt_chart_note.pack(fill="x", padx=14, pady=(0, 8))
        ba_card.bind("<Configure>",
            lambda e: self.opt_chart_note.configure(wraplength=max(300, e.width - 48)))

        # Optimization result card
        res_card = tk.Frame(inner, bg=BG_CARD, highlightbackground=BORDER,
                            highlightthickness=1)
        res_card.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(res_card, text="OPTIMIZATION RESULT", bg=BG_CARD, fg=ACCENT_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        self.result_status = tk.Label(res_card, text="NOT RUN", bg=BG_CARD, fg=FG_DIM,
                                      font=("Segoe UI", 15, "bold"))
        self.result_status.pack(anchor="w", padx=14)
        res_grid = tk.Frame(res_card, bg=BG_CARD)
        res_grid.pack(fill="x", padx=14, pady=(4, 2))
        self.result_rows = {}
        for i, key in enumerate(["CPU change", "Memory change", "Actions applied",
                                 "Recommendations", "Mode"]):
            r, c = i // 3, (i % 3) * 2
            tk.Label(res_grid, text=key, bg=BG_CARD, fg=FG_DIM,
                     font=("Segoe UI", 9)).grid(row=r, column=c, sticky="w",
                                                padx=(0, 6), pady=3)
            v = tk.Label(res_grid, text="--", bg=BG_CARD, fg=FG_SECONDARY,
                         font=("Consolas", 10, "bold"))
            v.grid(row=r, column=c + 1, sticky="w", padx=(0, 24), pady=3)
            self.result_rows[key] = v
        for c in range(6):
            res_grid.columnconfigure(c, weight=1 if c % 2 else 0)
        tk.Label(res_card, text="REASON", bg=BG_CARD, fg=FG_DIM,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(4, 0))
        self.result_reason = tk.Label(res_card,
            text="Run 'Optimize System' to produce a measured comparison.",
            bg=BG_CARD, fg=FG_SECONDARY, font=("Segoe UI", 9), wraplength=900,
            justify="left", anchor="w")
        self.result_reason.pack(fill="x", padx=14, pady=(2, 12))
        res_card.bind("<Configure>",
            lambda e: self.result_reason.configure(wraplength=max(360, e.width - 56)))

        def detail_card(title):
            card = tk.Frame(inner, bg=BG_CARD, highlightbackground=BORDER,
                            highlightthickness=1)
            card.pack(fill="x", padx=12, pady=(10, 0))
            tk.Label(card, text=title, bg=BG_CARD, fg=ACCENT_CYAN,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14,
                                                         pady=(12, 4))
            return card

        bef_card = detail_card("BEFORE OPTIMIZATION")
        self.before_frame = tk.Frame(bef_card, bg=BG_CARD)
        self.before_frame.pack(fill="x", padx=14, pady=(0, 10))

        act_card = detail_card("OPTIMIZATION ACTIONS")
        self.act_counts = tk.Label(act_card, text="--", bg=BG_CARD, fg=FG_SECONDARY,
                                   font=("Segoe UI", 10, "bold"))
        self.act_counts.pack(anchor="w", padx=14)
        self.actions_frame = tk.Frame(act_card, bg=BG_CARD)
        self.actions_frame.pack(fill="x", padx=14, pady=(6, 12))

        aft_card = detail_card("AFTER OPTIMIZATION")
        self.after_frame = tk.Frame(aft_card, bg=BG_CARD)
        self.after_frame.pack(fill="x", padx=14, pady=(0, 10))

        wc_card = tk.Frame(inner, bg=BG_CARD, highlightbackground=BORDER,
                           highlightthickness=1)
        wc_card.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(wc_card, text="WHAT CHANGED?", bg=BG_CARD, fg=ACCENT_PURPLE,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(12, 4))
        self.what_label = tk.Label(wc_card,
            text="Run 'Optimize System' to generate a data-driven comparison.",
            bg=BG_CARD, fg=FG_SECONDARY, font=("Segoe UI", 10), wraplength=1000,
            justify="left", anchor="w")
        self.what_label.pack(fill="x", padx=14, pady=(0, 12))
        wc_card.bind("<Configure>",
            lambda e: self.what_label.configure(wraplength=max(420, e.width - 56)))
        self._set_empty(self.before_frame,
                        "Baseline is captured when you run 'Optimize System'.")
        self._set_empty(self.after_frame,
                        "After-state is captured when you run 'Optimize System'.")
        self._set_empty(self.actions_frame, "No optimization actions recorded yet.")

        # Chart 2 — Live system utilization trend
        trend_card, _t_hdr, trend_body = section("SYSTEM RESOURCE UTILIZATION TREND",
                                                 "live psutil sampling every 5 s", 235)
        self.trend_fig = Figure(figsize=(6, 2.6), dpi=100, facecolor=BG_CARD)
        self.trend_ax = self.trend_fig.add_subplot(111)
        self.trend_ax.set_facecolor(BG_CARD)
        for sp in self.trend_ax.spines.values():
            sp.set_color(BORDER)
        self.trend_ax.tick_params(colors=FG_SECONDARY, labelsize=8)
        self.trend_canvas = FigureCanvasTkAgg(self.trend_fig, trend_body)
        self.trend_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._responsive_figure(self.trend_canvas, self.trend_fig, use_tight=False)

        # Chart 3 — Top processes (Memory / CPU toggle)
        tp_card, tp_hdr, tp_body = section("TOP RESOURCE-CONSUMING PROCESSES", "", 250)
        seg = tk.Frame(tp_hdr, bg=BG_CARD)
        seg.pack(side="right")
        self.btn_top_mem = tk.Button(seg, text="Memory",
            command=lambda: self._set_top_metric("memory"),
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0, cursor="hand2",
            padx=10, pady=3, bg=ACCENT_BLUE, fg="#ffffff",
            activebackground="#20203a", activeforeground="#ffffff")
        self.btn_top_cpu = tk.Button(seg, text="CPU",
            command=lambda: self._set_top_metric("cpu"),
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0, cursor="hand2",
            padx=10, pady=3, bg=BG_INPUT, fg=FG_SECONDARY,
            activebackground="#20203a", activeforeground="#ffffff")
        self.btn_top_mem.pack(side="left", padx=(0, 4))
        self.btn_top_cpu.pack(side="left")
        self.top_fig = Figure(figsize=(6, 2.7), dpi=100, facecolor=BG_CARD)
        self.top_ax = self.top_fig.add_subplot(111)
        self.top_ax.set_facecolor(BG_CARD)
        for sp in self.top_ax.spines.values():
            sp.set_color(BORDER)
        self.top_ax.tick_params(colors=FG_SECONDARY, labelsize=8)
        self.top_canvas = FigureCanvasTkAgg(self.top_fig, tp_body)
        self.top_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._responsive_figure(self.top_canvas, self.top_fig)

        # Optimization summary (two-column grid)
        sum_card = tk.Frame(inner, bg=BG_CARD, highlightbackground=BORDER,
                            highlightthickness=1)
        sum_card.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(sum_card, text="OPTIMIZATION SUMMARY", bg=BG_CARD, fg=ACCENT_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(12, 4))
        grid_f = tk.Frame(sum_card, bg=BG_CARD)
        grid_f.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        col_l = tk.Frame(grid_f, bg=BG_CARD)
        col_r = tk.Frame(grid_f, bg=BG_CARD)
        col_l.pack(side="left", fill="both", expand=True)
        col_r.pack(side="left", fill="both", expand=True, padx=(24, 0))
        self.sum_rows = {}
        summary_items = [
            ("cpu",         "CPU"),
            ("mem",         "Memory"),
            ("applied",     "Actions applied"),
            ("recommended", "Recommended actions"),
            ("sysstatus",   "System status"),
            ("mode",        "Optimization mode"),
            ("result",      "Overall result"),
        ]
        for i, (key, label) in enumerate(summary_items):
            parent = col_l if i % 2 == 0 else col_r
            r = i // 2
            tk.Label(parent, text=label, bg=BG_CARD, fg=FG_DIM,
                     font=("Segoe UI", 10)).grid(row=r, column=0, sticky="w", pady=3)
            val = tk.Label(parent, text="--", bg=BG_CARD, fg=FG_SECONDARY,
                           font=("Consolas", 11, "bold"))
            val.grid(row=r, column=1, sticky="e", pady=3)
            parent.columnconfigure(1, weight=1)
            self.sum_rows[key] = val

        # Priority changes strip
        prio_card = tk.Frame(inner, bg=BG_CARD, highlightbackground=BORDER,
                             highlightthickness=1)
        prio_card.pack(fill="x", padx=12, pady=(10, 14))
        tk.Label(prio_card, text="PRIORITY CHANGES", bg=BG_CARD, fg=ACCENT_PINK,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(10, 2))
        self.opt_prio = tk.Label(prio_card, text="No priority changes recorded yet.",
                                 bg=BG_CARD, fg=FG_SECONDARY, font=("Segoe UI", 10),
                                 wraplength=1000, justify="left")
        self.opt_prio.pack(fill="x", padx=14, pady=(0, 10))
        prio_card.bind("<Configure>",
            lambda e: self.opt_prio.configure(wraplength=max(480, e.width - 44)))

        # Initial renders (professional empty states)
        self._draw_trend()
        self._draw_top_procs()
        self._attach_trend_tooltip()

    def _responsive_figure(self, canvas, fig, use_tight=True):
        """Redraw a matplotlib figure whenever its Tk container frame is resized."""
        widget = canvas.get_tk_widget()
        frame = widget.master
        widget.configure(bg=BG_CARD, highlightthickness=0)
        state = {"job": None}

        def on_configure(event):
            w = frame.winfo_width()
            h = frame.winfo_height()
            if w < 60 or h < 40:
                return
            if state["job"]:
                frame.after_cancel(state["job"])
            state["job"] = frame.after(
                60, lambda: self._fit_figure(canvas, fig, w, h, use_tight))

        frame.bind("<Configure>", on_configure)

    def _fit_figure(self, canvas, fig, width, height, use_tight):
        try:
            widget = canvas.get_tk_widget()
            frame = widget.master
            w = frame.winfo_width()
            h = frame.winfo_height()
            if w < 60 or h < 40:
                w = width
                h = height
            if w < 60 or h < 40:
                return False
            w = max(180, w - 8)
            h = max(80, h - 6)
            try:
                widget.configure(width=w, height=h)
            except Exception:
                pass
            fig.set_size_inches(w / fig.dpi, h / fig.dpi, forward=True)
            if use_tight:
                try:
                    fig.tight_layout(pad=1.2)
                except Exception:
                    pass
            canvas.draw_idle()
            return True
        except Exception:
            return False

    def _update_chips(self, stats=None):
        s = stats if stats is not None else self.sys_stats
        admin = is_admin()
        reviewed = bool(self.before_stats and self.after_stats)
        if s:
            self.metric_vals["cpu"].configure(text="{:.1f}%".format(s.get('cpu_percent', 0.0)))
            self.metric_vals["mem"].configure(text="{:.1f}%".format(s.get('mem_percent', 0.0)))
        pair = "{:.1f}% \u2192 {:.1f}%"
        self.metric_subs["cpu"].configure(
            text=pair.format(self.before_stats['cpu'], self.after_stats['cpu']) if reviewed
            else "\u2014 no optimization run yet")
        self.metric_subs["mem"].configure(
            text=pair.format(self.before_stats['mem'], self.after_stats['mem']) if reviewed
            else "\u2014 no optimization run yet")
        if self.processes:
            top_p = max(self.processes, key=lambda p: p['mem_mb'])
            self.metric_vals["procs"].configure(text=str(len(self.processes)))
            self.metric_subs["procs"].configure(
                text="{} \u00b7 {:.0f} MB".format(top_p['name'][:16], top_p['mem_mb']))
        self.metric_vals["optim"].configure(
            text=str(len(self.optimized_pids)) if reviewed else "--")
        self.metric_subs["optim"].configure(
            text="{} recommendation{}".format(len(self.suggestions),
                                              "" if len(self.suggestions) == 1 else "s"))
        rank = {"HIGH": 2, "MEDIUM": 1}
        if self.bottlenecks:
            worst = max(self.bottlenecks, key=lambda b: rank.get(b['severity'], 0))
            sev_color = ACCENT_RED if worst['severity'] == "HIGH" else ACCENT_AMBER
            self.metric_vals["risk"].configure(text=worst['severity'], fg=sev_color)
            self.metric_subs["risk"].configure(text=worst['description'].split("\n")[0][:34])
        else:
            self.metric_vals["risk"].configure(text="LOW", fg=ACCENT_GREEN)
            self.metric_subs["risk"].configure(text="system within normal parameters")

    def _set_empty(self, frame, msg):
        for child in frame.winfo_children():
            child.destroy()
        lbl = tk.Label(frame, text=msg, bg=BG_CARD, fg=FG_DIM,
                       font=("Segoe UI", 9, "italic"), wraplength=800, justify="left")
        lbl.grid(row=0, column=0, columnspan=2, sticky="w", pady=2)
        frame.columnconfigure(1, weight=1)

    def _fill_kv(self, frame, rows):
        for child in frame.winfo_children():
            child.destroy()
        for i, (label, val, color) in enumerate(rows):
            tk.Label(frame, text=label, bg=BG_CARD, fg=FG_DIM,
                     font=("Segoe UI", 10)).grid(row=i, column=0, sticky="w",
                                                 pady=3, padx=(0, 12))
            v = tk.Label(frame, text=val, bg=BG_CARD, fg=color or FG_SECONDARY,
                         font=("Consolas", 11, "bold"))
            v.grid(row=i, column=1, sticky="e", pady=3)
        frame.columnconfigure(1, weight=1)

    def _capture_snapshot(self):
        procs = self.processes
        prios = [p.get('priority_name') for p in procs]
        rankb = {"HIGH": 2, "MEDIUM": 1}
        if self.bottlenecks:
            wb = max(self.bottlenecks, key=lambda b: rankb.get(b['severity'], 0))
            tnames = {"CPU": "CPU", "MEMORY": "Memory",
                      "CONTEXT_SWITCHES": "Context Switches"}
            risk = "{} \u00b7 {}".format(wb['severity'], tnames.get(wb['type'], wb['type']))
        else:
            risk = "LOW"
        snap = {
            'cpu': self.sys_stats.get('cpu_percent', 0.0),
            'mem': self.sys_stats.get('mem_percent', 0.0),
            'nprocs': len(procs),
            'cpu_heavy': sum(1 for p in procs if p['cpu'] > 15),
            'mem_heavy': sum(1 for p in procs if p['mem_mb'] > 200),
            'prio': "{} High \u00b7 {} Above \u00b7 {} Normal".format(
                prios.count('High'), prios.count('Above Normal'), prios.count('Normal')),
            'recs': len(self.suggestions),
            'risk': risk,
            'mode': "Administrator" if is_admin() else "Limited",
        }
        if procs:
            tm = max(procs, key=lambda p: p['mem_mb'])
            tc = max(procs, key=lambda p: p['cpu'])
            snap['top_mem'] = "{} \u2014 {:.0f} MB".format(tm['name'][:24], tm['mem_mb'])
            snap['top_cpu'] = "{} \u2014 {:.1f}%".format(tc['name'][:24], tc['cpu'])
        else:
            snap['top_mem'] = snap['top_cpu'] = "--"
        return snap

    def _sample_loop(self):
        """Lightweight real-system sampler feeding the trend graph."""
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            self.history.append({"time": datetime.datetime.now(),
                                 "cpu": cpu, "mem": mem})
            if len(self.history) > 240:
                del self.history[:-240]
            self._draw_trend()
        except Exception:
            pass
        try:
            self.after(5000, self._sample_loop)
        except Exception:
            pass

    def _draw_trend(self):
        self._fit_figure(self.trend_canvas, self.trend_fig, 0, 0, False)
        ax = self.trend_ax
        ax.clear()
        ax.set_facecolor(BG_CARD)
        for sp in ax.spines.values():
            sp.set_color(BORDER)
        hist = list(self.history)
        if len(hist) < 2:
            ax.set_xticks([])
            ax.set_yticks(range(0, 101, 25))
            ax.set_ylim(0, 100)
            ax.set_xlim(0, 1)
            ax.grid(axis="y", color=BORDER, linewidth=0.5, alpha=0.35)
            ax.text(0.5, 0.5,
                    "No historical samples available yet.\nRun 'Refresh System Scan' to begin live monitoring.",
                    transform=ax.transAxes, ha="center", va="center",
                    color=FG_DIM, fontsize=10, linespacing=1.6)
            ax.tick_params(colors=FG_SECONDARY, labelsize=8)
            self._trend_annot = None
            self.trend_data = {"xs": [], "cpu": [], "mem": [], "times": []}
            self.trend_canvas.draw_idle()
            return
        xs = list(range(len(hist)))
        cpu = [h['cpu'] for h in hist]
        mem = [h['mem'] for h in hist]
        times = [h['time'].strftime("%H:%M:%S") for h in hist]
        self.trend_data = {"xs": xs, "cpu": cpu, "mem": mem, "times": times}
        ax.plot(xs, mem, color=ACCENT_AMBER, linewidth=1.8, label="Memory")
        ax.plot(xs, cpu, color=ACCENT_CYAN, linewidth=1.8, label="CPU")
        ax.fill_between(xs, cpu, color=ACCENT_CYAN, alpha=0.08)
        if self.opt_event_index is not None and 0 <= self.opt_event_index < len(xs):
            ax.axvline(self.opt_event_index, color=ACCENT_PURPLE,
                       linestyle=(0, (4, 3)), linewidth=1.2, alpha=0.9)
            ax.text(self.opt_event_index + 0.4, 96, "optimization applied",
                    color=ACCENT_PURPLE, fontsize=7.5, va="top", ha="left",
                    rotation=90 if len(xs) > 40 else 0)
        ticks = [int(round(i * (len(xs) - 1) / 5.0)) for i in range(6)]
        dedup = [ticks[0]]
        for t in ticks[1:]:
            if t - dedup[-1] >= max(1, len(xs) // 20):
                dedup.append(t)
        ticks = dedup
        ax.set_xticks(ticks)
        ax.set_xticklabels([times[i] for i in ticks], fontsize=7.5)
        ax.set_xlim(0, len(xs) - 1)
        ax.set_ylim(0, 100)
        ax.set_ylabel("Utilization (%)", color=FG_SECONDARY, fontsize=9)
        ax.grid(axis="y", color=BORDER, linewidth=0.5, alpha=0.35)
        ax.set_axisbelow(True)
        ax.tick_params(colors=FG_SECONDARY, labelsize=8)
        self.trend_fig.subplots_adjust(left=0.075, right=0.99, top=0.84,
                                       bottom=0.18)
        ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.02), ncol=2,
                  frameon=False, fontsize=8, labelcolor=FG_PRIMARY,
                  borderaxespad=0)
        annot = ax.annotate("", xy=(0, 0), xytext=(14, 14), textcoords="offset points",
                            bbox=dict(boxstyle="round,pad=0.45", fc=BG_INPUT,
                                      ec=ACCENT_BLUE, lw=0.8),
                            color=FG_PRIMARY, fontsize=8, zorder=20, visible=False)
        annot.set_visible(False)
        self._trend_annot = annot
        self.trend_canvas.draw_idle()

    def _attach_trend_tooltip(self):
        def on_move(event):
            annot = getattr(self, "_trend_annot", None)
            data = self.trend_data
            if (annot is None or event.inaxes != self.trend_ax
                    or not data or not data["xs"]):
                if annot is not None and annot.get_visible():
                    annot.set_visible(False)
                    self.trend_canvas.draw_idle()
                return
            xs = data["xs"]
            idx = min(range(len(xs)), key=lambda i: abs(xs[i] - event.xdata))
            annot.xy = (xs[idx], max(data["cpu"][idx], data["mem"][idx]))
            annot.set_text("{}\nCPU {:.1f}%   MEM {:.1f}%".format(
                data["times"][idx], data["cpu"][idx], data["mem"][idx]))
            annot.set_visible(True)
            self.trend_canvas.draw_idle()

        self.trend_canvas.mpl_connect("motion_notify_event", on_move)

    def _set_top_metric(self, metric):
        self.top_metric = metric
        on = {"bg": ACCENT_BLUE, "fg": "#ffffff"}
        off = {"bg": BG_INPUT, "fg": FG_SECONDARY}
        for btn, m in ((self.btn_top_mem, "memory"), (self.btn_top_cpu, "cpu")):
            style = on if self.top_metric == m else off
            btn.configure(bg=style["bg"], fg=style["fg"],
                          activebackground="#20203a", activeforeground="#ffffff")
        self._draw_top_procs()

    def _draw_top_procs(self):
        self._fit_figure(self.top_canvas, self.top_fig, 0, 0, True)
        ax = self.top_ax
        ax.clear()
        ax.set_facecolor(BG_CARD)
        for sp in ax.spines.values():
            sp.set_color(BORDER)
        procs = list(self.processes)
        if not procs:
            ax.set_xticks([])
            ax.set_yticks([])
            ax.text(0.5, 0.5,
                    "No process data yet.\nRun 'Refresh System Scan' to capture the live process table.",
                    transform=ax.transAxes, ha="center", va="center",
                    color=FG_DIM, fontsize=10, linespacing=1.6)
            ax.tick_params(colors=FG_SECONDARY)
            self.top_canvas.draw_idle()
            return
        by_cpu = self.top_metric == "cpu"
        keyf = (lambda p: p['cpu']) if by_cpu else (lambda p: p['mem_mb'])
        top = sorted(procs, key=keyf, reverse=True)[:8]
        nonzero = [p for p in top if keyf(p) > 0]
        if nonzero:
            top = nonzero
        names = ["{} ({})".format(p['name'][:18], p['pid']) for p in top][::-1]
        vals = [keyf(p) for p in top][::-1]
        color = ACCENT_CYAN if by_cpu else ACCENT_PURPLE
        bars = ax.barh(range(len(top)), vals, height=0.62, color=color,
                       alpha=0.9, edgecolor=BORDER, linewidth=0.6)
        mx = max(vals) if vals else 1
        fmt = (lambda v: "{:.1f}%".format(v)) if by_cpu else (lambda v: "{:.0f} MB".format(v))
        for bar, v in zip(bars, vals):
            ax.text(bar.get_width() + mx * 0.02, bar.get_y() + bar.get_height() / 2,
                    fmt(v), va="center", fontsize=8, color=FG_PRIMARY, fontweight="bold")
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels(names, fontsize=8, color=FG_SECONDARY)
        ax.set_xlim(0, mx * 1.22)
        ax.set_xlabel("Normalized CPU (%)" if by_cpu else "Memory (MB)",
                      color=FG_SECONDARY, fontsize=8)
        ax.grid(axis="x", color=BORDER, linewidth=0.5, alpha=0.35)
        ax.set_axisbelow(True)
        ax.tick_params(colors=FG_SECONDARY, labelsize=8)
        try:
            self.top_fig.tight_layout(pad=1.4)
        except Exception:
            pass
        self.top_canvas.draw_idle()

    def _tab_log(self):
        f = tk.Frame(self.nb, bg=BG_DARK); self.nb.add(f, text="  Log  ")

        # Toolbar for log tab
        log_toolbar = tk.Frame(f, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        log_toolbar.pack(fill="x", side="bottom")
        tk.Button(log_toolbar, text="Clear Log", command=self._clear_log,
                  bg=BG_INPUT, fg=FG_SECONDARY, relief="flat", font=("Segoe UI", 9),
                  padx=10, pady=5, cursor="hand2").pack(side="right", padx=8, pady=4)
        tk.Button(log_toolbar, text="Export Log", command=self._export_log,
                  bg=BG_INPUT, fg=ACCENT_CYAN, relief="flat", font=("Segoe UI", 9),
                  padx=10, pady=5, cursor="hand2").pack(side="right", pady=4)

        self.log_text = scrolledtext.ScrolledText(f, bg=BG_CARD, fg=FG_SECONDARY,
            font=("Consolas", 10), insertbackground=FG_PRIMARY, borderwidth=0,
            highlightbackground=BORDER, highlightthickness=1, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        self.log_text.tag_configure("time",   foreground=FG_DIM)
        self.log_text.tag_configure("info",   foreground=ACCENT_CYAN)
        self.log_text.tag_configure("ok",     foreground=ACCENT_GREEN)
        self.log_text.tag_configure("warn",   foreground=ACCENT_AMBER)
        self.log_text.tag_configure("err",    foreground=ACCENT_RED)
        # FIX: 'action' tag was previously referenced as 'a' — undefined tag causes silent fallback
        self.log_text.tag_configure("action", foreground=ACCENT_PURPLE)
        self.log_text.tag_configure("debug",  foreground=FG_DIM)

    def log(self, msg, tag="info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] ", "time")
        self.log_text.insert("end", f"{msg}\n", tag)
        self.log_text.see("end")

    def set_status(self, t, c=FG_SECONDARY):
        self.status_lbl.configure(text=t, foreground=c)

    def _populate_tree(self):
        """Populate the process treeview, respecting current search filter and sort."""
        query = getattr(self, '_proc_search_var', None)
        query = query.get().strip().lower() if query else ""

        for i in self.ptree.get_children():
            self.ptree.delete(i)

        procs = list(self.processes)

        # Sort
        col = self._sort_col
        rev = self._sort_reverse
        numeric_cols = {"CPU%", "Memory MB", "Threads", "Ctx Switches", "PID"}
        col_key = {
            "PID":          lambda p: p['pid'],
            "Name":         lambda p: p['name'].lower(),
            "State":        lambda p: p['state'],
            "CPU%":         lambda p: p['cpu'],
            "Memory MB":    lambda p: p['mem_mb'],
            "Priority":     lambda p: p['priority_name'],
            "Threads":      lambda p: p['threads'],
            "Ctx Switches": lambda p: p['ctx_switches'],
        }
        if col in col_key:
            procs.sort(key=col_key[col], reverse=rev)

        # Filter
        visible = [p for p in procs
                   if not query or query in p['name'].lower() or query in str(p['pid'])]

        for p in visible:
            self.ptree.insert("", "end", values=(
                p['pid'], p['name'], p['state'],
                f"{p['cpu']:.1f}", f"{p['mem_mb']:.0f}",
                p['priority_name'], p['threads'], f"{p['ctx_switches']:,}"
            ))

        # Update count label
        if hasattr(self, '_proc_count_lbl'):
            if query:
                self._proc_count_lbl.configure(
                    text=f"{len(visible)} / {len(procs)} processes")
            else:
                self._proc_count_lbl.configure(text=f"{len(procs)} processes")

        self.ptree.bind("<Button-3>", self._show_context_menu)

    def _filter_tree(self):
        """Re-populate treeview with current search filter applied."""
        self._populate_tree()

    def _sort_tree(self, col):
        """Sort treeview by column; toggle direction on repeated click."""
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = (col in {"CPU%", "Memory MB", "Ctx Switches"})
        self._populate_tree()

    def _show_context_menu(self, event):
        item = self.ptree.identify_row(event.y)
        if not item:
            return
        self.ptree.selection_set(item)

        menu = tk.Menu(self, tearoff=0, bg=BG_PANEL, fg=FG_PRIMARY,
                       activebackground=ACCENT_BLUE, font=("Segoe UI", 10))
        pid  = int(self.ptree.item(item)['values'][0])
        name = str(self.ptree.item(item)['values'][1])

        menu.add_command(label=f"PID {pid}  —  {name}", state="disabled")
        menu.add_separator()
        menu.add_command(label="📋 Copy PID", command=lambda: self._copy_to_clipboard(str(pid)))
        menu.add_separator()
        menu.add_command(label="⬆  Set High Priority",    command=lambda: self._quick_prio(pid, "High"))
        menu.add_command(label="◼  Set Normal Priority",  command=lambda: self._quick_prio(pid, "Normal"))
        menu.add_command(label="⬇  Set Below Normal",     command=lambda: self._quick_prio(pid, "Below Normal"))
        menu.add_command(label="⬇⬇ Set Low (Idle)",       command=lambda: self._quick_prio(pid, "Low (Idle)"))
        menu.add_separator()
        menu.add_command(label=f"✖  Terminate {name}",
                         foreground=ACCENT_RED,
                         command=lambda: self._kill_process(pid))

        menu.post(event.x_root, event.y_root)

    def _copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)

    def _kill_process(self, pid):
        try:
            p = psutil.Process(pid)
            p.terminate()
            self.log(f"Terminated process {pid}", "ok")
            self._scan()
        except Exception as e:
            self.log(f"Could not kill process {pid}: {e}", "err")

    def _quick_prio(self, pid, prio):
        if apply_optimization(pid, prio):
            self.log(f"Priority for PID {pid} set to {prio}", "ok")
            self._scan()
        else:
            self.log(f"Failed to set priority for PID {pid}", "err")

    # ── Actions ────────────────────────────────────────────────────────────

    def _export_csv(self):
        """Export process table and scheduling results to a CSV file."""
        if not self.processes:
            messagebox.showwarning("No Data", "Run 'Refresh System Scan' first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Process Data",
            initialfile=f"cpu_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                # Process table
                w.writerow(["=== PROCESS TABLE ==="])
                w.writerow(["PID", "Name", "State", "CPU%", "Memory_MB",
                             "Priority", "Threads", "Ctx_Switches"])
                for p in self.processes:
                    w.writerow([p['pid'], p['name'], p['state'],
                                 f"{p['cpu']:.2f}", f"{p['mem_mb']:.1f}",
                                 p['priority_name'], p['threads'], p['ctx_switches']])

                # Scheduling results
                if self.sched_results:
                    w.writerow([])
                    w.writerow(["=== SCHEDULING ANALYSIS ==="])
                    w.writerow(["Algorithm", "Avg_Wait", "Avg_Response",
                                 "Avg_Turnaround", "CPU_Util%", "Throughput",
                                 "Context_Switches", "Fairness"])
                    for name, data in self.sched_results.items():
                        m = data['metrics']
                        w.writerow([name, f"{m['avg_wait']:.4f}", f"{m['avg_resp']:.4f}",
                                     f"{m['avg_tat']:.4f}", f"{m['cpu_util']:.2f}",
                                     f"{m['throughput']:.4f}", m['switches'],
                                     f"{m['fairness']:.4f}"])

                # System stats
                if self.sys_stats:
                    w.writerow([])
                    w.writerow(["=== SYSTEM SNAPSHOT ==="])
                    s = self.sys_stats
                    w.writerow(["CPU%", "Memory%", "Memory_Used_GB", "Memory_Total_GB"])
                    w.writerow([f"{s['cpu_percent']:.1f}", f"{s['mem_percent']:.1f}",
                                 f"{s['mem_used_gb']:.2f}", f"{s['mem_total_gb']:.2f}"])

            self.log(f"Exported to {os.path.basename(path)}", "ok")
            messagebox.showinfo("Export Complete",
                                f"Data exported to:\n{path}")
        except Exception as e:
            self.log(f"Export failed: {e}", "err")
            messagebox.showerror("Export Failed", str(e))

    def _export_log(self):
        """Save the activity log to a text file."""
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export Activity Log",
            initialfile=f"cpu_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if not path:
            return
        try:
            content = self.log_text.get("1.0", "end")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log(f"Log exported to {os.path.basename(path)}", "ok")
        except Exception as e:
            self.log(f"Log export failed: {e}", "err")

    def _clear_log(self):
        """Clear the activity log."""
        self.log_text.delete("1.0", "end")
        self.log("Log cleared.", "debug")

    def _edit_weights(self):
        """Open a dialog to customize the 6 optimization metric weights."""
        # Current weights (mirroring C++ OptimizationEngine defaults)
        if not hasattr(self, '_opt_weights'):
            self._opt_weights = {
                "Waiting Time":        0.25,
                "Response Time":       0.25,
                "Turnaround Time":     0.15,
                "CPU Utilization":     0.15,
                "Fairness":            0.10,
                "Context Switches":    0.10,
            }

        dlg = tk.Toplevel(self)
        dlg.title("Optimization Metric Weights")
        dlg.configure(bg=BG_DARK)
        dlg.resizable(False, False)
        dlg.grab_set()

        tk.Label(dlg, text="OPTIMIZATION WEIGHTS", bg=BG_DARK, fg=ACCENT_CYAN,
                 font=("Segoe UI", 13, "bold")).pack(pady=(16, 4), padx=24)
        tk.Label(dlg, text="Weights must sum to 1.0  ·  Lower-is-better: Wait, Response, Turnaround, Ctx Switches",
                 bg=BG_DARK, fg=FG_DIM, font=("Segoe UI", 9)).pack(pady=(0, 12), padx=24)

        frame = tk.Frame(dlg, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(padx=24, pady=4, fill="x")

        vars_ = {}
        for i, (name, val) in enumerate(self._opt_weights.items()):
            tk.Label(frame, text=name, bg=BG_CARD, fg=FG_SECONDARY,
                     font=("Segoe UI", 10), width=22, anchor="w").grid(
                row=i, column=0, padx=14, pady=6, sticky="w")
            v = tk.DoubleVar(value=round(val, 4))
            vars_[name] = v
            e = tk.Entry(frame, textvariable=v, width=8, bg=BG_INPUT, fg=FG_PRIMARY,
                         font=("Consolas", 11), relief="flat", insertbackground=FG_PRIMARY)
            e.grid(row=i, column=1, padx=14, pady=6)

        total_lbl = tk.Label(dlg, text="Sum = 1.00", bg=BG_DARK, fg=ACCENT_GREEN,
                             font=("Consolas", 10, "bold"))
        total_lbl.pack(pady=(8, 4))

        def _update_total(*_):
            try:
                total = sum(v.get() for v in vars_.values())
                color = ACCENT_GREEN if abs(total - 1.0) < 0.001 else ACCENT_RED
                total_lbl.configure(text=f"Sum = {total:.4f}", fg=color)
            except Exception:
                total_lbl.configure(text="Sum = ?", fg=ACCENT_AMBER)

        for v in vars_.values():
            v.trace_add("write", _update_total)

        def _apply():
            try:
                vals = {k: v.get() for k, v in vars_.items()}
                total = sum(vals.values())
                if abs(total - 1.0) > 0.005:
                    messagebox.showerror("Invalid Weights",
                                         f"Weights must sum to 1.0 (currently {total:.4f})",
                                         parent=dlg)
                    return
                self._opt_weights = vals
                self.log("Optimization weights updated. Re-run scheduling analysis to apply.", "action")
                dlg.destroy()
            except Exception as ex:
                messagebox.showerror("Error", str(ex), parent=dlg)

        def _reset():
            defaults = [0.25, 0.25, 0.15, 0.15, 0.10, 0.10]
            for v, d in zip(vars_.values(), defaults):
                v.set(d)

        btn_row = tk.Frame(dlg, bg=BG_DARK)
        btn_row.pack(pady=16, padx=24, fill="x")
        tk.Button(btn_row, text="Reset Defaults", command=_reset,
                  bg=BG_INPUT, fg=FG_SECONDARY, relief="flat",
                  font=("Segoe UI", 10), padx=12, pady=6, cursor="hand2").pack(side="left")
        tk.Button(btn_row, text="Apply", command=_apply,
                  bg=ACCENT_BLUE, fg="#ffffff", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=14, pady=6, cursor="hand2").pack(side="right")
        tk.Button(btn_row, text="Cancel", command=dlg.destroy,
                  bg=BG_INPUT, fg=FG_SECONDARY, relief="flat",
                  font=("Segoe UI", 10), padx=12, pady=6, cursor="hand2").pack(side="right", padx=8)

    def _run_as_admin(self):
        """Relaunch GUI with admin privileges via UAC."""
        try:
            script = os.path.abspath(sys.argv[0])
            python_exe = sys.executable
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", python_exe, f'"{script}"', None, 1)
            if result <= 32:
                raise OSError(f"Windows returned error code {result}")
            self.log("Relaunching as admin...", "ok")
            self.after(1000, sys.exit)
        except Exception as e:
            self.log(f"Failed to elevate: {e}", "err")

    def _scan(self):
        self.btn_scan.configure(state="disabled", text="Scanning...")
        self.btn_sched.configure(state="disabled")
        self.btn_optimize.configure(state="disabled")
        self.set_status("Scanning system...", ACCENT_AMBER)
        self.log("Scanning real OS processes...")
        def _do():
            try:
                self.processes, cpu_count = collect_processes()
                self.sys_stats = get_system_stats()
                self.bottlenecks = detect_bottlenecks(self.processes, self.sys_stats)
                self.workload = classify_workload(self.processes, self.sys_stats)
                self.suggestions = suggest_optimizations(self.processes, self.bottlenecks, self.workload)
                self.after(0, self._on_scan_done)
            except Exception as e:
                self.after(0, lambda error=e: self._on_scan_error(error))
        threading.Thread(target=_do, daemon=True).start()

    def _on_scan_error(self, error):
        self.btn_scan.configure(state="normal", text="Refresh System Scan")
        self.set_status("Scan failed — see activity log", ACCENT_RED)
        self.log(f"Scan failed: {error}", "err")

    def _on_scan_done(self):
        self.btn_scan.configure(state="normal", text="Refresh System Scan")
        self.btn_sched.configure(state="normal")
        self.btn_optimize.configure(state="normal")
        self._populate_tree()
        s = self.sys_stats
        
        # Dynamic Color logic for Health Indicators
        cpu_color = ACCENT_GREEN if s['cpu_percent'] < 50 else ACCENT_AMBER if s['cpu_percent'] < 80 else ACCENT_RED
        mem_color = ACCENT_GREEN if s['mem_percent'] < 60 else ACCENT_AMBER if s['mem_percent'] < 85 else ACCENT_RED
        
        self.cpu_lbl.configure(text=f"CPU: {s['cpu_percent']:.1f}%", fg=cpu_color)
        self.mem_lbl.configure(text=f"Memory: {s['mem_percent']:.1f}% ({s['mem_used_gb']:.1f}/{s['mem_total_gb']:.1f} GB)", fg=mem_color)
        self.proc_lbl.configure(text=f"Processes: {len(self.processes)}")
        self.core_lbl.configure(text=f"CPU Cores: {psutil.cpu_count(logical=True)}")
        if is_admin():
            self.admin_lbl.configure(text="Admin: YES (full optimization)", fg=ACCENT_GREEN)
        else:
            self.admin_lbl.configure(text="Admin: NO (limited optimization)", fg=ACCENT_AMBER)
        
        tnames = {"CPU": "CPU", "MEMORY": "Memory", "CONTEXT_SWITCHES": "Context Switches"}
        if self.bottlenecks:
            rank = {"HIGH": 2, "MEDIUM": 1}
            worst = max(self.bottlenecks, key=lambda b: rank.get(b['severity'], 0))
            sev = worst['severity']
            sev_color = ACCENT_RED if sev == "HIGH" else ACCENT_AMBER
            self.bn_level.configure(text=sev, fg=sev_color)
            self.bn_primary.configure(text=tnames.get(worst['type'], worst['type']),
                                      fg=sev_color)
            if worst['type'] == "CONTEXT_SWITCHES":
                self.bn_current.configure(text="{:,} switches".format(worst['value']))
            else:
                self.bn_current.configure(text="{:.1f}%".format(worst['value']))
            top = worst['top_processes'][0] if worst['top_processes'] else None
            if top:
                if worst['type'] == 'CPU':
                    self.bn_top.configure(
                        text="{} \u2014 {:.1f}% CPU".format(top['name'], top['cpu']))
                elif worst['type'] == 'MEMORY':
                    self.bn_top.configure(
                        text="{} \u2014 {:.0f} MB".format(top['name'], top['mem_mb']))
                else:
                    self.bn_top.configure(
                        text="{} \u2014 {:,} ctx switches".format(top['name'], top['ctx_switches']))
            if worst['type'] == 'MEMORY':
                reason = ("System memory usage is critically high and may cause swapping."
                          if sev == "HIGH" else "System memory usage is relatively high.")
            elif worst['type'] == 'CPU':
                reason = ("CPU load is critically high; interactive tasks may stutter."
                          if sev == "HIGH" else
                          "CPU utilization is elevated above comfortable levels.")
            else:
                reason = "Multiple processes generate excessive context switching overhead."
            extra = len(self.bottlenecks) - 1
            if extra > 0:
                reason += " +{} more finding{}.".format(extra, "s" if extra != 1 else "")
            self.bn_detail.configure(text=reason)
        else:
            self.bn_level.configure(text="LOW", fg=ACCENT_GREEN)
            self.bn_primary.configure(text="None", fg=ACCENT_GREEN)
            self.bn_current.configure(text="--")
            self.bn_top.configure(text="--")
            self.bn_detail.configure(text="System running within normal parameters.")

        self._update_chips()
        self.history.append({"time": datetime.datetime.now(),
                             "cpu": s['cpu_percent'], "mem": s['mem_percent']})
        if len(self.history) > 240:
            del self.history[:-240]
        self._draw_trend()
        self._draw_top_procs()
        self.after(220, self._refit_all_charts)
        
        self._write_analysis()
        self.log(f"Scanned {len(self.processes)} processes, {len(self.bottlenecks)} bottlenecks, {len(self.suggestions)} suggestions", "ok")
        self.set_status(f"{len(self.processes)} processes analyzed", ACCENT_GREEN)


    def _write_analysis(self):
        s = self.sys_stats
        w = self.workload

        cpu_col = (ACCENT_GREEN if s['cpu_percent'] < 50 else
                   ACCENT_AMBER if s['cpu_percent'] < 80 else ACCENT_RED)
        mem_col = (ACCENT_GREEN if s['mem_percent'] < 60 else
                   ACCENT_AMBER if s['mem_percent'] < 85 else ACCENT_RED)
        self.an_vals["cpu"].configure(text="{:.1f}%".format(s['cpu_percent']))
        self.an_bars["cpu"].setv(s['cpu_percent'], cpu_col)
        self.an_vals["mem"].configure(text="{:.1f}%".format(s['mem_percent']))
        self.an_bars["mem"].setv(s['mem_percent'], mem_col)
        self.an_vals["procs"].configure(text=str(w.get('count', len(self.processes))))
        self.an_vals["wtype"].configure(text=w['type'])
        self.an_verdict.configure(
            text="{} workload across {} processes \u2014 CPU {:.1f}%, memory {:.1f}% "
                 "({:.1f}/{:.1f} GB used).".format(
                     w['type'], w.get('count', len(self.processes)),
                     s['cpu_percent'], s['mem_percent'],
                     s['mem_used_gb'], s['mem_total_gb']),
            fg=ACCENT_CYAN)

        self._fill_kv(self.wl_frame, [
            ("Classification", w['type'], ACCENT_GREEN),
            ("CPU-bound",      str(w.get('cpu_bound', 0)), None),
            ("I/O-bound",      str(w.get('io_bound', 0)), None),
            ("Interactive",    str(w.get('interactive', 0)), None),
            ("Running",        str(w.get('running', 0)), ACCENT_CYAN),
            ("Sleeping",       str(w.get('sleeping', 0)), None),
        ])

        for child in self.bottles_frame.winfo_children():
            child.destroy()
        if not self.bottlenecks:
            tk.Label(self.bottles_frame,
                     text="No bottlenecks detected \u2014 system within normal parameters.",
                     bg=BG_CARD, fg=ACCENT_GREEN, font=("Segoe UI", 9, "italic"),
                     wraplength=380, justify="left").pack(anchor="w")
        else:
            for bn in self.bottlenecks:
                box = tk.Frame(self.bottles_frame, bg=BG_INPUT,
                               highlightbackground=BORDER, highlightthickness=1)
                box.pack(fill="x", pady=4)
                head = tk.Frame(box, bg=BG_INPUT)
                head.pack(fill="x", padx=10, pady=(8, 2))
                sev_col = ACCENT_RED if bn['severity'] == 'HIGH' else ACCENT_AMBER
                tnames = {"CPU": "CPU", "MEMORY": "Memory",
                          "CONTEXT_SWITCHES": "Context Switches"}
                tk.Label(head, text=tnames.get(bn['type'], bn['type']),
                         bg=BG_INPUT, fg=FG_PRIMARY,
                         font=("Segoe UI", 10, "bold")).pack(side="left")
                tk.Label(head, text="\u25cf {}".format(bn['severity']),
                         bg=BG_INPUT, fg=sev_col,
                         font=("Segoe UI", 9, "bold")).pack(side="right")
                tk.Label(box, text=bn['description'], bg=BG_INPUT,
                         fg=FG_SECONDARY, font=("Segoe UI", 9), anchor="w",
                         wraplength=360, justify="left").pack(fill="x", padx=10)
                top = bn['top_processes'][0] if bn['top_processes'] else None
                if top:
                    if bn['type'] == 'CPU':
                        detail = "{} \u2014 {:.1f}% CPU".format(top['name'][:24], top['cpu'])
                    elif bn['type'] == 'MEMORY':
                        detail = "{} \u2014 {:.0f} MB".format(top['name'][:24], top['mem_mb'])
                    else:
                        detail = "{} \u2014 {:,} switches".format(top['name'][:24], top['ctx_switches'])
                    tk.Label(box, text="Top: {}".format(detail), bg=BG_INPUT,
                             fg=FG_DIM, font=("Segoe UI", 9), anchor="w",
                             wraplength=360, justify="left").pack(fill="x",
                                                                  padx=10,
                                                                  pady=(0, 8))

        for child in self.sugg_frame.winfo_children():
            child.destroy()
        if not is_admin():
            self.sug_admin_note.configure(
                text="Running without administrator \u2014 protected/system processes "
                     "cannot be modified. Use 'Run as Admin' for full optimization.")
        else:
            self.sug_admin_note.configure(text="")
        if not self.suggestions:
            tk.Label(self.sugg_frame,
                     text="No optimizations needed \u2014 the current workload is healthy.",
                     bg=BG_CARD, fg=ACCENT_GREEN, font=("Segoe UI", 9, "italic"),
                     wraplength=800, justify="left").pack(anchor="w")
            return
        for sg in self.suggestions[:6]:
            box = tk.Frame(self.sugg_frame, bg=BG_INPUT,
                           highlightbackground=BORDER, highlightthickness=1)
            box.pack(fill="x", pady=4)
            head = tk.Frame(box, bg=BG_INPUT)
            head.pack(fill="x", padx=10, pady=(8, 2))
            tk.Label(head, text="{} \u00b7 {}".format(sg['name'][:28], sg['action']),
                     bg=BG_INPUT, fg=FG_PRIMARY,
                     font=("Segoe UI", 10, "bold")).pack(side="left")
            tk.Label(head, text="{} \u2192 {}".format(sg['current'], sg['recommended']),
                     bg=BG_INPUT, fg=ACCENT_CYAN,
                     font=("Consolas", 10, "bold")).pack(side="right")
            r = tk.Label(box, text="Reason: {}".format(sg['reason']),
                         bg=BG_INPUT, fg=FG_DIM, font=("Segoe UI", 9),
                         wraplength=760, justify="left", anchor="w")
            r.pack(fill="x", padx=10, pady=(0, 8))
        if len(self.suggestions) > 6:
            tk.Label(self.sugg_frame,
                     text="+ {} additional suggestions shown during optimization.".format(
                         len(self.suggestions) - 6),
                     bg=BG_CARD, fg=FG_DIM,
                     font=("Segoe UI", 9, "italic")).pack(anchor="w")

    def _sched(self):
        if not self.processes:
            self.log("Scan system first!", "warn"); return
        self.set_status("Running scheduling analysis...", ACCENT_AMBER)
        self.log("Running FCFS, SJF, SRTF, Round Robin, Priority...")
        def _do():
            try:
                sp = build_sched_workload(self.processes)
                self.sched_results = run_scheduling_analysis(sp)
                self.after(0, self._render_sched_review)
            except Exception as e:
                self.after(0, lambda: self.log(f"Error: {e}", "err"))
        threading.Thread(target=_do, daemon=True).start()

    def _draw_gantt(self):
        """Render a true preemptive Gantt timeline using actual execution segments."""
        self._fit_figure(self.gantt_canvas, self.gantt_fig, 0, 0, True)
        ax = self.gantt_ax
        ax.clear()
        ax.set_facecolor(BG_CARD)
        if not self.sched_results:
            return

        # Find best recommended algorithm name
        best_name = None
        if hasattr(self, 'sched_verdict'):
            vtxt = self.sched_verdict.cget("text")
            if "Recommended: " in vtxt:
                best_name = vtxt.replace("Recommended: ", "").split("  (")[0].strip()
        if not best_name or best_name not in self.sched_results:
            best_name = min(self.sched_results, key=lambda name: self.sched_results[name]['metrics']['avg_wait'])

        data = self.sched_results[best_name]
        gantt = data.get('gantt', [])
        if not gantt:
            return

        palette = [
            "#4fc3f7", "#69f0ae", "#ff4081", "#ffd740", "#b388ff",
            "#ff5252", "#00e5ff", "#76ff03", "#ff6e40", "#e040fb",
            "#448aff", "#64ffda", "#ffab40", "#7c4dff"
        ]

        # Extract unique processes (excluding IDLE)
        pids = []
        for seg in gantt:
            if seg['pid'] != -1 and seg['pid'] not in pids:
                pids.append(seg['pid'])

        pid_color = {pid: palette[i % len(palette)] for i, pid in enumerate(pids)}
        pid_y = {pid: i for i, pid in enumerate(pids)}

        has_idle = any(seg['pid'] == -1 for seg in gantt)
        if has_idle:
            pid_y[-1] = len(pids)
            pid_color[-1] = "#475569"

        max_time = max((seg['end'] for seg in gantt), default=1.0)
        if max_time <= 0:
            max_time = 1.0

        for seg in gantt:
            duration = seg['end'] - seg['start']
            if duration <= 0:
                continue
            pid = seg['pid']
            y = pid_y.get(pid, 0)
            col = pid_color.get(pid, ACCENT_BLUE)
            alpha = 0.50 if pid == -1 else 0.90
            ax.barh(y, duration, left=seg['start'], height=0.6,
                    color=col, alpha=alpha, edgecolor=BORDER, linewidth=0.6)
            
            # Label segment
            if duration >= max_time * 0.04:
                txt = "IDLE" if pid == -1 else f"P{pid}"
                ax.text(seg['start'] + duration / 2.0, y, txt,
                        ha="center", va="center", fontsize=7.5, fontweight="bold",
                        color="#0b0b12" if pid != -1 else "#cbd5e1")

        ytick_positions = [pid_y[p] for p in pids]
        ytick_labels = [next((s['name'][:14] for s in gantt if s['pid'] == p), f"P{p}") for p in pids]
        if has_idle:
            ytick_positions.append(pid_y[-1])
            ytick_labels.append("IDLE")

        ax.set_yticks(ytick_positions)
        ax.set_yticklabels(ytick_labels, fontsize=8, color=FG_SECONDARY)
        ax.set_xlabel("Elapsed Time Units", color=FG_SECONDARY, fontsize=8)
        ax.set_title(f"Gantt Schedule: {best_name} (Total Time: {max_time:.1f})",
                     color=ACCENT_CYAN, fontsize=9.5, fontweight="bold", pad=8)
        ax.set_xlim(0, max_time * 1.02)
        ax.grid(axis="x", color=BORDER, linewidth=0.3, alpha=0.6)
        ax.invert_yaxis()
        for sp in ax.spines.values():
            sp.set_color(BORDER)
        ax.tick_params(colors=FG_SECONDARY, labelsize=8)
        self.gantt_fig.subplots_adjust(left=0.22, right=0.96, top=0.88, bottom=0.18)
        self.gantt_canvas.draw()

    def _optimize(self):
        if not self.processes:
            self.log("Scan system first!", "warn"); return
        self.optimized_pids.clear()
        self.set_status("Optimizing system...", ACCENT_AMBER)
        self.log("Measuring BEFORE state...")
        if not is_admin():
            self.log("WARNING: Running without admin — some optimizations may fail", "warn")

        def _do():
            try:
                # BEFORE measurement
                before = measure_improvement(num_samples=5, interval=0.5)
                self.before_stats = before
                self.before_snapshot = self._capture_snapshot()

                self.after(0, lambda: self.log(f"BEFORE: CPU={before['cpu']:.1f}% MEM={before['mem']:.1f}%", "action"))

                # Apply optimizations
                applied = 0
                for sg in self.suggestions:
                    if apply_optimization(sg['pid'], sg['recommended']):
                        applied += 1
                        self.optimized_pids.add(sg['pid'])
                        self.after(0, lambda n=sg['name'], r=sg['recommended']: self.log(f"Applied: {n} -> {r}", "ok"))
                    time.sleep(0.1)

                self.actions_record = [
                    {'name': sg['name'], 'action': sg['action'],
                     'before': sg['current'], 'after': sg['recommended'],
                     'result': 'Applied' if sg['pid'] in self.optimized_pids else 'Skipped',
                     'reason': sg['reason']}
                    for sg in self.suggestions]
                self.after(0, lambda: self.log(f"Applied {applied}/{len(self.suggestions)} optimizations", "ok"))

                # AFTER measurement
                self.after(0, lambda: self.log("Measuring AFTER state...", "info"))
                time.sleep(1.0)
                after = measure_improvement(num_samples=5, interval=0.5)
                self.after_stats = after

                self.after(0, self._on_opt_done)
            except Exception as e:
                self.after(0, lambda: self.log(f"Error: {e}", "err"))

        threading.Thread(target=_do, daemon=True).start()

    def _on_opt_done(self):
        self._render_opt_review(self.before_stats, self.after_stats)

    def _render_sched_review(self):
        """Render a concise decision-oriented scheduling comparison."""
        # Compute weighted score using user-configured weights (or defaults)
        weights = getattr(self, '_opt_weights', {
            "Waiting Time": 0.25, "Response Time": 0.25, "Turnaround Time": 0.15,
            "CPU Utilization": 0.15, "Fairness": 0.10, "Context Switches": 0.10,
        })

        all_metrics = {name: data['metrics'] for name, data in self.sched_results.items()}
        # Find best for normalization
        best_wait  = min(m['avg_wait']  for m in all_metrics.values()) or 1e-9
        best_resp  = min(m['avg_resp']  for m in all_metrics.values()) or 1e-9
        best_tat   = min(m['avg_tat']   for m in all_metrics.values()) or 1e-9
        best_cpu   = max(m['cpu_util']  for m in all_metrics.values()) or 1e-9
        best_fair  = max(m['fairness']  for m in all_metrics.values()) or 1e-9
        best_sw    = min(m['switches']  for m in all_metrics.values()) or 1

        def _score(m):
            sw = m['switches'] if m['switches'] > 0 else 1
            return (
                weights["Waiting Time"]     * min(best_wait  / max(m['avg_wait'],  1e-9), 1.0) * 100 +
                weights["Response Time"]    * min(best_resp  / max(m['avg_resp'],  1e-9), 1.0) * 100 +
                weights["Turnaround Time"]  * min(best_tat   / max(m['avg_tat'],   1e-9), 1.0) * 100 +
                weights["CPU Utilization"]  * min(m['cpu_util']  / best_cpu,  1.0) * 100 +
                weights["Fairness"]         * min(m['fairness']  / best_fair, 1.0) * 100 +
                weights["Context Switches"] * min(best_sw / sw, 1.0) * 100
            )

        scored = sorted(
            [(name, data, _score(data['metrics'])) for name, data in self.sched_results.items()],
            key=lambda x: x[2], reverse=True
        )
        best_name, best_data, best_score = scored[0]
        best_metrics = best_data['metrics']
        rows = best_data['rows']

        self.sched_verdict.configure(
            text=f"Recommended: {best_name}  (score {best_score:.1f}/100)", fg=ACCENT_GREEN)
        self.sched_detail.configure(
            text=f"Ranked by weighted score across 6 metrics on {len(rows)} observed processes. "
                 f"Waiting: {best_metrics['avg_wait']:.2f}  "
                 f"Response: {best_metrics['avg_resp']:.2f}  "
                 f"Fairness: {best_metrics['fairness']:.4f}  "
                 "· Timeline is a simulation — not live kernel control.")

        for child in self.sched_table.winfo_children():
            child.destroy()

        # Extended comparison table with 7 columns
        col_defs = [
            ("Algorithm",    "w", 3),
            ("Score",        "e", 1),
            ("Avg Wait",     "e", 1),
            ("Response",     "e", 1),
            ("Turnaround",   "e", 1),
            ("CPU%",         "e", 1),
            ("Fairness",     "e", 1),
            ("Switches",     "e", 1),
        ]
        for c, (h, anchor, weight) in enumerate(col_defs):
            self.sched_table.columnconfigure(c, weight=weight)
            tk.Label(self.sched_table, text=h, bg=BG_CARD, fg=FG_DIM,
                     font=("Segoe UI", 8, "bold")).grid(row=0, column=c,
                                                        sticky=anchor,
                                                        padx=(0 if c else 0, 8),
                                                        pady=(0, 4))

        for r, (name, data, score) in enumerate(scored, start=1):
            m = data['metrics']
            is_best = name == best_name
            fg  = ACCENT_GREEN if is_best else FG_SECONDARY
            fnt = ("Segoe UI", 10, "bold") if is_best else ("Segoe UI", 10)
            mono = ("Consolas", 10, "bold") if is_best else ("Consolas", 10)
            marker = "★ " if is_best else "  "

            short = name.replace("Priority Scheduling", "Priority").replace("Round Robin", "RR")
            tk.Label(self.sched_table, text=f"{marker}{short}",
                     bg=BG_CARD, fg=fg, font=fnt, anchor="w").grid(
                row=r, column=0, sticky="w", pady=3, padx=(0, 8))

            vals = [
                f"{score:.1f}",
                f"{m['avg_wait']:.2f}",
                f"{m['avg_resp']:.2f}",
                f"{m['avg_tat']:.2f}",
                f"{m['cpu_util']:.1f}%",
                f"{m['fairness']:.4f}",
                f"{m['switches']:,}",
            ]
            for c, val in enumerate(vals, start=1):
                tk.Label(self.sched_table, text=val,
                         bg=BG_CARD, fg=fg, font=mono).grid(
                    row=r, column=c, sticky="e", pady=3, padx=(0, 8))

        for child in self.sched_notes_frame.winfo_children():
            child.destroy()
        notes = [
            (f"{best_name} has the highest weighted score ({best_score:.1f}/100) for this workload.",
             ACCENT_GREEN),
            ("Round Robin is preferable when interactive response time matters most.",
             FG_SECONDARY),
            ("Burst times are estimated from CPU activity; use Ctrl+W to adjust metric weights.",
             FG_DIM),
        ]
        for text, color in notes:
            tk.Label(self.sched_notes_frame, text=f"• {text}",
                     bg=BG_CARD, fg=color, font=("Segoe UI", 9), wraplength=380,
                     justify="left", anchor="w").pack(anchor="w", pady=3)

        self._draw_comparison_chart(scored, best_name)
        self._draw_gantt()
        self.log(f"Scheduling analysis complete: {best_name} recommended (score {best_score:.1f})", "ok")
        self.set_status(f"Scheduling recommendation: {best_name}", ACCENT_GREEN)
        self.nb.select(3)
        self.after(220, self._refit_all_charts)

    def _draw_comparison_chart(self, scored, recommended):
        """Render a clean, high-contrast algorithm ranking comparison chart."""
        self._fit_figure(self.comparison_canvas, self.comparison_fig, 0, 0, False)
        ax = self.comparison_ax
        ax.clear()
        ax.set_facecolor(BG_CARD)

        # Ranked by score ascending for bottom-to-top display
        raw_names = [item[0] for item in scored][::-1]
        display_names = [
            ("★ " + item[0].replace("Priority Scheduling", "Priority").replace("Round Robin", "RR")
             if item[0] == recommended else
             item[0].replace("Priority Scheduling", "Priority").replace("Round Robin", "RR"))
            for item in scored
        ][::-1]
        scores = [item[2] for item in scored][::-1]
        waits = [item[1]['metrics']['avg_wait'] for item in scored][::-1]
        colors = [ACCENT_GREEN if name == recommended else ACCENT_BLUE for name in raw_names]

        y_pos = list(range(len(display_names)))
        bars = ax.barh(y_pos, scores, height=0.56, color=colors, alpha=0.90,
                       edgecolor=BORDER, linewidth=0.8)

        for bar, score, wait in zip(bars, scores, waits):
            label_txt = f"{score:.1f} pts  (Wait: {wait:.2f})"
            if score > 45:
                ax.text(score - 1.5, bar.get_y() + bar.get_height() / 2, label_txt,
                        va="center", ha="right", fontsize=8, color="#0b0b12", fontweight="bold")
            else:
                ax.text(score + 1.2, bar.get_y() + bar.get_height() / 2, label_txt,
                        va="center", ha="left", fontsize=8, color=FG_PRIMARY, fontweight="bold")

        ax.set_yticks(y_pos)
        ax.set_yticklabels(display_names, fontsize=8.5, fontweight="bold", color=FG_PRIMARY)
        ax.set_xlim(0, 105)
        ax.set_xlabel("Overall Optimization Score (0-100 pts)", color=FG_SECONDARY, fontsize=8)
        ax.set_title("Algorithm Performance & Ranking", color=ACCENT_CYAN,
                     fontsize=9.5, fontweight="bold", pad=8)
        ax.grid(axis="x", color=BORDER, linewidth=0.4, alpha=0.45)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.tick_params(colors=FG_SECONDARY, labelsize=8)
        self.comparison_fig.subplots_adjust(left=0.22, right=0.96, top=0.88, bottom=0.18)
        self.comparison_canvas.draw()

    def _render_opt_review(self, before, after):
        """Render the optimization review from real measured before/after samples."""
        cpu_delta = before['cpu'] - after['cpu']
        mem_delta = before['mem'] - after['mem']
        attempted = len(self.suggestions)
        applied = [sg for sg in self.suggestions if sg['pid'] in self.optimized_pids]
        improved = cpu_delta > 0.5 or mem_delta > 0.5
        worsened = cpu_delta < -0.5 or mem_delta < -0.5
        material = max(abs(cpu_delta), abs(mem_delta)) >= 2.0

        # Verdict banner
        if improved and material:
            verdict, accent = "Resource pressure decreased measurably.", ACCENT_GREEN
        elif worsened and material:
            verdict, accent = "Resource pressure increased during the after-sample.", ACCENT_RED
        elif improved or worsened:
            verdict, accent = ("Only marginal shifts observed between samples \u2014 "
                               "within normal short-window variation.", ACCENT_AMBER)
        else:
            verdict, accent = "No material change detected in this short measurement window.", ACCENT_AMBER
        self.opt_verdict.configure(text=verdict, fg=accent)
        self.opt_banner.configure(highlightbackground=accent)

        # Optimization summary
        def pair(b, a):
            return "{:.1f}%  \u2192  {:.1f}%".format(b, a)

        def delta_color(delta):
            if delta > 0.5:
                return ACCENT_GREEN
            if delta < -0.5:
                return ACCENT_RED
            return FG_SECONDARY

        self.sum_rows["cpu"].configure(text=pair(before['cpu'], after['cpu']),
                                       fg=delta_color(cpu_delta))
        self.sum_rows["mem"].configure(text=pair(before['mem'], after['mem']),
                                       fg=delta_color(mem_delta))
        self.sum_rows["applied"].configure(
            text="{} / {}".format(len(applied), attempted),
            fg=ACCENT_GREEN if applied else ACCENT_AMBER)
        self.sum_rows["recommended"].configure(text=str(attempted), fg=FG_SECONDARY)
        admin_mode = is_admin()
        if improved and material:
            status_text, status_color = "Improved", ACCENT_GREEN
        elif worsened and material:
            status_text, status_color = "Higher Pressure", ACCENT_RED
        elif improved or worsened:
            status_text, status_color = "Stable (minor shift)", ACCENT_CYAN
        else:
            status_text, status_color = "Stable", ACCENT_CYAN
        self.sum_rows["sysstatus"].configure(text=status_text, fg=status_color)
        self.sum_rows["mode"].configure(
            text="Administrator" if admin_mode else "Limited",
            fg=ACCENT_GREEN if admin_mode else ACCENT_AMBER)
        if improved and material:
            result_text = "Material improvement"
        elif worsened and material:
            result_text = "Pressure increased"
        elif improved or worsened:
            result_text = "Minor fluctuation"
        else:
            result_text = "No material change"
        self.sum_rows["result"].configure(text=result_text, fg=accent)

        # Priority changes strip
        if applied:
            lines = ["\u2022 {}   {} \u2192 {}".format(sg['name'][:34], sg['current'], sg['recommended'])
                     for sg in applied[:3]]
            if len(applied) > 3:
                lines.append("+ {} more applied".format(len(applied) - 3))
            self.opt_prio.configure(text="\n".join(lines), fg=FG_SECONDARY)
        elif attempted:
            self.opt_prio.configure(
                text="None applied \u2014 Administrator privileges may be required for the recommended processes.",
                fg=ACCENT_AMBER)
        else:
            self.opt_prio.configure(
                text="No priority changes were recommended for this workload.",
                fg=FG_DIM)

        # Before/After chart — real sampled values only
        self._fit_figure(self.opt_canvas, self.opt_fig, 0, 0, False)
        ax = self.opt_ax
        ax.clear()
        ax.set_facecolor(BG_CARD)
        labels = ['CPU Utilization', 'Memory Utilization']
        positions = [0.0, 1.0]
        before_values = [before['cpu'], before['mem']]
        after_values = [after['cpu'], after['mem']]
        width = 0.20
        bars_before = ax.bar([0.0 - 0.12, 1.0 - 0.12], before_values, width,
                             label='Before', color=ACCENT_PINK, alpha=0.92,
                             edgecolor=BORDER, linewidth=0.8)
        bars_after = ax.bar([0.0 + 0.12, 1.0 + 0.12], after_values, width,
                            label='After', color=ACCENT_GREEN, alpha=0.92,
                            edgecolor=BORDER, linewidth=0.8)
        for bars in (bars_before, bars_after):
            for bar in bars:
                h = bar.get_height()
                if h > 78:
                    ax.text(bar.get_x() + bar.get_width() / 2, h - 6.0,
                            f"{h:.1f}%", ha="center", va="top",
                            fontsize=8.5, color="#0b0b12", fontweight="bold")
                else:
                    ax.text(bar.get_x() + bar.get_width() / 2, h + 2.0,
                            f"{h:.1f}%", ha="center", va="bottom",
                            fontsize=8.5, color=FG_PRIMARY, fontweight="bold")
        ax.set_xlim(-0.75, 1.75)
        ax.set_ylim(0, 110)
        ax.set_yticks(range(0, 101, 20))
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, color=FG_PRIMARY, fontsize=9.5, fontweight="bold")
        ax.set_ylabel("Utilization (%)", color=FG_SECONDARY, fontsize=8.5)
        ax.grid(axis="y", color=BORDER, linewidth=0.5, alpha=0.45)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.tick_params(colors=FG_SECONDARY, labelsize=8.5)
        ax.legend(loc="upper left", frameon=False, fontsize=8.5,
                  labelcolor=FG_PRIMARY, borderaxespad=0.4)
        self.opt_fig.subplots_adjust(left=0.10, right=0.90, top=0.90, bottom=0.18)
        self.opt_canvas.draw()

        def movement(d):
            if d > 0.5:
                return "down {:.1f} pts".format(d)
            if d < -0.5:
                return "up {:.1f} pts".format(abs(d))
            if abs(d) < 1e-9:
                return "unchanged"
            return "{} {:.1f} pts (minor)".format("down" if d > 0 else "up", abs(d))

        note = ("CPU {:.1f}% \u2192 {:.1f}% ({})   \u00b7   Memory {:.1f}% \u2192 {:.1f}% ({}). "
                "All values are direct measurements.").format(
            before['cpu'], after['cpu'], movement(cpu_delta),
            before['mem'], after['mem'], movement(mem_delta))
        self.opt_chart_note.configure(text=note)

        # ---- Before / Actions / After / Result narrative (real data only) ----
        applied_n = len(applied)
        skipped = attempted - applied_n
        bs = self.before_snapshot
        if bs:
            after_snap = self._capture_snapshot()
            after_snap['cpu'] = after['cpu']
            after_snap['mem'] = after['mem']

            risk_color = (lambda r: ACCENT_RED if r.startswith("HIGH")
                          else ACCENT_AMBER if "MEDIUM" in r else ACCENT_GREEN)
            self._fill_kv(self.before_frame, [
                ("CPU utilization",        "{:.2f}%".format(bs['cpu']), ACCENT_CYAN),
                ("Memory utilization",     "{:.2f}%".format(bs['mem']), ACCENT_AMBER),
                ("Running processes",      str(bs['nprocs']), None),
                ("CPU-heavy processes",    "{} (> 15% CPU)".format(bs['cpu_heavy']), None),
                ("Memory-heavy processes", "{} (> 200 MB)".format(bs['mem_heavy']), None),
                ("Priority mix",           bs['prio'], None),
                ("Recommended actions",    str(bs['recs']),
                 ACCENT_PINK if bs['recs'] else None),
                ("Risk level",             bs['risk'], risk_color(bs['risk'])),
                ("Optimization mode",      bs['mode'],
                 ACCENT_GREEN if bs['mode'] == "Administrator" else ACCENT_AMBER),
            ])
            self._fill_kv(self.after_frame, [
                ("CPU utilization",        "{:.2f}%".format(after_snap['cpu']), ACCENT_CYAN),
                ("Memory utilization",     "{:.2f}%".format(after_snap['mem']), ACCENT_AMBER),
                ("Running processes",      str(after_snap['nprocs']), None),
                ("Top CPU process",        after_snap['top_cpu'], None),
                ("Top memory process",     after_snap['top_mem'], None),
                ("Priority changes",       "{} applied".format(applied_n),
                 ACCENT_GREEN if applied_n else ACCENT_AMBER),
                ("Actions applied",        str(applied_n),
                 ACCENT_GREEN if applied_n else ACCENT_AMBER),
                ("Recommendations left",   str(skipped),
                 ACCENT_AMBER if skipped else ACCENT_GREEN),
                ("Risk level",             after_snap['risk'],
                 risk_color(after_snap['risk'])),
                ("Optimization mode",      after_snap['mode'],
                 ACCENT_GREEN if after_snap['mode'] == "Administrator" else ACCENT_AMBER),
            ])
            self.act_counts.configure(
                text="Recommended: {}    Applied: {}    Skipped: {}".format(
                    attempted, applied_n, skipped))

            for child in self.actions_frame.winfo_children():
                child.destroy()
            if not self.actions_record:
                self._set_empty(self.actions_frame,
                                "No optimization actions were recommended for this workload.")
            else:
                if applied_n == 0:
                    tk.Label(self.actions_frame,
                             text="No optimization actions were applied.",
                             bg=BG_CARD, fg=ACCENT_AMBER,
                             font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
                for rec in self.actions_record:
                    box = tk.Frame(self.actions_frame, bg=BG_INPUT,
                                   highlightbackground=BORDER, highlightthickness=1)
                    box.pack(fill="x", pady=4)
                    head = tk.Frame(box, bg=BG_INPUT)
                    head.pack(fill="x", padx=10, pady=(8, 2))
                    okc = ACCENT_GREEN if rec['result'] == 'Applied' else ACCENT_AMBER
                    tk.Label(head, text="{} \u00b7 {}".format(rec['name'][:26], rec['action']),
                             bg=BG_INPUT, fg=FG_PRIMARY,
                             font=("Segoe UI", 10, "bold")).pack(side="left")
                    tk.Label(head, text="\u25cf {}".format(rec['result']),
                             bg=BG_INPUT, fg=okc,
                             font=("Segoe UI", 9, "bold")).pack(side="right")
                    tk.Label(box,
                             text="Before: {}   \u2192   After: {}".format(rec['before'], rec['after']),
                             bg=BG_INPUT, fg=FG_SECONDARY,
                             font=("Consolas", 10), anchor="w").pack(fill="x", padx=10)
                    rs = tk.Label(box, text="Reason: {}".format(rec['reason']),
                                  bg=BG_INPUT, fg=FG_DIM, font=("Segoe UI", 9),
                                  wraplength=860, justify="left", anchor="w")
                    rs.pack(fill="x", padx=10, pady=(2, 8))
                    box.bind("<Configure>",
                             lambda e, w=rs: w.configure(wraplength=max(300, e.width - 40)))

            def delta_sentence(name, b, a):
                d = a - b
                if abs(d) < 0.01:
                    return "{} remained essentially unchanged ({:.2f}% \u2192 {:.2f}%).".format(
                        name, b, a)
                return "{} changed from {:.2f}% to {:.2f}% ({:+.2f} percentage points).".format(
                    name, b, a, d)

            lines = [delta_sentence("CPU utilization", bs['cpu'], after['cpu']),
                     delta_sentence("Memory utilization", bs['mem'], after['mem'])]
            if applied_n:
                lines.append("{} process priority change{} applied ({} \u2192 {}).".format(
                    applied_n, " was" if applied_n == 1 else "es were",
                    applied[0]['current'], applied[0]['recommended']))
            elif attempted:
                lines.append("No process priority changes could be applied.")
            else:
                lines.append("No process priority changes were recommended.")
            if skipped and not is_admin():
                if skipped == 1:
                    lines.append("1 optimization recommendation remains because the "
                                 "application is running in Limited mode.")
                else:
                    lines.append("{} optimization recommendations remain because the "
                                 "application is running in Limited mode.".format(skipped))
            if improved and material:
                lines.append("The measurement window produced a measurable improvement.")
            elif worsened and material:
                lines.append("Resource pressure increased during the measurement window.")
            else:
                lines.append("This measurement window did not produce a material improvement.")
            self.what_label.configure(text="\n".join(lines))

            if improved and material:
                stxt, scol = "IMPROVED", ACCENT_GREEN
            elif worsened and material:
                stxt, scol = "HIGHER RESOURCE PRESSURE", ACCENT_RED
            elif improved or worsened:
                stxt, scol = "STABLE", ACCENT_CYAN
            else:
                stxt, scol = "NO MATERIAL CHANGE", ACCENT_AMBER
            self.result_status.configure(text=stxt, fg=scol)
            self.result_rows["CPU change"].configure(text="{:+.2f} pts".format(cpu_delta))
            self.result_rows["Memory change"].configure(text="{:+.2f} pts".format(mem_delta))
            self.result_rows["Actions applied"].configure(text=str(applied_n))
            self.result_rows["Recommendations"].configure(text=str(attempted))
            self.result_rows["Mode"].configure(text=bs['mode'])
            if not self.actions_record:
                res_reason = "No priority changes were recommended for this workload."
            elif applied_n == 0:
                res_reason = ("Recommended changes could not be applied \u2014 Administrator "
                              "privileges may be required for these processes.")
            elif improved and material:
                res_reason = "Resource pressure decreased following the applied optimizations."
            elif worsened and material:
                res_reason = "Background activity offset the applied optimizations during sampling."
            else:
                res_reason = "Observed differences are within normal short-window variation."
            self.result_reason.configure(text=res_reason)

        self._update_chips({"cpu_percent": after['cpu'], "mem_percent": after['mem']})
        now = datetime.datetime.now()
        self.history.append({"time": now, "cpu": before['cpu'], "mem": before['mem']})
        self.history.append({"time": now, "cpu": after['cpu'], "mem": after['mem']})
        if len(self.history) > 240:
            del self.history[:-240]
        self.opt_event_index = len(self.history) - 1
        self._draw_trend()

        if improved and material:
            self.log(f"Optimization review complete. CPU: {before['cpu']:.1f}% → {after['cpu']:.1f}%", "ok")
            self.set_status(f"Review complete: CPU {cpu_delta:+.1f}%  MEM {mem_delta:+.1f}%", ACCENT_GREEN)
        else:
            self.log(f"Optimization review complete. CPU: {before['cpu']:.1f}% → {after['cpu']:.1f}%", "warn")
            self.set_status("Review complete — no material change", ACCENT_AMBER)
        self.nb.select(4)
        self.opt_view.yview_moveto(0)
        self.after(220, self._refit_all_charts)
        cpu_col = ACCENT_GREEN if after['cpu'] < 50 else ACCENT_AMBER if after['cpu'] < 80 else ACCENT_RED
        mem_col = ACCENT_GREEN if after['mem'] < 60 else ACCENT_AMBER if after['mem'] < 85 else ACCENT_RED
        self.cpu_lbl.configure(text=f"CPU: {after['cpu']:.1f}%", fg=cpu_col)
        self.mem_lbl.configure(text=f"Memory: {after['mem']:.1f}%", fg=mem_col)


if __name__ == "__main__":
    app = SchedulingGUI()
    app.mainloop()
