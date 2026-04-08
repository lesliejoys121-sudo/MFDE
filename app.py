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
        "total_score": round(score, 1),
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
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #0b0f19; color: #e2e8f0; margin: 0; }
        .glass { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .inbox-item:hover { background: rgba(255, 255, 255, 0.05); }
        .active-nav { border-left: 4px solid #3b82f6; background: rgba(59, 130, 246, 0.1); }
        [x-cloak] { display: none !important; }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #1f2937; border-radius: 10px; }
        .progress-fill { transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
        .animate-fadeIn { animation: fadeIn 0.5s ease-out forwards; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body x-data="triageApp()" x-init="checkAuth()" x-cloak class="h-screen overflow-hidden flex flex-col">
    <!-- LOGIN OVERLAY -->
    <div x-show="!isLoggedIn" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-95">
        <div class="glass p-10 rounded-2xl w-full max-w-md text-center shadow-2xl">
            <h1 class="text-4xl font-extrabold mb-2 bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">MFDE ENGINE</h1>
            <p class="text-gray-500 text-sm mb-8 font-medium italic">Misleading Feedback Decision Environment</p>
            <input type="text" x-model="loginUser" placeholder="Username" class="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 mb-4 focus:ring-2 focus:ring-blue-500 outline-none text-white transition-all">
            <input type="password" x-model="loginPass" @keyup.enter="login()" placeholder="Password" class="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 mb-6 focus:ring-2 focus:ring-blue-500 outline-none text-white transition-all">
            <button @click="login()" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-black py-4 rounded-lg transition-all shadow-lg shadow-blue-500/20 active:scale-95">SIGN IN</button>
            <p class="text-gray-500 text-[10px] mt-6 tracking-widest uppercase">Credentials: admin / mfde2024</p>
        </div>
    </div>

    <!-- HEADER -->
    <header class="h-20 flex items-center justify-between px-8 glass border-b border-gray-800 shrink-0">
        <div class="flex items-center gap-10">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/30 text-xl">M</div>
                <h2 class="text-2xl font-black tracking-tighter">Triage<span class="text-blue-400">Center</span></h2>
            </div>
            <!-- RANK METER -->
            <div class="hidden lg:flex items-center gap-4 pl-8 border-l border-gray-800">
                <div class="text-right">
                    <p class="text-[9px] font-black text-gray-500 uppercase tracking-[0.2em] leading-none mb-1">Expertise Rank</p>
                    <p class="text-xs font-black text-blue-400 uppercase tracking-tight" x-text="perf.rank"></p>
                </div>
                <div class="w-48 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-blue-600 to-cyan-400 progress-fill shadow-[0_0_8px_rgba(59,130,246,0.5)]" :style="'width: ' + perf.progress_percent + '%'"></div>
                </div>
            </div>
        </div>

        <div class="flex items-center gap-8">
            <!-- LIVE SCORE & STREAK -->
            <div class="flex items-center gap-4 bg-gray-900/50 px-5 py-2.5 rounded-2xl border border-gray-800 shadow-xl">
                <div class="text-center min-w-[60px]">
                    <p class="text-[8px] font-black text-gray-500 uppercase tracking-widest opacity-60">Total Score</p>
                    <p class="text-xl font-black text-white leading-tight" x-text="perf.total_score"></p>
                </div>
                <div x-show="perf.current_streak > 1" class="text-center border-l border-gray-800 pl-4 min-w-[60px] animate-bounce">
                    <p class="text-[8px] font-black text-orange-500 uppercase tracking-widest leading-none mb-0.5">Correct Streak</p>
                    <p class="text-xl font-black text-orange-400 leading-tight" x-text="'🔥 ' + perf.current_streak"></p>
                </div>
            </div>

            <select x-show="currentTab === 'inbox'" x-model="selectedTask" @change="loadInbox()" class="bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-xs font-bold outline-none text-white cursor-pointer hover:border-blue-500 transition-colors shadow-lg appearance-none pr-10 relative">
                <option value="easy">Easy (1.0x)</option>
                <option value="medium">Medium (1.5x)</option>
                <option value="hard">Hard (2.0x)</option>
            </select>
        </div>
    </header>

    <main class="flex-1 flex overflow-hidden">
        <!-- SIDEBAR -->
        <aside class="w-64 glass border-r border-gray-800 p-6 space-y-3 hidden md:block shrink-0">
            <button @click="currentTab = 'inbox'; loadInbox()" :class="{'active-nav': currentTab === 'inbox'}" class="w-full text-left p-4 rounded-xl transition-all flex items-center gap-3 hover:bg-gray-800/30">
                <span class="text-xl">📥</span> <span class="font-black text-sm uppercase tracking-wider">Triage Inbox</span>
            </button>
            <button @click="currentTab = 'sandbox'" :class="{'active-nav': currentTab === 'sandbox'}" class="w-full text-left p-4 rounded-xl transition-all flex items-center gap-3 hover:bg-gray-800/30">
                <span class="text-xl">🛡️</span> <span class="font-black text-sm uppercase tracking-wider">Pro-Scanner</span>
            </button>
            <div class="pt-8 pb-4 px-4">
                <p class="text-[9px] font-black text-gray-600 uppercase tracking-[0.3em]">System Tools</p>
            </div>
            <button class="w-full text-left p-4 rounded-xl hover:bg-gray-800 transition-all opacity-30 flex items-center gap-3 cursor-not-allowed">
                <span class="text-xl">📊</span> <span class="font-black text-sm uppercase tracking-wider text-gray-500">Analytics</span>
            </button>
            <button class="w-full text-left p-4 rounded-xl hover:bg-gray-800 transition-all opacity-30 flex items-center gap-3 cursor-not-allowed">
                <span class="text-xl">⚙️</span> <span class="font-black text-sm uppercase tracking-wider text-gray-500">Node Sync</span>
            </button>
            
            <div class="mt-auto pt-20">
                <div class="p-4 rounded-2xl bg-blue-600/5 border border-blue-500/10 text-center">
                    <p class="text-[8px] font-black text-blue-500 uppercase mb-1">System Status</p>
                    <p class="text-[10px] font-bold text-gray-400">Node Active: 104-B</p>
                    <div class="mt-2 w-full h-1 bg-gray-800 rounded-full overflow-hidden">
                        <div class="h-full bg-blue-500 animate-pulse w-2/3"></div>
                    </div>
                </div>
            </div>
        </aside>

        <!-- VIEW CONTAINER -->
        <div class="flex-1 flex overflow-hidden">
            <!-- INBOX VIEW -->
            <template x-if="currentTab === 'inbox'">
                <div class="flex-1 flex overflow-hidden">
                    <!-- MESSAGE LIST -->
                    <section class="w-[420px] border-r border-gray-800 flex flex-col bg-gray-900/40 shrink-0">
                        <div class="p-6 border-b border-gray-800 flex justify-between items-center bg-gray-900/60 shadow-lg z-10">
                            <h3 class="font-black text-[10px] uppercase tracking-[0.3em] text-gray-500">Operational Queue</h3>
                            <span class="text-[10px] font-black px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 shadow-inner" x-text="inbox.length + ' targets'"></span>
                        </div>
                        <div class="flex-1 overflow-y-auto custom-scrollbar">
                            <template x-for="email in inbox" :key="email.id">
                                <div @click="openEmail(email)" 
                                    :class="{'bg-blue-600/10 border-l-4 border-blue-500 shadow-inner': selectedEmail && selectedEmail.id === email.id, 'hover:bg-gray-800/40': !selectedEmail || selectedEmail.id !== email.id}" 
                                    class="p-6 border-b border-gray-800 cursor-pointer transition-all duration-300 transform active:scale-95">
                                    <div class="flex justify-between mb-2">
                                        <span class="text-[10px] font-black text-blue-400 uppercase tracking-widest" x-text="email.sender"></span>
                                        <div class="flex items-center gap-2">
                                            <div class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></div>
                                            <span class="text-[10px] text-gray-600 font-bold uppercase tracking-tighter">PENDING</span>
                                        </div>
                                    </div>
                                    <h4 class="text-base font-black text-gray-200 mb-1 leading-tight" x-text="email.subject"></h4>
                                    <p class="text-xs text-gray-500 line-clamp-1 font-medium italic opacity-70" x-text="email.body"></p>
                                </div>
                            </template>
                        </div>
                    </section>

                    <!-- DETAIL VIEW -->
                    <section class="flex-1 overflow-hidden flex flex-col bg-[#0b1018]">
                        <template x-if="!selectedEmail">
                            <div class="h-full flex items-center justify-center text-gray-700 flex-col opacity-20">
                                <span class="text-[10rem] mb-10 animate-pulse">📡</span>
                                <p class="text-3xl font-black tracking-[0.6em] uppercase text-center ml-[0.6em]">Awaiting Data Lock</p>
                            </div>
                        </template>
                        <template x-if="selectedEmail">
                            <div class="h-full flex flex-col p-14 custom-scrollbar overflow-y-auto animate-fadeIn">
                                <div class="mb-14 flex justify-between items-start">
                                    <div class="max-w-4xl">
                                        <h2 class="text-6xl font-black mb-8 tracking-tighter text-white leading-none shadow-text" x-text="selectedEmail.subject"></h2>
                                        <div class="flex items-center gap-6">
                                            <div class="w-16 h-16 rounded-[20px] bg-gradient-to-br from-blue-600 to-indigo-800 flex items-center justify-center font-black text-white shadow-[0_10px_30px_rgba(37,99,235,0.4)] text-3xl" x-text="selectedEmail.sender[0].toUpperCase()"></div>
                                            <div>
                                                <p class="font-black text-blue-400 text-2xl tracking-tight leading-none mb-1" x-text="selectedEmail.sender"></p>
                                                <p class="text-[10px] text-gray-600 uppercase tracking-[0.2em] font-black flex items-center gap-2">
                                                    <span class="w-2.5 h-2.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"></span> Verified Analysis Target
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="px-6 py-3 rounded-2xl bg-gray-900 border border-gray-800 text-[10px] font-black text-gray-500 shadow-2xl tracking-widest uppercase">ID: <span class="text-blue-500" x-text="selectedEmail.id"></span></div>
                                </div>
                                
                                <div class="flex-1 text-2xl leading-relaxed text-gray-300 glass p-14 rounded-[50px] mb-14 shadow-2xl font-light border-white/5 border backdrop-blur-2xl" x-text="selectedEmail.body"></div>
                                
                                <!-- ACTIONS -->
                                <div x-show="!isDone" class="flex gap-12 border-t border-gray-800/50 pt-14 mt-auto">
                                    <div class="flex-1 space-y-10">
                                        <h4 class="text-[10px] font-black text-gray-600 uppercase tracking-[0.6em] flex items-center gap-5">
                                            <span class="h-[1px] flex-1 bg-gray-800"></span> SELECT OPERATIONAL OVERRIDE <span class="h-[1px] flex-1 bg-gray-800"></span>
                                        </h4>
                                        <div class="flex gap-8">
                                            <button @click="submitTriage('reply', 'medium')" class="flex-1 bg-green-600/90 hover:bg-green-500 p-10 rounded-[40px] font-black text-white transition-all transform hover:scale-[1.03] active:scale-95 shadow-[0_20px_50px_rgba(22,163,74,0.3)] border border-green-400/20 text-xl tracking-[0.2em] uppercase">REPLY</button>
                                            <button @click="submitTriage('ignore', 'low')" class="flex-1 bg-gray-800 hover:bg-gray-700 p-10 rounded-[40px] font-black text-white transition-all transform hover:scale-[1.03] active:scale-95 shadow-2xl border border-gray-700 text-xl tracking-[0.2em] uppercase">IGNORE</button>
                                            <button @click="submitTriage('escalate', 'high')" class="flex-1 bg-red-600/90 hover:bg-red-500 p-10 rounded-[40px] font-black text-white transition-all transform hover:scale-[1.03] active:scale-95 shadow-[0_20px_50px_rgba(220,38,38,0.3)] border border-red-400/20 text-xl tracking-[0.2em] uppercase">ESCALATE</button>
                                        </div>
                                    </div>
                                    <div class="w-72 bg-blue-600/5 rounded-[50px] p-10 flex flex-col justify-center text-center border border-blue-500/10 backdrop-blur-3xl group shadow-2xl ring-1 ring-white/5">
                                        <p class="text-[10px] text-blue-500 font-black uppercase tracking-[0.3em] mb-4 opacity-40 group-hover:opacity-100 transition-opacity">Reward Yield</p>
                                        <p class="text-7xl font-black tracking-tighter text-white drop-shadow-xl" x-text="latestReward || '0.01'"></p>
                                        <div x-show="rewardWasNoisy" class="mt-6 px-4 py-1.5 bg-yellow-500/20 border border-yellow-500/40 rounded-full text-[10px] text-yellow-500 font-black animate-pulse tracking-widest">⚠️ NOISE</div>
                                    </div>
                                </div>
                            </div>
                        </template>
                    </section>
                </div>
            </template>

            <!-- SANDBOX VIEW -->
            <template x-if="currentTab === 'sandbox'">
                <section class="flex-1 bg-[#0b1018] p-20 overflow-y-auto custom-scrollbar">
                    <div class="max-w-6xl mx-auto animate-fadeIn">
                        <div class="mb-14">
                            <h2 class="text-6xl font-black text-white mb-6 tracking-tighter shadow-text">Pro-Scanner Engine</h2>
                            <p class="text-gray-500 max-w-3xl text-xl font-medium leading-relaxed opacity-60">Analyze live suspicious records without permanent ingestion. Our stateless neural engine identifies phishing markers and provides a verified risk calibration score.</p>
                        </div>
                        <div class="space-y-12">
                            <div class="relative group">
                                <div class="absolute -inset-1 bg-gradient-to-r from-blue-600 to-cyan-500 rounded-[50px] blur opacity-20 group-hover:opacity-40 transition duration-1000 group-hover:duration-200"></div>
                                <textarea x-model="scanText" placeholder="Paste suspicious record content for calibration..." class="relative w-full h-[32rem] bg-gray-900 border border-gray-800 rounded-[50px] p-16 text-3xl font-light outline-none focus:ring-4 focus:ring-blue-500/20 transition-all text-gray-300 custom-scrollbar shadow-3xl"></textarea>
                                <button @click="runScan()" :disabled="isScanning || !scanText.trim()" 
                                        class="absolute bottom-12 right-12 px-14 py-8 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-[30px] font-black text-white shadow-[0_20px_60px_rgba(37,99,235,0.5)] transition-all flex items-center gap-5 text-xl uppercase tracking-widest active:scale-95">
                                    <span x-show="isScanning" class="animate-spin text-3xl">🔄</span>
                                    <span x-text="isScanning ? 'Syncing...' : 'Initiate Neural Scan'"></span>
                                </button>
                            </div>
                            <template x-if="scanResult">
                                <div class="glass p-16 rounded-[60px] border-blue-500/20 bg-blue-500/5 animate-fadeIn shadow-[0_40px_100px_rgba(0,0,0,0.5)] ring-1 ring-blue-500/20">
                                    <div class="grid grid-cols-1 md:grid-cols-3 gap-16 items-center">
                                        <div class="space-y-4">
                                            <p class="text-[10px] font-black text-blue-500 uppercase tracking-[0.4em] opacity-60">Neural Phish Probability</p>
                                            <p class="text-8xl font-black text-white tracking-tighter" x-text="(scanResult.scam_likelihood * 100) + '%'"></p>
                                        </div>
                                        <div class="space-y-8">
                                            <p class="text-[10px] font-black text-gray-600 uppercase tracking-[0.4em] opacity-60">System Recommended Response</p>
                                            <div class="flex flex-col gap-4">
                                                <span :class="{'bg-red-500/20 text-red-500 border-red-500/50 shadow-[0_0_20px_rgba(239,68,68,0.2)]': scanResult.suggested_action === 'escalate', 'bg-green-500/20 text-green-500 border-green-400/50 shadow-[0_0_20px_rgba(34,197,94,0.2)]': scanResult.suggested_action === 'ignore'}" 
                                                      class="px-10 py-5 rounded-[24px] border text-xl font-black uppercase tracking-[0.2em] text-center" x-text="scanResult.suggested_action"></span>
                                                <span class="px-10 py-3 rounded-[20px] border border-gray-800 bg-gray-900/50 text-[10px] font-black text-gray-500 uppercase tracking-[0.3em] text-center" x-text="'PRIORITY: ' + scanResult.suggested_priority"></span>
                                            </div>
                                        </div>
                                        <div class="space-y-8">
                                            <p class="text-[10px] font-black text-gray-600 uppercase tracking-[0.4em] opacity-60">Identified Markers</p>
                                            <div class="grid grid-cols-2 gap-3">
                                                <template x-for="pattern in scanResult.detected_patterns">
                                                    <span class="px-5 py-3 bg-gray-900 rounded-2xl border border-gray-800 text-[10px] font-black text-gray-400 uppercase tracking-wider text-center" x-text="pattern"></span>
                                                </template>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="mt-16 pt-10 border-t border-white/5 flex items-center justify-between">
                                        <div class="flex items-center gap-3 text-[10px] font-black text-gray-600 uppercase tracking-widest">
                                            <span class="text-blue-500 text-lg">🛡️</span> Neural Privacy Isolation Active
                                        </div>
                                        <div class="text-[10px] font-black text-blue-500/40 uppercase tracking-widest italic">Confidential Session Node 104-B</div>
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
                loginUser: '',
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
                
                // NEW RESULT OVERLAY STATE
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
                        await fetch('/reset', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                task: this.selectedTask,
                                mode: 'infinite'
                            })
                        });
                        await this.updatePerf();
                    } catch (e) {}
                },
                openEmail(email) {
                    this.selectedEmail = email;
                    this.latestReward = null;
                    this.rewardWasNoisy = false;
                },
                async submitTriage(decision, priority) {
                    const res = await fetch('/step', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            decision, 
                            priority, 
                            email_id: this.selectedEmail.id // SYNC LOCK
                        })
                    });
                    const data = await res.json();
                    this.latestReward = data.reward.toFixed(1);
                    this.rewardWasNoisy = (Math.abs(data.reward - data.info.true_reward) > 0.01);
                    this.isDone = data.done;
                    
                    // TRIGGER RESULT OVERLAY
                    this.resultScore = data.reward;
                    this.resultReason = data.info.reason;
                    this.resultExpected = "Expected: " + data.info.correct_decision.toUpperCase() + " / " + data.info.correct_priority.toUpperCase();
                    this.resultIsSuccess = (data.reward > 0);
                    this.showResult = true;
                    
                    await this.updatePerf();
                    
                    const currentIndex = this.inbox.findIndex(e => e.id === this.selectedEmail.id);
                    
                    // Wait for user to read result, then close and shift
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

    <!-- NEW: RESULT OVERLAY MODAL -->
    <div x-show="showResult" x-transition.opacity class="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md">
        <div class="glass p-12 rounded-[50px] max-w-2xl w-full text-center animate-fadeIn border-t-4" :class="resultIsSuccess ? 'border-green-500' : 'border-red-500'">
            <div class="mb-8">
                <template x-if="resultIsSuccess">
                    <div class="w-24 h-24 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center text-5xl mx-auto shadow-[0_0_40px_rgba(34,197,94,0.3)]">✓</div>
                </template>
                <template x-if="!resultIsSuccess">
                    <div class="w-24 h-24 bg-red-500/20 text-red-500 rounded-full flex items-center justify-center text-5xl mx-auto shadow-[0_0_40px_rgba(239,68,68,0.3)]">!</div>
                </template>
            </div>
            <h3 class="text-4xl font-black text-white mb-4" x-text="resultIsSuccess ? 'Decision Correct' : 'Threat Missed!'"></h3>
            <div class="inline-block px-8 py-3 bg-gray-900/50 rounded-3xl mb-8 border border-white/5">
                <span class="text-4xl font-black block mb-2" :class="resultIsSuccess ? 'text-green-400' : 'text-red-400'" x-text="'+' + resultScore + ' XP'"></span>
                <span class="text-[10px] font-black text-blue-500 uppercase tracking-[0.3em]" x-text="resultExpected"></span>
            </div>
            <p class="text-2xl text-gray-400 font-medium leading-relaxed italic px-10" x-text="resultReason"></p>
            <div class="mt-10">
                <p class="text-[10px] font-black text-gray-600 uppercase tracking-[0.5em] animate-pulse">Analysis Synchronizing...</p>
            </div>
        </div>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)
