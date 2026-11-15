import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {progress} from '../lib/anim';
import {theme} from '../theme';
import type {SceneProps} from '../types';

export const schema = z.strictObject({text: z.string()});
type Props = z.infer<typeof schema>;

/** Frase de impacto, palavra por palavra, para cenas sem painel. */
export const Hook: React.FC<SceneProps<Props>> = ({props}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const words = props.text.split(/\s+/).filter(Boolean);
  // Frases longas diminuem para não invadir a área das legendas.
  const length = props.text.length;
  const fontSize = length <= 16 ? 132 : length <= 28 ? 108 : length <= 44 ? 88 : 72;
  return (
    <div
      style={{
        width: 900,
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'center',
        columnGap: 28,
        rowGap: 6,
        fontFamily: theme.sans,
        fontWeight: 700,
        fontSize,
        lineHeight: 1.05,
        letterSpacing: '-0.045em',
        color: theme.text,
        textAlign: 'center',
        textShadow: '0 0 80px rgba(255,255,255,0.28)',
      }}
    >
      {words.map((word, i) => {
        const t = progress(frame, fps, 4 + i * 5, 16);
        const upper = word.length > 2 && word === word.toUpperCase();
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              opacity: t,
              transform: `translateY(${(1 - t) * 40}px) scale(${0.9 + 0.1 * t})`,
              filter: t < 0.98 ? `blur(${(1 - t) * 10}px)` : undefined,
              ...(upper
                ? {fontFamily: theme.serif, fontStyle: 'italic', fontWeight: 400, letterSpacing: '0'}
                : {}),
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};
