from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json
import os
import asyncio
import time
import psutil
import subprocess
import sys
from typing import List, Dict, Any

# --- Calyx Logic Imports ---
from peer_database import PeerDatabase
from efficiency_monitor import EfficiencyMonitor
from seed_generator import DigitalSeed
from governance_dao import SynapseDAO, Proposal
from reward_engine import RewardEngine
from tools.calyx_logger import CalyxLogger
from synapses.sentiment_alpha import SentimentAlpha
from synapse_registry import synapseRegistry
from shard_manager import ShardManager

from config import SynapseConfig

conf = SynapseConfig()

app = FastAPI(title="Calyx Hub", version="1.3.4")
db = PeerDatabase(db_path=conf.get("paths", "peer_db"))
monitor = EfficiencyMonitor()
dao = SynapseDAO(db)
rewards = RewardEngine(epoch_emission=500.0) # 500 $SYN per epoch
# Use a relative path from the config if possible, or handle via env
logger = CalyxLogger(log_path=os.getenv("CALYX_LOG_PATH", "../../logs/node_activity.jsonl"))
registry_manager = synapseRegistry(storage_dir=conf.get("paths", "synapses_dir"))

# Task #10: Shard & Mesh State
shard_mgr = ShardManager("HUB_NODE", discovery_dir="mesh_discovery", config_path="NONE")

# Local state for running synapses (Task #9)
running_synapses: List[Dict[str, Any]] = []

# --- Phase 3: Neural Engines ---
sentiment_engine = SentimentAlpha()
inference_queue = asyncio.Queue()

class CommandRequest(BaseModel):
    text: str
    synapse_id: str = "sentiment_alpha"
    peer_id: str = "LOCAL_OPERATOR"

class InstallRequest(BaseModel):
    synapse_id: str
    name: str

class VoteRequest(BaseModel):
    proposal_id: str
    peer_id: str
    vote: bool

class ProposalRequest(BaseModel):
    proposer_id: str
    description: str
    synapse_id: str = "skill_0"
    weights_hash: str = "sha256-default"

class GPUVitals(BaseModel):
    temp: float
    vram_used: float
    vram_total: float
    load: int
    psk: str = ""

class MobileVitals(BaseModel):
    device_id: str = "Pixel 8"
    battery: int
    signal: int
    temp: float = 0.0
    psk: str = ""

# Task #25: Mailroom API
class MailLetter(BaseModel):
    sender: str
    timestamp: float
    body: str

# Task #28: Remote Mesh Logs
class RemoteLog(BaseModel):
    node_id: str
    event: str
    data: Dict[str, Any]
    t: str

mailboxes: Dict[str, List[MailLetter]] = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try: await connection.send_text(message)
            except: pass

manager = ConnectionManager()

async def log_streamer():
    """ Watches the JSONL log file and broadcasts to WS. """
    # Use environment variable for log path, with a safe fallback
    log_path = os.getenv("CALYX_LOG_PATH", os.path.join("..", "..", "logs", "node_activity.jsonl"))
    if not os.path.exists(log_path):
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        open(log_path, 'a').close()

    file_size = os.path.getsize(log_path)
    while True:
        try:
            current_size = os.path.getsize(log_path)
            if current_size > file_size:
                with open(log_path, 'r') as f:
                    f.seek(file_size)
                    lines = f.readlines()
                    for line in lines:
                        if line.strip():
                            await manager.broadcast(json.dumps({
                                "type": "LOG",
                                "payload": json.loads(line)
                            }))
                file_size = current_size
        except Exception as e:
            # print(f"[LOG_STREAMER] Error: {e}") # Silent error to avoid spam
            pass
        await asyncio.sleep(1)

async def sync_registry():
    """ Fetches the latest synapse registry from a remote source. """
    # Use environment variable for registry URL
    REMOTE_URL = os.getenv("CALYX_REGISTRY_URL", "https://raw.githubusercontent.com/<ORG_NAME>/<REPO_NAME>/master/Calyx/Core/packages/registry.json")
    print(f"[HUB] Syncing synapse registry from {REMOTE_URL}...")
    await asyncio.sleep(1) 
    print("[HUB] Registry synced successfully.")

# --- Phase 3: Worker Queue & Inference ---
async def neural_worker():
    """
    Background worker that pulls tasks from the queue and runs 1-bit inference on the 1080 Ti.
    """
    print("Neural Worker: Online and waiting for spikes...")
    while True:
        task = await inference_queue.get()
        peer_id = task.get("peer_id", "UNKNOWN")
        text = task.get("text", "")
        synapse_id = task.get("synapse_id", "sentiment_alpha")
        
        # Run 1-bit Inference
        result = sentiment_engine.infer(text)
        
        # Register Work & Rewards
        rewards.register_work(peer_id, spikes=result['spikes'])
        
        # Log to activity stream
        logger.log("NEURAL_INFERENCE", {
            "peer": peer_id,
            "sentiment": result['sentiment'],
            "conf": result['confidence'],
            "spikes": result['spikes']
        })
        
        # Prepare broadcast payload matching the UI expectation
        ui_payload = {
            "synapse_id": synapse_id,
            "input": text,
            "output": f"{result['sentiment']} (Conf: {result['confidence']}, Spikes: {result['spikes']})"
        }
        
        # Broadcast result to WebSocket
        await manager.broadcast(json.dumps({
            "type": "INFERENCE_RESULT",
            "payload": ui_payload
        }))
        
        # Update rewards UI
        payouts = rewards.calculate_payouts()
        local_payout = payouts.get(peer_id, 0.0)
        await manager.broadcast(json.dumps({
            "type": "REWARDS_UPDATE", 
            "payload": {"peer_id": peer_id, "total": local_payout}
        }))
        
        inference_queue.task_done()

@app.on_event("startup")
async def startup_event():
    # Load config in an async-friendly way (Task #10)
    shard_mgr.load_config("shard_config.json")
    
    asyncio.create_task(log_streamer())
    asyncio.create_task(sync_registry())
    asyncio.create_task(neural_worker())
    asyncio.create_task(shard_mgr.poll_mesh_files()) # Task #10: Monitor Mesh
    logger.log("HUB_BOOT", {"version": "1.3.4", "status": "mission-ready"})

@app.get("/api/mesh/nodes")
async def get_mesh_nodes():
    """ Returns nodes and links for D3.js visualization. """
    # Start with self (Hub)
    nodes = [{"id": shard_mgr.node_id, "group": 1, "label": "HUB (YOU)", "is_ready": True}]
    links = []
    
    # Add discovered nodes
    for node_id, shards in shard_mgr.mesh_shards.items():
        # A node is 'ready' if all its shards are ready
        is_ready = all(s.is_ready for s in shards) if shards else False
        nodes.append({"id": node_id, "group": 2, "label": node_id, "is_ready": is_ready})
        # Link based on sequential layer flow or just peer relationship
        links.append({"source": shard_mgr.node_id, "target": node_id, "value": 1})
        
    return {"nodes": nodes, "links": links}

# Task #25: Mailroom Endpoints
@app.post("/api/mailroom/send")
async def send_mail(letter: MailLetter):
    """ Receives a letter and stores it in the recipient's mailbox (broadcast for now). """
    # For now, we store letters globally or by a fixed ID if needed.
    # The client checks by node_id, so let's store it for everyone or a specific target.
    # Since mailroom.py sends without a target, let's assume it's for the HUB or general broadcast.
    target = "LAPTOP_RELAY" # Default for this sprint
    if target not in mailboxes: mailboxes[target] = []
    mailboxes[target].append(letter)
    logger.log("MAIL_RECEIVED", {"from": letter.sender, "body": letter.body[:20]})
    return {"status": "OK"}

@app.get("/api/mailroom/inbox/{node_id}")
async def get_inbox(node_id: str):
    """ Returns all letters for a specific node. """
    return mailboxes.get(node_id, [])

@app.get("/api/marketplace/details/{synapse_id}")
async def get_synapse_details(synapse_id: str):
    """ Returns full metadata for a specific synapse. """
    reg_path = os.path.join("packages", "registry.json")
    if os.path.exists(reg_path):
        with open(reg_path, "r") as f:
            registry = json.load(f)
            for s in registry.get("synapses", []):
                if s["id"] == synapse_id:
                    return s
    return {"error": "Not found"}

@app.post("/api/mesh/log")
async def receive_remote_log(log: RemoteLog):
    """ Receives a log from a mesh node and broadcasts to UI. """
    text = log.data.get('text', '')
    safe_text = text.encode('ascii', 'backslashreplace').decode('ascii')
    print(f"[REMOTE_LOG] From {log.node_id}: {safe_text}")
    logger.log(f"REMOTE_LOG_{log.node_id}", log.data)
    await manager.broadcast(json.dumps({
        "type": "LOG",
        "payload": {
            "event": f"NODE_{log.node_id}",
            "data": log.data
        }
    }))
    return {"status": "OK"}

@app.get("/", response_class=HTMLResponse)
async def read_hub(request: Request):
    peers = list(db.peers.values())
    reg_path = os.path.join("packages", "registry.json")
    registry = {"synapses": []}
    if os.path.exists(reg_path):
        with open(reg_path, "r") as f:
            registry = json.load(f)

    peer_rows = ""
    for p in peers:
        peer_rows += f"""
        <div onclick="openPeerModal('{p.peer_id}', {p.reputation:.2f}, {p.tokens_earned:.4f})" 
             class="bg-bark p-4 rounded-xl border border-chlorophyll/20 mb-4 peer-card cursor-pointer hover:border-chlorophyll/60 transition-all">
            <div class="flex justify-between items-center">
                <span class="text-mist font-bold">{p.peer_id[:12]}...</span>
                <span class="text-gold">Rep: {p.reputation:.2f}</span>
            </div>
        </div>
        """

    synapse_cards = ""
    for s in registry.get("synapses", []):
        is_running = any(rs['synapse_id'] == s['id'] for rs in running_synapses)
        btn_text = "RUNNING" if is_running else "INSTALL"
        btn_class = "bg-chlorophyll/40 text-mist" if is_running else "bg-gold/20 hover:bg-gold/40 text-gold"
        
        synapse_cards += f"""
        <div class="bg-black/40 p-6 rounded-2xl border border-gold/20 hover:border-gold/50 transition-all group">
            <div class="flex justify-between items-start mb-2">
                <h3 class="text-lg font-bold text-gold">{s['name']}</h3>
                <span class="text-[10px] bg-gold/10 text-gold px-2 py-1 rounded-full">{s['category']}</span>
            </div>
            <p class="text-xs text-mist/70 mb-4 h-8 overflow-hidden">{s['description']}</p>
            <div class="flex justify-between items-center pt-4 border-t border-mist/10">
                <button onclick="openDetailsModal('{s['id']}')" class="text-[10px] text-mist/50 hover:text-gold transition-all uppercase tracking-tighter">Details</button>
                <button onclick="installSynapse('{s['id']}', '{s['name']}')" 
                        class="text-xs {btn_class} px-4 py-1 rounded-lg border border-gold/30 transition-all">
                    {btn_text}
                </button>
            </div>
        </div>
        """

    running_rows = ""
    if not running_synapses:
        running_rows = '<div class="text-xs text-mist/30 italic">No synapses active.</div>'
    else:
        for rs in running_synapses:
            running_rows += f"""
            <div class="flex justify-between items-center bg-black/20 p-2 rounded-lg border border-chlorophyll/10 mb-2">
                <span class="text-[10px] text-mist font-mono uppercase">{rs['name']}</span>
                <span class="text-[10px] text-chlorophyll animate-pulse font-bold">ACTIVE</span>
            </div>
            """

    dao_rows = ""
    if not dao.proposals:
        dao_rows = '<div class="text-center text-mist/30 italic py-4">No active proposals in the DAO.</div>'
    else:
        for p_id, prop in dao.proposals.items():
            status_color = "text-gold" if prop.status == "OPEN" else "text-chlorophyll"
            dao_rows += f"""
            <div class="bg-black/40 p-6 rounded-2xl border border-mist/10 flex justify-between items-center mb-4">
                <div>
                    <h3 class="text-lg font-bold text-mist">{prop.proposal_id} <span class="text-[10px] {status_color}">[{prop.status}]</span></h3>
                    <p class="text-xs text-mist/50 mt-1">{prop.description}</p>
                </div>
                <div class="flex space-x-2">
                    <button onclick="castVote('{prop.proposal_id}', true)" class="bg-chlorophyll/20 hover:bg-chlorophyll/40 text-chlorophyll font-bold px-4 py-2 rounded-xl border border-chlorophyll/30 transition-all">YES</button>
                    <button onclick="castVote('{prop.proposal_id}', false)" class="bg-red-900/20 hover:bg-red-900/40 text-red-500 font-bold px-4 py-2 rounded-xl border border-red-500/30 transition-all">NO</button>
                </div>
            </div>
            """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Calyx Hub | Mission Control</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ background-color: #0A0F0D; color: #E0E0E0; font-family: 'Courier New', Courier, monospace; overflow-x: hidden; }}
            .bg-bark {{ background-color: rgba(74, 55, 40, 0.2); }}
            .text-gold {{ color: #FFD700; }}
            .text-chlorophyll {{ color: #2D6A4F; }}
            .spike-flash {{ background-color: rgba(45, 106, 79, 0.4) !important; }}
            @keyframes pulse-grow {{
                0% {{ transform: scale(1); filter: brightness(1); }}
                50% {{ transform: scale(1.02); filter: brightness(1.5); }}
                100% {{ transform: scale(1); filter: brightness(1); }}
            }}
            .plant-pulse {{ animation: pulse-grow 0.3s ease-out; }}
            .tab-active {{ border-bottom: 2px solid #FFD700; color: #FFD700; font-weight: bold; }}
            #neuralOutput::-webkit-scrollbar {{ width: 4px; }}
            #neuralOutput::-webkit-scrollbar-thumb {{ background: #2D6A4F; border-radius: 10px; }}
        </style>
    </head>
    <body class="p-8">
        <div class="max-w-6xl mx-auto">
            <div class="flex justify-between items-end border-b border-chlorophyll/30 pb-4 mb-8">
                <div>
                    <h1 class="text-3xl font-bold text-chlorophyll font-mono">CALYX_HUB <span class="text-xs text-mist/50">v1.3.4</span></h1>
                    <div class="flex space-x-8 mt-4">
                        <button onclick="showTab('mesh')" id="tab-mesh" class="tab-active text-xs uppercase tracking-widest pb-2">Mesh Monitor</button>
                        <button onclick="showTab('market')" id="tab-market" class="text-xs uppercase tracking-widest pb-2 text-mist/50">Synapse Market</button>
                        <button onclick="showTab('gov')" id="tab-gov" class="text-xs uppercase tracking-widest pb-2 text-mist/50">DAO Governance</button>
                    </div>
                </div>
                <div class="text-right pb-2 space-y-2">
                    <button onclick="openIdentityModal()" id="identityBtn" class="bg-bark border border-gold/30 text-[10px] text-gold px-4 py-1 rounded-full hover:bg-gold/10 transition-all">CONNECT_IDENTITY</button>
                    <div id="connectionStatus" class="text-red-500 font-bold text-[8px]">DISCONNECTED</div>
                </div>
            </div>

            <!-- TAB: MESH MONITOR -->
            <div id="content-mesh" class="space-y-8">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div class="col-span-2">
                        <h2 class="text-xl font-bold mb-4 uppercase tracking-widest text-mist/50 text-[10px]">Mesh_Intelligence_Graph</h2>
                        <div class="bg-bark p-6 rounded-2xl border border-chlorophyll/30 h-[400px] relative overflow-hidden">
                            <svg id="meshGraph" class="w-full h-full"></svg>
                            <div class="absolute bottom-4 right-4 text-[8px] text-mist/30 italic">Real-time Shard Topology</div>
                        </div>
                    </div>
                    
                    <div class="col-span-1 space-y-8">
                        <div>
                            <h2 class="text-xl font-bold mb-4 uppercase tracking-widest text-mist/50 text-[10px]">Launch_Readiness</h2>
                            <div class="bg-bark p-6 rounded-2xl border border-gold/20">
                                <div class="text-4xl font-bold text-chlorophyll">100%</div>
                                <div class="text-xs text-mist/50 mt-1 uppercase">Infrastructure Ready</div>
                                <div class="w-full bg-black/50 h-2 rounded-full mt-4 overflow-hidden">
                                    <div class="bg-chlorophyll h-full w-[100%]"></div>
                                </div>
                                <div class="mt-4 space-y-2">
                                    <div class="text-[10px] text-chlorophyll flex justify-between"><span>Core Protocol</span> <span>DONE</span></div>
                                    <div class="text-[10px] text-chlorophyll flex justify-between"><span>Mesh Hardening</span> <span>DONE</span></div>
                                    <div class="text-[10px] text-gold flex justify-between animate-pulse"><span>Neural Deployment</span> <span>ACTIVE</span></div>
                                </div>
                            </div>
                        </div>
                        
                        <div>
                            <h2 class="text-xl font-bold mb-4 uppercase tracking-widest text-mist/50 text-[10px]">Mesh_Wallet</h2>
                            <div class="bg-bark p-6 rounded-2xl border border-gold/30">
                                <div id="synBalance" class="text-3xl font-bold text-gold">0.00</div>
                                <div class="text-[10px] text-mist/50 uppercase mt-1">$SYN Earnings (Real-time)</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div class="col-span-1">
                        <h2 class="text-xl font-bold mb-4 uppercase tracking-widest text-mist/50 text-[10px]">Hardware (1080 Ti)</h2>
                        <div class="bg-bark p-6 rounded-2xl border border-gold/20 h-[190px]">
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <div id="gpuTemp" class="text-3xl font-bold text-mist">--°C</div>
                                    <div class="text-[10px] text-mist/50 uppercase">Temp</div>
                                </div>
                                <div>
                                    <div id="gpuLoad" class="text-3xl font-bold text-mist">--%</div>
                                    <div class="text-[10px] text-mist/50 uppercase">Load</div>
                                </div>
                            </div>
                            <div class="mt-4">
                                <div class="flex justify-between text-[10px] text-mist/50 uppercase mb-1">
                                    <span>VRAM</span>
                                    <span id="gpuVramText">-- / -- MB</span>
                                </div>
                                <div class="w-full bg-black/50 h-2 rounded-full overflow-hidden">
                                    <div id="gpuVramBar" class="bg-gold h-full w-0 transition-all duration-500"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-span-1">
                        <h2 class="text-xl font-bold mb-4 uppercase tracking-widest text-mist/50 text-[10px]">Command_Inference</h2>
                        <div class="bg-bark p-6 rounded-2xl border border-gold/20 mb-6">
                            <textarea id="commandInput" class="w-full bg-black/50 border border-mist/20 rounded-xl p-3 text-gold text-xs h-24 mb-4 focus:border-gold outline-none" placeholder="Enter Neural Pulse Data..."></textarea>
                            <button onclick="sendSpike()" class="w-full bg-chlorophyll hover:bg-chlorophyll/80 text-mist font-bold py-3 rounded-xl transition-all uppercase tracking-widest shadow-lg shadow-chlorophyll/10">FIRE_SPIKE</button>
                        </div>
                    </div>

                    <div class="col-span-1">
                        <h2 class="text-xl font-bold mb-4 uppercase tracking-widest text-mist/50 text-[10px]">Neural_Output</h2>
                        <div id="neuralOutput" class="bg-black/60 p-6 rounded-2xl border border-chlorophyll/40 h-[190px] overflow-y-auto text-[10px] font-mono space-y-4">
                            <div class="text-mist/30 italic">Awaiting results...</div>
                        </div>
                    </div>
                </div>
            </div>

            <div id="content-market" class="hidden grid grid-cols-1 md:grid-cols-3 gap-6">
                {synapse_cards if synapse_cards else '<div class="col-span-3 text-center text-mist/30 italic">No synapses found in registry.</div>'}
            </div>

            <div id="content-gov" class="hidden space-y-6">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div class="col-span-2">
                        <div class="bg-bark p-8 rounded-3xl border border-gold/30">
                            <h2 class="text-2xl font-bold text-gold mb-2">ACTIVE_PROPOSALS</h2>
                            <div id="proposalList">{dao_rows}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="mt-8">
                <h2 class="text-xl font-bold mb-4 uppercase tracking-widest text-mist/50 text-[10px]">Live_Log_Stream</h2>
                <div id="terminal" class="bg-black/80 p-4 rounded-xl border border-chlorophyll/30 h-64 overflow-y-auto text-[10px] text-chlorophyll font-mono"></div>
            </div>
        </div>

        <div id="identityModal" class="hidden fixed inset-0 bg-black/95 flex items-center justify-center p-4 z-50">
            <div class="bg-bark border border-gold/40 p-10 rounded-3xl max-w-sm w-full text-center">
                <h2 class="text-2xl font-black text-gold mb-6 uppercase tracking-widest">Connect_Mesh</h2>
                <input type="text" id="peerIdInput" class="w-full bg-black/50 border border-gold/20 rounded-xl p-4 text-gold font-mono text-center mb-6 outline-none focus:border-gold" placeholder="PEER_ID">
                <button onclick="setIdentity()" class="w-full bg-gold text-black font-black py-4 rounded-2xl hover:bg-gold/80 transition-all uppercase tracking-widest">Authenticate</button>
                <button onclick="closeIdentityModal()" class="mt-4 text-mist/30 text-[10px] uppercase hover:text-mist">Cancel</button>
            </div>
        </div>

        <!-- Task #18: Marketplace Detail Modal -->
        <div id="detailsModal" class="hidden fixed inset-0 bg-black/95 flex items-center justify-center p-4 z-50 overflow-y-auto">
            <div class="bg-bark border border-chlorophyll/40 p-8 rounded-3xl max-w-2xl w-full">
                <div class="flex justify-between items-start mb-6">
                    <div>
                        <h2 id="detailName" class="text-3xl font-black text-gold uppercase tracking-widest">---</h2>
                        <div id="detailCategory" class="text-xs text-mist/50 font-mono">Category: ---</div>
                    </div>
                    <button onclick="closeDetailsModal()" class="text-mist/30 hover:text-mist text-2xl">&times;</button>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                    <div class="space-y-4">
                        <div>
                            <div class="text-[10px] text-chlorophyll uppercase font-bold tracking-widest mb-1">Architecture</div>
                            <div id="detailArch" class="bg-black/40 p-3 rounded-xl border border-mist/10 text-xs font-mono">---</div>
                        </div>
                        <div>
                            <div class="text-[10px] text-chlorophyll uppercase font-bold tracking-widest mb-1">Author</div>
                            <div id="detailAuthor" class="bg-black/40 p-3 rounded-xl border border-mist/10 text-xs font-mono">---</div>
                        </div>
                        <div>
                            <div class="text-[10px] text-chlorophyll uppercase font-bold tracking-widest mb-1">Energy_Efficiency</div>
                            <div id="detailEfficiency" class="text-2xl font-black text-chlorophyll">---</div>
                        </div>
                    </div>
                    <div>
                        <div class="text-[10px] text-gold uppercase font-bold tracking-widest mb-1">Description</div>
                        <p id="detailDesc" class="text-xs text-mist/70 leading-relaxed bg-black/20 p-4 rounded-xl border border-gold/10 h-full">---</p>
                    </div>
                </div>

                <div class="flex justify-end space-x-4 border-t border-mist/10 pt-6">
                    <button id="detailInstallBtn" class="bg-chlorophyll text-mist font-bold px-8 py-3 rounded-2xl hover:bg-chlorophyll/80 transition-all uppercase tracking-widest">INSTALL_SYNAPSE</button>
                </div>
            </div>
        </div>

        <script>
            let currentPeerId = localStorage.getItem('calyx_peer_id') || 'LOCAL_OPERATOR';

            window.onload = () => {{
                if (currentPeerId !== 'LOCAL_OPERATOR') {{
                    document.getElementById('identityBtn').innerText = "ID: " + currentPeerId;
                }}
                fetchRewards();
                initGraph();
                updateGraph();
            }};

            // Task #18: Detail View Logic
            async function openDetailsModal(id) {{
                const resp = await fetch(`/api/marketplace/details/${{id}}`);
                const data = await resp.json();
                if (data.error) return;

                document.getElementById('detailName').innerText = data.name;
                document.getElementById('detailCategory').innerText = "Category: " + data.category;
                document.getElementById('detailArch').innerText = data.architecture;
                document.getElementById('detailAuthor').innerText = data.author;
                document.getElementById('detailEfficiency').innerText = data.energy_efficiency_score;
                document.getElementById('detailDesc').innerText = data.description;
                
                document.getElementById('detailInstallBtn').onclick = () => installSynapse(data.id, data.name);
                
                document.getElementById('detailsModal').classList.remove('hidden');
            }}

            function closeDetailsModal() {{ document.getElementById('detailsModal').classList.add('hidden'); }}

            async function fetchRewards() {{
                try {{
                    const resp = await fetch(`/api/rewards/${{currentPeerId}}`);
                    const data = await resp.json();
                    document.getElementById('synBalance').innerText = data.total.toFixed(2);
                }} catch(e) {{}}
            }}

            function openIdentityModal() {{ document.getElementById('identityModal').classList.remove('hidden'); }}
            function closeIdentityModal() {{ document.getElementById('identityModal').classList.add('hidden'); }}

            function setIdentity() {{
                const id = document.getElementById('peerIdInput').value.trim();
                if (id) {{
                    currentPeerId = id;
                    localStorage.setItem('calyx_peer_id', id);
                    location.reload();
                }}
            }}

            function showTab(tab) {{
                ['mesh', 'market', 'gov'].forEach(t => {{
                    document.getElementById('content-' + t).classList.add('hidden');
                    document.getElementById('tab-' + t).classList.remove('tab-active');
                }});
                document.getElementById('content-' + tab).classList.remove('hidden');
                document.getElementById('tab-' + tab).classList.add('tab-active');
            }}

            const ws = new WebSocket(`ws://${{window.location.host}}/ws`);
            ws.onmessage = (event) => {{
                const data = JSON.parse(event.data);
                if (data.type === "VITALS") updateHardwareUI(data.payload);
                if (data.type === "INFERENCE_RESULT") updateNeuralOutput(data.payload);
                if (data.type === "LOG") {{
                    appendToTerminal(data.payload);
                    updateGraph();
                }}
            }};

            function updateHardwareUI(vitals) {{
                document.getElementById('gpuTemp').innerText = vitals.temp + "°C";
                document.getElementById('gpuLoad').innerText = vitals.load + "%";
                document.getElementById('gpuVramText').innerText = `${{Math.round(vitals.vram_used)}} / ${{Math.round(vitals.vram_total)}} MB`;
                document.getElementById('gpuVramBar').style.width = (vitals.vram_used / vitals.vram_total * 100) + "%";
            }}

            function updateNeuralOutput(res) {{
                const out = document.getElementById('neuralOutput');
                if(out.innerHTML.includes('Awaiting')) out.innerHTML = '';
                const entry = document.createElement('div');
                entry.className = "p-2 bg-bark/40 rounded-lg border border-chlorophyll/20 mb-2";
                entry.innerHTML = `<div class="text-chlorophyll font-bold">PULSE: ${{res.input}}</div><div class="text-gold">RESULT: ${{res.output}}</div>`;
                out.prepend(entry);
            }}

            function appendToTerminal(log) {{
                const term = document.getElementById('terminal');
                const line = document.createElement('div');
                line.innerHTML = `<span class="text-mist/50">[${{new Date().toLocaleTimeString()}}]</span> <span class="text-gold">[${{log.event}}]</span> <span class="text-chlorophyll/80">${{JSON.stringify(log.data)}}</span>`;
                term.prepend(line);
            }}

            // D3 Graph Logic
            const svg = d3.select("#meshGraph");
            let simulation;

            function initGraph() {{
                const cb = document.getElementById('meshGraph').getBoundingClientRect();
                simulation = d3.forceSimulation()
                    .force("link", d3.forceLink().id(d => d.id).distance(100))
                    .force("charge", d3.forceManyBody().strength(-200))
                    .force("center", d3.forceCenter(cb.width / 2, cb.height / 2));
            }}

            async function updateGraph() {{
                const resp = await fetch('/api/mesh/nodes');
                const data = await resp.json();
                
                svg.selectAll("*").remove();
                
                const link = svg.append("g")
                    .attr("stroke", "#2D6A4F")
                    .attr("stroke-opacity", 0.6)
                    .selectAll("line")
                    .data(data.links)
                    .join("line");

                const node = svg.append("g")
                    .selectAll("circle")
                    .data(data.nodes)
                    .join("circle")
                    .attr("r", 10)
                    .attr("fill", d => {{
                        if (!d.is_ready) return "#FF4500"; // Red/Orange for OFFLINE
                        return d.group === 1 ? "#FFD700" : "#2D6A4F";
                    }});

                const text = svg.append("g")
                    .selectAll("text")
                    .data(data.nodes)
                    .join("text")
                    .text(d => d.label)
                    .attr("font-size", "10px")
                    .attr("fill", "#mist")
                    .attr("dx", 12)
                    .attr("dy", 4);

                simulation.nodes(data.nodes);
                simulation.force("link").links(data.links);
                simulation.on("tick", () => {{
                    link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
                        .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
                    node.attr("cx", d => d.x).attr("cy", d => d.y);
                    text.attr("x", d => d.x).attr("y", d => d.y);
                }});
                simulation.alpha(1).restart();
            }}

            async function sendSpike() {{
                const text = document.getElementById('commandInput').value;
                if (!text) return;
                await fetch('/api/command', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ text: text, peer_id: currentPeerId }})
                }});
                document.getElementById('commandInput').value = "";
            }}
        </script>
    </body>
    </html>
    """
    return html_content

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.disconnect(websocket)

@app.post("/api/command")
async def handle_command(cmd: CommandRequest):
    await inference_queue.put({"peer_id": cmd.peer_id, "text": cmd.text, "synapse_id": cmd.synapse_id})
    logger.log("COMMAND_INJECTED", {"synapse": cmd.synapse_id, "text": cmd.text[:50] + "...", "by": cmd.peer_id})
    return {"status": "QUEUED"}

@app.post("/api/marketplace/install")
async def handle_install(req: InstallRequest):
    if not any(rs['synapse_id'] == req.synapse_id for rs in running_synapses):
        running_synapses.append(req.model_dump())
        logger.log("SYNAPSE_INSTALLED", {"id": req.synapse_id, "name": req.name})
        return {"status": "INSTALLED"}
    return {"status": "ALREADY_RUNNING"}

@app.post("/api/stress/start")
async def handle_stress():
    logger.log("STRESS_TEST_INITIATED", {"duration": "60s"})
    subprocess.Popen([sys.executable, "tools/stress_test.py"])
    return {"status": "STARTED"}

@app.post("/api/vitals")
async def handle_vitals(vitals: GPUVitals):
    if vitals.psk != os.getenv("CALYX_SECURE_PSK", "CALYX_SECURE_2026"): return {"status": "UNAUTHORIZED"}
    await manager.broadcast(json.dumps({"type": "VITALS", "payload": vitals.model_dump()}))
    return {"status": "OK"}

@app.post("/api/mobile/vitals")
async def handle_mobile_vitals(vitals: MobileVitals):
    if vitals.psk != os.getenv("CALYX_MOBILE_PSK", "CALYX_MOBILE_2026"): return {"status": "UNAUTHORIZED"}
    await manager.broadcast(json.dumps({"type": "MOBILE_VITALS", "payload": vitals.model_dump()}))
    return {"status": "OK"}

@app.post("/api/infer")
async def handle_inference(req: CommandRequest):
    await inference_queue.put({"peer_id": req.peer_id, "text": req.text, "synapse_id": req.synapse_id})
    return {"status": "QUEUED", "queue_depth": inference_queue.qsize()}

@app.post("/api/dao/propose")
async def handle_propose(req: ProposalRequest):
    p_id = dao.create_proposal(req.proposer_id, req.description, req.synapse_id, req.weights_hash)
    if p_id:
        logger.log("DAO_PROPOSAL_CREATED", {"id": p_id, "by": req.proposer_id, "desc": req.description})
        return {"status": "CREATED", "proposal_id": p_id}
    return {"status": "REJECTED", "error": "Insufficient reputation."}

@app.post("/api/dao/vote")
async def handle_vote(req: VoteRequest):
    dao.cast_vote(req.peer_id, req.proposal_id, req.vote)
    logger.log("DAO_VOTE_CAST", {"id": req.proposal_id, "by": req.peer_id, "vote": req.vote})
    return {"status": "VOTE_RECORDED"}

@app.get("/api/rewards/{peer_id}")
async def get_peer_rewards(peer_id: str):
    payouts = rewards.calculate_payouts()
    return {"total": payouts.get(peer_id, 0.0)}

@app.get("/api/rewards")
async def get_rewards():
    return rewards.calculate_payouts()

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("CALYX_HUB_HOST", "0.0.0.0")
    port = int(os.getenv("CALYX_HUB_PORT", 8000))
    uvicorn.run(app, host=host, port=port)
