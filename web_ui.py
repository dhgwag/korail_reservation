#!/usr/bin/env python3
"""
코레일 자동 예매 웹 UI
- .env 설정 편집
- search_configs.json 관리
- 예매 스크립트 실행 및 실시간 로그
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

from flask import Flask, Response, jsonify, render_template_string, request

# ============ 경로 설정 ============
BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / ".env"
ENV_EXAMPLE = BASE_DIR / ".env.example"
CONFIGS_FILE = BASE_DIR / "search_configs.json"
SCRIPT_FILE = BASE_DIR / "auto_reserve_advanced.py"

app = Flask(__name__)

# ============ 프로세스 관리 ============
process_lock = threading.Lock()
running_process: subprocess.Popen | None = None
log_buffer: deque[str] = deque(maxlen=5000)
log_event = threading.Event()


# ============ .env 읽기/쓰기 ============
def read_env() -> dict:
    defaults = {
        "KORAIL_ID": "",
        "KORAIL_PW": "",
        "TELEGRAM_BOT_TOKEN": "",
        "TELEGRAM_CHAT_ID": "",
    }
    target = ENV_FILE if ENV_FILE.exists() else ENV_EXAMPLE
    if not target.exists():
        return defaults
    result = dict(defaults)
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            key, _, value = line.partition("=")
            key = key.strip()
            if key in defaults:
                result[key] = value.strip()
    return result


def write_env(data: dict):
    lines = [f"{k}={v}" for k, v in data.items()]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ============ search_configs.json 읽기/쓰기 ============
def read_configs() -> list[dict]:
    if not CONFIGS_FILE.exists():
        return []
    return json.loads(CONFIGS_FILE.read_text(encoding="utf-8"))


def write_configs(configs: list[dict]):
    CONFIGS_FILE.write_text(
        json.dumps(configs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


# ============ 프로세스 실행 ============
def stream_output(proc: subprocess.Popen):
    """프로세스의 stdout을 log_buffer에 추가"""
    global running_process
    try:
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            log_buffer.append(line.rstrip("\n"))
            log_event.set()
        proc.wait()
    finally:
        with process_lock:
            running_process = None
        log_buffer.append("[시스템] 예매 스크립트가 종료되었습니다.")
        log_event.set()


# ============ API 라우트 ============
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/env", methods=["GET"])
def get_env():
    return jsonify(read_env())


@app.route("/api/env", methods=["POST"])
def save_env():
    data = request.json
    env = read_env()
    for key in env:
        if key in data:
            env[key] = data[key]
    write_env(env)
    return jsonify({"ok": True})


@app.route("/api/configs", methods=["GET"])
def get_configs():
    return jsonify(read_configs())


@app.route("/api/configs", methods=["POST"])
def save_configs():
    configs = request.json
    write_configs(configs)
    return jsonify({"ok": True})


@app.route("/api/run", methods=["POST"])
def run_script():
    global running_process
    with process_lock:
        if running_process is not None:
            return jsonify({"ok": False, "error": "이미 실행 중입니다"})

        env_data = read_env()
        env = os.environ.copy()
        env.update(env_data)
        env["PYTHONUNBUFFERED"] = "1"

        venv_python = BASE_DIR / "venv" / "bin" / "python"
        python_cmd = str(venv_python) if venv_python.exists() else sys.executable

        log_buffer.clear()
        log_buffer.append("[시스템] 예매 스크립트를 시작합니다...")

        proc = subprocess.Popen(
            [python_cmd, "-u", str(SCRIPT_FILE)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            cwd=str(BASE_DIR),
        )
        running_process = proc

    t = threading.Thread(target=stream_output, args=(proc,), daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/api/stop", methods=["POST"])
def stop_script():
    global running_process
    with process_lock:
        if running_process is None:
            return jsonify({"ok": False, "error": "실행 중인 스크립트가 없습니다"})
        try:
            running_process.send_signal(signal.SIGINT)
        except ProcessLookupError:
            pass
    return jsonify({"ok": True})


@app.route("/api/status", methods=["GET"])
def get_status():
    with process_lock:
        is_running = running_process is not None
    return jsonify({"running": is_running})


@app.route("/api/log")
def stream_log():
    def generate():
        sent = 0
        while True:
            buf = list(log_buffer)
            if sent < len(buf):
                for line in buf[sent:]:
                    yield f"data: {line}\n\n"
                sent = len(buf)

            # 프로세스가 종료되었으면 마지막 로그 전송 후 종료
            with process_lock:
                is_running = running_process is not None
            if not is_running and sent >= len(log_buffer):
                yield "data: [END]\n\n"
                break

            log_event.wait(timeout=1)
            log_event.clear()

    return Response(generate(), mimetype="text/event-stream")


# ============ HTML 템플릿 ============
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>코레일 자동 예매</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }
.container { max-width: 800px; margin: 0 auto; padding: 20px; }
h1 { text-align: center; margin: 20px 0; color: #1a56db; font-size: 1.5em; }
.card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.card h2 { font-size: 1.1em; margin-bottom: 16px; color: #1a56db; display: flex; align-items: center; gap: 8px; }
.form-row { display: flex; align-items: center; margin-bottom: 12px; gap: 12px; }
.form-row label { min-width: 110px; font-size: 0.9em; color: #555; font-weight: 500; }
.form-row input, .form-row select { flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 0.9em; outline: none; transition: border-color 0.2s; }
.form-row input:focus, .form-row select:focus { border-color: #1a56db; }
.btn { padding: 8px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 0.9em; font-weight: 500; transition: all 0.2s; }
.btn-primary { background: #1a56db; color: white; }
.btn-primary:hover { background: #1544b5; }
.btn-danger { background: #dc3545; color: white; }
.btn-danger:hover { background: #b52a37; }
.btn-success { background: #28a745; color: white; }
.btn-success:hover { background: #1e8e3b; }
.btn-secondary { background: #6c757d; color: white; }
.btn-secondary:hover { background: #565e64; }
.btn-sm { padding: 4px 12px; font-size: 0.8em; }
.btn-group { display: flex; gap: 8px; margin-top: 12px; }
table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #eee; }
th { color: #555; font-weight: 600; font-size: 0.8em; text-transform: uppercase; }
tr:hover { background: #f8f9fa; }
.log-area { background: #1e1e1e; color: #d4d4d4; border-radius: 8px; padding: 16px; font-family: 'SF Mono', 'Menlo', monospace; font-size: 0.8em; height: 400px; overflow-y: auto; white-space: pre-wrap; word-wrap: break-word; }
.log-line { padding: 1px 0; }
.log-line.system { color: #569cd6; }
.log-line.success { color: #4ec9b0; }
.log-line.error { color: #f44747; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.status-dot.running { background: #28a745; animation: pulse 1.5s infinite; }
.status-dot.stopped { background: #6c757d; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.toast { position: fixed; top: 20px; right: 20px; padding: 12px 20px; border-radius: 8px; color: white; font-size: 0.9em; z-index: 1000; transition: opacity 0.3s; }
.toast.success { background: #28a745; }
.toast.error { background: #dc3545; }
.modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); z-index: 100; justify-content: center; align-items: center; }
.modal-overlay.active { display: flex; }
.modal { background: white; border-radius: 12px; padding: 24px; width: 90%; max-width: 500px; }
.modal h3 { margin-bottom: 16px; }
.empty-state { text-align: center; padding: 20px; color: #999; }
</style>
</head>
<body>

<div class="container">
  <h1>🚄 코레일 자동 예매</h1>

  <!-- 로그인 설정 -->
  <div class="card">
    <h2>🔑 로그인 설정</h2>
    <div class="form-row">
      <label>코레일 ID</label>
      <input type="text" id="env-KORAIL_ID" placeholder="회원번호 or 이메일 or 전화번호">
    </div>
    <div class="form-row">
      <label>코레일 PW</label>
      <input type="password" id="env-KORAIL_PW" placeholder="비밀번호">
    </div>
    <div class="form-row">
      <label>텔레그램 토큰</label>
      <input type="text" id="env-TELEGRAM_BOT_TOKEN" placeholder="선택사항">
    </div>
    <div class="form-row">
      <label>텔레그램 Chat ID</label>
      <input type="text" id="env-TELEGRAM_CHAT_ID" placeholder="선택사항">
    </div>
    <div class="btn-group">
      <button class="btn btn-primary" onclick="saveEnv()">저장</button>
    </div>
  </div>

  <!-- 검색 조건 -->
  <div class="card">
    <h2>🔍 검색 조건</h2>
    <div id="config-table-wrap"></div>
    <div class="btn-group">
      <button class="btn btn-primary" onclick="openConfigModal(-1)">+ 조건 추가</button>
    </div>
  </div>

  <!-- 실행 -->
  <div class="card">
    <h2>▶️ 예매 실행 <span class="status-dot stopped" id="status-dot"></span></h2>
    <div class="btn-group" style="margin-bottom: 12px;">
      <button class="btn btn-success" id="btn-run" onclick="runScript()">예매 시작</button>
      <button class="btn btn-danger" id="btn-stop" onclick="stopScript()" style="display:none;">중지</button>
    </div>
    <div class="log-area" id="log-area"></div>
  </div>
</div>

<!-- 검색 조건 편집 모달 -->
<div class="modal-overlay" id="config-modal">
  <div class="modal">
    <h3 id="modal-title">검색 조건 추가</h3>
    <div class="form-row">
      <label>출발역</label>
      <input type="text" id="cfg-dep_station" placeholder="서울">
    </div>
    <div class="form-row">
      <label>도착역</label>
      <input type="text" id="cfg-arr_station" placeholder="부산">
    </div>
    <div class="form-row">
      <label>출발날짜</label>
      <input type="date" id="cfg-dep_date">
    </div>
    <div class="form-row">
      <label>검색시작시간</label>
      <input type="time" id="cfg-dep_time" value="06:00">
    </div>
    <div class="form-row">
      <label>열차종류</label>
      <select id="cfg-train_type">
        <option value="KTX">KTX</option>
        <option value="MUGUNGHWA">무궁화호</option>
        <option value="ALL">전체</option>
      </select>
    </div>
    <div class="form-row">
      <label>선호시간 시작</label>
      <select id="cfg-time_start">
        <option value="">전체</option>
      </select>
    </div>
    <div class="form-row">
      <label>선호시간 종료</label>
      <select id="cfg-time_end">
        <option value="">전체</option>
      </select>
    </div>
    <div class="form-row">
      <label>좌석종류</label>
      <select id="cfg-seat_type">
        <option value="general">일반실</option>
        <option value="special">특실</option>
        <option value="any">전체</option>
      </select>
    </div>
    <div class="btn-group">
      <button class="btn btn-primary" onclick="saveConfig()">저장</button>
      <button class="btn btn-secondary" onclick="closeConfigModal()">취소</button>
    </div>
  </div>
</div>

<script>
let configs = [];
let editIndex = -1; // -1 = 신규

// 시간 select 옵션 생성
function initTimeSelects() {
  ['cfg-time_start', 'cfg-time_end'].forEach(id => {
    const sel = document.getElementById(id);
    sel.innerHTML = '<option value="">전체</option>';
    for (let h = 0; h < 24; h++) {
      const hh = String(h).padStart(2, '0');
      sel.innerHTML += `<option value="${hh}">${hh}시</option>`;
    }
  });
}

// 토스트 알림
function showToast(msg, type='success') {
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 2000);
}

// .env 로드
async function loadEnv() {
  const res = await fetch('/api/env');
  const data = await res.json();
  for (const [k, v] of Object.entries(data)) {
    const el = document.getElementById('env-' + k);
    if (el) el.value = v;
  }
}

// .env 저장
async function saveEnv() {
  const data = {};
  ['KORAIL_ID', 'KORAIL_PW', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'].forEach(k => {
    data[k] = document.getElementById('env-' + k).value;
  });
  await fetch('/api/env', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
  showToast('로그인 설정이 저장되었습니다');
}

// configs 로드
async function loadConfigs() {
  const res = await fetch('/api/configs');
  configs = await res.json();
  renderConfigs();
}

// configs 테이블 렌더링
function renderConfigs() {
  const wrap = document.getElementById('config-table-wrap');
  if (configs.length === 0) {
    wrap.innerHTML = '<div class="empty-state">검색 조건이 없습니다. 조건을 추가해주세요.</div>';
    return;
  }
  const seatMap = { general: '일반실', special: '특실', any: '전체' };
  let html = '<table><thead><tr><th>#</th><th>출발역</th><th>도착역</th><th>날짜</th><th>시간대</th><th>열차</th><th>좌석</th><th></th></tr></thead><tbody>';
  configs.forEach((c, i) => {
    const date = c.dep_date ? `${c.dep_date.slice(4,6)}/${c.dep_date.slice(6,8)}` : '';
    const timeRange = (c.time_start && c.time_end) ? `${c.time_start}~${c.time_end}시` : '전체';
    html += `<tr>
      <td>${i+1}</td>
      <td>${c.dep_station || ''}</td>
      <td>${c.arr_station || ''}</td>
      <td>${date}</td>
      <td>${timeRange}</td>
      <td>${c.train_type || 'KTX'}</td>
      <td>${seatMap[c.seat_type] || '전체'}</td>
      <td>
        <button class="btn btn-sm btn-secondary" onclick="openConfigModal(${i})">편집</button>
        <button class="btn btn-sm btn-danger" onclick="deleteConfig(${i})">삭제</button>
      </td>
    </tr>`;
  });
  html += '</tbody></table>';
  wrap.innerHTML = html;
}

// 날짜 변환 (YYYYMMDD <-> YYYY-MM-DD)
function toInputDate(s) {
  if (!s || s.length !== 8) return '';
  return s.slice(0,4) + '-' + s.slice(4,6) + '-' + s.slice(6,8);
}
function fromInputDate(s) {
  return s.replace(/-/g, '');
}
// 시간 변환 (HHMMSS <-> HH:MM)
function toInputTime(s) {
  if (!s || s.length < 4) return '06:00';
  return s.slice(0,2) + ':' + s.slice(2,4);
}
function fromInputTime(s) {
  return s.replace(/:/g, '') + '00';
}

// 모달 열기
function openConfigModal(idx) {
  editIndex = idx;
  document.getElementById('modal-title').textContent = idx === -1 ? '검색 조건 추가' : '검색 조건 편집';
  const c = idx === -1 ? {} : configs[idx];
  document.getElementById('cfg-dep_station').value = c.dep_station || '';
  document.getElementById('cfg-arr_station').value = c.arr_station || '';
  document.getElementById('cfg-dep_date').value = toInputDate(c.dep_date || '');
  document.getElementById('cfg-dep_time').value = toInputTime(c.dep_time || '060000');
  document.getElementById('cfg-train_type').value = c.train_type || 'KTX';
  document.getElementById('cfg-time_start').value = c.time_start || '';
  document.getElementById('cfg-time_end').value = c.time_end || '';
  document.getElementById('cfg-seat_type').value = c.seat_type || 'any';
  document.getElementById('config-modal').classList.add('active');
}

function closeConfigModal() {
  document.getElementById('config-modal').classList.remove('active');
}

// config 저장
async function saveConfig() {
  const c = {
    dep_station: document.getElementById('cfg-dep_station').value.trim(),
    arr_station: document.getElementById('cfg-arr_station').value.trim(),
    dep_date: fromInputDate(document.getElementById('cfg-dep_date').value),
    dep_time: fromInputTime(document.getElementById('cfg-dep_time').value),
    train_type: document.getElementById('cfg-train_type').value,
    time_start: document.getElementById('cfg-time_start').value || null,
    time_end: document.getElementById('cfg-time_end').value || null,
    seat_type: document.getElementById('cfg-seat_type').value,
  };
  if (!c.dep_station || !c.arr_station || !c.dep_date) {
    showToast('출발역, 도착역, 날짜는 필수입니다', 'error');
    return;
  }
  if (editIndex === -1) {
    configs.push(c);
  } else {
    configs[editIndex] = c;
  }
  await fetch('/api/configs', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(configs) });
  closeConfigModal();
  renderConfigs();
  showToast('검색 조건이 저장되었습니다');
}

// config 삭제
async function deleteConfig(idx) {
  if (!confirm(`검색 조건 #${idx+1}을 삭제하시겠습니까?`)) return;
  configs.splice(idx, 1);
  await fetch('/api/configs', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(configs) });
  renderConfigs();
  showToast('삭제되었습니다');
}

// 예매 실행
let eventSource = null;

async function runScript() {
  const res = await fetch('/api/run', { method: 'POST' });
  const data = await res.json();
  if (!data.ok) {
    showToast(data.error, 'error');
    return;
  }
  setRunningUI(true);
  startLogStream();
}

async function stopScript() {
  await fetch('/api/stop', { method: 'POST' });
  showToast('중지 요청을 보냈습니다');
}

function setRunningUI(running) {
  document.getElementById('btn-run').style.display = running ? 'none' : '';
  document.getElementById('btn-stop').style.display = running ? '' : 'none';
  const dot = document.getElementById('status-dot');
  dot.className = 'status-dot ' + (running ? 'running' : 'stopped');
}

function startLogStream() {
  const logArea = document.getElementById('log-area');
  logArea.innerHTML = '';
  if (eventSource) eventSource.close();
  eventSource = new EventSource('/api/log');
  eventSource.onmessage = (e) => {
    if (e.data === '[END]') {
      eventSource.close();
      eventSource = null;
      setRunningUI(false);
      return;
    }
    const line = document.createElement('div');
    line.className = 'log-line';
    if (e.data.includes('[시스템]')) line.className += ' system';
    else if (e.data.includes('성공')) line.className += ' success';
    else if (e.data.includes('실패') || e.data.includes('오류')) line.className += ' error';
    line.textContent = e.data;
    logArea.appendChild(line);
    logArea.scrollTop = logArea.scrollHeight;
  };
  eventSource.onerror = () => {
    eventSource.close();
    eventSource = null;
    setRunningUI(false);
  };
}

// 상태 폴링 (페이지 새로고침 대응)
async function checkStatus() {
  const res = await fetch('/api/status');
  const data = await res.json();
  setRunningUI(data.running);
  if (data.running) startLogStream();
}

// 초기화
initTimeSelects();
loadEnv();
loadConfigs();
checkStatus();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    import webbrowser

    port = 5000
    # 서버 시작 후 브라우저 오픈
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    print(f"웹 UI 서버 시작: http://127.0.0.1:{port}")
    print("종료하려면 Ctrl+C를 누르세요.")
    app.run(host="127.0.0.1", port=port, debug=False)
