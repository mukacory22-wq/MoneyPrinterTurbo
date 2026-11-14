import {z} from 'zod';

/** Contrato com app/services/commercial/timeline.py (build_render_props). */

export const COMPONENT_NAMES = [
  'Hook', 'Media', 'PhoneLockScreen', 'WhatsAppChat', 'AgentFlow', 'Calendar',
  'Stopwatch', 'SearchResults', 'Transcription', 'FormCard', 'TicketCards',
  'DataTable', 'MapCard', 'ChecklistStatus', 'BarChart', 'SocialPost',
  'DigitalClock',
] as const;
export type ComponentName = (typeof COMPONENT_NAMES)[number];

export const APP_ICONS = [
  'whatsapp', 'calendar', 'pix', 'alarm', 'ai', 'mic', 'maps', 'sheets',
  'instagram', 'bell', 'generic',
] as const;
export const appIconSchema = z.enum(APP_ICONS);
export type AppIcon = z.infer<typeof appIconSchema>;

const frame = z.number().int().nonnegative();

export const resolvedActionSchema = z.strictObject({
  do: z.string(),
  target: z.string().nullable(),
  frame,
});
export type ResolvedAction = z.infer<typeof resolvedActionSchema>;

export const sceneSchema = z.strictObject({
  id: z.string(),
  component: z.enum(COMPONENT_NAMES),
  props: z.record(z.string(), z.unknown()),
  from: frame,
  durationInFrames: z.number().int().positive(),
  camera: z.enum(['push_in', 'drift', 'static']),
  transition: z.enum(['blur_zoom', 'morph', 'cut']),
  media: z.string().nullable(),
  audio: z.string().nullable(),
  actions: z.array(resolvedActionSchema),
});
export type SceneData = z.infer<typeof sceneSchema>;

export const captionWordSchema = z.strictObject({
  text: z.string(),
  frame,
  emphasis: z.boolean(),
});
export const captionGroupSchema = z.strictObject({
  from: frame,
  to: frame,
  words: z.array(captionWordSchema).min(1),
});
export type CaptionGroup = z.infer<typeof captionGroupSchema>;

export const captionsSchema = z.strictObject({
  enabled: z.boolean(),
  yPercent: z.number(),
  fontSize: z.number(),
  highlightColor: z.string(),
  groups: z.array(captionGroupSchema),
});

export const musicSchema = z.strictObject({
  src: z.string(),
  loop: z.boolean(),
  envelope: z.array(z.strictObject({frame, db: z.number()})).min(1),
  fadeInFrames: frame,
  fadeOutFrames: frame,
});
export type MusicData = z.infer<typeof musicSchema>;

export const sfxSchema = z.strictObject({name: z.string(), frame, db: z.number()});

export const renderPropsSchema = z.strictObject({
  fps: z.number().int().positive(),
  width: z.number().int().positive(),
  height: z.number().int().positive(),
  durationInFrames: z.number().int().positive(),
  scenes: z.array(sceneSchema).min(1),
  captions: captionsSchema,
  music: musicSchema.nullable(),
  sfx: z.array(sfxSchema),
});
export type RenderProps = z.infer<typeof renderPropsSchema>;

/** O que cada componente de cena recebe. */
export type SceneProps<P> = {
  props: P;
  actions: ResolvedAction[];
  durationInFrames: number;
  mediaSrc: string | null;
};
