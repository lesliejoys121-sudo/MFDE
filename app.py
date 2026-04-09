from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse
from env import MFDEEnv
from models import Observation, Action, Reward, State, ResetRequest
from grader import grade
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="MFDE | Email Triage System",
    version="1.0",
    description="A stateless OpenEnv environment with an interactive Gmail-style Triage Dashboard."
)
env = MFDEEnv()

class ScanRequest(BaseModel):
    text: str

# --- OPENENV RUNTIME STANDARD ENDPOINTS ---

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/metadata")
def metadata():
    return {
        "name": "MFDE-Email-Triage",
        "description": "Misleading Feedback Decision Environment: Email Triage System. Tests AI agents on high-stakes decisions under noisy, misleading reward signals.",
        "version": "1.2.7",
        "tags": ["openenv", "nlp", "classification", "uncertainty", "calibration"]
    }

@app.get("/schema")
def schema():
    return {
        "action": {
            "decision": {"type": "string", "options": ["reply", "ignore", "escalate"]},
            "priority": {"type": "string", "options": ["low", "medium", "high"]},
            "email_id": {"type": "integer", "optional": True}
        },
        "observation": {
            "email_text": {"type": "string"},
            "sender": {"type": "string"},
            "subject": {"type": "string"},
            "step_count": {"type": "integer"}
        },
        "state": {
            "current_step": {"type": "integer"},
            "total_steps": {"type": "integer"},
            "task_name": {"type": "string"},
            "is_done": {"type": "boolean"},
            "history": {"type": "array"}
        }
    }

@app.post("/mcp")
def mcp(payload: Optional[dict] = Body(default=None)):
    return {
        "jsonrpc": "2.0",
        "result": {
            "name": "MFDE-Email-Triage",
            "capabilities": ["reset", "step", "state", "health", "metadata", "schema"]
        },
        "id": (payload or {}).get("id", None)
    }

# --- AI AGENT ENDPOINTS (STANDARD OPENENV) ---

@app.post("/reset", response_model=Observation)
def reset(req: Optional[ResetRequest] = None):
    # Handle cases where the body is missing or null
    actual_req = req or ResetRequest()
    return env.reset(actual_req.task, actual_req.mode)

@app.post("/step")
def step(action: Action):
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs,
        "reward": round(reward.value, 2),
        "done": done,
        "info": info
    }

@app.get("/state", response_model=State)
def state():
    return env.state()

# --- PERFORMANCE & ANALYTICS ---

@app.get("/api/performance")
def get_performance():
    score = env.cumulative_xp
    streak = env.current_streak
    
    # NEW: Expanded Rank Thresholds for Infinite Mode
    if score < 10.0: rank, next_goal = "Novice Analyst", 10.0
    elif score < 50.0: rank, next_goal = "Junior Triage", 50.0
    elif score < 150.0: rank, next_goal = "Senior Specialist", 150.0
    elif score < 500.0: rank, next_goal = "Master Triage Expert", 500.0
    else: rank, next_goal = "Grandmaster Phish-Hunter", 5000.0 # Legendary
    
    return {
        "total_score": round(score, 2),
        "current_streak": streak,
        "rank": rank,
        "progress_percent": min(100, (score / next_goal) * 100)
    }

# --- DASHBOARD / UI ENDPOINTS ---

@app.get("/api/inbox/{task}")
def get_inbox(task: str):
    emails = env.get_task_emails(task)
    if not emails:
        raise HTTPException(status_code=404, detail="Task not found")
    return [{"id": i, "sender": e["sender"], "subject": e["subject"], "body": e["email_text"]} for i, e in enumerate(emails)]

@app.post("/api/scan")
def scan_email(req: ScanRequest):
    return env.scan(req.text)

@app.get("/", response_class=HTMLResponse)
def root():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MFDE | Triage Command Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Inter', sans-serif; 
            color: #e2e8f0; 
            margin: 0; 
            background-color: #0b0f19;
            background-image: 
                radial-gradient(at 0% 0%, rgba(17, 24, 39, 1) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(30, 58, 138, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(15, 23, 42, 1) 0px, transparent 50%),
                radial-gradient(at 0% 100%, rgba(17, 24, 39, 1) 0px, transparent 50%);
            background-size: cover;
            background-attachment: fixed;
        }
        .glass { background: rgba(15, 23, 42, 0.4); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.05); box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1); }
        .inbox-item { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .inbox-item:hover { background: rgba(255, 255, 255, 0.03); border-left: 4px solid rgba(59, 130, 246, 0.5); padding-left: 1.25rem; }
        .active-nav { border-left: 4px solid #3b82f6; background: rgba(59, 130, 246, 0.1); box-shadow: inset 0 0 20px rgba(59,130,246,0.05); }
        [x-cloak] { display: none !important; }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
        .progress-fill { transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
        .animate-fadeIn { animation: fadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); filter: blur(4px); } to { opacity: 1; transform: translateY(0); filter: blur(0); } }
        .glow-btn { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .glow-btn:hover { filter: brightness(1.1); transform: translateY(-3px); }
        .glow-green:hover { box-shadow: 0 10px 40px -10px rgba(34,197,94,0.6); }
        .glow-red:hover { box-shadow: 0 10px 40px -10px rgba(239,68,68,0.6); }
        .glow-gray:hover { box-shadow: 0 10px 40px -10px rgba(156,163,175,0.3); }
        canvas { filter: drop-shadow(0 0 10px rgba(59, 130, 246, 0.1)); }
    </style>
</head>
<body x-data="triageApp()" x-init="checkAuth()" x-cloak class="h-screen overflow-hidden flex flex-col">
    <!-- LOGIN OVERLAY -->
    <div x-show="!isLoggedIn" class="fixed inset-0 z-[200] flex items-center justify-center bg-[#0b0f19]/95 backdrop-blur-xl">
        <div class="glass p-10 rounded-3xl w-full max-w-md text-center shadow-2xl border-white/10">
            <h1 class="text-5xl font-extrabold mb-2 bg-gradient-to-r from-blue-400 via-indigo-300 to-cyan-300 bg-clip-text text-transparent drop-shadow-lg">MFDE</h1>
            <p class="text-gray-400 text-xs mb-8 font-medium tracking-widest uppercase">Command Center Secure Login</p>
            <input type="text" x-model="loginUser" placeholder="Username" class="w-full bg-gray-900/50 border border-gray-700/50 rounded-xl p-4 mb-4 focus:ring-2 focus:ring-blue-500/50 outline-none text-white transition-all">
            <input type="password" x-model="loginPass" @keyup.enter="login()" placeholder="Password" class="w-full bg-gray-900/50 border border-gray-700/50 rounded-xl p-4 mb-6 focus:ring-2 focus:ring-blue-500/50 outline-none text-white transition-all">
            <button @click="login()" class="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-black py-4 rounded-xl transition-all shadow-[0_0_20px_rgba(37,99,235,0.3)] hover:shadow-[0_0_30px_rgba(37,99,235,0.5)] active:scale-95 tracking-widest text-lg">ACCESS TERMINAL</button>
            <p class="text-gray-600 text-[10px] mt-6 tracking-widest uppercase font-bold">Credentials: admin / mfde2024</p>
        </div>
    </div>

    <!-- HEADER -->
    <header class="h-24 flex items-center justify-between px-8 glass border-b border-white/5 shrink-0 z-50">
        <div class="flex items-center gap-10">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center font-bold text-white shadow-[0_0_20px_rgba(59,130,246,0.4)] text-2xl border border-white/10">M</div>
                <div>
                    <h2 class="text-2xl font-black tracking-tighter shadow-text">Triage<span class="text-blue-400">Center</span></h2>
                    <p class="text-[9px] text-blue-500/60 uppercase font-black tracking-[0.3em]">Neural Defense Grid</p>
                </div>
            </div>
            <!-- RANK METER -->
            <div class="hidden lg:flex items-center gap-5 pl-8 border-l border-white/5">
                <div class="text-right">
                    <p class="text-[9px] font-black text-gray-500 uppercase tracking-[0.2em] leading-none mb-1.5">Expertise Rank</p>
                    <p class="text-sm font-black bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent uppercase tracking-tight" x-text="perf.rank"></p>
                </div>
                <div class="w-56 h-2 bg-gray-900 rounded-full overflow-hidden border border-white/5 shadow-inner">
                    <div class="h-full bg-gradient-to-r from-blue-600 via-cyan-400 to-blue-400 progress-fill shadow-[0_0_10px_rgba(59,130,246,0.8)] relative">
                        <div class="absolute inset-0 bg-white/20 animate-pulse"></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="flex items-center gap-8">
            <!-- LIVE SCORE & STREAK -->
            <div class="flex items-center gap-5 glass px-6 py-3 rounded-2xl border-white/10 shadow-[0_10px_30px_rgba(0,0,0,0.5)]">
                <div class="text-center min-w-[70px]">
                    <p class="text-[9px] font-black text-gray-500 uppercase tracking-[0.2em] opacity-80 mb-0.5">Total XP</p>
                    <p class="text-2xl font-black text-white leading-tight drop-shadow-md" x-text="perf.total_score.toFixed(2)"></p>
                </div>
                <div x-show="perf.current_streak > 1" class="text-center border-l border-white/5 pl-5 min-w-[70px] animate-bounce">
                    <p class="text-[9px] font-black text-orange-500 uppercase tracking-[0.2em] leading-none mb-1">Streak</p>
                    <p class="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-b from-orange-400 to-red-500 leading-tight drop-shadow-md" x-text="'🔥 ' + perf.current_streak"></p>
                </div>
            </div>

            <select x-show="currentTab === 'inbox'" x-model="selectedTask" @change="loadInbox()" class="bg-gray-900/80 border border-white/10 rounded-2xl px-5 py-3 text-sm font-bold outline-none text-white cursor-pointer hover:border-blue-500/50 transition-colors shadow-lg appearance-none relative backdrop-blur-xl">
                <option value="easy">Easy Target (1.0x)</option>
                <option value="medium">Medium Target (1.5x)</option>
                <option value="hard">Hard Target (2.0x)</option>
            </select>
        </div>
    </header>

    <main class="flex-1 flex overflow-hidden">
        <!-- SIDEBAR -->
        <aside class="w-72 glass border-r border-white/5 p-6 flex flex-col gap-2 shrink-0 z-40">
            <button @click="currentTab = 'inbox'; loadInbox()" :class="{'active-nav': currentTab === 'inbox'}" class="w-full text-left p-4 rounded-2xl transition-all flex items-center gap-4 hover:bg-white/5 group">
                <div class="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-xl group-hover:scale-110 transition-transform shadow-inner border border-blue-500/20">📥</div> 
                <span class="font-black text-[11px] text-gray-300 uppercase tracking-[0.15em] group-hover:text-white transition-colors">Triage Inbox</span>
            </button>
            <button @click="currentTab = 'sandbox'" :class="{'active-nav': currentTab === 'sandbox'}" class="w-full text-left p-4 rounded-2xl transition-all flex items-center gap-4 hover:bg-white/5 group">
                <div class="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center text-xl group-hover:scale-110 transition-transform shadow-inner border border-indigo-500/20">🛡️</div> 
                <span class="font-black text-[11px] text-gray-300 uppercase tracking-[0.15em] group-hover:text-white transition-colors">Pro-Scanner</span>
            </button>
            <button @click="openAnalytics()" :class="{'active-nav': currentTab === 'analytics'}" class="w-full text-left p-4 rounded-2xl transition-all flex items-center gap-4 hover:bg-white/5 group">
                <div class="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center text-xl group-hover:scale-110 transition-transform shadow-inner border border-purple-500/20">📊</div> 
                <span class="font-black text-[11px] text-gray-300 uppercase tracking-[0.15em] group-hover:text-white transition-colors">Analytics Yield</span>
            </button>
            
            <div class="mt-auto pt-10">
                <div class="p-5 rounded-3xl bg-blue-900/10 border border-blue-500/20 text-center backdrop-blur-md shadow-[0_0_30px_rgba(59,130,246,0.05)]">
                    <p class="text-[9px] font-black text-blue-400 uppercase mb-2 tracking-[0.2em] shadow-text">System Core</p>
                    <p class="text-xs font-bold text-gray-300">Node Active: 104-B</p>
                    <div class="mt-3 w-full h-1.5 bg-gray-900 rounded-full overflow-hidden shadow-inner border border-white/5">
                        <div class="h-full bg-gradient-to-r from-blue-600 to-cyan-400 animate-pulse w-[85%]"></div>
                    </div>
                </div>
            </div>
        </aside>

        <!-- VIEW CONTAINER -->
        <div class="flex-1 flex overflow-hidden relative">
            <!-- INBOX VIEW -->
            <template x-if="currentTab === 'inbox'">
                <div class="flex-1 flex overflow-hidden absolute inset-0 animate-fadeIn">
                    <!-- MESSAGE LIST -->
                    <section class="w-[450px] border-r border-white/5 flex flex-col bg-gray-900/30 backdrop-blur-sm shrink-0 z-30">
                        <div class="p-7 border-b border-white/5 flex justify-between items-center glass shadow-xl z-20">
                            <h3 class="font-black text-[11px] uppercase tracking-[0.2em] text-gray-400">Operational Queue</h3>
                            <span class="text-[10px] font-black px-4 py-1.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.2)]" x-text="inbox.length + ' TARGETS'"></span>
                        </div>
                        <div class="flex-1 overflow-y-auto custom-scrollbar p-3">
                            <template x-for="email in inbox" :key="email.id">
                                <div @click="openEmail(email)" 
                                    :class="{'bg-blue-600/10 border-l-[6px] border-blue-500 shadow-[inset_0_0_20px_rgba(59,130,246,0.1)]': selectedEmail && selectedEmail.id === email.id, 'hover:bg-white/5 border-l-[6px] border-transparent': !selectedEmail || selectedEmail.id !== email.id}" 
                                    class="inbox-item p-6 mb-2 rounded-2xl cursor-pointer border border-transparent hover:border-white/5">
                                    <div class="flex justify-between mb-3 items-center">
                                        <span class="text-[10px] font-black text-blue-400 uppercase tracking-widest bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20" x-text="email.sender.split('@')[0]"></span>
                                        <div class="flex items-center gap-2">
                                            <div class="w-2 h-2 rounded-full bg-blue-500 animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.8)]"></div>
                                        </div>
                                    </div>
                                    <h4 class="text-[15px] font-black text-gray-100 mb-1.5 leading-snug drop-shadow-md" x-text="email.subject"></h4>
                                    <p class="text-xs text-gray-500 line-clamp-2 font-medium italic opacity-80" x-text="email.body"></p>
                                </div>
                            </template>
                        </div>
                    </section>

                    <!-- DETAIL VIEW -->
                    <section class="flex-1 overflow-hidden flex flex-col items-center bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-900/5 to-transparent relative z-20">
                        <template x-if="!selectedEmail">
                            <div class="h-full flex items-center justify-center text-gray-700 flex-col opacity-30 drop-shadow-2xl">
                                <span class="text-[12rem] mb-10 animate-pulse filter drop-shadow-[0_0_30px_rgba(255,255,255,0.1)]">📡</span>
                                <p class="text-3xl font-black tracking-[0.8em] uppercase text-center ml-[0.8em] text-transparent bg-clip-text bg-gradient-to-r from-gray-500 to-gray-700">Awaiting Lock</p>
                            </div>
                        </template>
                        <template x-if="selectedEmail">
                            <div class="w-full max-w-5xl h-full flex flex-col p-12 custom-scrollbar overflow-y-auto animate-fadeIn relative">
                                <!-- Watermark -->
                                <div class="absolute top-20 right-20 text-[10rem] font-black text-white/[0.02] uppercase select-none pointer-events-none tracking-tighter mix-blend-overlay">TARGET</div>
                                
                                <div class="mb-12 flex justify-between items-start pt-10">
                                    <div class="max-w-[80%]">
                                        <h2 class="text-5xl font-black mb-10 tracking-tight text-white leading-tight drop-shadow-[0_2px_10px_rgba(0,0,0,0.8)]" x-text="selectedEmail.subject"></h2>
                                        <div class="flex items-center gap-6">
                                            <div class="w-16 h-16 rounded-[24px] bg-gradient-to-br from-indigo-500 to-blue-700 flex items-center justify-center font-black text-white shadow-[0_10px_30px_rgba(59,130,246,0.3)] text-3xl border border-white/20" x-text="selectedEmail.sender[0].toUpperCase()"></div>
                                            <div>
                                                <p class="font-black text-blue-300 text-2xl tracking-tight leading-none mb-1.5 drop-shadow-md" x-text="selectedEmail.sender"></p>
                                                <p class="text-[10px] text-gray-400 uppercase tracking-[0.3em] font-black flex items-center gap-2">
                                                    <span class="w-3 h-3 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.8)] border border-green-200"></span> Verified Target
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="px-6 py-3 rounded-2xl glass border border-white/10 text-[10px] font-black text-gray-300 shadow-[0_10px_30px_rgba(0,0,0,0.5)] tracking-widest uppercase flex flex-col items-center gap-1">
                                        <span class="opacity-50">NODE ID</span>
                                        <span class="text-blue-400 text-lg" x-text="'#' + selectedEmail.id"></span>
                                    </div>
                                </div>
                                
                                <div class="flex-1 text-2xl leading-loose text-gray-200 glass p-14 rounded-[40px] mb-14 shadow-[0_20px_50px_rgba(0,0,0,0.5)] font-light border-white/10 border backdrop-blur-3xl relative z-10" x-text="selectedEmail.body"></div>
                                
                                <!-- ACTIONS -->
                                <div x-show="!isDone" class="flex gap-10 border-t border-white/10 pt-12 mt-auto relative z-10">
                                    <div class="flex-1 space-y-8">
                                        <h4 class="text-[10px] font-black text-gray-500 uppercase tracking-[0.4em] flex items-center gap-5">
                                            <span class="h-[1px] flex-1 bg-white/10"></span> SECURE OPERATIONAL OVERRIDE <span class="h-[1px] flex-1 bg-white/10"></span>
                                        </h4>
                                        <div class="flex gap-6">
                                            <button @click="submitTriage('reply', 'medium')" class="glow-btn glow-green flex-1 bg-gradient-to-b from-green-500 to-green-700 border border-green-400/30 p-8 rounded-[30px] font-black text-white shadow-[0_10px_30px_rgba(22,163,74,0.2)] text-xl tracking-[0.2em] uppercase">REPLY</button>
                                            <button @click="submitTriage('ignore', 'low')" class="glow-btn glow-gray flex-1 bg-gradient-to-b from-gray-700 to-gray-900 border border-gray-600/30 p-8 rounded-[30px] font-black text-white shadow-[0_10px_30px_rgba(0,0,0,0.5)] text-xl tracking-[0.2em] uppercase">IGNORE</button>
                                            <button @click="submitTriage('escalate', 'high')" class="glow-btn glow-red flex-1 bg-gradient-to-b from-red-600 to-red-800 border border-red-500/30 p-8 rounded-[30px] font-black text-white shadow-[0_10px_30px_rgba(220,38,38,0.2)] text-xl tracking-[0.2em] uppercase">ESCALATE</button>
                                        </div>
                                    </div>
                                    <div class="w-64 glass rounded-[40px] p-8 flex flex-col justify-center items-center text-center border border-white/10 backdrop-blur-3xl shadow-[0_20px_50px_rgba(0,0,0,0.3)] relative overflow-hidden group">
                                        <div class="absolute inset-0 bg-blue-500/10 translate-y-full group-hover:translate-y-0 transition-transform duration-500 rounded-[40px]"></div>
                                        <p class="text-[10px] text-blue-400 font-black uppercase tracking-[0.4em] mb-4 opacity-60 z-10">Yield Pos</p>
                                        <p class="text-7xl font-black tracking-tighter text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.4)] z-10" x-text="latestReward || '—'"></p>
                                        <div x-show="rewardWasNoisy" class="mt-4 px-4 py-1.5 bg-yellow-500/20 border border-yellow-500/50 rounded-full text-[9px] text-yellow-400 font-black animate-pulse tracking-widest z-10 shadow-[0_0_20px_rgba(234,179,8,0.3)]">⚠️ NOISE</div>
                                    </div>
                                </div>
                            </div>
                        </template>
                    </section>
                </div>
            </template>

            <!-- ANALYTICS VIEW -->
            <template x-if="currentTab === 'analytics'">
                <section class="flex-1 p-20 overflow-y-auto custom-scrollbar absolute inset-0 animate-fadeIn z-20">
                    <div class="max-w-6xl mx-auto">
                        <div class="mb-14 flex justify-between items-end">
                            <div>
                                <h2 class="text-5xl font-black text-white mb-4 tracking-tighter drop-shadow-xl">Yield Analytics</h2>
                                <p class="text-gray-400 text-lg font-medium leading-relaxed opacity-80 max-w-2xl">Real-time visualization of model performance and XP yield extraction rates across recent operations.</p>
                            </div>
                            <div class="glass px-8 py-4 rounded-3xl border border-white/10 text-center shadow-xl">
                                <p class="text-[10px] font-black tracking-widest text-gray-400 uppercase mb-1">Total Verified XP</p>
                                <p class="text-3xl font-black text-blue-400 drop-shadow-md" x-text="perf.total_score.toFixed(2)"></p>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-3 gap-10">
                            <div class="md:col-span-2 glass rounded-[40px] p-10 border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.5)]">
                                <div class="flex justify-between items-center mb-8">
                                    <h3 class="text-sm font-black text-gray-300 uppercase tracking-widest">Yield Trajectory</h3>
                                    <span class="px-4 py-1 rounded-full bg-green-500/10 border border-green-500/30 text-[10px] text-green-400 font-bold uppercase tracking-widest">LIVE SYNC</span>
                                </div>
                                <div class="h-80 w-full relative">
                                    <canvas id="yieldChart"></canvas>
                                </div>
                            </div>
                            <div class="glass rounded-[40px] p-8 border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.5)] flex flex-col">
                                <h3 class="text-sm font-black text-gray-300 uppercase tracking-widest mb-8 border-b border-white/10 pb-4">Global Network Ranks</h3>
                                <div class="flex-1 flex flex-col gap-5 justify-start">
                                    <!-- Leaderboard Mocks -->
                                    <div class="flex items-center justify-between p-4 rounded-2xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                                        <div class="flex items-center gap-4">
                                            <div class="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center font-black text-xs">#1</div>
                                            <div>
                                                <p class="font-bold text-gray-200 text-sm">GPT-4-SecOps</p>
                                                <p class="text-[10px] text-blue-400 font-black uppercase tracking-widest">Grandmaster</p>
                                            </div>
                                        </div>
                                        <p class="font-black text-white">4,204</p>
                                    </div>
                                    <div class="flex items-center justify-between p-4 rounded-2xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                                        <div class="flex items-center gap-4">
                                            <div class="w-10 h-10 rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500 flex items-center justify-center font-black text-xs">#2</div>
                                            <div>
                                                <p class="font-bold text-gray-200 text-sm">Claude-3-Triage</p>
                                                <p class="text-[10px] text-cyan-400 font-black uppercase tracking-widest">Master Triage</p>
                                            </div>
                                        </div>
                                        <p class="font-black text-white">3,142</p>
                                    </div>
                                    <div class="flex items-center justify-between p-4 rounded-2xl border border-blue-500/30 bg-blue-500/10 shadow-[0_0_20px_rgba(59,130,246,0.1)] relative overflow-hidden">
                                        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full animate-[shimmer_2s_infinite]"></div>
                                        <div class="flex items-center gap-4 relative z-10">
                                            <div class="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center font-black text-xs shadow-lg">YOU</div>
                                            <div>
                                                <p class="font-bold text-white text-sm" x-text="loginUser"></p>
                                                <p class="text-[10px] text-blue-300 font-black uppercase tracking-widest" x-text="perf.rank"></p>
                                            </div>
                                        </div>
                                        <p class="font-black text-white relative z-10" x-text="perf.total_score.toFixed(2)"></p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            </template>

            <!-- SANDBOX VIEW -->
            <template x-if="currentTab === 'sandbox'">
                <section class="flex-1 p-20 overflow-y-auto custom-scrollbar absolute inset-0 animate-fadeIn z-20">
                    <!-- existing sandbox markup with elevated styles -->
                    <div class="max-w-6xl mx-auto">
                        <div class="mb-14">
                            <h2 class="text-6xl font-black text-white mb-6 tracking-tighter drop-shadow-xl">Pro-Scanner Engine</h2>
                            <p class="text-gray-400 max-w-3xl text-xl font-medium leading-relaxed opacity-80">Analyze live suspicious records without permanent ingestion. Our stateless neural engine identifies phishing markers and provides a verified risk calibration score.</p>
                        </div>
                        <div class="space-y-12">
                            <div class="relative group">
                                <div class="absolute -inset-2 bg-gradient-to-r from-blue-600 via-indigo-500 to-cyan-500 rounded-[50px] blur-xl opacity-30 group-hover:opacity-60 transition duration-1000"></div>
                                <textarea x-model="scanText" placeholder="Paste suspicious record content for calibration..." class="relative w-full h-[32rem] bg-gray-900/80 border border-white/10 rounded-[40px] p-16 text-3xl font-light outline-none focus:ring-2 focus:ring-blue-500/50 transition-all text-gray-200 custom-scrollbar shadow-2xl backdrop-blur-xl"></textarea>
                                <button @click="runScan()" :disabled="isScanning || !scanText.trim()" 
                                        class="absolute bottom-12 right-12 px-14 py-8 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 rounded-[30px] font-black text-white shadow-[0_20px_50px_rgba(37,99,235,0.4)] hover:shadow-[0_20px_50px_rgba(37,99,235,0.6)] transition-all flex items-center gap-5 text-xl uppercase tracking-widest active:scale-95 border border-white/10">
                                    <span x-show="isScanning" class="animate-spin text-3xl">🔄</span>
                                    <span x-text="isScanning ? 'Syncing...' : 'Initiate Scan'"></span>
                                </button>
                            </div>
                            <template x-if="scanResult">
                                <div class="glass p-16 rounded-[50px] border-blue-500/30 bg-blue-500/10 animate-fadeIn shadow-[0_40px_100px_rgba(0,0,0,0.6)] ring-1 ring-blue-500/30 relative overflow-hidden">
                                    <div class="absolute -top-40 -right-40 w-96 h-96 bg-blue-500/20 blur-[100px] rounded-full point-events-none"></div>
                                    <div class="grid grid-cols-1 md:grid-cols-3 gap-16 items-center relative z-10">
                                        <div class="space-y-5">
                                            <p class="text-[10px] font-black text-blue-400 uppercase tracking-[0.4em] opacity-80">Neural Phish Probability</p>
                                            <p class="text-8xl font-black text-transparent bg-clip-text bg-gradient-to-br from-blue-300 to-white tracking-tighter drop-shadow-md" x-text="(scanResult.scam_likelihood * 100) + '%'"></p>
                                        </div>
                                        <div class="space-y-8">
                                            <p class="text-[10px] font-black text-gray-400 uppercase tracking-[0.4em]">Recommended Response</p>
                                            <div class="flex flex-col gap-4">
                                                <span :class="{'bg-red-500/20 text-red-400 border-red-500/50 shadow-[0_0_30px_rgba(239,68,68,0.2)]': scanResult.suggested_action === 'escalate', 'bg-green-500/20 text-green-400 border-green-500/50 shadow-[0_0_30px_rgba(34,197,94,0.2)]': scanResult.suggested_action === 'ignore'}" 
                                                      class="px-10 py-5 rounded-3xl border text-xl font-black uppercase tracking-[0.3em] text-center backdrop-blur-sm" x-text="scanResult.suggested_action"></span>
                                                <span class="px-10 py-4 rounded-[20px] border border-white/5 bg-gray-900/50 text-[10px] font-black text-gray-400 uppercase tracking-[0.4em] text-center" x-text="'PRIORITY: ' + scanResult.suggested_priority"></span>
                                            </div>
                                        </div>
                                        <div class="space-y-8">
                                            <p class="text-[10px] font-black text-gray-400 uppercase tracking-[0.4em]">Identified Markers</p>
                                            <div class="grid grid-cols-2 gap-4">
                                                <template x-for="pattern in scanResult.detected_patterns">
                                                    <span class="px-5 py-4 bg-gray-900/60 rounded-2xl border border-white/5 text-[10px] font-black text-blue-300 uppercase tracking-widest text-center shadow-inner" x-text="pattern"></span>
                                                </template>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="mt-16 pt-10 border-t border-white/10 flex items-center justify-between relative z-10">
                                        <div class="flex items-center gap-4 text-[11px] font-black text-gray-400 uppercase tracking-widest">
                                            <span class="text-blue-500 text-xl">🛡️</span> Neural Privacy Isolation Active
                                        </div>
                                        <div class="text-[10px] font-black text-blue-500/50 uppercase tracking-widest italic">Node 104-B Verified</div>
                                    </div>
                                </div>
                            </template>
                        </div>
                    </div>
                </section>
            </template>
        </div>
    </main>

    <script>
        function triageApp() {
            return {
                isLoggedIn: false,
                currentTab: 'inbox',
                loginUser: 'admin',
                loginPass: '',
                selectedTask: 'easy',
                inbox: [],
                selectedEmail: null,
                latestReward: null,
                rewardWasNoisy: false,
                isDone: false,
                scanText: '',
                isScanning: false,
                scanResult: null,
                perf: {total_score: 0.0, current_streak: 0, rank: "Novice Analyst", progress_percent: 0},
                chartInstance: null,
                historyYields: [],
                
                showResult: false,
                resultScore: 0,
                resultReason: '',
                resultExpected: '',
                resultIsSuccess: true,
                
                checkAuth() {
                    if(localStorage.getItem('mfde_auth') === 'true') {
                        this.isLoggedIn = true;
                        this.loadInbox();
                    }
                },
                async login() {
                    if(this.loginUser === 'admin' && this.loginPass === 'mfde2024') {
                        this.isLoggedIn = true;
                        localStorage.setItem('mfde_auth', 'true');
                        await this.loadInbox();
                        await this.updatePerf();
                    } else {
                        alert("UNAUTHORIZED ACCESS: Authentication Failure");
                    }
                },
                async updatePerf() {
                    const res = await fetch('/api/performance');
                    this.perf = await res.json();
                },
                async loadInbox() {
                    try {
                        const res = await fetch(`/api/inbox/${this.selectedTask}`);
                        this.inbox = await res.json();
                        this.selectedEmail = null;
                        this.latestReward = null;
                        this.historyYields = [];
                        await fetch('/reset', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                task: this.selectedTask,
                                mode: 'infinite'
                            })
                        });
                        await this.updatePerf();
                        this.updateChart();
                    } catch (e) {}
                },
                openEmail(email) {
                    this.selectedEmail = email;
                    this.latestReward = null;
                    this.rewardWasNoisy = false;
                },
                openAnalytics() {
                    this.currentTab = 'analytics';
                    setTimeout(() => { this.initChart(); }, 100);
                },
                initChart() {
                    const ctx = document.getElementById('yieldChart');
                    if(!ctx) return;
                    if(this.chartInstance) this.chartInstance.destroy();
                    
                    Chart.defaults.color = '#9ca3af';
                    Chart.defaults.font.family = 'Inter';
                    
                    this.chartInstance = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: this.historyYields.map((_, i) => 'Op ' + (i+1)),
                            datasets: [{
                                label: 'XP Yield',
                                data: this.historyYields,
                                borderColor: '#3b82f6',
                                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                borderWidth: 3,
                                fill: true,
                                tension: 0.4,
                                pointBackgroundColor: '#8b5cf6',
                                pointBorderColor: '#fff',
                                pointBorderWidth: 2,
                                pointRadius: 5,
                                pointHoverRadius: 7
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: false } },
                            scales: {
                                y: { grid: { color: 'rgba(255,255,255,0.05)' }, beginAtZero: true },
                                x: { grid: { display: false } }
                            }
                        }
                    });
                },
                updateChart() {
                    if(this.chartInstance) {
                        this.chartInstance.data.labels = this.historyYields.map((_, i) => 'Op ' + (i+1));
                        this.chartInstance.data.datasets[0].data = this.historyYields;
                        this.chartInstance.update();
                    }
                },
                async submitTriage(decision, priority) {
                    const res = await fetch('/step', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            decision, 
                            priority, 
                            email_id: this.selectedEmail.id
                        })
                    });
                    const data = await res.json();
                    this.latestReward = data.reward.toFixed(2);
                    this.rewardWasNoisy = (Math.abs(data.reward - data.info.true_reward) > 0.01);
                    this.isDone = data.done;
                    
                    this.historyYields.push(data.reward);
                    this.updateChart();
                    
                    // TRIGGER RESULT OVERLAY
                    this.resultScore = data.reward;
                    this.resultReason = data.info.reason;
                    this.resultExpected = "Expected: " + data.info.correct_decision.toUpperCase() + " / " + data.info.correct_priority.toUpperCase();
                    this.resultIsSuccess = (data.reward > 0);
                    this.showResult = true;
                    
                    await this.updatePerf();
                    
                    const currentIndex = this.inbox.findIndex(e => e.id === this.selectedEmail.id);
                    
                    setTimeout(() => {
                        this.showResult = false;
                        if(currentIndex < this.inbox.length - 1) {
                            if(!this.isDone) this.selectedEmail = this.inbox[currentIndex + 1];
                        }
                    }, 4000);
                },
                async runScan() {
                    this.isScanning = true;
                    this.scanResult = null;
                    const res = await fetch('/api/scan', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({text: this.scanText})
                    });
                    this.scanResult = await res.json();
                    this.isScanning = false;
                }
            }
        }
    </script>

    <!-- RESULT OVERLAY MODAL -->
    <div x-show="showResult" x-transition.opacity class="fixed inset-0 z-[100] flex items-center justify-center bg-[#0b0f19]/90 backdrop-blur-xl">
        <div class="glass p-16 rounded-[60px] max-w-2xl w-full text-center animate-fadeIn border-t-[6px] shadow-[0_30px_100px_rgba(0,0,0,0.8)]" :class="resultIsSuccess ? 'border-green-500 shadow-green-500/10' : 'border-red-500 shadow-red-500/10'">
            <div class="mb-10 relative">
                <template x-if="resultIsSuccess">
                    <div>
                        <div class="absolute inset-0 bg-green-500/20 blur-3xl rounded-full"></div>
                        <div class="relative w-32 h-32 bg-green-500/10 border border-green-500/30 text-green-400 rounded-full flex items-center justify-center text-6xl mx-auto shadow-[inset_0_0_30px_rgba(34,197,94,0.2)]">✓</div>
                    </div>
                </template>
                <template x-if="!resultIsSuccess">
                    <div>
                        <div class="absolute inset-0 bg-red-500/20 blur-3xl rounded-full"></div>
                        <div class="relative w-32 h-32 bg-red-500/10 border border-red-500/30 text-red-500 rounded-full flex items-center justify-center text-6xl mx-auto shadow-[inset_0_0_30px_rgba(239,68,68,0.2)]">!</div>
                    </div>
                </template>
            </div>
            <h3 class="text-5xl font-black text-white mb-6 tracking-tight drop-shadow-md" x-text="resultIsSuccess ? 'Decision Correct' : 'Threat Missed!'"></h3>
            <div class="inline-block px-10 py-4 bg-gray-900/60 rounded-[30px] mb-10 border border-white/5 shadow-inner">
                <span class="text-5xl font-black block mb-3 drop-shadow-[0_0_15px_currentColor]" :class="resultIsSuccess ? 'text-green-400' : 'text-red-500'" x-text="'+' + resultScore + ' XP'"></span>
                <span class="text-[10px] font-black text-blue-400 uppercase tracking-[0.4em]" x-text="resultExpected"></span>
            </div>
            <p class="text-2xl text-gray-300 font-medium leading-relaxed italic px-8" x-text="resultReason"></p>
            <div class="mt-12 pt-10 border-t border-white/5">
                <p class="text-[11px] font-black text-blue-500 uppercase tracking-[0.6em] animate-pulse">Syncing Telemetry...</p>
            </div>
        </div>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)
