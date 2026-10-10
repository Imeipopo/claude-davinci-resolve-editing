import React, { useLayoutEffect, useMemo, useRef } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { clamp, easeInOut, mulberry32, prog, useFonts } from './lib';
import { pixelPalettes, type PixelPalette } from './pools.ts';
import { content } from './content.ts';

export const pixelConfig = {
  seed: 7,
  bpm: 120,
  logical: [160, 90] as [number, number],
  scale: 12,
  glyphPx: 16,
  impact: [98, 36] as [number, number],
  titleY: 22,
  charStagger: 0.12,
  charFlight: 0.24,
};

type Pal = PixelPalette;

const SPRITE = [
  '........ww..........',
  '.......owwo.........',
  '.....oorrrroo.......',
  '....orrrrrrrro......',
  '...orrrRrrrrrro.....',
  '..owwwwwwwwwwwwo....',
  '.obobbbbbbbbbbobo...',
  '..obbbbbbbbbbbbo....',
  '..obbbbebbbbebbo....',
  '..obbbbbbllllbbo....',
  '..obbbbbblleldbo....',
  '...obbbbbllllbo.....',
  '....oobbbbbboo......',
  '...ogobbbbbbbbo.....',
  '..ogggobbllllbbo....',
  '..ogggobllllllbo....',
  '..ogggobllllllbo....',
  '..ogggobllllllbo....',
  '...ogggobllllbbo....',
  '....ooobbbbbbbo.....',
  '.....obbo..obbo.....',
  '.....obbo..obbo.....',
  '.....oddo..oddo.....',
  '.....oooo..oooo.....',
];
const spriteColors = (P: Pal): Record<string, string> => ({
  o: P.outline, w: P.pompom, r: P.hat, R: P.hatShade, b: P.body, l: P.light, e: P.outline, d: P.shade, g: P.pack,
});

type Glyph = { w: number; h: number; bits: Uint8Array };

const makeGlyphs = (text: string, px: number): Glyph[] => {
  const size = px + 4;
  return [...text].map((ch) => {
    const cv = document.createElement('canvas');
    cv.width = size;
    cv.height = size;
    const g = cv.getContext('2d')!;
    g.font = `700 ${px}px "Noto Sans TC"`;
    g.textBaseline = 'middle';
    g.textAlign = 'center';
    g.fillStyle = '#fff';
    g.fillText(ch, size / 2, size / 2 + 1);
    const data = g.getImageData(0, 0, size, size).data;
    const bits = new Uint8Array(size * size);
    for (let i = 0; i < size * size; i++) bits[i] = data[i * 4 + 3] >= 128 ? 1 : 0;
    return { w: size, h: size, bits };
  });
};

const line = (ctx: CanvasRenderingContext2D, x0: number, y0: number, x1: number, y1: number, color: string) => {
  x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1);
  ctx.fillStyle = color;
  const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
  let err = dx + dy;
  for (;;) {
    ctx.fillRect(x0, y0, 1, 1);
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err;
    if (e2 >= dy) { err += dy; x0 += sx; }
    if (e2 <= dx) { err += dx; y0 += sy; }
  }
};

const disc = (ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number, color: string) => {
  ctx.fillStyle = color;
  for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x * x + y * y <= r * r + r * 0.6) ctx.fillRect(cx + x, cy + y, 1, 1);
};

const ring = (ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number, color: string) => {
  ctx.fillStyle = color;
  const n = Math.max(8, Math.round(r * 7));
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    ctx.fillRect(Math.round(cx + Math.cos(a) * r), Math.round(cy + Math.sin(a) * r), 1, 1);
  }
};

const drawGlyph = (ctx: CanvasRenderingContext2D, gl: Glyph, x: number, y: number, squash: boolean, P: Pal) => {
  const sy = squash ? 0.75 : 1;
  const sx = squash ? 1.12 : 1;
  const hh = Math.round(gl.h * sy), ww = Math.round(gl.w * sx);
  const ox = Math.round(x - ww / 2), oy = Math.round(y + (gl.h - hh));
  const at = (u: number, v: number) => {
    const gu = Math.floor(u / sx), gv = Math.floor(v / sy);
    return gu >= 0 && gv >= 0 && gu < gl.w && gv < gl.h ? gl.bits[gv * gl.w + gu] : 0;
  };
  ctx.fillStyle = P.titleEdge;
  for (let v = -1; v <= hh; v++) for (let u = -1; u <= ww; u++) {
    if (at(u, v)) continue;
    if (at(u - 1, v) || at(u + 1, v) || at(u, v - 1) || at(u, v + 1) || at(u - 1, v - 1)) ctx.fillRect(ox + u, oy + v, 1, 1);
  }
  ctx.fillStyle = P.titleFill;
  for (let v = 0; v < hh; v++) for (let u = 0; u < ww; u++) if (at(u, v)) ctx.fillRect(ox + u, oy + v, 1, 1);
};

const stars = (() => {
  const r = mulberry32(pixelConfig.seed);
  return Array.from({ length: 30 }, () => ({ x: Math.floor(r() * 160), y: Math.floor(r() * 58), p: r() }))
    .filter((s) => Math.hypot(s.x - 148, s.y - 14) > 9);
})();
const chargeParts = (() => {
  const r = mulberry32(pixelConfig.seed + 1);
  return Array.from({ length: 22 }, () => ({ a: r() * Math.PI * 2, R: 14 + r() * 14, d: r() * 0.55 }));
})();
const burstParts = (() => {
  const r = mulberry32(pixelConfig.seed + 2);
  return Array.from({ length: 18 }, (_, i) => ({ a: (i / 18) * Math.PI * 2 + r() * 0.3, v: 30 + r() * 30 }));
})();

const BX = 24, BY = 48;

const pose = (tq: number) => {
  const raise = easeInOut(prog(tq, 1.5, 1.8));
  const cast = easeInOut(prog(tq, 2.5, 2.7));
  const back = easeInOut(prog(tq, 3.4, 3.8));
  const k = cast * (1 - back);
  const hx = 17 + 2 * k;
  const hy = 15 - 5 * raise * (1 - back) + 1 * k;
  const ang = (-90 - 10 * raise * (1 - cast) + 55 * k) * (Math.PI / 180);
  return { hx, hy, ang };
};

const drawScene = (ctx: CanvasRenderingContext2D, t: number, glyphs: Glyph[], P: Pal, stepFps: number) => {
  const cfg = pixelConfig;
  const tq = Math.floor(t * stepFps) / stepFps;
  const SC = spriteColors(P);
  const shakeOn = t >= 2.95 && t < 3.15;
  const sr = mulberry32(Math.floor(t * 30) + 99);
  const sx = shakeOn ? Math.round(sr() * 2 - 1) : 0;
  const sy = shakeOn ? Math.round(sr() * 2 - 1) : 0;
  ctx.save();
  ctx.translate(sx, sy);

  ctx.fillStyle = P.sky;
  ctx.fillRect(-2, -2, 164, 94);
  ctx.fillStyle = P.skyDark;
  ctx.fillRect(-2, -2, 164, 6);
  for (let y = 4; y < 10; y++) for (let x = -2; x < 162; x++) if ((x + y) % 2 === 0 && (y < 7 || (x + y) % 4 === 0)) ctx.fillRect(x, y, 1, 1);

  const tw = P.stars;
  for (const s of stars) {
    ctx.fillStyle = tw[Math.floor(t * 4 + s.p * 6) % tw.length];
    ctx.fillRect(s.x, s.y, 1, 1);
  }
  disc(ctx, 148, 14, 6, P.moon);
  disc(ctx, 151, 11, 5, P.sky);

  ctx.fillStyle = P.ground;
  ctx.fillRect(-2, 72, 164, 20);
  ctx.fillStyle = P.groundTop;
  ctx.fillRect(-2, 72, 164, 1);
  ctx.fillStyle = P.mortar;
  for (const yy of [78, 84]) ctx.fillRect(-2, yy, 164, 1);
  for (let row = 0; row < 3; row++) for (let x = (row % 2) * 6; x < 162; x += 12) ctx.fillRect(x, 73 + row * 6, 1, 5);

  const bob = tq < 1.5 || tq >= 3.8 ? Math.floor(tq * 2.5) % 2 : 0;
  const charge = prog(t, 1.5, 2.5);
  const { hx, hy, ang } = pose(tq);
  const ox = BX, oy = BY + bob;
  const gemX = ox + hx + Math.cos(ang) * 12, gemY = oy + hy + Math.sin(ang) * 12;

  for (let y = 0; y < SPRITE.length; y++) {
    const row = SPRITE[y];
    for (let x = 0; x < row.length; x++) {
      let ch = row[x];
      if (y < 2 && ch === 'w' && Math.floor(tq * 5) % 2 === 1) continue;
      if (y < 2 && Math.floor(tq * 5) % 2 === 1 && row[x + 1] === 'w') ch = 'w';
      const col = SC[ch];
      if (!col) continue;
      ctx.fillStyle = col;
      ctx.fillRect(ox + x, oy + y, 1, 1);
    }
  }
  const rimOn = t >= 1.75 && t < 3.0;
  if (rimOn) {
    const rim = charge > 0.6 && t < 2.8 ? P.rim[1] : P.rim[0];
    ctx.fillStyle = rim;
    for (let y = 0; y < SPRITE.length; y++) {
      const x = SPRITE[y].search(/[^.][.]*$/);
      if (x >= 0) ctx.fillRect(ox + x + 1, oy + y, 1, 1);
    }
  }
  line(ctx, ox + hx - Math.cos(ang) * 5, oy + hy - Math.sin(ang) * 5, gemX, gemY, P.staff);
  ctx.fillStyle = P.grip;
  ctx.fillRect(Math.round(ox + hx) - 1, Math.round(oy + hy), 2, 2);
  const gemCol = t >= 1.5 && t < 2.9 ? P.gemFlash[Math.floor(tq * 10) % 3] : P.gem;
  ctx.fillStyle = gemCol;
  ctx.fillRect(Math.round(gemX) - 1, Math.round(gemY) - 1, 2, 2);

  for (const p of chargeParts) {
    const t0 = 1.6 + p.d;
    const u = prog(t, t0, t0 + 0.38);
    if (u <= 0 || u >= 1) continue;
    const a = p.a + u * 3;
    const r = p.R * (1 - u);
    ctx.fillStyle = u < 0.4 ? P.parts[0] : u < 0.75 ? P.parts[1] : P.parts[2];
    ctx.fillRect(Math.round(gemX + Math.cos(a) * r), Math.round(gemY + Math.sin(a) * r), 1, 1);
  }

  const [ix, iy] = cfg.impact;
  const g0x = BX + 19 + Math.cos(-35 * Math.PI / 180) * 12, g0y = BY + 16 + Math.sin(-35 * Math.PI / 180) * 12;
  const flight = (s: number) => {
    const u = clamp(s) ** 1.6;
    return [g0x + (ix - g0x) * u, g0y + (iy - g0y) * u - Math.sin(Math.PI * clamp(s)) * 6];
  };
  if (t >= 2.6 && t < 2.95) {
    const s = prog(t, 2.6, 2.95);
    [[0.12, P.shot[0]], [0.06, P.shot[1]], [0, P.shot[2]]].forEach(([back, col]) => {
      const [px, py] = flight(s - (back as number));
      ctx.fillStyle = col as string;
      ctx.fillRect(Math.round(px) - 1, Math.round(py) - 1, 2, 2);
    });
  }
  if (t >= 2.95 && t < 3.5) {
    const s = t - 2.95;
    if (s < 0.2) ring(ctx, ix, iy, 2 + s * 60, s < 0.1 ? P.ring[0] : P.ring[1]);
    for (const p of burstParts) {
      const k = 6;
      const d = (p.v * (1 - Math.exp(-k * s))) / k;
      const px = ix + Math.cos(p.a) * d, py = iy + Math.sin(p.a) * d + 20 * s * s;
      ctx.fillStyle = s < 0.15 ? P.boom[0] : s < 0.32 ? P.boom[1] : P.boom[2];
      ctx.fillRect(Math.round(px), Math.round(py), 1, 1);
    }
  }

  const n = glyphs.length;
  const cell = cfg.glyphPx + 1;
  const tx0 = 98 - ((n - 1) * cell) / 2;
  glyphs.forEach((gl, i) => {
    const s0 = 2.95 + i * cfg.charStagger;
    const land = s0 + cfg.charFlight;
    if (t < s0) return;
    const tx = tx0 + i * cell, ty = cfg.titleY;
    let x = tx, y = ty;
    if (t < land) {
      const u = prog(t, s0, land);
      x = ix + (tx - ix) * u;
      y = iy - gl.h / 2 + (ty - (iy - gl.h / 2)) * u - Math.sin(Math.PI * u) * 12;
    }
    const squash = t >= land && t < land + 1 / stepFps;
    drawGlyph(ctx, gl, Math.round(x), Math.round(y), squash, P);
  });
  ctx.restore();
};

export const PixelIntro: React.FC<{ palette?: Pal; stepFps?: number }> = ({ palette = pixelPalettes.pico8, stepFps = 10 }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const ready = useFonts(['Noto Sans TC']);
  const ref = useRef<HTMLCanvasElement>(null);
  const small = useMemo(() => {
    const c = document.createElement('canvas');
    [c.width, c.height] = pixelConfig.logical;
    return c;
  }, []);
  const glyphs = useMemo(() => (ready ? makeGlyphs(content.pixel.title, pixelConfig.glyphPx) : []), [ready]);
  useLayoutEffect(() => {
    if (!ready) return;
    const t = frame / fps;
    const sctx = small.getContext('2d')!;
    sctx.imageSmoothingEnabled = false;
    drawScene(sctx, t, glyphs, palette, stepFps);
    const ctx = ref.current!.getContext('2d')!;
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(small, 0, 0, width, height);
  }, [frame, fps, ready, glyphs, small, width, height, palette, stepFps]);
  return (
    <AbsoluteFill style={{ background: palette.sky }}>
      <canvas ref={ref} width={width} height={height} style={{ imageRendering: 'pixelated' }} />
    </AbsoluteFill>
  );
};
