import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {Panel3D} from '../fx/Panel3D';
import {actionFrame, revealFrame} from '../lib/actions';
import {clamp, progress} from '../lib/anim';
import {AppIconBadge} from '../lib/icons';
import {theme} from '../theme';
import type {SceneProps} from '../types';

const hhmm = z.string().regex(/^\d{2}:\d{2}$/);
export const schema = z.strictObject({
  title: z.string(),
  date: z.string(),
  hours: z.tuple([z.number().int(), z.number().int()]),
  events: z.array(
    z.strictObject({
      id: z.string().min(1),
      title: z.string(),
      start: hhmm,
      end: hhmm,
      kind: z.enum(['busy', 'free', 'break']).default('busy'),
    }),
  ),
  side: z.strictObject({
    title: z.string(),
    subtitle: z.string().default(''),
    options: z.array(z.strictObject({id: z.string().min(1), label: z.string()})).default([]),
  }),
});
type Props = z.infer<typeof schema>;

const toHours = (value: string): number => {
  const [h, m] = value.split(':').map(Number);
  return h + m / 60;
};

const GRID_HEIGHT = 560;
const SCAN_FRAMES = 30;

/** Agenda do dia: blocos ocupados, varredura de luz e horários livres que surgem. */
export const Calendar: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const [first, last] = props.hours;
  const span = Math.max(last - first, 1);
  const hourPx = GRID_HEIGHT / span;

  const scanAt = actionFrame(actions, 'scan');
  const scanT = scanAt === null ? -1 : interpolate(frame, [scanAt, scanAt + SCAN_FRAMES], [0, 1], clamp);
  const scanning = scanAt !== null && frame >= scanAt && frame <= scanAt + SCAN_FRAMES;

  return (
    <Panel3D width={920} padding={32}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 14, fontSize: 27, fontWeight: 700}}>
          <AppIconBadge icon="calendar" size={40} />
          {props.title}
        </div>
        <div style={{fontSize: 21, color: theme.textDim, fontWeight: 500}}>{props.date}</div>
      </div>

      <div style={{display: 'flex', gap: 22}}>
        {/* grade de horários */}
        <div style={{position: 'relative', flex: 1, height: GRID_HEIGHT}}>
          {Array.from({length: span + 1}).map((_, i) => (
            <div key={i} style={{position: 'absolute', top: i * hourPx, left: 0, right: 0, display: 'flex', alignItems: 'center', transform: 'translateY(-50%)'}}>
              <div style={{width: 64, fontSize: 17, color: theme.textFaint, fontVariantNumeric: 'tabular-nums'}}>
                {String(first + i).padStart(2, '0')}:00
              </div>
              <div style={{flex: 1, height: 1, background: 'rgba(255,255,255,0.06)'}} />
            </div>
          ))}
          {props.events.map((event) => {
            const top = (toHours(event.start) - first) * hourPx;
            const height = (toHours(event.end) - toHours(event.start)) * hourPx;
            const at = revealFrame(actions, event.id);
            const t = at === null ? 1 : progress(frame, fps, at, 14);
            if (t <= 0) return null;
            const free = event.kind === 'free';
            const style: React.CSSProperties = free
              ? {border: '2.5px dashed rgba(255,255,255,0.95)', background: 'rgba(255,255,255,0.1)', color: '#fff', boxShadow: `0 0 ${30 * t}px rgba(255,255,255,0.25)`}
              : event.kind === 'break'
                ? {background: 'repeating-linear-gradient(135deg, rgba(255,255,255,0.05) 0 8px, rgba(255,255,255,0.015) 8px 16px)', color: theme.textDim}
                : {background: 'rgba(255,255,255,0.07)', borderLeft: `5px solid ${theme.blue}`, color: theme.text};
            return (
              <div
                key={event.id}
                style={{
                  position: 'absolute', left: 72, right: 0, top: top + 3, height: height - 6, boxSizing: 'border-box',
                  borderRadius: 12, padding: '0 16px', display: 'flex', alignItems: 'center',
                  fontSize: 20, fontWeight: 600, opacity: t, transform: `scale(${0.94 + 0.06 * t})`, ...style,
                }}
              >
                {event.title}
              </div>
            );
          })}
          {scanning ? (
            <div
              style={{
                position: 'absolute', left: 60, right: -6, top: scanT * GRID_HEIGHT, height: 5, borderRadius: 3,
                background: '#fff', boxShadow: '0 0 28px 8px rgba(255,255,255,0.55)',
                opacity: interpolate(scanT, [0, 0.1, 0.9, 1], [0, 1, 1, 0]),
              }}
            />
          ) : null}
        </div>

        {/* painel lateral */}
        <div style={{width: 250, boxSizing: 'border-box', padding: 20, borderRadius: 18, background: 'rgba(255,255,255,0.04)', border: `1.5px solid ${theme.border}`}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 10, fontSize: 22, fontWeight: 700}}>
            <AppIconBadge icon="ai" size={32} />
            {props.side.title}
          </div>
          {props.side.subtitle ? (
            <div style={{fontSize: 18, color: theme.textDim, margin: '8px 0 18px', lineHeight: 1.3}}>{props.side.subtitle}</div>
          ) : null}
          {props.side.options.map((option, i) => {
            const at = revealFrame(actions, option.id);
            const t = at === null ? 1 : progress(frame, fps, at + i * 3, 14);
            return (
              <div
                key={option.id}
                style={{
                  display: 'flex', alignItems: 'center', gap: 14, padding: '14px 16px', marginBottom: 12, borderRadius: 14,
                  background: 'rgba(255,255,255,0.07)', border: `1.5px solid rgba(255,255,255,0.14)`,
                  opacity: t, transform: `translateX(${(1 - t) * 24}px)`,
                }}
              >
                <div style={{width: 32, height: 32, borderRadius: '50%', background: '#fff', color: '#111', fontSize: 18, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                  {i + 1}
                </div>
                <div style={{fontSize: 30, fontWeight: 700}}>{option.label}</div>
              </div>
            );
          })}
        </div>
      </div>
    </Panel3D>
  );
};
