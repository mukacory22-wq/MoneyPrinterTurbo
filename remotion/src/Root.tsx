import React from 'react';
import {Composition} from 'remotion';
import {Commercial} from './Commercial';
import {loadFonts} from './fonts';
import type {RenderProps} from './types';

loadFonts();

const defaultProps: RenderProps = {
  fps: 30,
  width: 1080,
  height: 1920,
  durationInFrames: 90,
  scenes: [
    {
      id: 'exemplo', component: 'Hook', props: {text: 'Comente AGENDA'}, from: 0,
      durationInFrames: 90, camera: 'push_in', transition: 'blur_zoom', media: null,
      audio: null, actions: [],
    },
  ],
  captions: {enabled: true, yPercent: 68, fontSize: 64, highlightColor: '#8FB8FF', groups: []},
  music: null,
  sfx: [],
};

export const Root: React.FC = () => (
  <Composition
    id="Commercial"
    component={Commercial}
    defaultProps={defaultProps}
    fps={30}
    width={1080}
    height={1920}
    durationInFrames={90}
    calculateMetadata={({props}) => ({
      fps: props.fps,
      width: props.width,
      height: props.height,
      durationInFrames: props.durationInFrames,
    })}
  />
);
