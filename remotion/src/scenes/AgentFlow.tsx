import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {Panel3D} from '../fx/Panel3D';
import {actionFrame} from '../lib/actions';
import {clamp, progress} from '../lib/anim';
import {AppIconBadge} from '../lib/icons';
import {theme} from '../theme';
import {appIconSchema, type SceneProps} from '../types';

export const schema = z.strictObject({
  title: z.string(),
  toggle_off: z.string(),
  toggle_on: z.string(),
  steps: z.array(
    z.strictObject({
      id: z.string().min(1),
      icon: appIconSchema,
      title: z.string(),
      subtitle: z.string().default(''),
    }),
  ),
  dial_label: z.string().default('24h'),
  counter: z.strictObject({label: z.string(), start: z.number().int(), end: z.number().int()}),
});
type Props = z.infer<typeof schema>;

const Dial: React.FC<{label: string; on: number; angle: number}> = ({label, on, angle}) => {
  const size = 230;
  const c = size / 2;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {Array.from({length: 48}).map((_, i) => {
        const a = (i / 48) * Math.PI * 2;
        const r1 = c - 6;
        const r2 = c - (i % 4 === 0 ? 20 : 13);
        return (
          <line
            key={i}
            x1={c + Math.sin(a) * r1} y1={c - Math.cos(a) * r1}
            x2={c + Math.sin(a) * r2} y2={c - Math.cos(a) * r2}
            stroke="#fff" strokeOpacity={0.18 + 0.4 * on} strokeWidth={2}
          />
        );
      })}
      <circle cx={c} cy={c} r={c - 30} fill="none" stroke="#fff" strokeOpacity={0.12 + 0.88 * on} strokeWidth={2 + 5 * on} />
      <line
        x1={c} y1={c}
        x2={c + Math.sin(angle) * (c - 48)} y2={c - Math.cos(angle) * (c - 48)}
        stroke="#fff" strokeWidth={5} strokeLinecap="round"
      />
      <circle cx={c} cy={c} r={7} fill="#fff" />
      <text x={c} y={c + 52} textAnchor="middle" fill="#fff" fontFamily={theme.sans} fontWeight={700} fontSize={30}>
        {label}
      </text>
    </svg>
  );
};

/** Fluxo do agente: etapas que acendem, interruptor, mostrador e contador. */
export const AgentFlow: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const toggleAt = actionFrame(actions, 'toggle');
  const on = progress(frame, fps, toggleAt, 14);
  const countAt = actionFrame(actions, 'count');
  const countT = countAt === null ? 0 : interpolate(frame, [countAt, countAt + 24], [0, 1], clamp);
  const value = Math.round(props.counter.start + (props.counter.end - props.counter.start) * (1 - Math.pow(1 - countT, 3)));

  const activations = props.steps.map((s) => actionFrame(actions, 'activate', s.id));
  const latest = activations.reduce<number>(
    (best, at, i) => (at !== null && frame >= at && (best < 0 || at >= (activations[best] ?? -1)) ? i : best),
    -1,
  );
  const dialAngle = toggleAt !== null && frame >= toggleAt ? ((frame - toggleAt) / fps) * 1.6 : 0;

  return (
    <Panel3D width={920} padding={34}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 26}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 14, fontSize: 27, fontWeight: 700}}>
          <AppIconBadge icon="ai" size={40} />
          {props.title}
        </div>
        <div style={{display: 'flex', alignItems: 'center', gap: 14, fontSize: 22, fontWeight: 600, color: on > 0.5 ? theme.text : theme.textDim}}>
          {on > 0.5 ? props.toggle_on : props.toggle_off}
          <div
            style={{
              width: 68, height: 38, borderRadius: 19, padding: 4, boxSizing: 'border-box',
              background: `rgba(${Math.round(90 - 53 * on)}, ${Math.round(94 + 117 * on)}, ${Math.round(102 - 0 * on)}, 1)`,
            }}
          >
            <div style={{width: 30, height: 30, borderRadius: '50%', background: '#fff', transform: `translateX(${30 * on}px)`, boxShadow: '0 2px 6px rgba(0,0,0,0.4)'}} />
          </div>
        </div>
      </div>

      <div style={{display: 'flex', gap: 28}}>
        <div style={{flex: 1, display: 'flex', flexDirection: 'column', gap: 14}}>
          {props.steps.map((step, i) => {
            const lit = Math.max(progress(frame, fps, activations[i], 12), on);
            const active = i === latest ? progress(frame, fps, activations[i], 12) : 0;
            return (
              <div
                key={step.id}
                style={{
                  display: 'flex', alignItems: 'center', gap: 18, padding: '16px 18px', borderRadius: 18,
                  background: `rgba(255,255,255,${0.035 + 0.035 * lit})`,
                  border: `2px solid rgba(255,255,255,${0.06 + 0.84 * active})`,
                  opacity: 0.38 + 0.62 * lit,
                  transform: `scale(${1 + 0.025 * active})`,
                }}
              >
                <AppIconBadge icon={step.icon} size={50} dim={1 - lit} />
                <div>
                  <div style={{fontSize: 25, fontWeight: 700}}>{step.title}</div>
                  {step.subtitle ? <div style={{fontSize: 19, color: theme.textDim}}>{step.subtitle}</div> : null}
                </div>
              </div>
            );
          })}
        </div>

        <div style={{width: 250, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20}}>
          <Dial label={props.dial_label} on={on} angle={dialAngle} />
          <div style={{width: '100%', boxSizing: 'border-box', padding: '16px 20px', borderRadius: 18, background: 'rgba(255,255,255,0.05)', border: `1.5px solid ${theme.border}`}}>
            <div style={{fontSize: 19, color: theme.textDim}}>{props.counter.label}</div>
            <div style={{fontSize: 58, fontWeight: 700, letterSpacing: '-0.03em', lineHeight: 1.1}}>{value}</div>
          </div>
        </div>
      </div>
    </Panel3D>
  );
};
