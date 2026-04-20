const canvas = document.getElementById('cctvCanvas');
const ctx = canvas.getContext('2d');
const videoInput = document.getElementById('videoInput');
const uploadBtn = document.getElementById('uploadBtn');

// UI Elements
const els = {
    count: document.getElementById('valCount'),
    speed: document.getElementById('valSpeed'),
    density: document.getElementById('valDensity'),
    latency: document.getElementById('valInference'),
    epsilon: document.getElementById('valEpsilon'),
    targetFPS: document.getElementById('valTargetFPS'),
    conf: document.getElementById('valConf'),
    policy: document.getElementById('policyAction'),
    signals: {
        North: document.getElementById('sigNorth'),
        South: document.getElementById('sigSouth'),
        East: document.getElementById('sigEast'),
        West: document.getElementById('sigWest')
    },
    rewardBars: document.getElementById('rewardBars')
};

let ws;
const REWARD_HISTORY_SIZE = 20;
let rewardHistory = [];

function connectWS(videoPath = null) {
    if (ws) ws.close();
    
    ws = new WebSocket(`ws://${location.hostname}:8001/ws/process`);
    
    ws.onopen = () => {
        console.log("Connected to RL Engine");
        ws.send(JSON.stringify({ action: "start", path: videoPath }));
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateUI(data);
    };
    
    ws.onerror = (err) => console.error("WS Error:", err);
    ws.onclose = () => console.log("Connection closed");
}

function updateUI(data) {
    const { frame, telemetry, processed_ms } = data;
    
    // Draw Frame
    const image = new Image();
    image.onload = () => {
        canvas.width = image.width;
        canvas.height = image.height;
        ctx.drawImage(image, 0, 0);
    };
    image.src = `data:image/jpeg;base64,${frame}`;
    
    // Update Stats
    els.count.innerText = telemetry.vehicle_count;
    els.speed.innerText = `${Math.round(telemetry.avg_speed * 100)} km/h`;
    els.density.innerText = `${Math.round(telemetry.density * 100)}%`;
    els.latency.innerText = `${Math.round(telemetry.inference_time_ms)} ms`;
    
    // RL Monitoring
    els.epsilon.innerText = telemetry.rl_stats.epsilon.toFixed(3);
    els.targetFPS.innerText = `${telemetry.rl_action.fps} FPS`;
    els.conf.innerText = telemetry.rl_action.confidence.toFixed(2);
    
    // Update Policy label
    if (telemetry.rl_action.fps > 20) els.policy.innerText = "High Fidelity";
    else if (telemetry.rl_action.fps < 10) els.policy.innerText = "Power Saving";
    else els.policy.innerText = "Balanced Opt.";

    // Update Signals
    const sigStatus = telemetry.signal_control;
    Object.keys(els.signals).forEach(dir => {
        const sigEl = els.signals[dir];
        const timing = sigStatus.phase_timings[dir];
        sigEl.querySelector('span').innerText = timing;
        
        // Simulating green light for current direction
        if (sigStatus.current_green === dir) {
            sigEl.classList.add('green');
            sigEl.classList.remove('red');
        } else {
            sigEl.classList.add('red');
            sigEl.classList.remove('green');
        }
    });

    // Mock Reward Bars
    updateRewardBars(Math.random() * 50 + 20); // Simulating reward visualization
}

function updateRewardBars(val) {
    rewardHistory.push(val);
    if (rewardHistory.length > REWARD_HISTORY_SIZE) rewardHistory.shift();
    
    els.rewardBars.innerHTML = '';
    rewardHistory.forEach(h => {
        const bar = document.createElement('div');
        bar.className = 'bar';
        bar.style.height = `${h}%`;
        els.rewardBars.appendChild(bar);
    });
}

// Upload Handling
uploadBtn.onclick = () => videoInput.click();

videoInput.onchange = async () => {
    const file = videoInput.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const resp = await fetch(`http://${location.hostname}:8001/api/upload`, {
            method: 'POST',
            body: formData
        });
        const result = await resp.json();
        console.log("Upload Success:", result);
        connectWS(result.path);
    } catch (err) {
        console.error("Upload failed", err);
    }
};

// Initial connection
connectWS();
