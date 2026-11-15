import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {Panel3D} from '../fx/Panel3D';
import {actionFrame} from '../lib/actions';
import {progress} from '../lib/anim';
import {theme} from '../theme';
import type {SceneProps} from '../types';

export const schema = z.strictObject({
  query: z.string(),
  results: z.array(
    z.strictObject({
      id: z.string().min(1),
      name: z.string(),
      meta: z.string().default(''),
      status: z.string().default(''),
      tone: z.enum(['bad', 'good', 'neutral']).default('neutral'),
      button: z.string().default(''),
    }),
  ),
});
type Props = z.infer<typeof schema>;

const TONE = {bad: '#FF6B61', good: '#3DDC84', neutral: theme.textDim} as const;
const FRAMES_PER_CHAR = 2;

/** Busca sendo digitada + mini mapa + lista de resultados. */
export const SearchResults: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const typeAt = actionFrame(actions, 'type');
  const chars =
    typeAt === null
      ? props.query.length
      : Math.max(0, Math.min(props.query.length, Math.floor((frame - typeAt) / FRAMES_PER_CHAR)));
  const typing = typeAt !== null && frame >= typeAt && chars < props.query.length;
  const cursor = typing || Math.floor(frame / 15) % 2 === 0;

  return (
    <Panel3D width={920} padding={0} style={{overflow: 'hidden'}}>
      <div style={{padding: '26px 28px 0'}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 14, height: 62, borderRadius: 31, padding: '0 24px', background: 'rgba(255,255,255,0.08)', fontSize: 27}}>
          <svg viewBox="0 0 24 24" width={28} height={28}>
            <circle cx="11" cy="11" r="6.5" fill="none" stroke={theme.textDim} strokeWidth={2.2} />
            <path d="M16 16l4.5 4.5" stroke={theme.textDim} strokeWidth={2.2} strokeLinecap="round" />
          </svg>
          <span>{props.query.slice(0, chars)}</span>
          <span style={{width: 2.5, height: 30, background: '#fff', opacity: cursor ? 1 : 0, marginLeft: -8}} />
        </div>
      </div>
      {/* mini mapa estilizado */}
      <svg viewBox="0 0 920 170" width={920} height={170} style={{display: 'block', marginTop: 20, background: '#1B1E22'}}>
        <path d="M-10 120 C200 60 380 150 560 90 S860 40 940 70" stroke="#2C3036" strokeWidth={26} fill="none" />
        <path d="M180 -10 L250 180M610 -10 L560 180M-10 40 L940 20" stroke="#2C3036" strokeWidth={14} fill="none" />
        <rect x={690} y={84} width={150} height={70} rx={8} fill="#1F3B2A" />
        {[[300, 62, '#FF5A52'], [470, 96, '#9AA0A6'], [742, 70, '#FF5A52']].map(([x, y, c], i) => (
          <g key={i} transform={`translate(${x} ${y})`}>
            <path d="M0 22C-9 10 -12 4 -12 -2a12 12 0 0 1 24 0c0 6 -3 12 -12 24z" fill={c as string} />
            <circle r={4.5} cy={-2} fill="#16181C" />
          </g>
        ))}
      </svg>
      <div style={{padding: '18px 28px 26px', display: 'flex', flexDirection: 'column', gap: 12}}>
        {props.results.map((r) => {
          const lit = progress(frame, fps, actionFrame(actions, 'highlight', r.id), 12);
          return (
            <div
              key={r.id}
              style={{
                display: 'flex', alignItems: 'center', gap: 18, padding: '16px 18px', borderRadius: 18,
                background: `rgba(255,255,255,${0.04 + 0.05 * lit})`,
                border: `2px solid rgba(255,255,255,${0.06 + 0.8 * lit})`,
                transform: `scale(${1 + 0.02 * lit})`,
              }}
            >
              <div style={{width: 54, height: 54, borderRadius: '50%', background: 'rgba(255,255,255,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, fontWeight: 700}}>
                {r.name.trim().charAt(0).toUpperCase()}
              </div>
              <div style={{flex: 1}}>
                <div style={{fontSize: 26, fontWeight: 700}}>{r.name}</div>
                {r.meta ? <div style={{fontSize: 19, color: theme.textDim}}>{r.meta}</div> : null}
                {r.status ? <div style={{fontSize: 20, fontWeight: 600, color: TONE[r.tone]}}>{r.status}</div> : null}
              </div>
              {r.button ? (
                <div style={{padding: '10px 24px', borderRadius: 14, background: '#fff', color: '#111', fontSize: 22, fontWeight: 700, transform: `scale(${1 + 0.08 * Math.sin(lit * Math.PI)})`}}>
                  {r.button}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </Panel3D>
  );
};
