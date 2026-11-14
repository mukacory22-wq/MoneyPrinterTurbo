import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {theme} from '../theme';

type Props = {
  children: React.ReactNode;
  width?: number;
  tiltDeg?: number;
  paper?: boolean;
  bare?: boolean; // sem cartão (o filho desenha a própria moldura, ex.: celular)
  padding?: number;
  style?: React.CSSProperties;
};

/** Cartão flutuante com leve inclinação 3D e deriva lenta. */
export const Panel3D: React.FC<Props> = ({
  children, width = 900, tiltDeg = 6, paper = false, bare = false, padding = 36, style,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const drift = Math.sin((t * 2 * Math.PI) / 6);
  const rotateY = drift * 1.5;
  const rotateX = tiltDeg * 0.5 + Math.cos((t * 2 * Math.PI) / 7) * 0.6;

  const card: React.CSSProperties = bare
    ? {}
    : {
        background: paper
          ? `linear-gradient(180deg, #F6F3EA 0%, ${theme.paper} 100%)`
          : `linear-gradient(180deg, ${theme.panelRaised} 0%, ${theme.panel} 100%)`,
        color: paper ? theme.ink : theme.text,
        border: `1.5px solid ${paper ? 'rgba(255,255,255,0.6)' : theme.border}`,
        borderRadius: theme.radius,
        boxShadow: paper
          ? '0 60px 120px rgba(0,0,0,0.65), 0 0 90px rgba(255,255,255,0.08)'
          : '0 60px 120px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.06)',
        padding,
      };

  return (
    <div style={{perspective: 1600}}>
      <div
        style={{
          width,
          boxSizing: 'border-box',
          fontFamily: theme.sans,
          transform: `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`,
          transformStyle: 'preserve-3d',
          ...card,
          ...style,
        }}
      >
        {children}
      </div>
    </div>
  );
};
