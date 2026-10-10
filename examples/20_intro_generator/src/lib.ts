import { useEffect, useState } from 'react';
import { continueRender, delayRender, staticFile } from 'remotion';

export { mulberry32 } from './rng.ts';

export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const prog = (t: number, a: number, b: number) => clamp((t - a) / (b - a));
export const lerp = (a: number, b: number, u: number) => a + (b - a) * u;
export const easeInOut = (u: number) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
export const easeOut = (u: number) => 1 - Math.pow(1 - u, 3);

// Step response of a damped spring starting at t0; zeta=1 is critical damping.
export const spring = (t: number, t0: number, freq = 2.5, zeta = 1) => {
  const x = t - t0;
  if (x <= 0) return 0;
  const w = 2 * Math.PI * freq;
  if (zeta >= 1) return 1 - (1 + w * x) * Math.exp(-w * x);
  const wd = w * Math.sqrt(1 - zeta * zeta);
  return 1 - Math.exp(-zeta * w * x) * (Math.cos(wd * x) + ((zeta * w) / wd) * Math.sin(wd * x));
};

const FONTS: Record<string, [string, string][]> = {
  'Noto Sans TC': [['fonts/NotoSansTC.ttf', '100 900']],
  'Noto Serif TC': [['fonts/NotoSerifTC.ttf', '200 900']],
  'IBM Plex Mono': [['fonts/IBMPlexMono-Medium.ttf', '500']],
  'Press Start 2P': [['fonts/PressStart2P.ttf', '400']],
  'LXGW WenKai TC': [['fonts/LXGWWenKaiTC-Regular.ttf', '400'], ['fonts/LXGWWenKaiTC-Bold.ttf', '700']],
  'Cactus Classical Serif': [['fonts/CactusClassicalSerif-Regular.ttf', '400']],
};

const loaded = new Map<string, Promise<void>>();
const loadFamily = (family: string) => {
  if (!FONTS[family]) throw new Error(`unknown font family: ${family}`);
  if (!loaded.has(family)) {
    loaded.set(
      family,
      Promise.all(
        FONTS[family].map(([file, weight]) =>
          new FontFace(family, `url(${staticFile(file)})`, { weight }).load().then((f) => {
            document.fonts.add(f);
          }),
        ),
      ).then(() => undefined),
    );
  }
  return loaded.get(family)!;
};

export const useFonts = (families: string[]) => {
  const key = families.join('|');
  const [handle] = useState(() => delayRender(`fonts ${key}`));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    Promise.all(key.split('|').map(loadFamily)).then(() => {
      setReady(true);
      continueRender(handle);
    });
  }, [handle, key]);
  return ready;
};
