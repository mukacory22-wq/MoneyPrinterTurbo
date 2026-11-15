import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {Panel3D} from '../fx/Panel3D';
import {actionFrame} from '../lib/actions';
import {progress} from '../lib/anim';
import {theme} from '../theme';
import type {SceneProps} from '../types';

export const schema = z.strictObject({
  title: z.string(),
  badge: z.string().default(''),
  bars: z.array(z.strictObject({id: z.string().min(1), label: z.string(), value: z.number()})),
});
type Props = z.infer<typeof schema>;

const HEIGHT = 420;

/** Gráfico de barras que cresce; uma barra pode ganhar destaque. */
export const BarChart: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const growAt = actionFrame(actions, 'grow') ?? 6;
  const max = Math.max(...props.bars.map((b) => b.value), 1);
  const highlightIndex = props.bars.findIndex((b) => actionFrame(actions, 'highlight', b.id) !== null);
  const highlight = highlightIndex < 0 ? 0 : progress(frame, fps, actionFrame(actions, 'highlight', props.bars[highlightIndex].id), 14);

  return (
    <Panel3D width={900} padding={34}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 26}}>
        <div style={{fontSize: 28, fontWeight: 700}}>{props.title}</div>
        {props.badge ? (
          <div style={{padding: '8px 16px', borderRadius: 12, background: 'rgba(255,255,255,0.1)', fontSize: 20, fontWeight: 600, opacity: highlightIndex < 0 ? 1 : highlight}}>{props.badge}</div>
        ) : null}
      </div>
      <div style={{display: 'flex', alignItems: 'flex-end', gap: 18, height: HEIGHT + 44}}>
        {props.bars.map((bar, i) => {
          const t = progress(frame, fps, growAt + i * 3, 20);
          const mine = i === highlightIndex;
          const shade = mine ? 0.3 + 0.7 * highlight : 0.3 - 0.12 * highlight;
          return (
            <div key={bar.id} style={{flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10}}>
              <div style={{fontSize: 24, fontWeight: 700, opacity: t}}>{Math.round(bar.value * t)}</div>
              <div style={{width: '100%', height: Math.max(4, (bar.value / max) * HEIGHT * t), borderRadius: 10, background: `rgba(255,255,255,${shade})`, boxShadow: mine ? `0 0 ${50 * highlight}px rgba(255,255,255,${0.35 * highlight})` : undefined}} />
            </div>
          );
        })}
      </div>
      <div style={{display: 'flex', gap: 18, marginTop: 12}}>
        {props.bars.map((bar) => (
          <div key={bar.id} style={{flex: 1, textAlign: 'center', fontSize: 21, color: theme.textDim}}>{bar.label}</div>
        ))}
      </div>
    </Panel3D>
  );
};
