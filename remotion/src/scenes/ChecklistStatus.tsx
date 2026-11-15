import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {Panel3D} from '../fx/Panel3D';
import {actionFrame} from '../lib/actions';
import {progress} from '../lib/anim';
import {AppIconBadge, CheckIcon} from '../lib/icons';
import {theme} from '../theme';
import type {SceneProps} from '../types';

export const schema = z.strictObject({
  title: z.string(),
  header_left: z.string().default(''),
  header_right: z.string().default(''),
  items: z.array(
    z.strictObject({
      id: z.string().min(1),
      time: z.string(),
      name: z.string(),
      pending_label: z.string(),
      done_label: z.string(),
    }),
  ),
});
type Props = z.infer<typeof schema>;

/** Lista cujo status muda de pendente para concluído. */
export const ChecklistStatus: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <Panel3D width={900} padding={32}>
      <div style={{display: 'flex', alignItems: 'center', gap: 14, fontSize: 27, fontWeight: 700, marginBottom: 22}}>
        <AppIconBadge icon="bell" size={40} />
        {props.title}
      </div>
      {props.header_left || props.header_right ? (
        <div style={{display: 'flex', alignItems: 'center', gap: 18, marginBottom: 20, fontSize: 22, fontWeight: 600}}>
          <div style={{padding: '10px 18px', borderRadius: 12, background: 'rgba(255,255,255,0.07)'}}>{props.header_left}</div>
          <svg viewBox="0 0 80 20" width={80} height={20}>
            <path d="M78 10H6M14 3L5 10l9 7" fill="none" stroke={theme.textDim} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div style={{padding: '10px 18px', borderRadius: 12, border: '2px solid rgba(255,255,255,0.85)'}}>{props.header_right}</div>
        </div>
      ) : null}
      {props.items.map((item) => {
        const t = progress(frame, fps, actionFrame(actions, 'done', item.id), 12);
        const done = t > 0.4;
        return (
          <div key={item.id} style={{display: 'flex', alignItems: 'center', gap: 20, padding: '18px 20px', marginBottom: 12, borderRadius: 16, background: `rgba(255,255,255,${0.04 + 0.04 * t})`, border: `1.5px solid rgba(255,255,255,${0.06 + 0.2 * t})`}}>
            <div style={{width: 100, fontSize: 26, fontWeight: 700, fontVariantNumeric: 'tabular-nums'}}>{item.time}</div>
            <div style={{flex: 1, fontSize: 25, fontWeight: 500}}>{item.name}</div>
            <div style={{display: 'flex', alignItems: 'center', gap: 12, fontSize: 22, fontWeight: 600, color: done ? theme.text : theme.textDim, transform: `scale(${1 + 0.08 * Math.sin(t * Math.PI)})`}}>
              <div style={{width: 30, height: 30, borderRadius: '50%', background: done ? theme.green : 'rgba(255,255,255,0.14)', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                {done ? <CheckIcon size={19} /> : null}
              </div>
              {done ? item.done_label : item.pending_label}
            </div>
          </div>
        );
      })}
    </Panel3D>
  );
};
