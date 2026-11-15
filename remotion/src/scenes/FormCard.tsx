import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {Panel3D} from '../fx/Panel3D';
import {actionFrame} from '../lib/actions';
import {clamp, progress} from '../lib/anim';
import {theme} from '../theme';
import type {SceneProps} from '../types';

const labelValue = z.strictObject({label: z.string(), value: z.string()});
export const schema = z.strictObject({
  title: z.string(),
  subtitle: z.string().default(''),
  fields: z.array(labelValue),
  section: z.string().default(''),
  options: z.array(z.strictObject({id: z.string().min(1), title: z.string(), subtitle: z.string().default('')})),
});
type Props = z.infer<typeof schema>;

const WRITE_FRAMES = 16;
const INK = 'rgba(22,24,28,0.55)';

/** Ficha em papel: campos manuscritos e opções marcáveis. */
export const FormCard: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const writeAt = actionFrame(actions, 'write');

  return (
    <Panel3D width={880} padding={40} paper>
      <div style={{fontSize: 34, fontWeight: 700, letterSpacing: '-0.02em'}}>{props.title}</div>
      {props.subtitle ? <div style={{fontSize: 20, color: INK, marginTop: 2}}>{props.subtitle}</div> : null}
      <div style={{height: 3, background: theme.ink, margin: '18px 0 20px'}} />

      {props.fields.map((field, i) => {
        const start = writeAt === null ? null : writeAt + i * (WRITE_FRAMES - 4);
        const reveal = start === null ? 1 : interpolate(frame, [start, start + WRITE_FRAMES], [0, 1], clamp);
        return (
          <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: 20, marginBottom: 10}}>
            <div style={{width: 150, fontSize: 21, color: INK}}>{field.label}</div>
            <div style={{flex: 1, borderBottom: '1.5px solid rgba(22,24,28,0.25)', minHeight: 50}}>
              <span style={{display: 'inline-block', fontFamily: theme.hand, fontSize: 40, lineHeight: 1.1, whiteSpace: 'nowrap', clipPath: `inset(-10% ${(1 - reveal) * 100}% -10% 0)`}}>
                {field.value}
              </span>
            </div>
          </div>
        );
      })}

      {props.section ? (
        <div style={{fontSize: 19, fontWeight: 700, letterSpacing: '0.12em', color: INK, margin: '26px 0 12px', textTransform: 'uppercase'}}>
          {props.section}
        </div>
      ) : null}
      {props.options.map((option) => {
        const t = progress(frame, fps, actionFrame(actions, 'check', option.id), 12);
        return (
          <div key={option.id} style={{display: 'flex', alignItems: 'center', gap: 18, padding: '12px 14px', borderRadius: 12, background: `rgba(22,24,28,${0.08 * t})`, marginBottom: 4}}>
            <div style={{position: 'relative', width: 38, height: 38, border: `3px solid ${theme.ink}`, borderRadius: 7, flexShrink: 0}}>
              <svg viewBox="0 0 40 40" width={52} height={52} style={{position: 'absolute', left: -6, top: -14, overflow: 'visible'}}>
                <path d="M7 22l9 10L36 4" fill="none" stroke={theme.ink} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round"
                  strokeDasharray={60} strokeDashoffset={60 * (1 - t)} />
              </svg>
            </div>
            <div>
              <div style={{fontSize: 27, fontWeight: 700}}>{option.title}</div>
              {option.subtitle ? <div style={{fontSize: 19, color: INK}}>{option.subtitle}</div> : null}
            </div>
          </div>
        );
      })}
    </Panel3D>
  );
};
