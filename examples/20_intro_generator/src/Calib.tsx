import React from 'react';
import { AbsoluteFill } from 'remotion';

const W = 1080, H = 1920;
const band = (i: number) => (i % 2 === 0 ? '#2B2F36' : '#3A404A');
const hot = (y: number) => (y % 500 === 0 ? '#FF4D4D' : '#FFFFFF');

export const Calib: React.FC = () => (
  <AbsoluteFill style={{ background: '#2B2F36', fontFamily: '"IBM Plex Mono", monospace' }}>
    {Array.from({ length: H / 100 }, (_, i) => (
      <div key={`b${i}`} style={{ position: 'absolute', left: 0, top: i * 100, width: W, height: 100, background: band(i) }} />
    ))}
    <svg width={W} height={H} style={{ position: 'absolute', inset: 0 }}>
      {Array.from({ length: H / 100 + 1 }, (_, i) => (
        <line key={`h${i}`} x1={0} x2={W} y1={i * 100} y2={i * 100} stroke={hot(i * 100)} strokeWidth={i * 100 % 500 === 0 ? 4 : 2} />
      ))}
      {Array.from({ length: W / 100 + 1 }, (_, i) => (
        <line key={`v${i}`} x1={i * 100} x2={i * 100} y1={0} y2={H} stroke={i * 100 % 500 === 0 ? '#FF4D4D' : '#6FD3FF'} strokeWidth={i * 100 % 500 === 0 ? 4 : 2} opacity={0.8} />
      ))}
      <rect x={2} y={2} width={W - 4} height={H - 4} fill="none" stroke="#FFE14D" strokeWidth={4} />
      <line x1={W / 2} x2={W / 2} y1={H / 2 - 60} y2={H / 2 + 60} stroke="#FFE14D" strokeWidth={4} />
      <line x1={W / 2 - 60} x2={W / 2 + 60} y1={H / 2} y2={H / 2} stroke="#FFE14D" strokeWidth={4} />
    </svg>
    {Array.from({ length: H / 100 }, (_, i) =>
      [20, 470, 900].map((x) => (
        <div key={`y${i}-${x}`} style={{ position: 'absolute', left: x, top: i * 100 + 6, fontSize: 40, color: hot(i * 100), fontWeight: 500 }}>
          {i * 100}
        </div>
      )),
    )}
    {Array.from({ length: W / 100 }, (_, i) =>
      [200, 900, 1500].map((y) => (
        <div key={`x${i}-${y}`} style={{ position: 'absolute', left: i * 100 + 8, top: y + 58, fontSize: 30, color: '#6FD3FF' }}>
          x{i * 100}
        </div>
      )),
    )}
  </AbsoluteFill>
);
