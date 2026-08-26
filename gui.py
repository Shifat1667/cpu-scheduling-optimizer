"""
Real-Time CPU Scheduling & Process Optimization System
======================================================
Collects real OS process data, detects bottlenecks, applies safe
optimizations (priority adjustment), and measures Before/After results.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading, ctypes, os, datetime, math, statistics, time, sys

import psutil

import matplotlib
matplotlib.use("TkAgg")
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

        self._styles()
        self._build_ui()
        self.log("System initialized. Ready for workload analysis.", "info")

    def _styles(self):
        s = ttk.Style(self); s.theme_use("clam")
        s.configure(".", background=BG_DARK, foreground=FG_PRIMARY, borderwidth=0)
        s.configure("TFrame", background=BG_DARK)
        s.configure("TLabel", background=BG_DARK, foreground=FG_PRIMARY, font=("Segoe UI", 11))
        s.configure("Header.TLabel", font=("Segoe UI", 24, "bold"), foreground=ACCENT_CYAN, background=BG_DARK)
        s.configure("Sub.TLabel", font=("Segoe UI", 12), foreground=FG_SECONDARY, background=BG_DARK)
        s.configure("Eyebrow.TLabel", font=("Segoe UI", 10, "bold"), foreground=ACCENT_PURPLE, background=BG_DARK)
        s.configure("Custom.Treeview", background=BG_CARD, foreground=FG_PRIMARY,
                     fieldbackground=BG_CARD, borderwidth=0, rowheight=34, font=("Consolas", 11))
        s.configure("Custom.Treeview.Heading", background=BG_PANEL, foreground=ACCENT_CYAN,
                     font=("Segoe UI", 11, "bold"), borderwidth=0)
        s.map("Custom.Treeview", background=[("selected", ACCENT_BLUE)], foreground=[("selected", "#000")])
        s.configure("Custom.TNotebook", background=BG_DARK, borderwidth=0)
        s.configure("Custom.TNotebook.Tab", background=BG_PANEL, foreground=FG_PRIMARY,
                     font=("Segoe UI", 11, "bold"), padding=(20, 10))
        s.map("Custom.TNotebook.Tab", background=[("selected", BG_CARD)], foreground=[("selected", ACCENT_CYAN)])

    def _build_ui(self):
        # Main Container
        main_container = tk.Frame(self, bg=BG_DARK)
        main_container.pack(fill="both", expand=True)

        # Top Header
        header = tk.Frame(main_container, bg=BG_PANEL, height=72, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        title_f = tk.Frame(header, bg=BG_PANEL)
        title_f.pack(side="left", padx=20, pady=6)
        ttk.Label(title_f, text="CPU SCHEDULING OPTIMIZER", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(title_f, text="System Resource Optimization Tool", style="Header.TLabel").pack(anchor="w")
        
        self.status_lbl = ttk.Label(header, text="● System Ready", style="Sub.TLabel")
        self.status_lbl.pack(side="right", padx=20, pady=(15, 0))

        # Body Layout
        body = tk.Frame(main_container, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        # Sidebar
        sidebar = tk.Frame(body, bg=BG_PANEL, width=310, highlightbackground=BORDER, highlightthickness=1)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        sb_content = tk.Frame(sidebar, bg=BG_PANEL, padx=15, pady=15)
        sb_content.pack(fill="both", expand=True)

        # HUD
        hud = tk.Frame(sb_content, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1, padx=12, pady=12)
        hud.pack(fill="x", pady=(0, 20))
        tk.Label(hud, text="SYSTEM STATUS", bg=BG_CARD, fg=ACCENT_CYAN, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.cpu_lbl = tk.Label(hud, text="CPU: ---%", bg=BG_CARD, fg=ACCENT_GREEN, font=("Consolas", 14, "bold"))
        self.cpu_lbl.pack(anchor="w", pady=(8, 0))
        self.mem_lbl = tk.Label(hud, text="MEM: ---%", bg=BG_CARD, fg=ACCENT_AMBER, font=("Consolas", 14, "bold"))
        self.mem_lbl.pack(anchor="w", pady=(0, 8))
        self.proc_lbl = tk.Label(hud, text="Processes: --", bg=BG_CARD, fg=FG_SECONDARY, font=("Segoe UI", 10))
        self.proc_lbl.pack(anchor="w")
        self.core_lbl = tk.Label(hud, text="Cores: --", bg=BG_CARD, fg=FG_SECONDARY, font=("Segoe UI", 10))
        self.core_lbl.pack(anchor="w")
        self.admin_lbl = tk.Label(hud, text="Admin: checking...", bg=BG_CARD, fg=FG_SECONDARY, font=("Segoe UI", 10))
        self.admin_lbl.pack(anchor="w")

        # Controls
        actions = tk.Frame(sb_content, bg=BG_PANEL)
        actions.pack(fill="x", pady=(0, 20))
        self.btn_scan = tk.Button(actions, text="Refresh System", bg=ACCENT_BLUE, fg="#fff",
            font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2", padx=15, pady=10, command=self._scan)
        self.btn_scan.pack(fill="x", pady=(0, 8))
        self.btn_sched = tk.Button(actions, text="Run Scheduling Analysis", bg=BG_CARD, fg=ACCENT_GREEN,
            font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2", padx=15, pady=10, command=self._sched, state="disabled")
        self.btn_sched.pack(fill="x", pady=(0, 8))
        self.btn_optimize = tk.Button(actions, text="Optimize System", bg=BG_CARD, fg=ACCENT_PINK,
            font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2", padx=15, pady=10, command=self._optimize, state="disabled")
        self.btn_optimize.pack(fill="x")

        if not is_admin():
            self.btn_admin = tk.Button(actions, text="Run as Admin", bg=ACCENT_AMBER, fg="#000",
                font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", padx=15, pady=8,
                command=self._run_as_admin)
            self.btn_admin.pack(fill="x", pady=(10, 0))

        self.bn_card = tk.Frame(sb_content, bg=BG_CARD, highlightbackground=ACCENT_RED, highlightthickness=1, padx=15, pady=15)
        self.bn_card.pack(fill="x", pady=(20, 0))
        tk.Label(self.bn_card, text="RISK ANALYSIS", bg=BG_CARD, fg=ACCENT_RED, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.bn_label = tk.Label(self.bn_card, text="--", bg=BG_CARD, fg=ACCENT_AMBER, font=("Consolas", 12, "bold"))
        self.bn_label.pack(anchor="w", pady=(8, 0))
        self.bn_detail = tk.Label(self.bn_card, text="", bg=BG_CARD, fg=FG_SECONDARY, font=("Segoe UI", 10), wraplength=260, justify="left")
        self.bn_detail.pack(anchor="w")

        self.nb = ttk.Notebook(body, style="Custom.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=20, pady=20)
        self._tab_processes(); self._tab_analysis(); self._tab_scheduling(); self._tab_optimization(); self._tab_log()



    def _build_control(self, parent):
        pass


    # ── Tabs ───────────────────────────────────────────────────────────────
    def _tab_processes(self):
        f = tk.Frame(self.nb, bg=BG_DARK); self.nb.add(f, text="  Processes  ")
        cols = ("PID","Name","State","CPU%","Memory MB","Priority","Threads","Ctx Switches")
        tf = tk.Frame(f, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        tf.pack(fill="both", expand=True, padx=8, pady=8)
        self.ptree = ttk.Treeview(tf, columns=cols, show="headings", style="Custom.Treeview")
        for c in cols:
            if c == "Name":
                self.ptree.heading(c, text=c, anchor="w"); self.ptree.column(c, width=230, minwidth=180, anchor="w", stretch=True)
                continue
            w = 70 if c in ("PID","CPU%","Threads","Ctx Switches") else 110 if c in ("Priority","Memory MB") else 130
            self.ptree.heading(c, text=c, anchor="w"); self.ptree.column(c, width=w, minwidth=w, anchor="center", stretch=False)
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.ptree.yview)
        self.ptree.configure(yscrollcommand=vsb.set)
        self.ptree.pack(side="left", fill="both", expand=True); vsb.pack(side="right", fill="y")

    def _tab_analysis(self):
        f = tk.Frame(self.nb, bg=BG_DARK); self.nb.add(f, text="  Analysis  ")
        self.analysis_text = scrolledtext.ScrolledText(f, bg=BG_CARD, fg=FG_PRIMARY, font=("Consolas", 11),
            insertbackground=FG_PRIMARY, borderwidth=0, highlightbackground=BORDER, highlightthickness=1, wrap="word")
        self.analysis_text.pack(fill="both", expand=True, padx=8, pady=8)
        self.analysis_text.tag_configure("h", foreground=ACCENT_CYAN, font=("Consolas", 11, "bold"))
        self.analysis_text.tag_configure("g", foreground=ACCENT_GREEN)
        self.analysis_text.tag_configure("r", foreground=ACCENT_RED)
        self.analysis_text.tag_configure("a", foreground=ACCENT_AMBER)
        self.analysis_text.tag_configure("d", foreground=FG_DIM)

    def _tab_scheduling(self):
        f = tk.Frame(self.nb, bg=BG_DARK); self.nb.add(f, text="  Scheduling  ")
        split = ttk.PanedWindow(f, orient="vertical")
        split.pack(fill="both", expand=True, padx=8, pady=8)
        report_frame = tk.Frame(split, bg=BG_DARK)
        timeline_frame = tk.Frame(split, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        split.add(report_frame, weight=3)
        split.add(timeline_frame, weight=2)
        self.sched_text = scrolledtext.ScrolledText(report_frame, bg=BG_CARD, fg=FG_PRIMARY, font=("Consolas", 11),
            insertbackground=FG_PRIMARY, borderwidth=0, highlightbackground=BORDER, highlightthickness=1, wrap="word")
        self.sched_text.pack(fill="both", expand=True)
        self.sched_text.tag_configure("h", foreground=ACCENT_CYAN, font=("Consolas", 11, "bold"))
        self.sched_text.tag_configure("g", foreground=ACCENT_GREEN, font=("Consolas", 11, "bold"))
        self.sched_text.tag_configure("a", foreground=ACCENT_AMBER)
        self.sched_text.tag_configure("d", foreground=FG_DIM)

        charts = ttk.PanedWindow(timeline_frame, orient="horizontal")
        charts.pack(fill="both", expand=True, padx=4, pady=4)
        comparison_frame = tk.Frame(charts, bg=BG_CARD)
        gantt_frame = tk.Frame(charts, bg=BG_CARD)
        charts.add(comparison_frame, weight=1)
        charts.add(gantt_frame, weight=2)

        tk.Label(comparison_frame, text="ALGORITHM PERFORMANCE", bg=BG_CARD, fg=ACCENT_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=8, pady=(4, 0))
        self.comparison_fig = Figure(figsize=(5, 3), dpi=100, facecolor=BG_DARK)
        self.comparison_ax = self.comparison_fig.add_subplot(111)
        self.comparison_ax.set_facecolor(BG_CARD)
        self.comparison_canvas = FigureCanvasTkAgg(self.comparison_fig, comparison_frame)
        self.comparison_canvas.get_tk_widget().pack(fill="both", expand=True)

        tk.Label(gantt_frame, text="RECOMMENDED SCHEDULE TIMELINE", bg=BG_CARD, fg=ACCENT_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=8, pady=(4, 0))
        self.gantt_fig = Figure(figsize=(12,3), dpi=100, facecolor=BG_DARK)
        self.gantt_ax = self.gantt_fig.add_subplot(111)
        self.gantt_ax.set_facecolor(BG_CARD)
        for sp in self.gantt_ax.spines.values(): sp.set_color(BORDER)
        self.gantt_ax.tick_params(colors=FG_SECONDARY, labelsize=8)
        self.gantt_canvas = FigureCanvasTkAgg(self.gantt_fig, gantt_frame)
        self.gantt_canvas.get_tk_widget().pack(fill="both", expand=True)

    def _tab_optimization(self):
        f = tk.Frame(self.nb, bg=BG_DARK); self.nb.add(f, text="  Optimization  ")
        split = ttk.PanedWindow(f, orient="vertical")
        split.pack(fill="both", expand=True, padx=8, pady=8)
        report_frame = tk.Frame(split, bg=BG_DARK)
        chart_frame = tk.Frame(split, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        split.add(report_frame, weight=3)
        split.add(chart_frame, weight=2)
        self.opt_text = scrolledtext.ScrolledText(report_frame, bg=BG_CARD, fg=FG_PRIMARY, font=("Consolas", 11),
            insertbackground=FG_PRIMARY, borderwidth=0, highlightbackground=BORDER, highlightthickness=1, wrap="word")
        self.opt_text.pack(fill="both", expand=True)
        self.opt_text.tag_configure("h", foreground=ACCENT_CYAN, font=("Consolas", 11, "bold"))
        self.opt_text.tag_configure("g", foreground=ACCENT_GREEN, font=("Consolas", 11, "bold"))
        self.opt_text.tag_configure("r", foreground=ACCENT_RED)
        self.opt_text.tag_configure("a", foreground=ACCENT_AMBER)
        self.opt_text.tag_configure("d", foreground=FG_DIM)

        tk.Label(chart_frame, text="RESOURCE COMPARISON", bg=BG_CARD, fg=ACCENT_CYAN,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(8, 0))
        self.opt_fig = Figure(figsize=(10,3), dpi=100, facecolor=BG_DARK)
        self.opt_ax = self.opt_fig.add_subplot(111)
        self.opt_ax.set_facecolor(BG_CARD)
        for sp in self.opt_ax.spines.values(): sp.set_color(BORDER)
        self.opt_ax.tick_params(colors=FG_SECONDARY, labelsize=8)
        self.opt_canvas = FigureCanvasTkAgg(self.opt_fig, chart_frame)
        self.opt_canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=(0, 4))

    def _tab_log(self):
        f = tk.Frame(self.nb, bg=BG_DARK); self.nb.add(f, text="  Log  ")
        self.log_text = scrolledtext.ScrolledText(f, bg=BG_CARD, fg=FG_SECONDARY, font=("Consolas", 10),
            insertbackground=FG_PRIMARY, borderwidth=0, highlightbackground=BORDER, highlightthickness=1, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)
        self.log_text.tag_configure("time", foreground=FG_DIM)
        self.log_text.tag_configure("info", foreground=ACCENT_CYAN)
        self.log_text.tag_configure("ok", foreground=ACCENT_GREEN)
        self.log_text.tag_configure("warn", foreground=ACCENT_AMBER)
        self.log_text.tag_configure("err", foreground=ACCENT_RED)

    def log(self, msg, tag="info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] ", "time")
        self.log_text.insert("end", f"{msg}\n", tag)
        self.log_text.see("end")

    def set_status(self, t, c=FG_SECONDARY):
        self.status_lbl.configure(text=t, foreground=c)

    def _populate_tree(self):
        for i in self.ptree.get_children(): self.ptree.delete(i)
        for i, p in enumerate(self.processes):
            self.ptree.insert("", "end", values=(
                p['pid'], p['name'], p['state'],
                f"{p['cpu']:.1f}", f"{p['mem_mb']:.0f}",
                p['priority_name'], p['threads'], f"{p['ctx_switches']:,}"
            ))
        self.ptree.bind("<Button-3>", self._show_context_menu)

    def _show_context_menu(self, event):
        item = self.ptree.identify_row(event.y)
        if not item: return
        
        menu = tk.Menu(self, tearoff=0, bg=BG_PANEL, fg=FG_PRIMARY, activebackground=ACCENT_BLUE, font=("Segoe UI", 10))
        pid = int(self.ptree.item(item)['values'][0])
        name = self.ptree.item(item)['values'][1]
        
        menu.add_command(label=f"Kill {name}", foreground=ACCENT_RED, command=lambda: self._kill_process(pid))
        menu.add_separator()
        menu.add_command(label="Set High Priority", command=lambda: self._quick_prio(pid, "High"))
        menu.add_command(label="Set Normal Priority", command=lambda: self._quick_prio(pid, "Normal"))
        menu.add_command(label="Set Low Priority", command=lambda: self._quick_prio(pid, "Low (Idle)"))
        
        menu.post(event.x_root, event.y_root)

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
    def _run_as_admin(self):
        """Relaunch GUI with admin privileges via UAC."""
        try:
            script = os.path.abspath(sys.argv[0])
            python_exe = sys.executable
            result = ctypes.windll.shell32.ShellExecuteW(None, "runas", python_exe, f'"{script}"', None, 1)
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
        self.btn_scan.configure(state="normal", text="Scan system")
        self.set_status("Scan failed — see activity log", ACCENT_RED)
        self.log(f"Scan failed: {error}", "err")

    def _on_scan_done(self):
        self.btn_scan.configure(state="normal", text="Refresh system scan")
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
        
        if self.bottlenecks:
            bn = self.bottlenecks[0]
            sev_color = ACCENT_RED if bn['severity'] == 'HIGH' else ACCENT_AMBER
            self.bn_label.configure(text=f"{bn['type']} — {bn['severity']}", fg=sev_color)
            top = bn['top_processes'][0] if bn['top_processes'] else None
            detail = bn['description']
            if top: detail += f"\nTop: {top['name']} ({top['cpu']:.1f}% CPU)" if bn['type'] == 'CPU' else f"\nTop: {top['name']} ({top['mem_mb']:.0f} MB)"
            self.bn_detail.configure(text=detail)
        else:
            self.bn_label.configure(text="None detected", fg=ACCENT_GREEN)
            self.bn_detail.configure(text="System running within normal parameters")
        
        self._write_analysis()
        self.log(f"Scanned {len(self.processes)} processes, {len(self.bottlenecks)} bottlenecks, {len(self.suggestions)} suggestions", "ok")
        self.set_status(f"{len(self.processes)} processes analyzed", ACCENT_GREEN)


    def _write_analysis(self):
        t = self.analysis_text; t.delete("1.0", "end")
        s = self.sys_stats; w = self.workload
        t.insert("end", "=== SYSTEM ANALYSIS ===\n\n", "h")
        t.insert("end", f"CPU Usage:       {s['cpu_percent']:.1f}%\n", "a")
        t.insert("end", f"Memory Usage:    {s['mem_percent']:.1f}% ({s['mem_used_gb']:.1f} / {s['mem_total_gb']:.1f} GB)\n", "a")
        t.insert("end", f"Processes:       {w['count']}\n\n", "a")

        t.insert("end", "=== WORKLOAD CLASSIFICATION ===\n\n", "h")
        t.insert("end", f"Type:            {w['type']}\n", "g")
        t.insert("end", f"CPU-bound:       {w.get('cpu_bound',0)}\n")
        t.insert("end", f"I/O-bound:       {w.get('io_bound',0)}\n")
        t.insert("end", f"Interactive:     {w.get('interactive',0)}\n")
        t.insert("end", f"Running:         {w.get('running',0)}\n")
        t.insert("end", f"Sleeping:        {w.get('sleeping',0)}\n\n")

        t.insert("end", "=== BOTTLENECKS ===\n\n", "h")
        if self.bottlenecks:
            for bn in self.bottlenecks:
                color = "r" if bn['severity'] == 'HIGH' else "a"
                t.insert("end", f"[{bn['severity']}] {bn['type']}: {bn['description']}\n", color)
                for p in bn['top_processes'][:3]:
                    t.insert("end", f"    {p['name'][:32]:<34} CPU: {p['cpu']:.1f}%  MEM: {p['mem_mb']:.0f} MB\n", "d")
        else:
            t.insert("end", "No bottlenecks detected.\n", "g")

        t.insert("end", f"\n=== OPTIMIZATION SUGGESTIONS ({len(self.suggestions)}) ===\n\n", "h")
        if not is_admin():
            t.insert("end", "NOTE: Running without admin — some processes cannot be modified.\n", "a")
            t.insert("end", "Click 'Run as Admin' to enable full optimization.\n\n", "a")
        if self.suggestions:
            for sg in self.suggestions[:5]:
                t.insert("end", f"  {sg['name'][:32]}\n", "a")
                t.insert("end", f"    Action: {sg['action']}  {sg['current']} -> {sg['recommended']}\n")
                t.insert("end", f"    Reason: {sg['reason']}\n", "d")
                t.insert("end", f"    Expected: {sg['expected_effect']}\n\n", "d")
        else:
            t.insert("end", "No optimizations needed.\n", "g")

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
        ax = self.gantt_ax; ax.clear(); ax.set_facecolor(BG_CARD)
        if not self.sched_results: return
        first = min(self.sched_results, key=lambda name: self.sched_results[name]['metrics']['avg_wait'])
        rows = self.sched_results[first]['rows']
        colors = ["#4fc3f7","#69f0ae","#ff4081","#ffd740","#b388ff","#ff5252","#00e5ff",
                  "#76ff03","#ff6e40","#e040fb","#448aff","#64ffda","#ffab40","#7c4dff"]
        for i, r in enumerate(rows):
            ax.barh(i, r['burst'], left=r['arrival'], height=0.6, color=colors[i%len(colors)], alpha=0.85, edgecolor="#000", linewidth=0.5)
            ax.text((r['arrival']+r['completion'])/2, i, f"P{r['pid']}", ha="center", va="center", fontsize=7, fontweight="bold", color="#000")
        ax.set_yticks(range(len(rows))); ax.set_yticklabels([r['name'][:16] for r in rows], fontsize=8, color=FG_SECONDARY)
        ax.set_xlabel("Time", color=FG_SECONDARY, fontsize=8); ax.set_title(f"Gantt — {first}", color=ACCENT_CYAN, fontsize=10, fontweight="bold")
        mx = max(r['completion'] for r in rows) if rows else 1
        ax.set_xlim(0, mx*1.05); ax.grid(axis="x", color=BORDER, linewidth=0.3, alpha=0.5); ax.invert_yaxis()
        for sp in ax.spines.values(): sp.set_color(BORDER)
        ax.tick_params(colors=FG_SECONDARY, labelsize=8)
        self.gantt_fig.tight_layout(); self.gantt_canvas.draw()

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

                self.after(0, lambda: self.log(f"BEFORE: CPU={before['cpu']:.1f}% MEM={before['mem']:.1f}%", "a"))

                # Apply optimizations
                applied = 0
                for sg in self.suggestions:
                    if apply_optimization(sg['pid'], sg['recommended']):
                        applied += 1
                        self.optimized_pids.add(sg['pid'])
                        self.after(0, lambda n=sg['name'], r=sg['recommended']: self.log(f"Applied: {n} -> {r}", "ok"))
                    time.sleep(0.1)

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
        ranked = sorted(self.sched_results.items(), key=lambda item: item[1]['metrics']['avg_wait'])
        best_name, best_data = ranked[0]
        best_metrics = best_data['metrics']
        rows = best_data['rows']

        t = self.sched_text; t.delete("1.0", "end")
        t.insert("end", "SCHEDULING DECISION\n", "h")
        t.insert("end", f"Recommended approach: {best_name}\n", "g")
        t.insert("end", f"Lowest average wait across {len(rows)} observed processes: {best_metrics['avg_wait']:.2f} time units.\n\n", "d")
        t.insert("end", "ALGORITHM COMPARISON\n", "h")
        t.insert("end", "Algorithm                 Avg wait   Response   Fairness    Switches\n", "d")
        t.insert("end", "─" * 72 + "\n", "d")
        for name, data in ranked:
            metrics = data['metrics']
            tag = "g" if name == best_name else "d"
            marker = "★ " if name == best_name else "  "
            t.insert("end", f"{marker}{name[:22]:<22}  {metrics['avg_wait']:>8.2f}   {metrics['avg_resp']:>8.2f}   "
                            f"{metrics['fairness']:>8.4f}   {metrics['switches']:>8}\n", tag)
        t.insert("end", "\nDECISION NOTES\n", "h")
        t.insert("end", f"• {best_name} is selected by lowest average waiting time for this captured workload.\n", "g")
        t.insert("end", "• Round Robin may still be preferable when consistent interactive response is the priority.\n", "d")
        t.insert("end", "• Timeline below shows the recommended algorithm’s derived schedule, not live kernel control.\n", "d")

        self._draw_comparison_chart(ranked, best_name)
        self._draw_gantt()
        self.log(f"Scheduling analysis complete: {best_name} recommended", "ok")
        self.set_status(f"Scheduling recommendation: {best_name}", ACCENT_GREEN)
        self.nb.select(2)

    def _draw_comparison_chart(self, ranked, recommended):
        """Draw a readable comparison of the algorithms used in the report."""
        ax = self.comparison_ax; ax.clear(); ax.set_facecolor(BG_CARD)
        names = [name.replace("Priority Scheduling", "Priority") for name, _ in ranked]
        waits = [data['metrics']['avg_wait'] for _, data in ranked]
        colors = [ACCENT_GREEN if name == recommended else ACCENT_BLUE for name, _ in ranked]
        bars = ax.barh(range(len(names)), waits, color=colors, alpha=0.9, height=0.62)
        for bar, value in zip(bars, waits):
            ax.text(value + max(waits, default=1) * 0.025, bar.get_y() + bar.get_height() / 2,
                    f"{value:.2f}", va="center", fontsize=8, color=FG_PRIMARY, fontweight="bold")
        ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=8, color=FG_SECONDARY)
        ax.set_xlabel("Average wait (lower is better)", color=FG_SECONDARY, fontsize=8)
        ax.set_title("Waiting-time comparison", color=FG_PRIMARY, fontsize=10, fontweight="bold")
        ax.set_xlim(0, max(waits, default=1) * 1.24)
        ax.grid(axis="x", color=BORDER, linewidth=0.3, alpha=0.6)
        ax.invert_yaxis()
        for spine in ax.spines.values(): spine.set_color(BORDER)
        ax.tick_params(colors=FG_SECONDARY, labelsize=8)
        self.comparison_fig.tight_layout(); self.comparison_canvas.draw()

    def _render_opt_review(self, before, after):
        """Render a compact, readable before/after optimization report."""
        cpu_delta = before['cpu'] - after['cpu']
        mem_delta = before['mem'] - after['mem']
        attempted = len(self.suggestions)
        applied = [sg for sg in self.suggestions if sg['pid'] in self.optimized_pids]

        if cpu_delta > 0.5 or mem_delta > 0.5:
            verdict, verdict_tag = "Resource pressure decreased in at least one metric.", "g"
        elif cpu_delta < -0.5 or mem_delta < -0.5:
            verdict, verdict_tag = "Resource pressure increased during the after-sample.", "r"
        else:
            verdict, verdict_tag = "No material change detected in this short measurement window.", "a"

        def change(delta):
            if delta > 0.5:
                return f"-{delta:.1f}%", "g", "Lower"
            if delta < -0.5:
                return f"+{abs(delta):.1f}%", "r", "Higher"
            return "±0.0%", "d", "Stable"

        cpu_change, cpu_tag, cpu_status = change(cpu_delta)
        mem_change, mem_tag, mem_status = change(mem_delta)
        t = self.opt_text; t.delete("1.0", "end")
        t.insert("end", "OPTIMIZATION REVIEW\n", "h")
        t.insert("end", f"{verdict}\n\n", verdict_tag)
        t.insert("end", "RESOURCE SNAPSHOT\n", "h")
        t.insert("end", "Metric                 Before     After      Change     Status\n", "d")
        t.insert("end", "─" * 67 + "\n", "d")
        t.insert("end", f"CPU utilization        {before['cpu']:>5.1f}%     {after['cpu']:>5.1f}%     ")
        t.insert("end", f"{cpu_change:>7}    {cpu_status}\n", cpu_tag)
        t.insert("end", f"Memory utilization     {before['mem']:>5.1f}%     {after['mem']:>5.1f}%     ")
        t.insert("end", f"{mem_change:>7}    {mem_status}\n\n", mem_tag)

        t.insert("end", "PRIORITY CHANGES\n", "h")
        t.insert("end", f"Applied {len(applied)} of {attempted} recommended changes.\n", "g" if applied else "a")
        if not is_admin():
            t.insert("end", "Limited mode: protected processes may require Administrator privileges.\n", "a")
        if applied:
            for sg in applied[:4]:
                t.insert("end", f"• {sg['name'][:32]}  {sg['current']} → {sg['recommended']}\n", "d")
            if len(applied) > 4:
                t.insert("end", f"  + {len(applied) - 4} additional changes applied\n", "d")
        elif attempted:
            t.insert("end", "No changes could be applied. Run as Administrator to access eligible processes.\n", "a")
        else:
            t.insert("end", "No priority changes were recommended for this workload.\n", "g")
        t.insert("end", "\nMeasurements are short system samples; normal background activity can affect results.\n", "d")

        ax = self.opt_ax; ax.clear(); ax.set_facecolor(BG_CARD)
        labels = ['CPU usage', 'Memory usage']
        before_values = [before['cpu'], before['mem']]
        after_values = [after['cpu'], after['mem']]
        positions = list(range(len(labels)))
        before_bars = ax.bar([x - 0.17 for x in positions], before_values, 0.34,
                             label='Before', color=ACCENT_PINK, alpha=0.85)
        after_bars = ax.bar([x + 0.17 for x in positions], after_values, 0.34,
                            label='After', color=ACCENT_GREEN, alpha=0.85)
        for bar in [*before_bars, *after_bars]:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                    f"{bar.get_height():.1f}%", ha="center", va="bottom", fontsize=8,
                    color=FG_PRIMARY, fontweight="bold")
        ax.set_xticks(positions); ax.set_xticklabels(labels, color=FG_SECONDARY, fontsize=9)
        ax.set_ylabel("Utilization (%)", color=FG_SECONDARY)
        ax.set_title("Before and after sampling", color=ACCENT_CYAN, fontsize=11, fontweight="bold")
        ax.legend(facecolor=BG_CARD, edgecolor=BORDER, labelcolor=FG_PRIMARY)
        ax.set_ylim(0, 108); ax.grid(axis="y", color=BORDER, linewidth=0.3, alpha=0.5)
        for spine in ax.spines.values(): spine.set_color(BORDER)
        ax.tick_params(colors=FG_SECONDARY, labelsize=8)
        self.opt_fig.tight_layout(); self.opt_canvas.draw()

        if cpu_delta > 0.5 or mem_delta > 0.5:
            self.log(f"Optimization review complete. CPU: {before['cpu']:.1f}% → {after['cpu']:.1f}%", "ok")
            self.set_status(f"Review complete: CPU {cpu_delta:+.1f}%  MEM {mem_delta:+.1f}%", ACCENT_GREEN)
        else:
            self.log(f"Optimization review complete. CPU: {before['cpu']:.1f}% → {after['cpu']:.1f}%", "warn")
            self.set_status("Review complete — no material change", ACCENT_AMBER)
        self.nb.select(3)
        self.cpu_lbl.configure(text=f"CPU: {after['cpu']:.1f}%")
        self.mem_lbl.configure(text=f"Memory: {after['mem']:.1f}%")


if __name__ == "__main__":
    app = SchedulingGUI()
    app.mainloop()
