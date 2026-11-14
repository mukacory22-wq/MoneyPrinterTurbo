import type React from 'react';
import type {z} from 'zod';
import * as Hook from './scenes/Hook';
import * as Media from './scenes/Media';
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
};
