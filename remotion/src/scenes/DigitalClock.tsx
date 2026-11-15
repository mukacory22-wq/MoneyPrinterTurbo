import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {z} from 'zod';
import {actionFrame} from '../lib/actions';
import {clamp} from '../lib/anim';
import {theme} from '../theme';
import type {SceneProps} from '../types';

export const schema = z.strictObject({
  time_from: z.string(),
  time_to: z.string().nullable().default(null),
  footer_left: z.string().default(''),
  footer_right: z.string().default(''),
});
type Props = z.infer<typeof schema>;

// segmentos: a(topo) b(dir. sup.) c(dir. inf.) d(base) e(esq. inf.) f(esq. sup.) g(meio)
const DIGITS: Record<string, string> = {
  '0': 'abcdef', '1': 'bc', '2': 'abdeg', '3': 'abcdg', '4': 'bcfg',
  '5': 'acdfg', '6': 'acdefg', '7': 'abc', '8': 'abcdefg', '9': 'abcdfg',
};
const W = 120;
const H = 220;
const T = 22;
const SEGMENTS: Record<string, [number, number, number, number]> = {
  a: [T, 0, W - 2 * T, T], g: [T, (H - T) / 2, W - 2 * T, T], d: [T, H - T, W - 2 * T, T],
  f: [0, T, T, (H - 3 * T) / 2], b: [W - T, T, T, (H - 3 * T) / 2],
  e: [0, (H + T) / 2, T, (H - 3 * T) / 2], c: [W - T, (H + T) / 2, T, (H - 3 * T) / 2],
};

const Digit: React.FC<{char: string; glow: number}> = ({char, glow}) => {
  const on = DIGITS[char] ?? '';
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{overflow: 'visible'}}>
      {Object.entries(SEGMENTS).map(([name, [x, y, w, h]]) => (
        <rect key={name} x={x} y={y} width={w} height={h} rx={8}
          fill={on.includes(name) ? '#fff' : 'rgba(255,255,255,0.05)'}
          style={on.includes(name) ? {filter: `drop-shadow(0 0 ${14 * glow}px rgba(255,255,255,0.85))`} : undefined} />
      ))}
    </svg>
  );
};

/** Relógio despertador digital com dígitos de sete segmentos. */
export const DigitalClock: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const setAt = props.time_to ? actionFrame(actions, 'set') : null;
  const switched = setAt !== null && frame >= setAt + 3;
  const time = switched && props.time_to ? props.time_to : props.time_from;
  // piscada na troca de hora
  const flicker = setAt === null ? 1 : interpolate(frame, [setAt, setAt + 3, setAt + 8], [1, 0.15, 1], clamp);
  const colon = Math.floor(frame / 15) % 2 === 0 ? 1 : 0.25;

  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', fontFamily: theme.sans, filter: 'drop-shadow(0 60px 90px rgba(0,0,0,0.8))'}}>
      <div style={{display: 'flex', gap: 300, marginBottom: -6}}>
        <div style={{width: 90, height: 22, borderRadius: '10px 10px 0 0', background: '#3A3D44'}} />
        <div style={{width: 90, height: 22, borderRadius: '10px 10px 0 0', background: '#3A3D44'}} />
      </div>
      <div style={{width: 760, boxSizing: 'border-box', padding: 34, borderRadius: 46, background: 'linear-gradient(180deg, #3B3E45 0%, #26282D 100%)', border: '2px solid rgba(255,255,255,0.1)'}}>
        <div style={{background: '#050506', borderRadius: 24, padding: '54px 30px 44px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 22, opacity: flicker}}>
          {time.split('').map((char, i) =>
            char === ':' ? (
              <div key={i} style={{display: 'flex', flexDirection: 'column', gap: 54, opacity: colon}}>
                <div style={{width: 24, height: 24, borderRadius: 6, background: '#fff'}} />
                <div style={{width: 24, height: 24, borderRadius: 6, background: '#fff'}} />
              </div>
            ) : (
              <Digit key={i} char={char} glow={flicker} />
            ),
          )}
        </div>
        <div style={{display: 'flex', justifyContent: 'space-between', marginTop: 18, padding: '0 10px', fontSize: 21, fontWeight: 600, letterSpacing: '0.08em', color: 'rgba(255,255,255,0.45)', textTransform: 'uppercase'}}>
          <span>{props.footer_left}</span>
          <span>{props.footer_right}</span>
        </div>
      </div>
      <div style={{width: 860, height: 150, marginTop: -4, borderRadius: 10, background: 'linear-gradient(180deg, #6B5D49 0%, #4A3F31 100%)', border: '1px solid rgba(255,255,255,0.08)'}} />
    </div>
  );
};
