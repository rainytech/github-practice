import json, os, sys, subprocess
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

proj = sys.argv[1]
only = sys.argv[2:]  # optional scene names
lines = json.load(open(f"{proj}/voice-script/lines.json"))
k = Kokoro("/root/.cache/hyperframes/tts/models/kokoro-v1.0.onnx", "/root/.cache/hyperframes/tts/voices/voices-v1.0.bin")
tpath = f"{proj}/voice-script/timing.json"
timing = json.load(open(tpath)) if os.path.exists(tpath) else {}
tmp = "/tmp/claude-0/-home-user-github-practice/92ad5459-ff0d-592f-af47-f461d632c9be/scratchpad/tts"
os.makedirs(tmp, exist_ok=True)
GAP = 0.5
for scene, ls in lines.items():
    if only and scene not in only:
        continue
    parts, marks, t, sr = [], [], 0.0, 24000
    for i, line in enumerate(ls):
        a, sr = k.create(line, voice="hm_omega", speed=1.0, lang="en-us")
        nz = np.where(np.abs(a) > 0.003)[0]
        a = a[max(nz[0] - 600, 0): nz[-1] + 1200] if len(nz) else a
        d = len(a) / sr
        marks.append([round(t, 2), round(d, 2)])
        parts.append(a)
        t += d
        if i < len(ls) - 1:
            parts.append(np.zeros(int(GAP * sr), dtype=a.dtype)); t += GAP
    raw = f"{tmp}/{scene}_raw.wav"
    sf.write(raw, np.concatenate(parts), sr)
    out = f"{proj}/assets/voice/{scene}.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", out], check=True)
    timing[scene] = {"dur": round(t, 2), "lines": marks}
    print(scene, round(t, 2), flush=True)
json.dump(timing, open(tpath, "w"), indent=1)
