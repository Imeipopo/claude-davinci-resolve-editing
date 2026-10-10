// node gen.mjs sheet <from> <to>              -> lock-frame stills + contact sheet
// node gen.mjs render <seed> [--fps 30] [--alpha]
//   full video (pixel gets synthesized SFX). --fps re-times the same animation (it is a pure function of
//   seconds), e.g. 30 to match a 30 fps Resolve timeline. --alpha writes ProRes 4444 with a transparent
//   background (template 6 only) for overlaying on a higher track.
import { bundle } from '@remotion/bundler';
import { renderMedia, renderStill, selectComposition } from '@remotion/renderer';
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { drawConfig, TEMPLATES } from './src/pools.ts';

const root = path.dirname(new URL(import.meta.url).pathname);
const outDir = path.join(root, 'out', 'gen');
mkdirSync(outDir, { recursive: true });

const argv = process.argv.slice(2);
const flag = (name) => { const i = argv.indexOf(name); return i < 0 ? null : (argv.splice(i, 1), name.startsWith('--fps') ? Number(argv.splice(i, 1)[0]) : true); };
const fpsOverride = flag('--fps');
const alpha = flag('--alpha');
const [mode, a, b] = argv;
const serveUrl = await bundle({ entryPoint: path.join(root, 'src/index.ts') });
const comp = async (inputProps) => {
  const c = await selectComposition({ serveUrl, id: 'random', inputProps });
  if (!fpsOverride) return c;
  return { ...c, fps: fpsOverride, durationInFrames: Math.round((c.durationInFrames / c.fps) * fpsOverride) };
};

if (mode === 'sheet') {
  const rows = [];
  for (let seed = Number(a); seed <= Number(b); seed++) {
    const d = drawConfig(seed);
    const m = TEMPLATES[d.template];
    const output = path.join(outDir, `seed${seed}.png`);
    await renderStill({ composition: await comp({ seed }), serveUrl, output, frame: m.lockFrame, inputProps: { seed } });
    rows.push({ seed, file: output, title: `#${seed}  ${m.label}`, labels: d.labels, rerolls: d.rerolls });
    console.log(`seed ${seed}: ${m.label} / ${d.labels.join(' / ')}`);
  }
  const manifest = path.join(outDir, `sheet_${a}-${b}.json`);
  writeFileSync(manifest, JSON.stringify(rows, null, 2));
  execFileSync(path.join(root, '.venv/bin/python'), [path.join(root, 'sheet.py'), manifest, path.join(outDir, `sheet_${a}-${b}.png`)], { stdio: 'inherit' });
} else if (mode === 'render') {
  const seed = Number(a);
  const d = drawConfig(seed);
  const m = TEMPLATES[d.template];
  if (alpha && d.template !== 'type') throw new Error(`--alpha needs template 6 (seed ${seed} is ${m.label})`);
  const fps = fpsOverride || 60;
  const name = `${m.label.split(' ')[1]}_seed${seed}_${m.ratio}_${(m.durationInFrames / 60).toFixed(2)}s_${fps}fps${alpha ? '_alpha' : ''}`;
  const inputProps = { seed, transparent: Boolean(alpha) };
  const composition = await comp(inputProps);
  if (alpha) {
    const out = path.join(outDir, `${name}.mov`);
    await renderMedia({ composition, serveUrl, codec: 'prores', proResProfile: '4444', imageFormat: 'png',
      pixelFormat: 'yuva444p10le', outputLocation: out, inputProps });
    console.log(out);
    process.exit(0);
  }
  const silent = path.join(outDir, `${name}_silent.mp4`);
  await renderMedia({
    composition, serveUrl, codec: 'h264', crf: 16, x264Preset: 'slow', colorSpace: 'bt709',
    outputLocation: silent, inputProps,
  });
  const final = path.join(outDir, `${name}.mp4`);
  if (d.template === 'pixel') {
    const wav = path.join(outDir, `${name}.wav`);
    execFileSync(path.join(root, '.venv/bin/python'), [path.join(root, 'sfx_pixel.py'), wav]);
    execFileSync(path.join(root, '.venv/bin/python'), [path.join(root, 'mux.py'), silent, wav, final], { stdio: 'inherit' });
  } else {
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', silent, '-c', 'copy', '-movflags', '+faststart', final]);
  }
  console.log(final);
} else {
  throw new Error('usage: node gen.mjs sheet <from> <to> | render <seed> [--fps 30] [--alpha]');
}
