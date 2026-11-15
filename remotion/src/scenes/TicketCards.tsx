import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {actionFrame} from '../lib/actions';
import {progress} from '../lib/anim';
import {CheckIcon} from '../lib/icons';
import {theme} from '../theme';
import type {SceneProps} from '../types';

export const schema = z.strictObject({
  title: z.string(),
  subtitle: z.string().default(''),
  fields: z.array(z.strictObject({label: z.string(), value: z.string()})),
  cards: z.array(z.strictObject({id: z.string().min(1), label: z.string(), value: z.string()})),
  chosen_label: z.string().default(''),
  stamp_text: z.string().default('CONFIRMADA'),
});
type Props = z.infer<typeof schema>;

const INK = 'rgba(22,24,28,0.55)';

/** Cartões de opção em papel: um é escolhido e recebe o carimbo de confirmação. */
export const TicketCards: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const chosenIndex = props.cards.findIndex((c) => actionFrame(actions, 'choose', c.id) !== null);
  const chooseAt = chosenIndex >= 0 ? actionFrame(actions, 'choose', props.cards[chosenIndex].id) : null;
  const choose = progress(frame, fps, chooseAt, 16);
  const stampAt = actionFrame(actions, 'stamp');
  const stamp = progress(frame, fps, stampAt, 10);
  const count = props.cards.length;
  const cardWidth = count === 1 ? 540 : Math.min(420, (900 - (count - 1) * 28) / count);

  return (
    <div style={{display: 'flex', gap: 28 * (1 - choose), justifyContent: 'center', alignItems: 'center', perspective: 1600, fontFamily: theme.sans}}>
      {props.cards.map((card, i) => {
        const mine = i === chosenIndex;
        const fade = chosenIndex >= 0 && !mine ? choose : 0;
        if (fade >= 0.999) return null;
        return (
          <div
            key={card.id}
            style={{
              width: cardWidth * (1 - fade),
              opacity: 1 - fade,
              overflow: fade > 0 ? 'hidden' : 'visible',
              transform: `rotateX(4deg) rotateY(${(i - (count - 1) / 2) * 5 * (1 - choose)}deg) scale(${mine ? 1 + 0.12 * choose : 1})`,
            }}
          >
            <div style={{width: cardWidth, boxSizing: 'border-box', position: 'relative', padding: 30, borderRadius: 24, color: theme.ink, background: `linear-gradient(180deg, #F6F3EA 0%, ${theme.paper} 100%)`, boxShadow: '0 50px 100px rgba(0,0,0,0.7), 0 0 80px rgba(255,255,255,0.08)'}}>
              <div style={{fontSize: 27, fontWeight: 700}}>{props.title}</div>
              {props.subtitle ? <div style={{fontSize: 17, fontWeight: 700, letterSpacing: '0.12em', color: INK}}>{props.subtitle}</div> : null}
              <div style={{height: 2.5, background: theme.ink, margin: '14px 0 16px'}} />
              {props.fields.map((field, j) => (
                <div key={j} style={{display: 'flex', alignItems: 'baseline', gap: 14, marginBottom: 6}}>
                  <div style={{width: 110, fontSize: 19, color: INK}}>{field.label}</div>
                  <div style={{fontFamily: theme.hand, fontSize: 34, lineHeight: 1.1}}>{field.value}</div>
                </div>
              ))}
              <div style={{marginTop: 18, border: `3px solid ${theme.ink}`, borderRadius: 14, padding: '10px 0 14px', textAlign: 'center'}}>
                <div style={{fontSize: 16, fontWeight: 700, letterSpacing: '0.16em', color: INK}}>{card.label}</div>
                <div style={{fontSize: 74, fontWeight: 700, letterSpacing: '-0.03em', lineHeight: 1.05}}>{card.value}</div>
              </div>
              {mine && props.chosen_label && choose > 0.5 ? (
                <div style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, margin: '18px auto 0', padding: '10px 18px', borderRadius: 12, background: theme.ink, color: '#fff', fontSize: 21, fontWeight: 700, width: 'fit-content', opacity: (choose - 0.5) * 2}}>
                  <div style={{width: 20, height: 20, borderRadius: '50%', background: theme.green}} />
                  {props.chosen_label}
                </div>
              ) : null}
              {mine && stampAt !== null && stamp > 0 ? (
                <div style={{position: 'absolute', right: -30, top: -46, display: 'flex', alignItems: 'center', gap: 10, padding: '10px 18px', border: `5px solid ${theme.ink}`, borderRadius: 14, background: 'rgba(246,243,234,0.9)', fontSize: 26, fontWeight: 800, letterSpacing: '0.04em', transform: `rotate(-8deg) scale(${1.4 - 0.4 * stamp})`, opacity: stamp}}>
                  <div style={{width: 34, height: 34, borderRadius: '50%', background: theme.ink, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                    <CheckIcon size={22} />
                  </div>
                  {props.stamp_text}
                </div>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
};
