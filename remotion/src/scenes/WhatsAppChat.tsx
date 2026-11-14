import React from 'react';
import {interpolate, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {Phone} from '../fx/Phone';
import {actionFrame} from '../lib/actions';
import {clamp, progress} from '../lib/anim';
import {theme} from '../theme';
import type {SceneProps} from '../types';

const message = z.strictObject({
  id: z.string().min(1),
  sender: z.enum(['them', 'me']),
  kind: z.enum(['text', 'audio']).default('text'),
  text: z.string().default(''),
  audio_seconds: z.number().int().default(0),
  time: z.string().default(''),
});
export const schema = z.strictObject({
  contact: z.strictObject({name: z.string(), subtitle: z.string().default('')}),
  messages: z.array(message),
  composer: z.enum(['idle', 'recording']).default('idle'),
});
type Props = z.infer<typeof schema>;
type Message = z.infer<typeof message>;

export const TYPING_FRAMES = 18;
const C = {bg: '#0B141A', header: '#1F2C34', them: '#1F2C34', me: '#005C4B', accent: '#00A884'};

const Ticks: React.FC = () => (
  <svg viewBox="0 0 28 16" width={26} height={15}>
    <path d="M2 8.500l4 4 8-9M11 12.500l1 1 8-9.5" fill="none" stroke="#53BDEB" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const Wave: React.FC<{seed: string; played: number; bars?: number; height?: number}> = ({
  seed, played, bars = 30, height = 38,
}) => (
  <div style={{display: 'flex', alignItems: 'center', gap: 3, height}}>
    {Array.from({length: bars}).map((_, i) => {
      const h = 0.22 + 0.78 * random(`${seed}-${i}`) * (0.55 + 0.45 * Math.sin((i / bars) * Math.PI));
      return (
        <div
          key={i}
          style={{
            width: 4,
            height: h * height,
            borderRadius: 2,
            background: i / bars < played ? '#E9EDEF' : 'rgba(233,237,239,0.38)',
          }}
        />
      );
    })}
  </div>
);

const fmt = (seconds: number): string =>
  `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;

const Bubble: React.FC<{m: Message; appear: number; played: number}> = ({m, appear, played}) => {
  const mine = m.sender === 'me';
  return (
    <div
      style={{
        alignSelf: mine ? 'flex-end' : 'flex-start',
        maxWidth: '84%',
        background: mine ? C.me : C.them,
        borderRadius: 20,
        borderTopRightRadius: mine ? 6 : 20,
        borderTopLeftRadius: mine ? 20 : 6,
        padding: m.kind === 'audio' ? '14px 16px 8px' : '12px 16px 8px',
        opacity: appear,
        transform: `translateY(${(1 - appear) * 26}px) scale(${0.9 + 0.1 * appear})`,
        transformOrigin: mine ? '100% 100%' : '0% 100%',
        boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
      }}
    >
      {m.kind === 'audio' ? (
        <div style={{display: 'flex', alignItems: 'center', gap: 14, minWidth: 330}}>
          <svg viewBox="0 0 24 24" width={34} height={34}>
            <path d="M7 4.500v15l12-7.500z" fill="#E9EDEF" />
          </svg>
          <Wave seed={m.id} played={played} />
        </div>
      ) : (
        <div style={{fontSize: 25, lineHeight: 1.32, color: '#E9EDEF'}}>{m.text}</div>
      )}
      <div
        style={{
          display: 'flex',
          justifyContent: m.kind === 'audio' ? 'space-between' : 'flex-end',
          alignItems: 'center',
          gap: 6,
          marginTop: 4,
          fontSize: 17,
          color: 'rgba(233,237,239,0.6)',
        }}
      >
        {m.kind === 'audio' ? <span>{fmt(played > 0 ? played * m.audio_seconds : m.audio_seconds)}</span> : null}
        <span style={{display: 'flex', alignItems: 'center', gap: 5}}>
          {m.time}
          {mine ? <Ticks /> : null}
        </span>
      </div>
    </div>
  );
};

const TypingDots: React.FC<{mine: boolean; frame: number}> = ({mine, frame}) => (
  <div
    style={{
      alignSelf: mine ? 'flex-end' : 'flex-start',
      background: mine ? C.me : C.them,
      borderRadius: 20,
      padding: '18px 20px',
      display: 'flex',
      gap: 8,
    }}
  >
    {[0, 1, 2].map((i) => (
      <div
        key={i}
        style={{
          width: 11,
          height: 11,
          borderRadius: '50%',
          background: '#E9EDEF',
          opacity: 0.35 + 0.65 * Math.max(0, Math.sin((frame - i * 3) / 2.6)),
        }}
      />
    ))}
  </div>
);

/** Conversa de WhatsApp dentro de um celular: texto, áudio, digitando e gravando. */
export const WhatsAppChat: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const initial = props.contact.name.trim().charAt(0).toUpperCase();

  return (
    <Phone background={C.bg}>
      <div style={{fontFamily: theme.sans, height: '100%', display: 'flex', flexDirection: 'column'}}>
        {/* cabeçalho */}
        <div style={{background: C.header, padding: '78px 20px 16px', display: 'flex', alignItems: 'center', gap: 14}}>
          <svg viewBox="0 0 24 24" width={26} height={26}>
            <path d="M15 5l-7 7 7 7" fill="none" stroke="#E9EDEF" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div
            style={{
              width: 54, height: 54, borderRadius: '50%', background: '#6B7C85', color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26, fontWeight: 600,
            }}
          >
            {initial}
          </div>
          <div>
            <div style={{fontSize: 25, fontWeight: 600, color: '#E9EDEF'}}>{props.contact.name}</div>
            {props.contact.subtitle ? (
              <div style={{fontSize: 18, color: 'rgba(233,237,239,0.6)'}}>{props.contact.subtitle}</div>
            ) : null}
          </div>
        </div>

        {/* mensagens */}
        <div style={{flex: 1, padding: '18px 16px', display: 'flex', flexDirection: 'column', gap: 12, overflow: 'hidden'}}>
          {props.messages.map((m) => {
            const showAt = actionFrame(actions, 'show', m.id);
            const typingAt = actionFrame(actions, 'typing', m.id);
            const start = typingAt !== null ? typingAt + TYPING_FRAMES : showAt;
            if (typingAt !== null && frame >= typingAt && frame < typingAt + TYPING_FRAMES) {
              return <TypingDots key={m.id} mine={m.sender === 'me'} frame={frame - typingAt} />;
            }
            const appear = start === null ? 1 : progress(frame, fps, start, 14);
            if (appear <= 0) return null;
            const playAt = actionFrame(actions, 'play', m.id);
            const played =
              playAt === null
                ? 0
                : interpolate(frame, [playAt, playAt + Math.max(m.audio_seconds, 1) * fps], [0, 1], clamp);
            return <Bubble key={m.id} m={m} appear={appear} played={played} />;
          })}
        </div>

        {/* campo de mensagem */}
        <div style={{padding: '10px 14px 30px', display: 'flex', alignItems: 'center', gap: 12}}>
          <div
            style={{
              flex: 1, height: 58, borderRadius: 29, background: C.header, display: 'flex',
              alignItems: 'center', padding: '0 22px', fontSize: 23, color: 'rgba(233,237,239,0.5)', gap: 12,
            }}
          >
            {props.composer === 'recording' ? (
              <>
                <div style={{width: 12, height: 12, borderRadius: '50%', background: theme.red, opacity: 0.5 + 0.5 * Math.sin(frame / 4)}} />
                <span style={{color: '#E9EDEF'}}>{fmt(frame / fps)}</span>
                <Wave seed="rec" played={(frame % 60) / 60} bars={22} height={28} />
              </>
            ) : (
              'Mensagem'
            )}
          </div>
          <div
            style={{
              width: 58, height: 58, borderRadius: '50%', background: C.accent, display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              transform: `scale(${props.composer === 'recording' ? 1.15 + 0.05 * Math.sin(frame / 5) : 1})`,
            }}
          >
            <svg viewBox="0 0 24 24" width={28} height={28}>
              <rect x="9" y="3.5" width="6" height="10.5" rx="3" fill="#fff" />
              <path d="M5.5 11.500a6.5 6.5 0 0 0 13 0M12 18v3" fill="none" stroke="#fff" strokeWidth={2} strokeLinecap="round" />
            </svg>
          </div>
        </div>
      </div>
    </Phone>
  );
};
