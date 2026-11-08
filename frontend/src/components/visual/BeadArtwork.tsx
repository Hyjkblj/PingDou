import { useEffect, useRef } from 'react';
import { mockColors } from '../../mocks/fixtures';

type Props = { size?: number; className?: string; variant?: 'cat' | 'flower' | 'portrait' };

export function BeadArtwork({ size = 320, className, variant = 'cat' }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.fillStyle = '#fafaf7';
    ctx.fillRect(0, 0, size, size);
    const cells = 24;
    const cell = size / cells;
    const palette = Object.fromEntries(mockColors.map((c) => [c.id, c.rgb]));
    for (let row = 0; row < cells; row += 1) {
      for (let column = 0; column < cells; column += 1) {
        const x = (column - cells / 2) / (cells * 0.33);
        const y = (row - cells / 2) / (cells * 0.38);
        let color: string | null = null;
        if (variant === 'flower') {
          const a = Math.atan2(y, x) * 5;
          const r = Math.hypot(x, y);
          if (r < 0.32) color = palette.c10;
          else if (r < 0.92 + Math.cos(a) * 0.16) color = row % 3 ? palette.c08 : palette.c09;
          if (row > 15 && Math.abs(column - 12) < 2) color = palette.c11;
        } else {
          const within = x * x + y * y < 1;
          if (within) {
            const eye = row > 9 && row < 12 && Math.abs(Math.abs(column - 12) - 4) < 1.2;
            const nose = row > 12 && row < 15 && Math.abs(column - 12) < 1.5;
            const edge = Math.abs(x) > 0.55 || row > 17;
            color = eye ? palette.c06 : nose ? palette.c09 : edge ? palette.c04 : palette.c03;
          }
        }
        if (!color) continue;
        const cx = column * cell + cell / 2;
        const cy = row * cell + cell / 2;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(cx, cy, cell * 0.41, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = 'rgba(32,35,33,.15)';
        ctx.lineWidth = 0.65;
        ctx.stroke();
      }
    }
  }, [size, variant]);

  return <canvas ref={ref} className={className} style={{ width: '100%', height: 'auto', aspectRatio: '1' }} />;
}
