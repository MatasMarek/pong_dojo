"""Avatar voices: Windows' built-in Czech voice (Microsoft Jakub), offline.

1. render: one PowerShell process (System.Speech) speaks a batch of lines into WAV
   files in .voice_cache/ (see dojo/paths.py), in a background thread. The repository
   ships the cache pre-rendered, so the stock lines play on any system; new lines (own
   taunts) need Windows with PowerShell 7 and the Czech voice, elsewhere they stay silent.
2. shape: each avatar's voice profile reshapes the WAV in pure Python - pitch, growl
   (overdrive + rumble), echo, robot (ring modulation) - and boosts it into a shout.
3. play: returns the sound's length and a mouth envelope (loudness per 1/30 s), so the
   avatar's mouth moves with the words.
Lines that are not rendered yet are simply silent (the taunt bubble still shows).
"""
import array
import hashlib
import json
import math
import os
import subprocess
import threading
import wave

import pygame

from dojo import paths

CACHE = paths.VOICE_CACHE
RATE = 22050
VOICE_NAME = 'Microsoft Jakub'

PS_SCRIPT = r'''
param([string]$job)
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
try { $s.SelectVoice('%s') } catch { Write-Error 'Czech voice not available'; exit 3 }
if ($s.Voice.Culture.Name -ne 'cs-CZ') { Write-Error ('wrong voice: ' + $s.Voice.Name); exit 3 }
$s.Rate = 3
$s.Volume = 100
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(%d, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$items = Get-Content -Raw -Encoding UTF8 $job | ConvertFrom-Json
foreach ($it in $items) {
  $tmp = $it.path + '.part'
  $s.SetOutputToWaveFile($tmp, $fmt)
  $s.Speak($it.text)
  $s.SetOutputToNull()
  Move-Item -Force $tmp $it.path
}
''' % (VOICE_NAME, RATE)


def shell():
    import shutil
    return shutil.which('pwsh') or r'C:\Program Files\PowerShell\7\pwsh.exe'


def key(text):
    return hashlib.sha1((text + '|rate3|cs-CZ').encode('utf-8')).hexdigest()[:16]


def wav_path(text):
    return os.path.join(CACHE, key(text) + '.wav')


class Voice:
    def __init__(self):
        self.ok = pygame.mixer.get_init() is not None
        self.out_rate = pygame.mixer.get_init()[0] if self.ok else RATE
        self.stereo = self.ok and pygame.mixer.get_init()[2] == 2
        self.on = True
        self.shaped = {}       # (text, profile) -> (Sound, seconds, envelope)
        self.pending = set()
        self.lock = threading.Lock()
        self.channel = None
        self.last_error = ''

    # --- rendering --------------------------------------------------------------------
    def prepare(self, lines, profiles=()):
        """Render (in the background) every line not yet in the cache, then pre-shape."""
        if not self.ok:
            return
        os.makedirs(CACHE, exist_ok=True)
        todo = [t for t in dict.fromkeys(lines) if t and not os.path.exists(wav_path(t)) and t not in self.pending]
        self.pending.update(todo)
        threading.Thread(target=self._render_then_shape, args=(todo, list(lines), list(profiles)), daemon=True).start()

    def _render_then_shape(self, todo, lines, profiles):
        if todo:
            script = os.path.join(CACHE, 'render.ps1')
            with open(script, 'w', encoding='utf-8-sig') as fh:
                fh.write(PS_SCRIPT)
            job = os.path.join(CACHE, f'job_{threading.get_ident()}.json')
            with open(job, 'w', encoding='utf-8') as fh:
                json.dump([{'text': t, 'path': wav_path(t)} for t in todo], fh, ensure_ascii=False)
            try:
                # PowerShell 7 (pwsh) sees Windows' Czech voice; Windows PowerShell 5.1 does not
                # (it only sees the English desktop voices), so it is not used as a fallback.
                r = subprocess.run([shell(), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                    '-File', script, job], capture_output=True, timeout=600,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                self.last_error = r.stderr.decode('utf-8', 'replace').strip()[:300] if r.returncode else ''
            except (OSError, subprocess.SubprocessError) as exc:
                self.last_error = str(exc)
            finally:
                try:
                    os.remove(job)
                except OSError:
                    pass
            self.pending.difference_update(todo)
        for prof in profiles:
            for t in lines:
                self.get(t, prof)

    # --- shaping ----------------------------------------------------------------------
    def get(self, text, profile):
        k = (text, profile['pitch'], profile['effect'])
        with self.lock:
            if k in self.shaped:
                return self.shaped[k]
        path = wav_path(text)
        if not os.path.exists(path):
            return None
        try:
            with wave.open(path, 'rb') as w:
                raw = w.readframes(w.getnframes())
                src_rate = w.getframerate()
        except (OSError, wave.Error, EOFError):
            return None
        a = array.array('h')
        a.frombytes(raw)
        samples = shape([x / 32768.0 for x in a], src_rate, self.out_rate, profile)
        env = envelope(samples, self.out_rate)
        out = array.array('h', (int(max(-1.0, min(1.0, x)) * 32767) for x in samples))
        if self.stereo:
            st = array.array('h')
            for v in out:
                st.extend((v, v))
            out = st
        try:
            snd = pygame.mixer.Sound(buffer=out.tobytes())
        except pygame.error:
            return None
        item = (snd, len(samples) / self.out_rate, env)
        with self.lock:
            self.shaped[k] = item
        return item

    def say(self, text, profile):
        """Start the shout. Returns (seconds, envelope) or None if not ready / muted."""
        if not (self.ok and self.on):
            return None
        item = self.get(text, profile)
        if item is None:
            return None
        snd, secs, env = item
        if self.channel is not None:
            self.channel.stop()
        self.channel = snd.play()
        return secs, env


def shape(x, src_rate, out_rate, profile):
    pitch = float(profile.get('pitch', 1.0))
    effect = profile.get('effect', 'žádný')
    # pitch + resample in one go (pitch < 1 = deeper and slower)
    step = pitch * src_rate / out_rate
    n = int(len(x) / step)
    y = []
    for i in range(n):
        p = i * step
        j = int(p)
        f = p - j
        a = x[j]
        b = x[j + 1] if j + 1 < len(x) else a
        y.append(a + (b - a) * f)
    # shout: compress + boost
    peak = max((abs(v) for v in y), default=1.0) or 1.0
    gain = 0.9 / peak
    if effect == 'vrčení':
        drive = 4.0
        y = [math.tanh(v * gain * drive) * 0.8 for v in y]
        rumble = [0.18 * math.sin(2 * math.pi * 38 * i / out_rate) for i in range(len(y))]
        y = [v * (0.75 + r) for v, r in zip(y, rumble)]
    elif effect == 'robot':
        y = [math.tanh(v * gain * 1.5) * math.sin(2 * math.pi * 95 * i / out_rate) for i, v in enumerate(y)]
    else:
        y = [math.tanh(v * gain * 2.2) * 0.85 for v in y]
    if effect == 'ozvěna':
        d1, d2 = int(0.11 * out_rate), int(0.23 * out_rate)
        y = y + [0.0] * d2
        for i in range(len(y) - 1, -1, -1):
            if i >= d1:
                y[i] += 0.42 * y[i - d1]
            if i >= d2:
                y[i] += 0.22 * y[i - d2]
        peak = max(abs(v) for v in y) or 1.0
        y = [v * 0.92 / peak for v in y]
    return y


def envelope(y, rate, fps=30):
    hop = max(1, rate // fps)
    env = []
    for i in range(0, len(y), hop):
        chunk = y[i:i + hop]
        env.append(math.sqrt(sum(v * v for v in chunk) / len(chunk)) if chunk else 0.0)
    top = max(env, default=1.0) or 1.0
    return [min(1.0, e / top * 1.3) for e in env]
