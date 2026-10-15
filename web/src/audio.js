// Sonido ambiente sintetizado con WebAudio (no hay archivos de audio): rumor de la ciudad, trafico,
// lluvia, viento, truenos, pasos segun el piso, aleteo de palomas, pitos y campanas de la Catedral.
export class SoundScape {
  constructor() {
    this.ctx = null;
    this.muted = false;
  }

  start() {
    if (this.ctx) { this.ctx.resume?.(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = (this.ctx = new AC());
    this.master = ctx.createGain(); this.master.gain.value = this.muted ? 0 : 0.9;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -14; comp.ratio.value = 3;
    this.master.connect(comp).connect(ctx.destination);
    // ruido blanco y marron (2 s y 6 s)
    const white = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const wd = white.getChannelData(0);
    for (let i = 0; i < wd.length; i++) wd[i] = Math.random() * 2 - 1;
    const brown = ctx.createBuffer(1, ctx.sampleRate * 6, ctx.sampleRate);
    const bd = brown.getChannelData(0);
    let last = 0;
    for (let i = 0; i < bd.length; i++) { last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02; bd[i] = last * 3.5; }
    this.white = white; this.brown = brown;
    const loop = (buf, ...nodes) => {
      const s = ctx.createBufferSource(); s.buffer = buf; s.loop = true;
      let n = s;
      for (const x of nodes) n = n.connect(x);
      s.start(0, Math.random() * buf.duration);
      return nodes[nodes.length - 1];
    };
    const filt = (type, f, q = 0.7) => { const b = ctx.createBiquadFilter(); b.type = type; b.frequency.value = f; b.Q.value = q; return b; };
    const gain = (v) => { const g = ctx.createGain(); g.gain.value = v; return g; };
    // ciudad: rumor grave constante
    loop(brown, filt('lowpass', 260), gain(0.22)).connect(this.master);
    // trafico cercano
    this.trafficG = loop(white, filt('bandpass', 230, 0.6), filt('lowpass', 900), gain(0));
    this.trafficG.connect(this.master);
    // lluvia: siseo + golpeteo grave
    this.rainG = loop(white, filt('highpass', 500), filt('lowpass', 7000), gain(0)); this.rainG.connect(this.master);
    this.rainLowG = loop(brown, filt('lowpass', 900), gain(0)); this.rainLowG.connect(this.master);
    // viento con barrido lento
    const wf = filt('bandpass', 380, 1.4);
    const lfo = ctx.createOscillator(); lfo.frequency.value = 0.07;
    const lg = gain(160); lfo.connect(lg).connect(wf.frequency); lfo.start();
    this.windG = loop(white, wf, gain(0)); this.windG.connect(this.master);
    // motor del vehiculo mas cercano
    this.engine = ctx.createOscillator(); this.engine.type = 'sawtooth'; this.engine.frequency.value = 45;
    this.engineG = gain(0);
    this.engine.connect(filt('lowpass', 320)).connect(this.engineG).connect(this.master);
    this.engine.start();
  }

  setMuted(m) {
    this.muted = m;
    if (this.master) this.master.gain.setTargetAtTime(m ? 0 : 0.9, this.ctx.currentTime, 0.1);
  }

  /** niveles continuos (0..1) */
  setLevels({ rain = 0, wind = 0, traffic = 0, engineDist = 1e9, engineSpeed = 0 }) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.rainG.gain.setTargetAtTime(0.32 * rain, t, 0.5);
    this.rainLowG.gain.setTargetAtTime(0.25 * rain, t, 0.5);
    this.windG.gain.setTargetAtTime(0.12 * wind, t, 0.8);
    this.trafficG.gain.setTargetAtTime(0.05 + 0.12 * traffic, t, 0.4);
    const eg = engineDist < 30 ? Math.min(0.12, 1.4 / (engineDist * engineDist + 4)) : 0;
    this.engineG.gain.setTargetAtTime(eg, t, 0.15);
    this.engine.frequency.setTargetAtTime(38 + engineSpeed * 5, t, 0.2);
  }

  burst(buf, { type = 'bandpass', f = 1500, q = 1, vol = 0.3, attack = 0.002, decay = 0.07, when = 0, pan = 0 }) {
    const ctx = this.ctx; if (!ctx) return;
    const t = ctx.currentTime + when;
    const s = ctx.createBufferSource(); s.buffer = buf;
    const b = ctx.createBiquadFilter(); b.type = type; b.frequency.value = f; b.Q.value = q;
    const g = ctx.createGain(); g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(vol, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + attack + decay);
    const p = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    if (p) p.pan.value = Math.max(-1, Math.min(1, pan));
    s.connect(b).connect(g);
    (p ? g.connect(p) : g).connect(this.master);
    s.start(t, Math.random() * (buf.duration - attack - decay - 0.05), attack + decay + 0.05);
  }

  /** paso: surface 'piedra' | 'asfalto' | 'pasto'; wet 0..1 */
  step(run, wet) {
    if (!this.ctx) return;
    this.burst(this.white, { f: run ? 1300 : 1700, q: 1.1, vol: run ? 0.22 : 0.13, decay: run ? 0.06 : 0.08 });
    this.burst(this.brown, { type: 'lowpass', f: 180, vol: run ? 0.5 : 0.3, decay: 0.05 });
    if (wet > 0.3) this.burst(this.white, { type: 'highpass', f: 2800, vol: 0.12 * wet, decay: 0.14, when: 0.01 });
  }

  /** aleteo de palomas al despegar; dist en m, pan -1..1 */
  flutter(dist, pan) {
    if (!this.ctx || dist > 40) return;
    const v = Math.min(0.5, 6 / (dist + 3));
    const n = 7 + ((Math.random() * 6) | 0);
    for (let i = 0; i < n; i++) this.burst(this.white, { f: 900 + Math.random() * 500, q: 0.8, vol: v * (1 - i / n), decay: 0.035, when: i * (0.045 + Math.random() * 0.02), pan });
  }

  thunder(delay) {
    const ctx = this.ctx; if (!ctx) return;
    const t = ctx.currentTime;
    const power = Math.max(0.25, 1 - delay / 5);
    const s = ctx.createBufferSource(); s.buffer = this.brown;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass';
    lp.frequency.setValueAtTime(500, t); lp.frequency.exponentialRampToValueAtTime(70, t + 4);
    const g = ctx.createGain(); g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(1.6 * power, t + 0.08 + delay * 0.05);
    g.gain.exponentialRampToValueAtTime(0.001, t + 5.5);
    s.connect(lp).connect(g).connect(this.master);
    s.start(t, 0, 6);
    if (delay < 1.2) this.burst(this.white, { type: 'highpass', f: 1800, vol: 0.5, decay: 0.25 });
  }

  /** pito de carro (tercera menor), con paneo */
  horn(dist, pan) {
    const ctx = this.ctx; if (!ctx || dist > 60) return;
    const t = ctx.currentTime, v = Math.min(0.18, 4 / (dist + 6));
    const twice = Math.random() < 0.5;
    for (const f of [370, 466]) {
      const o = ctx.createOscillator(); o.type = 'square'; o.frequency.value = f;
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2000;
      const g = ctx.createGain(); g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(v, t + 0.01); g.gain.setValueAtTime(v, t + 0.3); g.gain.linearRampToValueAtTime(0, t + 0.34);
      if (twice) { g.gain.setValueAtTime(0, t + 0.45); g.gain.linearRampToValueAtTime(v, t + 0.46); g.gain.setValueAtTime(v, t + 0.62); g.gain.linearRampToValueAtTime(0, t + 0.66); }
      const p = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
      if (p) p.pan.value = pan;
      o.connect(lp).connect(g);
      (p ? g.connect(p) : g).connect(this.master);
      o.start(t); o.stop(t + 0.8);
    }
  }

  /** campanadas de la Catedral */
  bells(count, dist, pan) {
    const ctx = this.ctx; if (!ctx) return;
    const v = Math.min(0.35, 25 / (dist + 20));
    const parts = [[0.5, 0.35, 7], [1, 1, 5], [1.19, 0.5, 3.5], [1.5, 0.35, 3], [2, 0.3, 2.5], [2.52, 0.18, 1.8], [3.01, 0.1, 1.2]];
    for (let k = 0; k < count; k++) {
      const t = ctx.currentTime + k * 2.4;
      const f0 = 196;
      for (const [r, a, d] of parts) {
        const o = ctx.createOscillator(); o.frequency.value = f0 * r;
        const g = ctx.createGain(); g.gain.setValueAtTime(0, t);
        g.gain.linearRampToValueAtTime(v * a * 0.5, t + 0.005); g.gain.exponentialRampToValueAtTime(0.0001, t + d);
        const p = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
        if (p) p.pan.value = pan;
        o.connect(g); (p ? g.connect(p) : g).connect(this.master);
        o.start(t); o.stop(t + d + 0.1);
      }
    }
  }

  /** arrullo de paloma */
  coo(dist, pan) {
    const ctx = this.ctx; if (!ctx || dist > 15) return;
    const t = ctx.currentTime, v = Math.min(0.06, 0.6 / (dist + 4));
    const o = ctx.createOscillator(); o.type = 'sine';
    o.frequency.setValueAtTime(300, t); o.frequency.linearRampToValueAtTime(380, t + 0.25); o.frequency.linearRampToValueAtTime(290, t + 0.7);
    const trem = ctx.createOscillator(); trem.frequency.value = 22;
    const tg = ctx.createGain(); tg.gain.value = 0.4;
    const g = ctx.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + 0.1); g.gain.linearRampToValueAtTime(0, t + 0.75);
    trem.connect(tg).connect(g.gain);
    const p = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    if (p) p.pan.value = pan;
    o.connect(g); (p ? g.connect(p) : g).connect(this.master);
    o.start(t); trem.start(t); o.stop(t + 0.8); trem.stop(t + 0.8);
  }
}
