/**
 * Web Audio API — synthetic alert sounds.
 * No external audio files needed.
 */

let audioCtx: AudioContext | null = null;

function getCtx(): AudioContext {
  if (!audioCtx) {
    audioCtx = new AudioContext();
  }
  return audioCtx;
}

function playTone(
  frequency: number,
  duration: number,
  type: OscillatorType = "sine",
  volume = 0.4
) {
  const ctx = getCtx();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.type = type;
  osc.frequency.setValueAtTime(frequency, ctx.currentTime);

  gain.gain.setValueAtTime(volume, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.start();
  osc.stop(ctx.currentTime + duration);
}

/** 1 short beep — for "elevated" level */
export function playElevatedAlert() {
  playTone(880, 0.3, "sine", 0.35);
}

/** 2 rapid beeps — for "critical" level */
export function playCriticalAlert() {
  playTone(1046, 0.25, "square", 0.3);
  setTimeout(() => playTone(1046, 0.25, "square", 0.3), 300);
}

/** 3-tone siren — for "crisis" level */
export function playCrisisAlert() {
  playTone(1200, 0.3, "sawtooth", 0.35);
  setTimeout(() => playTone(1500, 0.3, "sawtooth", 0.35), 350);
  setTimeout(() => playTone(1800, 0.4, "sawtooth", 0.35), 700);
}

/** Play alert sound based on escalation level */
export function playAlertForLevel(level: string) {
  switch (level) {
    case "elevated":
      playElevatedAlert();
      break;
    case "critical":
      playCriticalAlert();
      break;
    case "crisis":
      playCrisisAlert();
      break;
  }
}
