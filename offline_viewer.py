#!/usr/bin/env python3
"""Serve a dependency-free, live Raspberry Shake UDP DATACAST viewer locally."""

from __future__ import annotations

import argparse
import json
import queue
import socket
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


DEFAULT_UDP_PORT = 8888
DEFAULT_HTTP_PORT = 8765


def parse_packet(packet: bytes) -> tuple[str, float, list[int]]:
    """Parse a Raspberry Shake DATACAST packet without evaluating its text."""
    text = packet.decode("ascii", errors="strict").strip()
    if not (text.startswith("{") and text.endswith("}")):
        raise ValueError("packet is not enclosed in braces")
    fields = [field.strip() for field in text[1:-1].split(",")]
    if len(fields) < 3:
        raise ValueError("packet has no samples")
    channel = fields[0].strip("'\"")
    if not channel:
        raise ValueError("packet has no channel")
    timestamp = float(fields[1])
    samples = [int(value) for value in fields[2:]]
    if not samples:
        raise ValueError("packet has no samples")
    return channel, timestamp, samples


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Raspberry Shake — Offline Live Stream</title>
<style>
  * { box-sizing: border-box }
  html, body { height:100%; margin:0 }
  body { background:#101418; color:#d8e5ed; font:15px ui-monospace,Menlo,monospace; display:grid; grid-template-rows:auto 1fr; overflow:hidden }
  header { background:#192129; padding:9px 14px; display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap }
  .brand, .controls { display:flex; align-items:center; gap:12px; flex-wrap:wrap }
  #state { color:#4dd0e1 }
  button, select { background:#26333d; color:#d8e5ed; border:1px solid #465966; border-radius:5px; padding:7px 10px; font:inherit }
  button:hover, select:hover { border-color:#4dd0e1 }
  button:focus-visible, select:focus-visible { outline:2px solid #4dd0e1; outline-offset:2px }
  button[aria-pressed="true"] { background:#0d6873; border-color:#4dd0e1 }
  select:disabled { opacity:.55 }
  #plots { min-height:0; display:grid; grid-template-rows:1fr }
  #plots.with-spectrogram { grid-template-rows:minmax(180px,1fr) minmax(220px,.8fr) }
  .panel { min-height:0; position:relative }
  #spectrogram-panel { border-top:1px solid #31404b }
  [hidden] { display:none !important }
  canvas { display:block; width:100%; height:100% }
  @media (max-width:700px) {
    header { align-items:flex-start }
    .brand, .controls { width:100%; justify-content:space-between }
    #plots.with-spectrogram { grid-template-rows:minmax(150px,1fr) minmax(190px,1fr) }
  }
</style></head><body>
<header>
  <div class="brand"><span><b>Raspberry Shake</b> · Offline Live Stream</span><span id="state">Waiting for UDP data…</span></div>
  <div class="controls">
    <button id="spectrogram-toggle" type="button" aria-pressed="false">Spectrogram: Off</button>
    <label for="spectrogram-channel">Channel</label>
    <select id="spectrogram-channel" disabled aria-label="Spectrogram channel"><option>Waiting…</option></select>
  </div>
</header>
<main id="plots">
  <section class="panel" aria-label="Live seismic waveforms"><canvas id="plot" role="img" aria-label="Live seismic waveforms"></canvas></section>
  <section class="panel" id="spectrogram-panel" aria-label="Live spectrogram" hidden><canvas id="spectrogram" role="img" aria-label="Live seismic spectrogram"></canvas></section>
</main>
<script>
const KEEP_MS=120000, SPEC_SECONDS=30, FFT_SIZE=128, HOP_SIZE=32;
const traces=new Map(), plotCanvas=document.querySelector('#plot'), plotCtx=plotCanvas.getContext('2d');
const specCanvas=document.querySelector('#spectrogram'), specCtx=specCanvas.getContext('2d');
const plots=document.querySelector('#plots'), specPanel=document.querySelector('#spectrogram-panel');
const state=document.querySelector('#state'), toggle=document.querySelector('#spectrogram-toggle'), channelSelect=document.querySelector('#spectrogram-channel');
let packets=0, bad=0, last=0, spectrogramOn=false, userSelectedChannel=false, lastSpecDraw=0;

function resizeCanvas(canvas, context) {
  const d=devicePixelRatio||1, width=Math.max(1,canvas.clientWidth), height=Math.max(1,canvas.clientHeight);
  const pixelWidth=Math.round(width*d), pixelHeight=Math.round(height*d);
  if (canvas.width!==pixelWidth || canvas.height!==pixelHeight) { canvas.width=pixelWidth; canvas.height=pixelHeight; }
  context.setTransform(d,0,0,d,0,0);
  return [width,height];
}

function updateChannels() {
  const selected=channelSelect.value, names=[...traces.keys()].sort();
  channelSelect.replaceChildren(...names.map(name=>new Option(name,name)));
  channelSelect.disabled=!names.length;
  if (names.includes(selected)) channelSelect.value=selected;
  else {
    const vertical=names.find(name=>name.endsWith('Z'));
    channelSelect.value=vertical||names[0]||'';
  }
}

function add(packet) {
  packets++; last=performance.now();
  let trace=traces.get(packet.channel);
  if (!trace) {
    trace={points:[], lastStamp:null, lastCount:0, rate:null};
    traces.set(packet.channel,trace); updateChannels();
  }
  const packetDelta=trace.lastStamp===null ? 0 : packet.timestamp-trace.lastStamp;
  if (packetDelta>0 && packetDelta<10 && trace.lastCount>0) {
    const measured=trace.lastCount/packetDelta;
    if (measured>=1 && measured<=1000) trace.rate=trace.rate===null ? measured : trace.rate*.8+measured*.2;
  }
  const dt=trace.rate ? 1/trace.rate : 0;
  packet.samples.forEach((value,index)=>trace.points.push([packet.timestamp+index*dt,value]));
  trace.lastStamp=packet.timestamp; trace.lastCount=packet.samples.length;
  const newest=packet.timestamp;
  while(trace.points.length && trace.points[0][0]<newest-KEEP_MS/1000) trace.points.shift();
}

const events=new EventSource('/events');
events.onmessage=event=>{ try { add(JSON.parse(event.data)); } catch (_) { bad++; } };
events.onerror=()=>state.textContent='Connection to local viewer lost; reconnecting…';

toggle.addEventListener('click',()=>{
  spectrogramOn=!spectrogramOn;
  toggle.setAttribute('aria-pressed',String(spectrogramOn));
  toggle.textContent=`Spectrogram: ${spectrogramOn?'On':'Off'}`;
  specPanel.hidden=!spectrogramOn;
  plots.classList.toggle('with-spectrogram',spectrogramOn);
  lastSpecDraw=0;
});
channelSelect.addEventListener('change',()=>{ userSelectedChannel=true; lastSpecDraw=0; });

function drawWaveforms() {
  const [width,height]=resizeCanvas(plotCanvas,plotCtx), names=[...traces.keys()].sort(), now=performance.now();
  plotCtx.clearRect(0,0,width,height);
  const age=last ? ((now-last)/1000).toFixed(1) : '–';
  state.textContent=last&&now-last<3000 ? `Receiving data · ${packets} packets` : `Waiting for data · last packet ${age}s ago`;
  if (!names.length) {
    plotCtx.fillStyle='#91a4b0'; plotCtx.font='18px ui-monospace,monospace';
    plotCtx.fillText('Listening for Raspberry Shake UDP DATACAST on port 8888…',24,48); return;
  }
  if (!userSelectedChannel && names.some(name=>name.endsWith('Z')) && !channelSelect.value.endsWith('Z')) channelSelect.value=names.find(name=>name.endsWith('Z'));
  const newest=Math.max(...names.map(name=>{const points=traces.get(name).points;return points.length?points[points.length-1][0]:0;}));
  const start=newest-KEEP_MS/1000, row=height/names.length;
  names.forEach((name,index)=>{
    const top=index*row, mid=top+row/2, points=traces.get(name).points.filter(point=>point[0]>=start);
    plotCtx.strokeStyle='#31404b'; plotCtx.beginPath(); plotCtx.moveTo(0,mid); plotCtx.lineTo(width,mid); plotCtx.stroke();
    plotCtx.fillStyle='#d8e5ed'; plotCtx.font='bold 14px ui-monospace,monospace'; plotCtx.fillText(name,12,top+20);
    plotCtx.fillStyle='#91a4b0'; plotCtx.font='12px ui-monospace,monospace'; plotCtx.fillText(`${points.length} samples · 120 seconds`,12,top+38);
    if (!points.length) return;
    const center=points.reduce((sum,point)=>sum+point[1],0)/points.length;
    const amplitude=Math.max(1,...points.map(point=>Math.abs(point[1]-center))), scale=row*.40/amplitude;
    plotCtx.strokeStyle='#4dd0e1'; plotCtx.lineWidth=1.2; plotCtx.beginPath();
    points.forEach((point,j)=>{const x=(point[0]-start)/(KEEP_MS/1000)*width, y=mid-(point[1]-center)*scale;j?plotCtx.lineTo(x,y):plotCtx.moveTo(x,y);});
    plotCtx.stroke();
  });
}

function fftMagnitudes(values) {
  const n=values.length, real=new Float64Array(n), imag=new Float64Array(n);
  const mean=values.reduce((sum,value)=>sum+value,0)/n;
  for (let i=0;i<n;i++) real[i]=(values[i]-mean)*(.5-.5*Math.cos(2*Math.PI*i/(n-1)));
  for (let i=1,j=0;i<n;i++) {
    let bit=n>>1; for (;j&bit;bit>>=1) j^=bit; j^=bit;
    if (i<j) { [real[i],real[j]]=[real[j],real[i]]; [imag[i],imag[j]]=[imag[j],imag[i]]; }
  }
  for (let len=2;len<=n;len<<=1) {
    const angle=-2*Math.PI/len;
    for (let start=0;start<n;start+=len) for (let offset=0;offset<len/2;offset++) {
      const c=Math.cos(angle*offset), s=Math.sin(angle*offset), even=start+offset, odd=even+len/2;
      const tr=real[odd]*c-imag[odd]*s, ti=real[odd]*s+imag[odd]*c;
      real[odd]=real[even]-tr; imag[odd]=imag[even]-ti; real[even]+=tr; imag[even]+=ti;
    }
  }
  const result=[];
  for (let i=0;i<=n/2;i++) result.push(20*Math.log10(Math.hypot(real[i],imag[i])+1e-9));
  return result;
}

function spectrumColor(value) {
  const stops=[[8,8,18],[48,19,92],[128,36,126],[221,76,55],[252,230,90]], scaled=Math.max(0,Math.min(.999,value))*(stops.length-1);
  const index=Math.floor(scaled), mix=scaled-index, a=stops[index], b=stops[index+1];
  return `rgb(${Math.round(a[0]+(b[0]-a[0])*mix)},${Math.round(a[1]+(b[1]-a[1])*mix)},${Math.round(a[2]+(b[2]-a[2])*mix)})`;
}

function drawSpectrogram() {
  const [width,height]=resizeCanvas(specCanvas,specCtx), channel=channelSelect.value, trace=traces.get(channel);
  specCtx.clearRect(0,0,width,height); specCtx.fillStyle='#101418'; specCtx.fillRect(0,0,width,height);
  const left=58,right=18,top=30,bottom=32,plotWidth=Math.max(1,width-left-right),plotHeight=Math.max(1,height-top-bottom);
  specCtx.fillStyle='#d8e5ed'; specCtx.font='bold 13px ui-monospace,monospace';
  specCtx.fillText(channel ? `${channel} spectrogram` : 'Spectrogram',left,19);
  if (!trace || !trace.rate || trace.points.length<FFT_SIZE) {
    specCtx.fillStyle='#91a4b0'; specCtx.font='13px ui-monospace,monospace'; specCtx.fillText(`Collecting at least ${FFT_SIZE} samples…`,left,top+28); return;
  }
  const newest=trace.points[trace.points.length-1][0], cutoff=newest-SPEC_SECONDS;
  const samples=trace.points.filter(point=>point[0]>=cutoff).map(point=>point[1]);
  if (samples.length<FFT_SIZE) return;
  const frames=[];
  for (let start=0;start+FFT_SIZE<=samples.length;start+=HOP_SIZE) frames.push(fftMagnitudes(samples.slice(start,start+FFT_SIZE)));
  const peak=Math.max(...frames.flat()), floor=peak-70, cellWidth=plotWidth/frames.length, bins=FFT_SIZE/2+1, cellHeight=plotHeight/(bins-1);
  frames.forEach((frame,xIndex)=>frame.forEach((db,bin)=>{
    const normalized=(db-floor)/(peak-floor), x=left+xIndex*cellWidth, y=top+plotHeight-bin*cellHeight;
    specCtx.fillStyle=spectrumColor(normalized); specCtx.fillRect(x,y-cellHeight,Math.ceil(cellWidth)+.5,Math.ceil(cellHeight)+.5);
  }));
  specCtx.strokeStyle='#667783'; specCtx.lineWidth=1; specCtx.strokeRect(left,top,plotWidth,plotHeight);
  specCtx.fillStyle='#91a4b0'; specCtx.font='11px ui-monospace,monospace';
  const nyquist=trace.rate/2;
  for (let i=0;i<=4;i++) {
    const y=top+plotHeight-i*plotHeight/4, hz=nyquist*i/4;
    specCtx.fillText(`${hz.toFixed(hz<10?1:0)} Hz`,5,y+4);
  }
  for (let i=0;i<=3;i++) {
    const x=left+i*plotWidth/3, seconds=-SPEC_SECONDS+i*SPEC_SECONDS/3;
    specCtx.fillText(`${Math.round(seconds)}s`,Math.max(left,x-12),height-10);
  }
  specCtx.fillStyle='#d8e5ed'; specCtx.fillText(`sample rate ${trace.rate.toFixed(1)} Hz · color: relative power (70 dB range)`,left+130,19);
  specCanvas.setAttribute('aria-label',`${channel} live spectrogram from zero to ${nyquist.toFixed(1)} hertz over the last ${SPEC_SECONDS} seconds`);
}

function draw(now) {
  drawWaveforms();
  if (spectrogramOn && now-lastSpecDraw>350) { drawSpectrogram(); lastSpecDraw=now; }
  requestAnimationFrame(draw);
}
requestAnimationFrame(draw);
</script></body></html>"""


class DemoServer:
    def __init__(self, udp_port: int) -> None:
        self.udp_port = udp_port
        self.events: queue.Queue[dict[str, object]] = queue.Queue(maxsize=500)
        self.running = True
        self.packet_count = 0
        self.bad_packets = 0

    def receive(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", self.udp_port))
        sock.settimeout(0.5)
        while self.running:
            try:
                packet, _address = sock.recvfrom(65535)
                channel, timestamp, samples = parse_packet(packet)
                event = {"channel": channel, "timestamp": timestamp, "samples": samples}
                try:
                    self.events.put_nowait(event)
                except queue.Full:
                    self.events.get_nowait()
                    self.events.put_nowait(event)
                self.packet_count += 1
            except socket.timeout:
                continue
            except (UnicodeDecodeError, ValueError):
                self.bad_packets += 1
        sock.close()


def make_handler(demo: DemoServer):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: object) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
            if self.path == "/":
                content = PAGE.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            elif self.path == "/events":
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                try:
                    while demo.running:
                        try:
                            event = demo.events.get(timeout=10)
                            self.wfile.write(f"data: {json.dumps(event, separators=(',', ':'))}\n\n".encode())
                        except queue.Empty:
                            self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_UDP_PORT, help="UDP port to listen on (default: 8888)")
    parser.add_argument("--http-port", type=int, default=DEFAULT_HTTP_PORT, help="local viewer port (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="do not open the local viewer automatically")
    args = parser.parse_args()
    for label, port in (("UDP", args.port), ("HTTP", args.http_port)):
        if not 1 <= port <= 65535:
            parser.error(f"{label} port must be between 1 and 65535")

    demo = DemoServer(args.port)
    threading.Thread(target=demo.receive, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.http_port), make_handler(demo))
    url = f"http://127.0.0.1:{args.http_port}/"
    print(f"Listening for Raspberry Shake UDP data on port {args.port}.")
    print(f"Live viewer: {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping offline viewer.")
    finally:
        demo.running = False
        server.server_close()


if __name__ == "__main__":
    main()
