import { mulberry32 } from './rng.ts';

const PICO = {
  black: '#000000', navy: '#1D2B53', plum: '#7E2553', green: '#008751', brown: '#AB5236',
  dgray: '#5F574F', lgray: '#C2C3C7', white: '#FFF1E8', red: '#FF004D', orange: '#FFA300',
  yellow: '#FFEC27', lime: '#00E436', blue: '#29ADFF', lav: '#83769C', pink: '#FF77A8', peach: '#FFCCAA',
};
const GB = ['#0F380F', '#306230', '#8BAC0F', '#9BBC0F'];

export const pixelPalettes = {
  pico8: {
    label: 'PICO-8',
    sky: PICO.navy, skyDark: PICO.black, stars: [PICO.lgray, PICO.white, PICO.lgray, PICO.dgray, PICO.lav, PICO.lgray],
    moon: PICO.white, ground: PICO.dgray, groundTop: PICO.lgray, mortar: PICO.black,
    outline: PICO.black, body: PICO.brown, shade: PICO.plum, light: PICO.peach, hat: PICO.red, hatShade: PICO.plum,
    pompom: PICO.white, pack: PICO.green, staff: PICO.orange, grip: PICO.brown, gem: PICO.blue,
    gemFlash: [PICO.white, PICO.pink, PICO.blue], parts: [PICO.white, PICO.pink, PICO.plum], rim: [PICO.orange, PICO.yellow],
    titleFill: PICO.yellow, titleEdge: PICO.plum, boom: [PICO.white, PICO.yellow, PICO.orange], ring: [PICO.yellow, PICO.pink],
    shot: [PICO.plum, PICO.pink, PICO.white],
  },
  gameboy: {
    label: 'Game Boy 四綠階',
    sky: GB[1], skyDark: GB[0], stars: [GB[2], GB[3], GB[2], GB[0], GB[2], GB[3]],
    moon: GB[3], ground: GB[0], groundTop: GB[2], mortar: GB[1],
    outline: GB[0], body: GB[2], shade: GB[1], light: GB[3], hat: GB[3], hatShade: GB[2],
    pompom: GB[2], pack: GB[1], staff: GB[3], grip: GB[1], gem: GB[3],
    gemFlash: [GB[3], GB[2], GB[0]], parts: [GB[3], GB[2], GB[0]], rim: [GB[2], GB[3]],
    titleFill: GB[3], titleEdge: GB[0], boom: [GB[3], GB[3], GB[2]], ring: [GB[3], GB[2]],
    shot: [GB[0], GB[2], GB[3]],
  },
};
export type PixelPalette = typeof pixelPalettes.pico8;

const PICO_HATS = {
  red: { label: '紅帽', hat: PICO.red, hatShade: PICO.plum },
  blue: { label: '藍帽', hat: PICO.blue, hatShade: PICO.navy },
  lime: { label: '綠帽', hat: PICO.lime, hatShade: PICO.green },
};

export const sandPalettes = {
  amber: { label: '琥珀光桌', table: '#F6E7C8', sand: '#3B2A1E', glowIn: '#FBF2DE', glowOut: '#E9D3A8' },
  slate: { label: '冷灰光桌', table: '#E8ECEC', sand: '#283036', glowIn: '#F5F8F8', glowOut: '#D2D9DB' },
  rust: { label: '赭紅沙', table: '#F4E4D2', sand: '#5A2A1E', glowIn: '#FBF1E6', glowOut: '#E7CBB0' },
};
export const sandFonts = {
  serif: { label: '思源宋體 600', family: 'Noto Serif TC', weight: 600 },
  wenkai: { label: '霞鶩文楷 Bold', family: 'LXGW WenKai TC', weight: 700 },
  cactus: { label: '仙人掌明體', family: 'Cactus Classical Serif', weight: 400 },
};

export const typePalettes = {
  clinic: { label: 'P6 衛教清爽', bg: '#F5FAFA', ink: '#1E2A30', structure: '#0F6E78', accent: '#F2A541', accentOpacity: 1, dark: false },
  forest: { label: 'P3 墨綠紙金', bg: '#102820', ink: '#F4E9D5', structure: '#F2B544', accent: '#F4E9D5', accentOpacity: 0.28, dark: true },
};
export const typeFonts = {
  serif: { label: '思源宋體 500', family: 'Noto Serif TC', weight: 500 },
  wenkai: { label: '霞鶩文楷 Regular', family: 'LXGW WenKai TC', weight: 400 },
};

export const TEMPLATES = {
  pixel: { label: '11 像素風', width: 1920, height: 1080, durationInFrames: 360, lockFrame: 330, ratio: '16x9' },
  sand: { label: '8B 沙畫', width: 1920, height: 1080, durationInFrames: 720, lockFrame: 690, ratio: '16x9' },
  type: { label: '6 字體即結構', width: 1080, height: 1920, durationInFrames: 900, lockFrame: 870, ratio: '9x16' },
};
export type TemplateId = keyof typeof TEMPLATES;

export type Drawn =
  | { seed: number; template: 'pixel'; labels: string[]; params: { palette: PixelPalette; stepFps: number } }
  | { seed: number; template: 'sand'; labels: string[]; params: { palette: typeof sandPalettes.amber; font: typeof sandFonts.serif; sweep: 'ltr' | 'rtl' } }
  | { seed: number; template: 'type'; labels: string[]; params: { palette: typeof typePalettes.clinic; font: typeof typeFonts.serif; slabOpacity: number } };

const pickKey = <T extends object>(r: () => number, obj: T): keyof T => {
  const keys = Object.keys(obj) as (keyof T)[];
  return keys[Math.floor(r() * keys.length)];
};
const pick = <T,>(r: () => number, arr: T[]): T => arr[Math.floor(r() * arr.length)];

// Combinations from the "don't pair" list; a hit means reroll.
const conflict = (d: Drawn) => {
  if (d.template === 'type' && d.params.palette.dark && d.params.font.weight < 500) return '深底配細字重：H.264 壓縮後細橫線會糊';
  return null;
};

export const drawConfig = (seed: number): Drawn & { rerolls: string[] } => {
  const r = mulberry32(seed * 7919 + 1);
  const rerolls: string[] = [];
  for (let attempt = 0; attempt < 30; attempt++) {
    const template = pickKey(r, TEMPLATES);
    let d: Drawn;
    if (template === 'pixel') {
      const pk = pickKey(r, pixelPalettes);
      let palette: PixelPalette = pixelPalettes[pk];
      const labels = [palette.label];
      if (pk === 'pico8') {
        const hat = PICO_HATS[pickKey(r, PICO_HATS)];
        palette = { ...palette, hat: hat.hat, hatShade: hat.hatShade };
        labels.push(hat.label);
      }
      const stepFps = pick(r, [8, 10, 12]);
      labels.push(`步進 ${stepFps}fps`);
      d = { seed, template, labels, params: { palette, stepFps } };
    } else if (template === 'sand') {
      const palette = sandPalettes[pickKey(r, sandPalettes)];
      const font = sandFonts[pickKey(r, sandFonts)];
      const sweep = pick(r, ['ltr', 'rtl'] as const);
      d = { seed, template, labels: [palette.label, font.label, sweep === 'ltr' ? '左往右抹' : '右往左抹'], params: { palette, font, sweep } };
    } else {
      const palette = typePalettes[pickKey(r, typePalettes)];
      const font = typeFonts[pickKey(r, typeFonts)];
      const slabOpacity = pick(r, [0.12, 0.16, 0.22]);
      d = { seed, template, labels: [palette.label, font.label, `薄板透明度 ${slabOpacity}`], params: { palette, font, slabOpacity } };
    }
    const why = conflict(d);
    if (!why) return { ...d, rerolls };
    rerolls.push(`${d.labels.join('／')} → 重抽（${why}）`);
  }
  throw new Error(`seed ${seed}: no valid combination after 30 tries`);
};
