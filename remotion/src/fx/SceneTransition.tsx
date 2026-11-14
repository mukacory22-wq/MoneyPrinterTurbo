import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {clamp} from '../lib/anim';

export const ENTER_FRAMES = 10;
export const EXIT_FRAMES = 12;
/** Quadros em que a cena continua visível por cima da seguinte (fusão). */
export const EXIT_OVERLAP = 6;

type Props = {
  durationInFrames: number; // duração própria da cena (sem a sobreposição)
  enter: boolean;
  exit: boolean;
  children: React.ReactNode;
};

/** Entrada e saída com desfoque + escala (fusão entre cenas). */
export const SceneTransition: React.FC<Props> = ({durationInFrames, enter, exit, children}) => {
  const frame = useCurrentFrame();
  const ease = Easing.bezier(0.22, 1, 0.36, 1);
  const inT = enter ? interpolate(frame, [0, ENTER_FRAMES], [0, 1], {...clamp, easing: ease}) : 1;
  const exitStart = durationInFrames + EXIT_OVERLAP - EXIT_FRAMES;
  const outT = exit
    ? interpolate(frame, [exitStart, exitStart + EXIT_FRAMES], [0, 1], {
        ...clamp,
        easing: Easing.in(Easing.cubic),
      })
    : 0;

  const opacity = inT * (1 - outT);
  const blur = (1 - inT) * 14 + outT * 14;
  const scale = (0.94 + 0.06 * inT) * (1 + 0.07 * outT);

  return (
    <AbsoluteFill
      style={{
        opacity,
        filter: blur > 0.05 ? `blur(${blur}px)` : undefined,
        transform: `scale(${scale})`,
        transformOrigin: '50% 38%',
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
