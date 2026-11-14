import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {Phone} from '../fx/Phone';
import {actionFrame, revealFrame} from '../lib/actions';
import {clamp, progress} from '../lib/anim';
import {AppIconBadge} from '../lib/icons';
import {theme} from '../theme';
import {appIconSchema, type SceneProps} from '../types';

export const schema = z.strictObject({
  time: z.string(),
  date: z.string(),
  alarm: z
    .strictObject({id: z.string().min(1), label: z.string(), sub: z.string().default('')})
    .nullable()
    .default(null),
  notifications: z
    .array(
      z.strictObject({
        id: z.string().min(1),
        app: appIconSchema,
        title: z.string(),
        body: z.string(),
        meta: z.string().default(''),
      }),
    )
    .default([]),
});
type Props = z.infer<typeof schema>;

const card: React.CSSProperties = {
  background: 'rgba(58,60,66,0.72)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 28,
  padding: '18px 20px',
  boxShadow: '0 12px 30px rgba(0,0,0,0.35)',
};

/** Tela de bloqueio: hora, alarme opcional e notificações que vão empilhando. */
export const PhoneLockScreen: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const pressAt = props.alarm ? actionFrame(actions, 'press', props.alarm.id) : null;
  const press = pressAt === null ? 0 : interpolate(frame, [pressAt, pressAt + 4, pressAt + 9], [0, 1, 0], clamp);
  const dismissed = pressAt === null ? 0 : progress(frame, fps, pressAt + 8, 14);

  return (
    <Phone background="linear-gradient(180deg, #2B2D33 0%, #17181C 55%, #0C0D10 100%)">
      <div style={{fontFamily: theme.sans, color: theme.text, padding: '96px 26px 0'}}>
        <div style={{textAlign: 'center', fontSize: 25, fontWeight: 500, color: 'rgba(255,255,255,0.78)'}}>
          {props.date}
        </div>
        <div
          style={{
            textAlign: 'center',
            fontSize: 148,
            fontWeight: 600,
            letterSpacing: '-0.04em',
            lineHeight: 1.05,
            marginBottom: 26,
            textShadow: '0 0 60px rgba(255,255,255,0.18)',
          }}
        >
          {props.time}
        </div>

        {props.alarm ? (
          <div
            style={{
              ...card,
              opacity: 1 - dismissed,
              transform: `scale(${1 - 0.06 * dismissed})`,
              maxHeight: interpolate(dismissed, [0, 1], [240, 0]),
              marginBottom: interpolate(dismissed, [0, 1], [16, 0]),
              paddingTop: interpolate(dismissed, [0, 1], [18, 0]),
              paddingBottom: interpolate(dismissed, [0, 1], [18, 0]),
              overflow: 'hidden',
            }}
          >
            <div style={{display: 'flex', gap: 14, alignItems: 'center', marginBottom: 14}}>
              <AppIconBadge icon="alarm" size={50} />
              <div>
                <div style={{fontSize: 24, fontWeight: 700}}>{props.alarm.label}</div>
                <div style={{fontSize: 20, color: theme.textDim}}>{props.alarm.sub}</div>
              </div>
            </div>
            <div style={{display: 'flex', gap: 12}}>
              <div style={{flex: 1, textAlign: 'center', padding: '12px 0', borderRadius: 16, background: 'rgba(255,255,255,0.12)', fontSize: 21, fontWeight: 600}}>
                Adiar
              </div>
              <div
                style={{
                  flex: 1,
                  textAlign: 'center',
                  padding: '12px 0',
                  borderRadius: 16,
                  background: '#fff',
                  color: '#111',
                  fontSize: 21,
                  fontWeight: 700,
                  transform: `scale(${1 - 0.08 * press})`,
                  filter: `brightness(${1 - 0.25 * press})`,
                }}
              >
                Parar
              </div>
            </div>
          </div>
        ) : null}

        {props.notifications.map((n) => {
          const at = revealFrame(actions, n.id);
          const t = at === null ? 1 : progress(frame, fps, at, 16);
          if (t <= 0) return null;
          return (
            <div
              key={n.id}
              style={{
                ...card,
                display: 'flex',
                gap: 16,
                alignItems: 'center',
                marginBottom: 14 * t,
                opacity: t,
                maxHeight: 200 * t,
                transform: `translateY(${(1 - t) * 50}px) scale(${0.92 + 0.08 * t})`,
              }}
            >
              <AppIconBadge icon={n.app} size={58} />
              <div style={{minWidth: 0, flex: 1}}>
                <div style={{display: 'flex', justifyContent: 'space-between', gap: 10}}>
                  <div style={{fontSize: 23, fontWeight: 700, whiteSpace: 'nowrap'}}>{n.title}</div>
                </div>
                <div style={{fontSize: 23, fontWeight: 500}}>{n.body}</div>
                {n.meta ? <div style={{fontSize: 19, color: theme.textDim}}>{n.meta}</div> : null}
              </div>
            </div>
          );
        })}
      </div>
    </Phone>
  );
};
