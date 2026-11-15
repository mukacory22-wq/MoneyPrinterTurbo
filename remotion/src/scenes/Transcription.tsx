import React from 'react';
import {interpolate, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {Panel3D} from '../fx/Panel3D';
import {actionFrame} from '../lib/actions';
import {clamp, progress} from '../lib/anim';
import {AppIconBadge} from '../lib/icons';
import {theme} from '../theme';
import type {SceneProps} from '../types';

export const schema = z.strictObject({
  title: z.string(),
  sender: z.string(),
  duration_seconds: z.number().int(),
  text: z.string(),
  highlight: z.string().default(''),
});
type Props = z.infer<typeof schema>;

const BARS = 56;
const fmt = (s: number): string => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

/** Áudio sendo transcrito: a onda avança e o texto é digitado junto. */
export const Transcription: React.FC<SceneProps<Props>> = ({props, actions, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const playAt = actionFrame(actions, 'play') ?? 8;
  const length = Math.max(12, Math.min(props.duration_seconds * fps, durationInFrames - playAt - 24));
  const t = interpolate(frame, [playAt, playAt + length], [0, 1], clamp);
  const chars = Math.floor(props.text.length * t);
  const playing = t > 0 && t < 1;

  const shown = props.text.slice(0, chars);
  const mark = progress(frame, fps, actionFrame(actions, 'highlight'), 12);
  const at = props.highlight ? props.text.indexOf(props.highlight) : -1;
  const parts: React.ReactNode[] =
    at < 0 || mark <= 0
      ? [shown]
      : [
          shown.slice(0, at),
          <span key="h" style={{background: `rgba(76,141,255,${0.75 * mark})`, borderRadius: 6, padding: '2px 4px', margin: '0 -4px'}}>
            {shown.slice(at, at + props.highlight.length)}
          </span>,
          shown.slice(at + props.highlight.length),
        ];

  return (
    <Panel3D width={920} padding={34}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 26}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 14, fontSize: 27, fontWeight: 700}}>
          <AppIconBadge icon="mic" size={40} />
          {props.title}
        </div>
        <div style={{fontSize: 21, color: theme.textDim}}>{props.sender}</div>
      </div>
      <div style={{display: 'flex', alignItems: 'center', gap: 20, marginBottom: 26}}>
        <div style={{width: 64, height: 64, borderRadius: '50%', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0}}>
          <svg viewBox="0 0 24 24" width={30} height={30}>
            {playing ? <path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" fill="#111" /> : <path d="M8 4.5v15l12-7.5z" fill="#111" />}
          </svg>
        </div>
        <div style={{flex: 1, display: 'flex', alignItems: 'center', gap: 5, height: 70}}>
          {Array.from({length: BARS}).map((_, i) => {
            const h = 0.2 + 0.8 * random(`w${i}`) * (0.5 + 0.5 * Math.sin((i / BARS) * Math.PI));
            const near = playing && Math.abs(i / BARS - t) < 0.04;
            return (
              <div key={i} style={{flex: 1, height: `${h * 100 * (near ? 1.25 : 1)}%`, borderRadius: 3, background: i / BARS <= t ? '#fff' : 'rgba(255,255,255,0.28)'}} />
            );
          })}
        </div>
        <div style={{fontSize: 24, fontWeight: 600, fontVariantNumeric: 'tabular-nums', width: 70, textAlign: 'right'}}>
          {fmt(t * props.duration_seconds)}
        </div>
      </div>
      <div style={{minHeight: 300, boxSizing: 'border-box', padding: 28, borderRadius: 18, background: 'rgba(0,0,0,0.28)', border: `1.5px solid ${theme.border}`, fontSize: 33, lineHeight: 1.4, fontWeight: 500}}>
        {chars > 0 ? '“' : ''}
        {parts}
        {t >= 1 ? '”' : <span style={{display: 'inline-block', width: 3, height: 36, background: '#fff', verticalAlign: 'text-bottom', marginLeft: 2, opacity: Math.floor(frame / 8) % 2 ? 1 : 0.3}} />}
      </div>
    </Panel3D>
  );
};
