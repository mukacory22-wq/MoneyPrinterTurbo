import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {actionFrame} from '../lib/actions';
import {clamp, progress} from '../lib/anim';
import {CheckIcon} from '../lib/icons';
import {theme} from '../theme';
import type {SceneProps} from '../types';

export const schema = z.strictObject({
  total_seconds: z.number().int(),
  steps: z.array(z.strictObject({id: z.string().min(1), at_seconds: z.number().int(), label: z.string()})),
});
type Props = z.infer<typeof schema>;

const mmss = (seconds: number): string =>
  `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
const short = (seconds: number): string =>
  `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;

const SIZE = 460;

/** Cronômetro analógico + digital; o tempo avança até cada etapa marcada. */
export const Stopwatch: React.FC<SceneProps<Props>> = ({props, actions, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const marks = props.steps
    .map((s) => ({frame: actionFrame(actions, 'mark', s.id), seconds: s.at_seconds}))
    .filter((m): m is {frame: number; seconds: number} => m.frame !== null)
    .sort((a, b) => a.frame - b.frame);
  // Quadros-chave: o ponteiro chega ao tempo de cada etapa no instante da marca.
  const keys: {frame: number; seconds: number}[] = [{frame: 0, seconds: 0}];
  for (const mark of marks) {
    if (mark.frame > keys[keys.length - 1].frame) keys.push(mark);
    else keys[keys.length - 1] = {frame: keys[keys.length - 1].frame, seconds: mark.seconds};
  }
  if (keys.length === 1) keys.push({frame: Math.max(durationInFrames - 10, 1), seconds: props.total_seconds});
  const elapsed = interpolate(frame, keys.map((k) => k.frame), keys.map((k) => k.seconds), clamp);

  const c = SIZE / 2;
  const angle = (elapsed / 60) * Math.PI * 2;
  const hand = c - 74;

  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 34, fontFamily: theme.sans}}>
      <div style={{position: 'relative', width: SIZE, height: SIZE + 70, filter: 'drop-shadow(0 50px 80px rgba(0,0,0,0.75))'}}>
        {/* coroa */}
        <div style={{position: 'absolute', left: c - 34, top: 0, width: 68, height: 40, borderRadius: 10, background: 'linear-gradient(180deg, #D9D9D6, #8E8E8A)'}} />
        <div style={{position: 'absolute', left: c - 18, top: 36, width: 36, height: 40, background: 'linear-gradient(90deg, #8E8E8A, #E6E6E2, #8E8E8A)'}} />
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{position: 'absolute', top: 70}}>
          <defs>
            <linearGradient id="rim" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#F2F2EE" />
              <stop offset="0.5" stopColor="#8D8D89" />
              <stop offset="1" stopColor="#DCDCD8" />
            </linearGradient>
            <radialGradient id="face" cx="0.5" cy="0.4" r="0.7">
              <stop offset="0" stopColor="#FFFFFF" />
              <stop offset="1" stopColor="#DAD7CD" />
            </radialGradient>
          </defs>
          <circle cx={c} cy={c} r={c - 2} fill="url(#rim)" />
          <circle cx={c} cy={c} r={c - 24} fill="url(#face)" />
          {Array.from({length: 60}).map((_, i) => {
            const a = (i / 60) * Math.PI * 2;
            const major = i % 5 === 0;
            const r1 = c - 34;
            const r2 = c - (major ? 56 : 46);
            return (
              <line key={i}
                x1={c + Math.sin(a) * r1} y1={c - Math.cos(a) * r1}
                x2={c + Math.sin(a) * r2} y2={c - Math.cos(a) * r2}
                stroke="#16181C" strokeWidth={major ? 4 : 2} />
            );
          })}
          {Array.from({length: 12}).map((_, i) => {
            const a = (i / 12) * Math.PI * 2;
            const r = c - 86;
            return (
              <text key={i} x={c + Math.sin(a) * r} y={c - Math.cos(a) * r + 11} textAnchor="middle"
                fontFamily={theme.sans} fontWeight={700} fontSize={30} fill="#16181C">
                {i === 0 ? 60 : i * 5}
              </text>
            );
          })}
          <rect x={c - 76} y={c + 44} width={152} height={54} rx={10} fill="#0B0C0F" />
          <text x={c} y={c + 83} textAnchor="middle" fontFamily={theme.sans} fontWeight={700} fontSize={36} fill="#fff"
            style={{fontVariantNumeric: 'tabular-nums'}}>
            {mmss(elapsed)}
          </text>
          <line x1={c - Math.sin(angle) * 34} y1={c + Math.cos(angle) * 34}
            x2={c + Math.sin(angle) * hand} y2={c - Math.cos(angle) * hand}
            stroke="#16181C" strokeWidth={7} strokeLinecap="round" />
          <circle cx={c} cy={c} r={14} fill="#16181C" />
          <circle cx={c} cy={c} r={5} fill="#E9E7DF" />
        </svg>
      </div>

      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, width: 800}}>
        {props.steps.map((step) => {
          const at = actionFrame(actions, 'mark', step.id);
          const t = progress(frame, fps, at, 12);
          return (
            <div
              key={step.id}
              style={{
                display: 'flex', alignItems: 'center', gap: 16, padding: '16px 20px', borderRadius: 16,
                background: `rgba(255,255,255,${0.04 + 0.04 * t})`,
                border: `2px solid rgba(255,255,255,${0.08 + 0.6 * t})`,
                color: theme.text, opacity: 0.45 + 0.55 * t, transform: `scale(${1 + 0.03 * Math.sin(t * Math.PI)})`,
              }}
            >
              <div style={{width: 36, height: 36, borderRadius: '50%', background: t > 0.3 ? theme.green : 'rgba(255,255,255,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                {t > 0.3 ? <CheckIcon size={22} /> : null}
              </div>
              <div style={{fontSize: 26, fontWeight: 700, fontVariantNumeric: 'tabular-nums'}}>{short(step.at_seconds)}</div>
              <div style={{fontSize: 24, color: theme.textDim}}>{step.label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
