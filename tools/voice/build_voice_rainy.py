"""Build a video's voice-over in Rainy Goodwill's cloned voice (Chatterbox, MIT licence).

Usage:  HF_HUB_OFFLINE=1 /root/clone-venv/bin/python tools/voice/build_voice_rainy.py videos/<project> [scene ...]
Reads   <project>/voice-script/lines.json  ({"scene": ["line", ...], ...})
Writes  <project>/assets/voice/<scene>.wav (0.5 s gaps, loudnorm -14 LUFS, 48 kHz)
        <project>/voice-script/timing.json ({"scene": {"dur": s, "lines": [[start, dur], ...]}})

Reference voice: tools/voice/rainy_ref.wav (NOT in git, for privacy). Make it from the user's
phone recording (Recording_1.m4a, 2:26) when a fresh container lacks it:
    ffmpeg -i Recording_1.m4a -t 22 -af "highpass=f=70,loudnorm=I=-18" -ar 24000 tools/voice/rainy_ref.wav
Setup in a fresh container (~3 min):
    python3.11 -m venv /root/clone-venv && /root/clone-venv/bin/pip install chatterbox-tts
Speed on CPU: about 5 s of work per 1 s of speech; run it in the background.
HF_HUB_OFFLINE=1 after the first download: online the model load can hang on the HF Hub check.
"""
import json, os, subprocess, sys, tempfile
import torch, torchaudio as ta
from chatterbox.tts import ChatterboxTTS

EXAGGERATION = 0.75   # 0.5 = calm, 0.75 = enthusiastic (user asked for more enthusiasm, 25 Nov 2026)
CFG_WEIGHT = 0.4      # lower = livelier pace
GAP = 0.5
REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rainy_ref.wav")

proj = sys.argv[1]
only = sys.argv[2:]
if not os.path.exists(REF):
    sys.exit(f"Missing {REF}: ask the user to upload his voice recording (see the docstring).")
lines = json.load(open(f"{proj}/voice-script/lines.json"))
tpath = f"{proj}/voice-script/timing.json"
timing = json.load(open(tpath)) if os.path.exists(tpath) else {}
torch.manual_seed(7)
m = ChatterboxTTS.from_pretrained(device="cpu")
sr = m.sr
tmp = tempfile.mkdtemp()
os.makedirs(f"{proj}/assets/voice", exist_ok=True)
for scene, ls in lines.items():
    if only and scene not in only:
        continue
    parts, marks, t = [], [], 0.0
    for i, line in enumerate(ls):
        w = m.generate(line, audio_prompt_path=REF, exaggeration=EXAGGERATION, cfg_weight=CFG_WEIGHT)
        a = w[0]
        nz = (a.abs() > 0.003).nonzero()
        if len(nz):
            a = a[max(int(nz[0]) - 600, 0): int(nz[-1]) + 1200]
        d = a.shape[0] / sr
        marks.append([round(t, 2), round(d, 2)])
        parts.append(a)
        t += d
        if i < len(ls) - 1:
            parts.append(torch.zeros(int(GAP * sr)))
            t += GAP
    raw = os.path.join(tmp, f"{scene}.wav")
    ta.save(raw, torch.cat(parts).unsqueeze(0), sr)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af",
                    "highpass=f=70,loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                    f"{proj}/assets/voice/{scene}.wav"], check=True)
    timing[scene] = {"dur": round(t, 2), "lines": marks}
    json.dump(timing, open(tpath, "w"), indent=1)
    print(scene, round(t, 2), flush=True)
