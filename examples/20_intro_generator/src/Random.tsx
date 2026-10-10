import React, { useMemo } from 'react';
import type { CalculateMetadataFunction } from 'remotion';
import { PixelIntro } from './Pixel';
import { SandIntro } from './Sand';
import { TypeStructure } from './TypeStructure';
import { drawConfig, TEMPLATES } from './pools.ts';

type Props = { seed: number; transparent?: boolean };

export const RandomIntro: React.FC<Props> = ({ seed, transparent = false }) => {
  const d = useMemo(() => drawConfig(seed), [seed]);
  if (d.template === 'pixel') return <PixelIntro {...d.params} />;
  if (d.template === 'sand') return <SandIntro {...d.params} />;
  return <TypeStructure {...d.params} transparent={transparent} />;
};

export const randomMetadata: CalculateMetadataFunction<Props> = ({ props }) => {
  const m = TEMPLATES[drawConfig(props.seed).template];
  return { width: m.width, height: m.height, durationInFrames: m.durationInFrames, fps: 60 };
};
