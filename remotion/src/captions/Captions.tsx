import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {clamp} from '../lib/anim';
import {theme} from '../theme';
import type {CaptionGroup, RenderProps} from '../types';

type Word = CaptionGroup['words'][number];
type Run = {emphasis: boolean; words: Word[]};

const toRuns = (words: Word[]): Run[] => {
  const runs: Run[] = [];
  for (const word of words) {
    const last = runs[runs.length - 1];
    if (last && last.emphasis && word.emphasis) last.words.push(word);
    else runs.push({emphasis: word.emphasis, words: [word]});
  }
  return runs;
};

const WordSpan: React.FC<{word: Word; frame: number}> = ({word, frame}) => {
  const t = interpolate(frame, [word.frame - 2, word.frame + 5], [0, 1], clamp);
  return (
    <span
      style={{
        display: 'inline-block',
        opacity: 0.26 + 0.74 * t,
        filter: t < 0.98 ? `blur(${(1 - t) * 3}px)` : undefined,
        transform: `translateY(${(1 - t) * 8}px)`,
      }}
    >
      {word.text}
    </span>
  );
};

const Handle: React.FC<{color: string; style: React.CSSProperties}> = ({color, style}) => (
  <span
    style={{position: 'absolute', width: 9, height: 9, background: color, borderRadius: 2, ...style}}
  />
);

/** Legenda palavra a palavra; destaque em serifada itálica com caixa de seleção. */
export const Captions: React.FC<{captions: RenderProps['captions']}> = ({captions}) => {
  const frame = useCurrentFrame();
  if (!captions.enabled) return null;
  const group = captions.groups.find((g) => frame >= g.from && frame < g.to);
  if (!group) return null;

  const color = captions.highlightColor;
  const groupIn = interpolate(frame, [group.from, group.from + 4], [0, 1], clamp);

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          left: 60,
          right: 60,
          top: `${captions.yPercent}%`,
          transform: 'translateY(-50%)',
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          alignItems: 'center',
          columnGap: captions.fontSize * 0.28,
          rowGap: 8,
          fontFamily: theme.sans,
          fontWeight: 500,
          fontSize: captions.fontSize,
          letterSpacing: '-0.02em',
          lineHeight: 1.25,
          color: theme.text,
          textShadow: '0 2px 24px rgba(0,0,0,0.9)',
          opacity: groupIn,
        }}
      >
        {toRuns(group.words).map((run, i) => {
          if (!run.emphasis) return <WordSpan key={i} word={run.words[0]} frame={frame} />;
          const start = run.words[0].frame;
          const box = interpolate(frame, [start - 1, start + 6], [0, 1], clamp);
          return (
            <span
              key={i}
              style={{
                position: 'relative',
                display: 'inline-flex',
                columnGap: captions.fontSize * 0.26,
                padding: '0 12px 4px',
                fontFamily: theme.serif,
                fontStyle: 'italic',
                fontWeight: 400,
                fontSize: captions.fontSize * 1.16,
                letterSpacing: '-0.01em',
              }}
            >
              <span
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: `${color}26`,
                  border: `2px solid ${color}`,
                  opacity: box,
                  transform: `scaleX(${0.6 + 0.4 * box})`,
                  transformOrigin: '0% 50%',
                }}
              >
                <Handle color={color} style={{left: -5, top: -5}} />
                <Handle color={color} style={{right: -5, top: -5}} />
                <Handle color={color} style={{left: -5, bottom: -5}} />
                <Handle color={color} style={{right: -5, bottom: -5}} />
              </span>
              {run.words.map((word, j) => (
                <span key={j} style={{position: 'relative'}}>
                  <WordSpan word={word} frame={frame} />
                </span>
              ))}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
