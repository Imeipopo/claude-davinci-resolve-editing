import React, { createContext, useContext } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { clamp, lerp, prog, spring, useFonts } from './lib';
import { typeFonts, typePalettes } from './pools.ts';

type TypePal = typeof typePalettes.clinic;
type TypeFont = typeof typeFonts.serif;
const Style = createContext<{ pal: TypePal; font: TypeFont }>({ pal: typePalettes.clinic, font: typeFonts.serif });

export const typeConfig = {
  sans: '"Noto Sans TC"',
  mono: '"IBM Plex Mono"',
  springHz: 2.2,
  charStagger: 0.06,
};

const cfg = typeConfig;
const sp = (t: number, t0: number) => clamp(spring(t, t0, cfg.springHz, 1));

type Kind = 'serif' | 'key';

const Glyph: React.FC<{
  ch: string; kind: Kind; size: number; x: number; y: number; t: number; tin: number; tout?: number;
  morph?: { t0: number; x: number; y: number; sx: number; sy: number; opacity?: number };
}> = ({ ch, kind, size, x, y, t, tin, tout, morph }) => {
  const { pal, font } = useContext(Style);
  const pin = sp(t, tin);
  const pout = tout === undefined ? 0 : sp(t, tout);
  if (tout !== undefined && pout > 0.999) return null;
  const m = morph ? sp(t, morph.t0) : 0;
  const dx = morph ? lerp(0, morph.x - x, m) : 0;
  const dy = morph ? lerp(0, morph.y - y, m) : 0;
  const sx = morph ? lerp(1, morph.sx, m) : 1;
  const sy = morph ? lerp(1, morph.sy, m) : 1;
  const op = morph?.opacity !== undefined ? lerp(1, morph.opacity, m) : 1;
  const masked = !morph || t < morph.t0;
  return (
    <div style={{ position: 'absolute', left: x, top: y - size * 0.06, width: size, height: size * 1.12, overflow: masked ? 'hidden' : 'visible' }}>
      <div
        style={{
          position: 'absolute', left: 0, top: size * 0.06, width: size, height: size,
          fontFamily: kind === 'key' ? cfg.sans : `"${font.family}"`, fontWeight: kind === 'key' ? 900 : font.weight,
          fontSize: size, lineHeight: 1, color: kind === 'key' ? pal.structure : pal.ink,
          transformOrigin: '0 0', opacity: op,
          transform: `translate(${dx}px, ${dy + (1 - pin) * size * 1.15 + pout * size * 1.15}px) scale(${sx}, ${sy})`,
        }}
      >
        {ch}
      </div>
    </div>
  );
};

type Seg = { text: string; kind: Kind; size: number };

const layout = (segs: Seg[], cx: number, bottom: number) => {
  const total = segs.reduce((a, s) => a + s.text.length * s.size, 0);
  let x = cx - total / 2;
  const out: { ch: string; kind: Kind; size: number; x: number; y: number; seg: number }[] = [];
  segs.forEach((s, si) => {
    for (const ch of s.text) {
      out.push({ ch, kind: s.kind, size: s.size, x, y: bottom - s.size, seg: si });
      x += s.size;
    }
  });
  return out;
};

const CX = 490;
const L = 110, R = 870;
const POST_W = 72, POST_TOP = 1000, POST_BOT = 1380;
const BEAM_Y = 968, BEAM_H = 32;

export const TypeStructure: React.FC<{ palette?: TypePal; font?: TypeFont; slabOpacity?: number; transparent?: boolean }> = ({
  palette = typePalettes.clinic,
  font = typeFonts.serif,
  slabOpacity = 0.16,
  transparent = false,
}) => {
  const bg = transparent ? 'transparent' : palette.bg;
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const ready = useFonts(['Noto Sans TC', 'IBM Plex Mono', font.family]);
  const t = frame / fps;
  if (!ready) return <AbsoluteFill style={{ background: bg }} />;

  const s1 = layout([{ text: '看不見', kind: 'key', size: 96 }, { text: '的，', kind: 'serif', size: 96 }], CX, 868);
  const s2a = layout([{ text: '最會跟你', kind: 'serif', size: 96 }], CX, 860);
  const s2b = layout([{ text: '回家', kind: 'key', size: 120 }, { text: '。', kind: 'serif', size: 96 }], CX, 1010);
  const s3 = layout([{ text: '搓滿', kind: 'serif', size: 84 }, { text: '二十秒', kind: 'key', size: 84 }, { text: '，', kind: 'serif', size: 84 }], CX, 864);
  const s4 = layout([{ text: '才算真的', kind: 'serif', size: 72 }, { text: '乾淨', kind: 'key', size: 108 }, { text: '。', kind: 'serif', size: 72 }], CX, BEAM_Y - 10);

  const glyphs: React.ReactNode[] = [];
  const slabSize = 250, slabLeft = CX - (slabSize * 3) / 2, slabTop = 300;
  s1.forEach((g, i) => {
    const tin = 0.2 + i * cfg.charStagger;
    if (g.seg === 0)
      glyphs.push(<Glyph key={`a${i}`} {...g} t={t} tin={tin} morph={{ t0: 2.75, x: slabLeft + i * slabSize, y: slabTop, sx: slabSize / 96, sy: slabSize / 96, opacity: slabOpacity }} />);
    else glyphs.push(<Glyph key={`a${i}`} {...g} t={t} tin={tin} tout={2.6} />);
  });
  s2a.forEach((g, i) => glyphs.push(<Glyph key={`b${i}`} {...g} t={t} tin={3.4 + i * cfg.charStagger} tout={6.65} />));
  s2b.forEach((g, i) => {
    const tin = 3.75 + i * 0.08;
    if (g.seg === 0) {
      const px = i === 0 ? 130 : 850 - POST_W;
      glyphs.push(<Glyph key={`c${i}`} {...g} t={t} tin={tin} morph={{ t0: 6.8, x: px, y: POST_TOP, sx: POST_W / 120, sy: (POST_BOT - POST_TOP) / 120 }} />);
    } else glyphs.push(<Glyph key={`c${i}`} {...g} t={t} tin={tin} tout={6.65} />);
  });
  const keyStart = s3.find((g) => g.seg === 1)!.x;
  s3.forEach((g, i) => {
    const tin = 7.6 + i * cfg.charStagger;
    if (g.seg === 1) {
      const j = i - 2;
      const sx = (R - 20 - (L + 20)) / (3 * 84);
      glyphs.push(<Glyph key={`d${i}`} {...g} t={t} tin={tin} morph={{ t0: 10.6, x: L + 20 + j * 84 * sx, y: BEAM_Y, sx, sy: BEAM_H / 84 }} />);
    } else glyphs.push(<Glyph key={`d${i}`} {...g} t={t} tin={tin} tout={10.5} />);
  });
  void keyStart;
  s4.forEach((g, i) => glyphs.push(<Glyph key={`e${i}`} {...g} t={t} tin={11.85 + i * cfg.charStagger} />));

  const draw = (a: number, b: number) => clamp(sp(t, a) * (b > a ? 1 : 1));
  const narrow = sp(t, 0.5) * 0.6 + prog(t, 0.5, 2.5) * 0.4;
  const topLineY = t < 2.75 ? lerp(640, 720, narrow) : lerp(720, 560, sp(t, 2.75));
  const botLineY = lerp(1000, 920, narrow);
  const botRetract = sp(t, 2.6);
  const lineIn = sp(t, 0.1);
  const hang = sp(t, 7.2);
  const release = sp(t, 12.6) * 6;
  const beamOn = sp(t, 10.75);
  const fill = sp(t, 10.95);
  const labels = sp(t, 11.05);
  const breathe = 1 + 0.012 * Math.sin(Math.PI * prog(t, 12.6, 15));
  const sw = palette.structure;

  const hanger = (x: number) => `M ${x} 560 Q ${x + release} ${(560 + BEAM_Y) / 2} ${x} ${lerp(560, BEAM_Y, hang)}`;

  return (
    <Style.Provider value={{ pal: palette, font }}>
    <AbsoluteFill style={{ background: bg }}>
      <AbsoluteFill style={{ transform: `scale(${breathe})`, transformOrigin: `${CX}px 960px` }}>
        <svg width={width} height={height} style={{ position: 'absolute', inset: 0 }}>
          <line x1={L} x2={L + (R - L) * lineIn} y1={topLineY} y2={topLineY} stroke={sw} strokeWidth={t < 2.75 ? 2 : lerp(2, 4, sp(t, 2.75))} />
          {botRetract < 0.999 && <line x1={L} x2={L + (R - L) * lineIn * (1 - botRetract)} y1={botLineY} y2={botLineY} stroke={sw} strokeWidth={2} />}
          {hang > 0.001 && <path d={hanger(166)} stroke={sw} strokeWidth={3} fill="none" />}
          {hang > 0.001 && <path d={hanger(850 - POST_W / 2)} stroke={sw} strokeWidth={3} fill="none" />}
          {fill > 0.001 && <rect x={L + 20} y={BEAM_Y} width={(R - L - 40) * fill} height={BEAM_H} fill={palette.accent} opacity={palette.accentOpacity} />}
          {beamOn > 0.001 && (
            <g opacity={beamOn}>
              <rect x={L + 20} y={BEAM_Y} width={R - L - 40} height={BEAM_H} fill="none" stroke={sw} strokeWidth={3} />
              {Array.from({ length: 21 }, (_, k) => {
                const x = L + 20 + ((R - L - 40) * k) / 20;
                return <line key={k} x1={x} x2={x} y1={BEAM_Y + BEAM_H} y2={BEAM_Y + BEAM_H + (k % 10 === 0 ? 22 : k % 5 === 0 ? 16 : 10)} stroke={sw} strokeWidth={2} />;
              })}
            </g>
          )}
        </svg>
        {glyphs}
        {labels > 0.001 && (
          <>
            <div style={{ position: 'absolute', left: 214, top: BEAM_Y + BEAM_H + 28, fontFamily: cfg.mono, fontSize: 48, color: palette.structure, opacity: labels }}>0</div>
            <div style={{ position: 'absolute', left: 778 - 12 - 58, top: BEAM_Y + BEAM_H + 28, fontFamily: cfg.mono, fontSize: 48, color: palette.structure, opacity: labels }}>20</div>
          </>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
    </Style.Provider>
  );
};
