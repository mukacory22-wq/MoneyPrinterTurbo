import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {Panel3D} from '../fx/Panel3D';
import {actionFrame} from '../lib/actions';
import {clamp, progress} from '../lib/anim';
import {AppIconBadge, CheckIcon} from '../lib/icons';
import {theme} from '../theme';
import type {SceneProps} from '../types';

export const schema = z.strictObject({
  place: z.strictObject({name: z.string(), address: z.string()}),
  button: z.string().default('Enviar'),
  sent_label: z.string(),
});
type Props = z.infer<typeof schema>;

const ROUTE = 'M150 470 L150 300 Q150 270 180 270 L560 270';
const ROUTE_LENGTH = 580;

/** Mapa estilizado: a rota é desenhada, o pino cai e a localização é enviada. */
export const MapCard: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const routeAt = actionFrame(actions, 'route');
  const route = routeAt === null ? 0 : interpolate(frame, [routeAt, routeAt + 26], [0, 1], clamp);
  const pin = progress(frame, fps, routeAt === null ? null : routeAt + 20, 14);
  const sendAt = actionFrame(actions, 'send');
  const press = sendAt === null ? 0 : interpolate(frame, [sendAt, sendAt + 4, sendAt + 9], [0, 1, 0], clamp);
  const sent = progress(frame, fps, sendAt === null ? null : sendAt + 8, 12);

  return (
    <Panel3D width={900} padding={0} style={{overflow: 'hidden'}}>
      <svg viewBox="0 0 900 540" width={900} height={540} style={{display: 'block', background: '#1B1E22'}}>
        <rect x={610} y={60} width={230} height={150} rx={12} fill="#1F3B2A" />
        <path d="M-10 270 L910 270M150 -10 L150 550M430 -10 L470 550M700 -10 L700 550M-10 110 L910 80M-10 440 L910 470" stroke="#2C3036" strokeWidth={30} fill="none" />
        <path d="M-10 270 L910 270M150 -10 L150 550" stroke="#33383F" strokeWidth={2} strokeDasharray="14 18" fill="none" />
        <path d={ROUTE} stroke={theme.blue} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" fill="none"
          strokeDasharray={ROUTE_LENGTH} strokeDashoffset={ROUTE_LENGTH * (1 - route)} />
        <circle cx={150} cy={470} r={16} fill={theme.blue} stroke="#fff" strokeWidth={5} />
        <g transform={`translate(560 ${270 - 40 * (1 - pin)})`} opacity={pin}>
          <circle r={70 * pin} fill="none" stroke={theme.red} strokeOpacity={0.5 * (1 - pin * 0.4)} strokeWidth={3} />
          <path d="M0 0C-26 -34 -36 -52 -36 -70a36 36 0 0 1 72 0c0 18 -10 36 -36 70z" fill={theme.red} />
          <circle cy={-70} r={13} fill="#16181C" />
        </g>
      </svg>
      <div style={{padding: '22px 28px 26px', fontFamily: theme.sans}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 18}}>
          <AppIconBadge icon="maps" size={54} />
          <div style={{flex: 1}}>
            <div style={{fontSize: 28, fontWeight: 700}}>{props.place.name}</div>
            <div style={{fontSize: 21, color: theme.textDim}}>{props.place.address}</div>
          </div>
          <div style={{padding: '12px 28px', borderRadius: 14, background: '#fff', color: '#111', fontSize: 23, fontWeight: 700, transform: `scale(${1 - 0.1 * press})`, filter: `brightness(${1 - 0.25 * press})`}}>
            {props.button}
          </div>
        </div>
        <div style={{display: 'flex', alignItems: 'center', gap: 12, marginTop: 16 * sent, height: 34 * sent, opacity: sent, overflow: 'hidden', fontSize: 22, fontWeight: 600}}>
          <div style={{width: 28, height: 28, borderRadius: '50%', background: theme.green, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <CheckIcon size={18} />
          </div>
          {props.sent_label}
        </div>
      </div>
    </Panel3D>
  );
};
