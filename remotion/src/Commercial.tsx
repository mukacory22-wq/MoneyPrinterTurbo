import React, {useMemo} from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {Soundtrack} from './audio/Soundtrack';
import {Captions} from './captions/Captions';
import {Background, Vignette} from './fx/Background';
import {Camera} from './fx/Camera';
import {EXIT_OVERLAP, SceneTransition} from './fx/SceneTransition';
import {REGISTRY} from './registry';
import {stage} from './theme';
import type {RenderProps, SceneData} from './types';

const Scene: React.FC<{scene: SceneData; enter: boolean; exit: boolean}> = ({scene, enter, exit}) => {
  const entry = REGISTRY[scene.component];
  if (!entry) throw new Error(`Componente ainda não implementado: ${scene.component}`);
  const props = useMemo(() => entry.schema.parse(scene.props), [entry, scene.props]);
  const {Component} = entry;
  const fullscreen = entry.fullscreen ? entry.fullscreen(props as never) : false;
  const content = (
    <Component
      props={props}
      actions={scene.actions}
      durationInFrames={scene.durationInFrames}
      mediaSrc={scene.media}
    />
  );
  return (
    <SceneTransition durationInFrames={scene.durationInFrames} enter={enter} exit={exit}>
      <Camera mode={scene.camera} durationInFrames={scene.durationInFrames + EXIT_OVERLAP}>
        {fullscreen ? (
          content
        ) : (
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: stage.top,
              height: stage.height,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {content}
          </div>
        )}
      </Camera>
    </SceneTransition>
  );
};

/** "morph": cenas seguidas com o mesmo componente trocam sem animação. */
const isMorph = (current: SceneData, previous: SceneData | undefined): boolean =>
  current.transition === 'morph' && previous !== undefined && previous.component === current.component;

export const Commercial: React.FC<RenderProps> = (data) => {
  const {scenes} = data;
  return (
    <AbsoluteFill>
      <Background />
      {scenes.map((scene, i) => {
        const next = scenes[i + 1];
        const animateIn = i > 0 && scene.transition !== 'cut' && !isMorph(scene, scenes[i - 1]);
        const animateOut = next !== undefined && next.transition !== 'cut' && !isMorph(next, scene);
        return (
          <Sequence
            key={scene.id}
            from={scene.from}
            durationInFrames={scene.durationInFrames + (animateOut ? EXIT_OVERLAP : 0)}
          >
            <Scene scene={scene} enter={animateIn} exit={animateOut} />
          </Sequence>
        );
      })}
      <Vignette />
      <Captions captions={data.captions} />
      <Soundtrack data={data} />
    </AbsoluteFill>
  );
};
