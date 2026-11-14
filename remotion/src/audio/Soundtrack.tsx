import React from 'react';
import {Audio, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp, dbToGain} from '../lib/anim';
import type {MusicData, RenderProps} from '../types';

/** Interpolação linear em dB — igual a timeline.envelope_db_at no Python. */
export const envelopeDbAt = (envelope: MusicData['envelope'], frame: number): number => {
  if (frame <= envelope[0].frame) return envelope[0].db;
  for (let i = 1; i < envelope.length; i++) {
    const left = envelope[i - 1];
    const right = envelope[i];
    if (frame <= right.frame) {
      const span = right.frame - left.frame;
      const ratio = span ? (frame - left.frame) / span : 1;
      return left.db + (right.db - left.db) * ratio;
    }
  }
  return envelope[envelope.length - 1].db;
};

const Music: React.FC<{music: MusicData}> = ({music}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const fadeIn = music.fadeInFrames
    ? interpolate(frame, [0, music.fadeInFrames], [0, 1], clamp)
    : 1;
  const fadeOut = music.fadeOutFrames
    ? interpolate(frame, [durationInFrames - music.fadeOutFrames, durationInFrames], [1, 0], clamp)
    : 1;
  const volume = dbToGain(envelopeDbAt(music.envelope, frame)) * fadeIn * fadeOut;
  return <Audio src={staticFile(music.src)} loop={music.loop} volume={volume} />;
};

/** Narração por cena, trilha com ducking e efeitos sonoros. */
export const Soundtrack: React.FC<{data: RenderProps}> = ({data}) => (
  <>
    {data.scenes.map((scene) =>
      scene.audio ? (
        <Sequence key={scene.id} from={scene.from} layout="none">
          <Audio src={staticFile(scene.audio)} />
        </Sequence>
      ) : null,
    )}
    {data.music ? <Music music={data.music} /> : null}
    {data.sfx.map((fx, i) => (
      <Sequence key={i} from={fx.frame} durationInFrames={45} layout="none">
        <Audio src={staticFile(`sfx/${fx.name}.wav`)} volume={dbToGain(fx.db)} />
      </Sequence>
    ))}
  </>
);
