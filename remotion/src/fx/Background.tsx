import React from 'react';
import {AbsoluteFill, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {theme} from '../theme';

const PARTICLES = 34;

/** Fundo fixo: spotlight, piso em grade com perspectiva e partículas desfocadas. */
export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const t = frame / fps;

  return (
    <AbsoluteFill style={{backgroundColor: theme.bg, overflow: 'hidden'}}>
      {/* foco de luz atrás do painel */}
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(ellipse 62% 34% at 50% 36%, rgba(255,255,255,0.085) 0%, rgba(255,255,255,0.03) 45%, rgba(255,255,255,0) 75%)',
        }}
      />
      {/* piso em grade */}
      <div
        style={{
          position: 'absolute',
          left: -width,
          width: width * 3,
          top: height * 0.56,
          height: height * 0.9,
          transform: 'perspective(900px) rotateX(64deg)',
          transformOrigin: '50% 0%',
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.075) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.075) 2px, transparent 2px)',
          backgroundSize: '180px 180px',
          backgroundPosition: `0px ${(t * 14) % 180}px`,
          maskImage: 'linear-gradient(to bottom, transparent 0%, black 22%, black 60%, transparent 100%)',
          WebkitMaskImage:
            'linear-gradient(to bottom, transparent 0%, black 22%, black 60%, transparent 100%)',
        }}
      />
      {/* partículas */}
      {Array.from({length: PARTICLES}).map((_, i) => {
        const size = 10 + random(`s${i}`) * 34;
        const speed = 6 + random(`v${i}`) * 14;
        const x = random(`x${i}`) * width + Math.sin(t * 0.3 + i) * 18;
        const span = height + 200;
        const y = (((random(`y${i}`) * span - t * speed) % span) + span) % span - 100;
        const twinkle = 0.55 + 0.45 * Math.sin(t * (0.5 + random(`t${i}`)) + i * 1.7);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: size,
              height: size,
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.9)',
              opacity: (0.03 + random(`o${i}`) * 0.07) * twinkle,
              filter: `blur(${3 + random(`b${i}`) * 7}px)`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/** Escurecimento dos cantos; fica por cima de tudo. */
export const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      background:
        'radial-gradient(ellipse 85% 70% at 50% 42%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)',
    }}
  />
);
