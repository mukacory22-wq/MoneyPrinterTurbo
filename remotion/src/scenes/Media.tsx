import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {z} from 'zod';
import {Panel3D} from '../fx/Panel3D';
import {clamp} from '../lib/anim';
import type {SceneProps} from '../types';

export const schema = z.strictObject({fit: z.enum(['panel', 'fullscreen']).default('panel')});
type Props = z.infer<typeof schema>;

const VIDEO = /\.(mp4|mov|webm)$/i;

/** Imagem ou vídeo externo: em painel 3D ou em tela cheia. Vídeos tocam sem som. */
export const Media: React.FC<SceneProps<Props>> = ({props, mediaSrc, durationInFrames}) => {
  const frame = useCurrentFrame();
  if (!mediaSrc) return null;
  const src = staticFile(mediaSrc);
  const zoom = interpolate(frame, [0, durationInFrames], [1.04, 1.14], clamp);
  const fill: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    transform: `scale(${zoom})`,
  };
  const media = VIDEO.test(mediaSrc) ? (
    <OffthreadVideo src={src} muted style={fill} />
  ) : (
    <Img src={src} style={fill} />
  );

  if (props.fit === 'fullscreen') {
    return (
      <AbsoluteFill>
        {media}
        <AbsoluteFill
          style={{
            background:
              'linear-gradient(180deg, rgba(7,8,10,0.55) 0%, rgba(7,8,10,0) 30%, rgba(7,8,10,0.2) 55%, rgba(7,8,10,0.92) 78%)',
          }}
        />
      </AbsoluteFill>
    );
  }
  return (
    <Panel3D width={900} padding={0} style={{height: 900, overflow: 'hidden'}}>
      <div style={{width: '100%', height: '100%', overflow: 'hidden', borderRadius: 27}}>{media}</div>
    </Panel3D>
  );
};

/** Cenas de tela cheia ignoram o palco e ocupam o quadro inteiro. */
export const isFullscreen = (props: Props): boolean => props.fit === 'fullscreen';
