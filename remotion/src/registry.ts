import type React from 'react';
import type {z} from 'zod';
import * as AgentFlow from './scenes/AgentFlow';
import * as Calendar from './scenes/Calendar';
import * as Hook from './scenes/Hook';
import * as Media from './scenes/Media';
import * as PhoneLockScreen from './scenes/PhoneLockScreen';
import * as Stopwatch from './scenes/Stopwatch';
import * as WhatsAppChat from './scenes/WhatsAppChat';
import type {ComponentName, SceneProps} from './types';

export type RegistryEntry = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Component: React.FC<SceneProps<any>>;
  schema: z.ZodType;
  /** true quando a cena ocupa o quadro inteiro em vez do palco. */
  fullscreen?: (props: never) => boolean;
};

/** Componentes implementados. Um nome ausente aqui falha na validação. */
export const REGISTRY: Partial<Record<ComponentName, RegistryEntry>> = {
  Hook: {Component: Hook.Hook, schema: Hook.schema},
  Media: {Component: Media.Media, schema: Media.schema, fullscreen: Media.isFullscreen as never},
  PhoneLockScreen: {Component: PhoneLockScreen.PhoneLockScreen, schema: PhoneLockScreen.schema},
  WhatsAppChat: {Component: WhatsAppChat.WhatsAppChat, schema: WhatsAppChat.schema},
  AgentFlow: {Component: AgentFlow.AgentFlow, schema: AgentFlow.schema},
  Calendar: {Component: Calendar.Calendar, schema: Calendar.schema},
  Stopwatch: {Component: Stopwatch.Stopwatch, schema: Stopwatch.schema},
};
