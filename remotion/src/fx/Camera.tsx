import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {clamp} from '../lib/anim';

type Props = {
  mode: 'push_in' | 'drift' | 'static';
  durationInFrames: number;
  children: React.ReactNode;
};

/** Movimento de câmera contínuo da cena. */
export const Camera: React.FC<Props> = ({mode, durationInFrames, children}) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [0, durationInFrames], [0, 1], clamp);
  const scale = mode === 'push_in' ? 1 + 0.06 * t : 1;
  const x = mode === 'drift' ? -20 + 40 * t : 0;
  return (
    <AbsoluteFill
      style={{transform: `translateX(${x}px) scale(${scale})`, transformOrigin: '50% 38%'}}
    >
      {children}
    </AbsoluteFill>
  );
};
