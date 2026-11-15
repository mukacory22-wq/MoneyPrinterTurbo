import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {Panel3D} from '../fx/Panel3D';
import {revealFrame} from '../lib/actions';
import {progress} from '../lib/anim';
import {AppIconBadge} from '../lib/icons';
import {theme} from '../theme';
import {appIconSchema, type SceneProps} from '../types';

export const schema = z.strictObject({
  account: z.strictObject({name: z.string(), subtitle: z.string().default('')}),
  title: z.string(),
  steps: z.array(z.strictObject({id: z.string().min(1), icon: appIconSchema, label: z.string()})),
  comments: z.array(z.strictObject({id: z.string().min(1), user: z.string(), keyword: z.string()})),
  count_label: z.string().default(''),
});
type Props = z.infer<typeof schema>;

/** Post de rede social: etapas que acendem e comentários chegando com a palavra-chave. */
export const SocialPost: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <Panel3D width={880} padding={30}>
      <div style={{display: 'flex', alignItems: 'center', gap: 16, marginBottom: 22}}>
        <div style={{width: 60, height: 60, borderRadius: '50%', background: 'linear-gradient(135deg, #5B616B, #2B2E33)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 27, fontWeight: 700}}>
          {props.account.name.trim().charAt(0).toUpperCase()}
        </div>
        <div style={{flex: 1}}>
          <div style={{fontSize: 25, fontWeight: 700}}>{props.account.name}</div>
          {props.account.subtitle ? <div style={{fontSize: 19, color: theme.textDim}}>{props.account.subtitle}</div> : null}
        </div>
      </div>
      <div style={{fontSize: 30, fontWeight: 700, marginBottom: 18}}>{props.title}</div>
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12}}>
        {props.steps.map((step, i) => {
          const at = revealFrame(actions, step.id);
          const t = at === null ? 1 : progress(frame, fps, at, 12);
          return (
            <div key={step.id} style={{display: 'flex', alignItems: 'center', gap: 14, padding: '14px 16px', borderRadius: 16, background: `rgba(255,255,255,${0.035 + 0.045 * t})`, border: `1.5px solid ${theme.border}`, opacity: 0.35 + 0.65 * t}}>
              <div style={{fontSize: 19, color: theme.textFaint, width: 16}}>{i + 1}</div>
              <AppIconBadge icon={step.icon} size={42} dim={1 - t} />
              <div style={{fontSize: 24, fontWeight: 700}}>{step.label}</div>
            </div>
          );
        })}
      </div>
      {props.count_label ? <div style={{fontSize: 20, color: theme.textDim, margin: '18px 0 6px', textAlign: 'right'}}>{props.count_label}</div> : null}
      <div style={{borderTop: `1.5px solid ${theme.border}`, marginTop: 10, paddingTop: 14}}>
        {props.comments.map((comment) => {
          const at = revealFrame(actions, comment.id);
          const t = at === null ? 1 : progress(frame, fps, at, 12);
          if (t <= 0) return null;
          return (
            <div key={comment.id} style={{display: 'flex', alignItems: 'center', gap: 14, height: 62 * t, opacity: t, transform: `translateY(${(1 - t) * 20}px)`, overflow: 'hidden'}}>
              <div style={{width: 42, height: 42, borderRadius: '50%', background: 'rgba(255,255,255,0.14)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 19, fontWeight: 700, flexShrink: 0}}>
                {comment.user.trim().charAt(0).toUpperCase()}
              </div>
              <div style={{fontSize: 21, color: theme.textDim}}>{comment.user}</div>
              <div style={{padding: '4px 12px', borderRadius: 8, background: '#fff', color: '#111', fontSize: 21, fontWeight: 800, letterSpacing: '0.03em'}}>{comment.keyword}</div>
            </div>
          );
        })}
      </div>
    </Panel3D>
  );
};
