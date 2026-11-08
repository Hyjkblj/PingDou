import { useCallback, useEffect, useRef } from 'react';
import type { PaletteColor } from '../api/types';

type Tool = 'draw' | 'erase' | 'eyedropper';

type Props = {
  matrix: (string | null)[][];
  colors: PaletteColor[];
  selectedColorId: string | null;
  tool: Tool;
  zoom: number;
  showGrid: boolean;
  showCodes: boolean;
  onCellChange: (row: number, column: number, colorId: string | null) => void;
  onPickColor: (colorId: string | null) => void;
};

export function PatternCanvas({
  matrix, colors, selectedColorId, tool, zoom, showGrid, showCodes, onCellChange, onPickColor,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawingRef = useRef(false);
  const lastCellRef = useRef('');

  const height = matrix.length;
  const width = matrix[0]?.length || 0;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !width || !height) return;
    const colorMap = new Map(colors.map((color) => [color.id, color]));
    const baseCell = Math.max(5, Math.min(24, 760 / Math.max(width, height)));
    const cell = baseCell * zoom;
    const cssWidth = width * cell;
    const cssHeight = height * cell;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(cssWidth * dpr);
    canvas.height = Math.round(cssHeight * dpr);
    canvas.style.width = cssWidth + 'px';
    canvas.style.height = cssHeight + 'px';
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssWidth, cssHeight);
    ctx.fillStyle = '#fdfdfb';
    ctx.fillRect(0, 0, cssWidth, cssHeight);

    for (let row = 0; row < height; row += 1) {
      for (let column = 0; column < width; column += 1) {
        const colorId = matrix[row][column];
        const x = column * cell;
        const y = row * cell;
        if (!colorId) {
          if ((row + column) % 2 === 0) {
            ctx.fillStyle = '#f1f1ed';
            ctx.fillRect(x, y, cell, cell);
          }
        } else {
          const color = colorMap.get(colorId);
          ctx.fillStyle = color?.rgb || '#d6d8d2';
          ctx.fillRect(x, y, cell, cell);
          if (cell >= 16) {
            ctx.fillStyle = 'rgba(255,255,255,.18)';
            ctx.beginPath();
            ctx.arc(x + cell * 0.34, y + cell * 0.3, cell * 0.17, 0, Math.PI * 2);
            ctx.fill();
          }
          if (showCodes && cell >= 24 && color) {
            const hex = color.rgb.replace('#', '');
            const luminance = (parseInt(hex.slice(0, 2), 16) * 299 + parseInt(hex.slice(2, 4), 16) * 587 + parseInt(hex.slice(4, 6), 16) * 114) / 1000;
            ctx.fillStyle = luminance > 145 ? 'rgba(20,24,22,.72)' : 'rgba(255,255,255,.86)';
            ctx.font = '600 ' + Math.max(8, Math.floor(cell * 0.31)) + 'px DM Sans, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(color.code, x + cell / 2, y + cell / 2);
          }
        }
      }
    }
    if (showGrid) {
      ctx.beginPath();
      ctx.strokeStyle = cell < 9 ? 'rgba(65,69,66,.16)' : 'rgba(65,69,66,.24)';
      ctx.lineWidth = cell < 9 ? 0.5 : 0.75;
      for (let column = 0; column <= width; column += 1) {
        ctx.moveTo(column * cell, 0); ctx.lineTo(column * cell, cssHeight);
      }
      for (let row = 0; row <= height; row += 1) {
        ctx.moveTo(0, row * cell); ctx.lineTo(cssWidth, row * cell);
      }
      ctx.stroke();
    }
    ctx.strokeStyle = '#3f4541';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(0.75, 0.75, cssWidth - 1.5, cssHeight - 1.5);
  }, [matrix, colors, width, height, zoom, showGrid, showCodes]);

  const interact = useCallback((event: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !width || !height) return;
    const rect = canvas.getBoundingClientRect();
    const column = Math.min(width - 1, Math.max(0, Math.floor((event.clientX - rect.left) / rect.width * width)));
    const row = Math.min(height - 1, Math.max(0, Math.floor((event.clientY - rect.top) / rect.height * height)));
    const key = row + ':' + column;
    if (key === lastCellRef.current && tool !== 'eyedropper') return;
    lastCellRef.current = key;
    if (tool === 'eyedropper') {
      onPickColor(matrix[row][column]);
      drawingRef.current = false;
      return;
    }
    onCellChange(row, column, tool === 'erase' ? null : selectedColorId);
  }, [height, matrix, onCellChange, onPickColor, selectedColorId, tool, width]);

  return (
    <canvas
      ref={canvasRef}
      className={'pattern-canvas cursor-' + tool}
      aria-label={width + ' 乘 ' + height + ' 拼豆图纸编辑画布'}
      onPointerDown={(event) => {
        drawingRef.current = true;
        lastCellRef.current = '';
        event.currentTarget.setPointerCapture(event.pointerId);
        interact(event);
      }}
      onPointerMove={(event) => { if (drawingRef.current) interact(event); }}
      onPointerUp={(event) => {
        drawingRef.current = false;
        lastCellRef.current = '';
        event.currentTarget.releasePointerCapture(event.pointerId);
      }}
      onPointerCancel={() => { drawingRef.current = false; lastCellRef.current = ''; }}
    />
  );
}
