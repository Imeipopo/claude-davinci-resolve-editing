import React, { useLayoutEffect, useMemo, useRef } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { clamp, easeInOut, easeOut, mulberry32, prog, useFonts } from './lib';
import { sandFonts, sandPalettes } from './pools.ts';
import { content } from './content.ts';

type SandPal = typeof sandPalettes.amber;
type SandFont = typeof sandFonts.serif;

export const sandConfig = {
  seed: 11,
  bpm: 100,
  titlePx: 176,
  subPx: 54,
  brush: 15,
  sceneLen: 2.4,
  sweepHalf: 0.3,
  grainStep: 3,
};

type P = [number, number];
type Stroke = { pts: (lt: number) => P[]; t0: number; t1: number; w?: number };

const W = 1920, H = 1080;

const arc = (cx: number, cy: number, rx: number, ry: number, a0: number, a1: number, n = 48): P[] =>
  Array.from({ length: n + 1 }, (_, i) => {
    const a = a0 + ((a1 - a0) * i) / n;
    return [cx + Math.cos(a) * rx, cy + Math.sin(a) * ry];
  });
const seg = (x0: number, y0: number, x1: number, y1: number, n = 24): P[] =>
  Array.from({ length: n + 1 }, (_, i) => [x0 + ((x1 - x0) * i) / n, y0 + ((y1 - y0) * i) / n]);
const bez = (p0: P, p1: P, p2: P, p3: P, n = 40): P[] =>
  Array.from({ length: n + 1 }, (_, i) => {
    const u = i / n, v = 1 - u;
    return [
      v * v * v * p0[0] + 3 * v * v * u * p1[0] + 3 * v * u * u * p2[0] + u * u * u * p3[0],
      v * v * v * p0[1] + 3 * v * v * u * p1[1] + 3 * v * u * u * p2[1] + u * u * u * p3[1],
    ];
  });
const rot = (pts: P[], ox: number, oy: number, deg: number): P[] => {
  const a = (deg * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  return pts.map(([x, y]) => [ox + (x - ox) * c - (y - oy) * s, oy + (x - ox) * s + (y - oy) * c]);
};
const fixed = (pts: P[]) => () => pts;

const sway = (lt: number) => 1.6 * Math.sin(prog(lt, 1.6, 2.4) * Math.PI * 2) * Math.sin(prog(lt, 1.6, 2.4) * Math.PI);

const umbrellaScene = (): Stroke[] => {
  const r = mulberry32(sandConfig.seed);
  const swayed = (pts: P[]) => (lt: number) => rot(pts, 960, 700, sway(lt));
  const strokes: Stroke[] = [
    { pts: swayed(arc(960, 470, 260, 250, Math.PI, Math.PI * 2, 64)), t0: 0.25, t1: 1.0 },
    { pts: swayed(seg(960, 215, 960, 700)), t0: 0.55, t1: 1.1 },
    { pts: swayed(arc(935, 700, 25, 25, 0, Math.PI, 16)), t0: 1.1, t1: 1.3 },
  ];
  for (let i = 0; i < 4; i++)
    strokes.push({ pts: swayed(arc(765 + 130 * i, 470, 65, 34, Math.PI, Math.PI * 2, 20)), t0: 0.85 + i * 0.1, t1: 1.25 + i * 0.1, w: 11 });
  strokes.push(
    { pts: fixed(arc(885, 560, 34, 36, -Math.PI / 2, Math.PI * 1.5, 30)), t0: 0.95, t1: 1.35 },
    { pts: fixed(bez([885, 600], [852, 640], [842, 720], [850, 820])), t0: 1.2, t1: 1.6 },
    { pts: fixed(bez([872, 640], [905, 668], [935, 672], [952, 662])), t0: 1.3, t1: 1.6, w: 11 },
    { pts: fixed(arc(1040, 566, 32, 34, -Math.PI / 2, Math.PI * 1.5, 30)), t0: 1.0, t1: 1.4 },
    { pts: fixed(bez([1040, 605], [1076, 650], [1080, 730], [1072, 820])), t0: 1.25, t1: 1.65 },
    { pts: fixed(bez([640, 838], [800, 826], [1120, 826], [1280, 838])), t0: 1.45, t1: 1.85, w: 12 },
  );
  let made = 0;
  while (made < 14) {
    const x = 560 + r() * 800, y = 170 + r() * 680;
    if (Math.hypot(x - 960, y - 470) < 320 && y < 560) continue;
    if (x > 790 && x < 1130 && y > 470) continue;
    strokes.push({ pts: fixed(seg(x, y, x - 10, y + 38, 6)), t0: 1.3 + made * 0.03, t1: 1.5 + made * 0.03, w: 8 });
    made++;
  }
  return strokes;
};

const catScene = (): Stroke[] => {
  const tail = (lt: number): P[] => {
    const wag = 18 * Math.sin(prog(lt, 1.6, 2.4) * Math.PI * 3) * Math.sin(prog(lt, 1.6, 2.4) * Math.PI);
    const a = ((-60 + wag) * Math.PI) / 180;
    return bez([1108, 668], [1150, 672], [1168 + Math.cos(a) * 10, 650], [1168 + Math.cos(a) * 30, 640 + Math.sin(a) * 50]);
  };
  return [
    { pts: fixed(bez([700, 640], [700, 515], [1220, 515], [1220, 640])), t0: 0.25, t1: 0.85 },
    { pts: fixed(seg(680, 702, 1240, 702)), t0: 0.5, t1: 0.95 },
    { pts: fixed(bez([722, 640], [650, 625], [648, 705], [690, 770])), t0: 0.6, t1: 0.95 },
    { pts: fixed(bez([1198, 640], [1270, 625], [1272, 705], [1230, 770])), t0: 0.6, t1: 0.95 },
    { pts: fixed(seg(690, 788, 1230, 788)), t0: 0.85, t1: 1.2 },
    { pts: fixed(seg(722, 788, 716, 830, 6)), t0: 1.15, t1: 1.3, w: 11 },
    { pts: fixed(seg(1198, 788, 1204, 830, 6)), t0: 1.15, t1: 1.3, w: 11 },
    { pts: fixed(arc(995, 650, 125, 50, Math.PI * 0.95, Math.PI * 2.95, 60)), t0: 0.9, t1: 1.45 },
    { pts: fixed(arc(868, 628, 42, 40, -Math.PI / 2, Math.PI * 1.5, 30)), t0: 1.0, t1: 1.4 },
    { pts: fixed([[838, 600], [840, 560], [866, 588]]), t0: 1.3, t1: 1.45, w: 11 },
    { pts: fixed([[880, 588], [906, 562], [902, 604]]), t0: 1.35, t1: 1.5, w: 11 },
    { pts: fixed(arc(856, 632, 10, 7, 0, Math.PI, 10)), t0: 1.45, t1: 1.55, w: 7 },
    { pts: tail, t0: 1.35, t1: 1.6, w: 13 },
  ];
};

const ringX = (lt: number) => 1170 - 260 * easeInOut(prog(lt, 1.55, 2.15));

const ringScene = (): Stroke[] => [
  { pts: fixed([...seg(420, 470, 560, 510, 8), ...seg(560, 510, 980, 510), ...arc(980, 550, 40, 40, -Math.PI / 2, Math.PI / 2, 20), ...seg(980, 590, 560, 590), ...seg(560, 590, 420, 650, 8)]), t0: 0.25, t1: 1.05 },
  { pts: fixed(arc(770, 550, 14, 30, -Math.PI / 2, Math.PI / 2, 12)), t0: 1.0, t1: 1.15, w: 8 },
  { pts: fixed(arc(880, 550, 12, 26, -Math.PI / 2, Math.PI / 2, 12)), t0: 1.05, t1: 1.2, w: 8 },
  { pts: (lt) => arc(ringX(lt), 550, 24, 60, 0, Math.PI * 2, 40), t0: 0.75, t1: 1.25, w: 13 },
  { pts: (lt) => { const x = ringX(lt); return [[x - 20, 482], [x, 456], [x + 20, 482], [x, 500], [x - 20, 482]]; }, t0: 1.15, t1: 1.4, w: 10 },
  { pts: (lt) => { const x = ringX(lt); return bez([1500, 400], [1350, 420], [x + 120, 455], [x + 34, 488]); }, t0: 1.2, t1: 1.6 },
  { pts: (lt) => { const x = ringX(lt); return bez([1500, 720], [1350, 690], [x + 120, 640], [x + 34, 610]); }, t0: 1.25, t1: 1.65 },
];

const SCENES = [umbrellaScene(), catScene(), ringScene()];

const strokePath = (ctx: CanvasRenderingContext2D, pts: P[], frac: number) => {
  if (frac <= 0 || pts.length < 2) return;
  const n = (pts.length - 1) * frac;
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i <= Math.floor(n); i++) ctx.lineTo(pts[i][0], pts[i][1]);
  const k = Math.floor(n), f = n - k;
  if (k < pts.length - 1) ctx.lineTo(pts[k][0] + (pts[k + 1][0] - pts[k][0]) * f, pts[k][1] + (pts[k + 1][1] - pts[k][1]) * f);
  ctx.stroke();
};

const hexRGB = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));

const buildBase = (alphaScale: number, sand: string) => {
  const [sr, sg, sb] = hexRGB(sand);
  const r = mulberry32(sandConfig.seed + 5);
  const gw = 17, gh = 10;
  const grid = Array.from({ length: gw * gh }, () => r());
  const low = (x: number, y: number) => {
    const gx = (x / W) * (gw - 1), gy = (y / H) * (gh - 1);
    const ix = Math.floor(gx), iy = Math.floor(gy), fx = gx - ix, fy = gy - iy;
    const g = (a: number, b: number) => grid[Math.min(gh - 1, b) * gw + Math.min(gw - 1, a)];
    return (g(ix, iy) * (1 - fx) + g(ix + 1, iy) * fx) * (1 - fy) + (g(ix, iy + 1) * (1 - fx) + g(ix + 1, iy + 1) * fx) * fy;
  };
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const g = cv.getContext('2d')!;
  const img = g.createImageData(W, H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = (y * W + x) * 4;
    const a = clamp((0.86 + 0.08 * low(x, y) + (r() - 0.6) * 0.3) * alphaScale);
    const shade = (r() - 0.5) * 18;
    img.data[i] = sr + shade; img.data[i + 1] = sg + shade; img.data[i + 2] = sb + shade;
    img.data[i + 3] = a * 255;
  }
  g.putImageData(img, 0, 0);
  return cv;
};

const renderScene = (ctx: CanvasRenderingContext2D, base: HTMLCanvasElement, k: number, lt: number, ghost: number, sand: string) => {
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  ctx.clearRect(0, 0, W, H);
  ctx.drawImage(base, 0, 0);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  const strokes = SCENES[k];
  for (const s of strokes) {
    const frac = easeOut(prog(lt, s.t0, s.t1));
    if (frac <= 0) continue;
    const pts = s.pts(lt);
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = sand;
    ctx.globalAlpha = 0.22;
    ctx.lineWidth = (s.w ?? sandConfig.brush) + 14;
    strokePath(ctx, pts, frac);
  }
  ctx.globalCompositeOperation = 'destination-out';
  ctx.strokeStyle = '#000';
  for (const s of strokes) {
    const pts = s.pts(lt);
    const w = s.w ?? sandConfig.brush;
    if (ghost > 0) {
      ctx.globalAlpha = 0.28 * ghost;
      ctx.lineWidth = w * 0.7;
      strokePath(ctx, pts, 1);
    }
    const frac = easeOut(prog(lt, s.t0, s.t1));
    if (frac <= 0) continue;
    ctx.globalAlpha = 0.9;
    ctx.lineWidth = w;
    strokePath(ctx, pts, frac);
    ctx.globalAlpha = 0.45;
    ctx.lineWidth = w * 0.55;
    ctx.save(); ctx.translate(2.5, -2); strokePath(ctx, pts, frac); ctx.restore();
    ctx.save(); ctx.translate(-2, 2.5); strokePath(ctx, pts, frac); ctx.restore();
  }
  ctx.globalCompositeOperation = 'destination-over';
  ctx.globalAlpha = 1;
  ctx.drawImage(speckle(sand), 0, 0);
  ctx.globalCompositeOperation = 'source-over';
};

const speckleCache = new Map<string, HTMLCanvasElement>();
const speckle = (sand: string) => {
  if (speckleCache.has(sand)) return speckleCache.get(sand)!;
  const r = mulberry32(sandConfig.seed + 21);
  const speckleCv = document.createElement('canvas');
  speckleCv.width = W; speckleCv.height = H;
  speckleCache.set(sand, speckleCv);
  const g = speckleCv.getContext('2d')!;
  g.fillStyle = sand;
  for (let i = 0; i < 90000; i++) {
    g.globalAlpha = 0.35 + r() * 0.55;
    const s = r() < 0.7 ? 1 : 2;
    g.fillRect(Math.floor(r() * W), Math.floor(r() * H), s, s);
  }
  return speckleCv;
};

type Grain = { sx: number; sy: number; tx: number; ty: number; d: number; a: number };

const buildGrains = (font: SandFont): Grain[] => {
  const cfg = sandConfig;
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const g = cv.getContext('2d')!;
  g.fillStyle = '#fff';
  g.textAlign = 'center';
  g.textBaseline = 'alphabetic';
  g.font = `${font.weight} ${cfg.titlePx}px "${font.family}"`;
  g.fillText(content.sand.title, W / 2, 560);
  g.font = `${font.weight} ${cfg.subPx}px "${font.family}"`;
  g.fillText(content.sand.subtitle, W / 2, 700);
  const data = g.getImageData(0, 0, W, H).data;
  const r = mulberry32(cfg.seed + 9);
  const out: Grain[] = [];
  const st = cfg.grainStep;
  for (let y = 0; y < H; y += st) for (let x = 0; x < W; x += st) {
    if (data[(y * W + x) * 4 + 3] < 110) continue;
    const isSub = y > 620;
    const ang = r() * Math.PI * 2, dist = 160 + r() * 420;
    const order = (x - 380) / 1160;
    out.push({
      sx: x + Math.cos(ang) * dist, sy: y + Math.sin(ang) * dist * 0.7,
      tx: x + (r() - 0.5) * 1.2, ty: y + (r() - 0.5) * 1.2,
      d: isSub ? 1.15 + order * 0.35 + r() * 0.15 : clamp(order) * 1.0 + r() * 0.2,
      a: 0.7 + r() * 0.3,
    });
  }
  return out;
};

const sweepEdge = (u: number) => -1500 + 2650 * easeInOut(u);
const SWEEP_CY = 1280, SWEEP_R = 1500;

export const SandIntro: React.FC<{ palette?: SandPal; font?: SandFont; sweep?: 'ltr' | 'rtl' }> = ({
  palette = sandPalettes.amber,
  font = sandFonts.serif,
  sweep = 'ltr',
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ready = useFonts([font.family]);
  const ref = useRef<HTMLCanvasElement>(null);
  const assets = useMemo(() => {
    if (!ready) return null;
    const mk = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };
    return { base: buildBase(1, palette.sand), thin: buildBase(0.2, palette.sand), grains: buildGrains(font), A: mk(), B: mk() };
  }, [ready, palette, font]);

  useLayoutEffect(() => {
    if (!assets) return;
    const cfg = sandConfig;
    const t = frame / fps;
    const ctx = ref.current!.getContext('2d')!;
    const L = cfg.sceneLen;
    const glow = ctx.createRadialGradient(W / 2, H / 2, 100, W / 2, H / 2, 1150);
    glow.addColorStop(0, palette.glowIn);
    glow.addColorStop(1, palette.glowOut);
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, W, H);

    const drawLayer = (target: HTMLCanvasElement, idx: number, lt: number, ghost: number) => {
      const g = target.getContext('2d')!;
      if (idx < 3) renderScene(g, assets.base, idx, lt, ghost, palette.sand);
      else {
        g.globalCompositeOperation = 'source-over';
        g.clearRect(0, 0, W, H);
        g.drawImage(assets.thin, 0, 0);
      }
      return target;
    };
    const cur = Math.min(3, Math.floor(t / L));
    const curT = t - cur * L;
    const nextB = (cur + 1) * L;
    const prevB = cur * L;
    let sweepU = -1, from = cur, to = cur + 1, fromT = curT, toT = 0;
    if (cur < 3 && t >= nextB - cfg.sweepHalf) {
      sweepU = prog(t, nextB - cfg.sweepHalf, nextB + cfg.sweepHalf);
      toT = t - nextB;
    } else if (cur > 0 && t < prevB + cfg.sweepHalf) {
      sweepU = prog(t, prevB - cfg.sweepHalf, prevB + cfg.sweepHalf);
      from = cur - 1; to = cur; fromT = t - from * L; toT = curT;
    }
    if (sweepU >= 0) {
      ctx.drawImage(drawLayer(assets.A, from, fromT, 0), 0, 0);
      const cx = sweep === 'ltr' ? sweepEdge(sweepU) : W - sweepEdge(sweepU);
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, SWEEP_CY, SWEEP_R, 0, Math.PI * 2);
      ctx.clip();
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, W, H);
      ctx.drawImage(drawLayer(assets.B, to, toT, to < 3 ? 1 - clamp(toT / 1.2) : 0), 0, 0);
      ctx.restore();
      ctx.save();
      ctx.lineCap = 'round';
      ctx.strokeStyle = palette.sand;
      ctx.globalAlpha = 0.5;
      ctx.lineWidth = 44;
      ctx.beginPath();
      ctx.arc(cx, SWEEP_CY, SWEEP_R + 18, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 0.25;
      ctx.lineWidth = 90;
      ctx.stroke();
      ctx.restore();
    } else {
      ctx.drawImage(drawLayer(assets.A, cur, curT, cur > 0 && cur < 3 ? 1 - clamp(curT / 1.2) : 0), 0, 0);
    }

    const gt = t - 3 * L;
    if (gt > 0) {
      ctx.fillStyle = palette.sand;
      const s = cfg.grainStep + 0.4;
      for (const gr of assets.grains) {
        const u = prog(gt, 0.15 + gr.d, 0.15 + gr.d + 0.55);
        if (u <= 0) continue;
        const e = easeOut(u);
        ctx.globalAlpha = gr.a * Math.min(1, u * 4);
        ctx.fillRect(gr.sx + (gr.tx - gr.sx) * e, gr.sy + (gr.ty - gr.sy) * e, s, s);
      }
      ctx.globalAlpha = 1;
    }
  }, [frame, fps, assets, palette, sweep]);

  return (
    <AbsoluteFill style={{ background: palette.table }}>
      <canvas ref={ref} width={W} height={H} />
    </AbsoluteFill>
  );
};
