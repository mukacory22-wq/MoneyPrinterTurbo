import {interpolate, spring} from 'remotion';

export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

/** Progresso 0→1 com mola a partir de `start` (0 antes; 0 se start for null). */
export const progress = (
  frame: number,
  fps: number,
  start: number | null,
  durationInFrames = 12,
): number => {
  if (start === null || frame < start) return 0;
  return spring({
    frame: frame - start,
    fps,
    durationInFrames,
    config: {damping: 200, stiffness: 180, mass: 0.6},
  });
};

/** Progresso linear 0→1 entre dois quadros. */
export const linear = (frame: number, from: number, to: number): number =>
  interpolate(frame, [from, Math.max(to, from + 1)], [0, 1], clamp);

export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

export const dbToGain = (db: number): number => Math.pow(10, db / 20);
