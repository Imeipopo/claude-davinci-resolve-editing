import React from 'react';
import { Composition } from 'remotion';
import { PixelIntro } from './Pixel';
import { SandIntro } from './Sand';
import { TypeStructure } from './TypeStructure';
import { Calib } from './Calib';
import { RandomIntro, randomMetadata } from './Random';

export const Root: React.FC = () => (
  <>
    <Composition id="pixel" component={PixelIntro} durationInFrames={360} fps={60} width={1920} height={1080} />
    <Composition id="sand" component={SandIntro} durationInFrames={720} fps={60} width={1920} height={1080} />
    <Composition id="type" component={TypeStructure} durationInFrames={900} fps={60} width={1080} height={1920} />
    <Composition id="calib" component={Calib} durationInFrames={150} fps={30} width={1080} height={1920} />
    <Composition id="random" component={RandomIntro} defaultProps={{ seed: 1 }} calculateMetadata={randomMetadata} durationInFrames={360} fps={60} width={1920} height={1080} />
  </>
);
