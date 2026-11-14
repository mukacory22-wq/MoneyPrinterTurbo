import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export const PHONE = {width: 570, height: 970, radius: 84, bezel: 12} as const;

/** Moldura de celular com inclinação 3D, ilha dinâmica e reflexo. */
export const Phone: React.FC<{children: React.ReactNode; background?: string}> = ({
  children, background = '#0B0C0F',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const rotateY = -7 + Math.sin((t * 2 * Math.PI) / 6) * 2.5;
  const rotateX = 3 + Math.cos((t * 2 * Math.PI) / 7) * 0.8;
  const inner = PHONE.radius - PHONE.bezel;
  return (
    <div style={{perspective: 1700}}>
      <div
        style={{
          width: PHONE.width,
          height: PHONE.height,
          boxSizing: 'border-box',
          padding: PHONE.bezel,
          borderRadius: PHONE.radius,
          background: 'linear-gradient(145deg, #3A3D44 0%, #1B1D21 35%, #101114 100%)',
          boxShadow:
            '0 70px 130px rgba(0,0,0,0.75), 0 0 0 1.5px rgba(255,255,255,0.14), inset 0 0 0 2px rgba(0,0,0,0.6)',
          transform: `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`,
          transformStyle: 'preserve-3d',
          position: 'relative',
        }}
      >
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: '100%',
            borderRadius: inner,
            overflow: 'hidden',
            background,
          }}
        >
          {children}
          {/* ilha dinâmica */}
          <div
            style={{
              position: 'absolute',
              top: 18,
              left: '50%',
              width: 150,
              height: 42,
              marginLeft: -75,
              borderRadius: 21,
              background: '#000',
            }}
          />
          {/* reflexo do vidro */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background:
                'linear-gradient(115deg, rgba(255,255,255,0.09) 0%, rgba(255,255,255,0) 28%, rgba(255,255,255,0) 100%)',
              pointerEvents: 'none',
            }}
          />
        </div>
      </div>
    </div>
  );
};
