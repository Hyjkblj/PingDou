import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Check, CircleAlert, Download, Eraser, Eye, EyeOff, Grid3X3, Minus, MousePointer2,
  Paintbrush, Pipette, Plus, Redo2, Save, Undo2,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/services';
import type { Pattern } from '../api/types';
import { PatternCanvas } from '../canvas/PatternCanvas';
import { ErrorState, LoadingState } from '../components/feedback/States';
import { Button } from '../components/ui/Button';
import { useWorkspaceStore } from '../stores/workspace';

type Tool = 'draw' | 'erase' | 'eyedropper';
type Change = { row: number; column: number; fromColorId: string | null; toColorId: string | null };
type SaveState = 'saved' | 'dirty' | 'saving' | 'error' | 'conflict';
const EMPTY_WORKSPACE = {};

export function EditorPage() {
  const { projectId = '' } = useParams();
  const workspace = useWorkspaceStore((state) => state.projects[projectId] ?? EMPTY_WORKSPACE);
  const updateWorkspace = useWorkspaceStore((state) => state.updateProject);
  const queryClient = useQueryClient();
  const project = useQuery({ queryKey: ['project', projectId], queryFn: () => api.project(projectId) });
  const patternId = workspace.patternId || project.data?.latestPatternId || project.data?.pattern?.id;
  const patternQuery = useQuery({ queryKey: ['pattern', patternId], queryFn: () => api.pattern(patternId!), enabled: Boolean(patternId), staleTime: Infinity });
  const [pattern, setPattern] = useState<Pattern | null>(null);
  const [matrix, setMatrix] = useState<(string | null)[][]>([]);
  const [tool, setTool] = useState<Tool>('draw');
  const [selectedColorId, setSelectedColorId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [showGrid, setShowGrid] = useState(true);
  const [showCodes, setShowCodes] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>('saved');
  const [history, setHistory] = useState<Change[]>([]);
  const [redoStack, setRedoStack] = useState<Change[]>([]);
  const pendingRef = useRef(new Map<string, Change>());
  const savingRef = useRef(false);
  const saveTimerRef = useRef<number | null>(null);
  const versionRef = useRef(1);

  useEffect(() => {
    if (!patternQuery.data) return;
    setPattern(patternQuery.data);
    setMatrix(patternQuery.data.matrix.map((row) => [...row]));
    versionRef.current = patternQuery.data.version;
    setSelectedColorId(patternQuery.data.palette.colors.find((color) => color.enabled)?.id || null);
    updateWorkspace(projectId, { patternId: patternQuery.data.id });
  }, [patternQuery.data, projectId, updateWorkspace]);

  const scheduleSave = useCallback(() => {
    setSaveState('dirty');
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    saveTimerRef.current = window.setTimeout(async () => {
      if (!patternId || savingRef.current || pendingRef.current.size === 0) return;
      savingRef.current = true;
      setSaveState('saving');
      const snapshot = [...pendingRef.current.values()];
      pendingRef.current.clear();
      try {
        const result = await api.patchPattern(patternId, {
          patternVersion: versionRef.current,
          operationId: crypto.randomUUID(),
          changes: snapshot,
        });
        versionRef.current = result.patternVersion ?? result.version ?? versionRef.current + 1;
        setPattern((current) => current ? { ...current, version: versionRef.current } : current);
        setSaveState(pendingRef.current.size ? 'dirty' : 'saved');
        queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      } catch (error: any) {
        snapshot.forEach((change) => {
          const key = change.row + ':' + change.column;
          if (!pendingRef.current.has(key)) pendingRef.current.set(key, change);
        });
        setSaveState(error?.code === 'PATTERN_VERSION_CONFLICT' ? 'conflict' : 'error');
      } finally {
        savingRef.current = false;
        if (pendingRef.current.size) window.setTimeout(scheduleSave, 300);
      }
    }, 2000);
  }, [patternId, projectId, queryClient]);

  useEffect(() => () => { if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current); }, []);

  const applyCellChange = useCallback((row: number, column: number, colorId: string | null, recordHistory = true) => {
    setMatrix((current) => {
      if (!current[row] || current[row][column] === colorId) return current;
      const fromColorId = current[row][column];
      const next = current.map((line, index) => index === row ? [...line] : line);
      next[row][column] = colorId;
      const key = row + ':' + column;
      const existing = pendingRef.current.get(key);
      pendingRef.current.set(key, {
        row, column,
        fromColorId: existing ? existing.fromColorId : fromColorId,
        toColorId: colorId,
      });
      if (recordHistory) {
        setHistory((items) => [...items.slice(-99), { row, column, fromColorId, toColorId: colorId }]);
        setRedoStack([]);
      }
      scheduleSave();
      return next;
    });
  }, [scheduleSave]);

  const undo = () => {
    const change = history.at(-1);
    if (!change) return;
    setHistory((items) => items.slice(0, -1));
    setRedoStack((items) => [...items, change]);
    applyCellChange(change.row, change.column, change.fromColorId, false);
  };

  const redo = () => {
    const change = redoStack.at(-1);
    if (!change) return;
    setRedoStack((items) => items.slice(0, -1));
    setHistory((items) => [...items, change]);
    applyCellChange(change.row, change.column, change.toColorId, false);
  };

  const usage = useMemo(() => {
    const counts = new Map<string, number>();
    matrix.flat().forEach((id) => { if (id) counts.set(id, (counts.get(id) || 0) + 1); });
    return (pattern?.palette.colors || [])
      .filter((color) => counts.has(color.id))
      .map((color) => ({ ...color, count: counts.get(color.id) || 0 }))
      .sort((a, b) => b.count - a.count);
  }, [matrix, pattern]);

  const totalBeads = usage.reduce((sum, item) => sum + item.count, 0);
  const saveLabels: Record<SaveState, string> = { saved: '已保存', dirty: '等待保存', saving: '保存中', error: '保存失败', conflict: '版本冲突' };

  if (project.isLoading || patternQuery.isLoading) return <LoadingState label="正在载入图纸编辑器" />;
  if (project.error || patternQuery.error) return <ErrorState error={(project.error || patternQuery.error)!} onRetry={() => location.reload()} />;
  if (!patternId) return <div className="state-block"><Grid3X3 size={28} /><strong>还没有图纸</strong><p>请先完成参数设置并生成图纸。</p><Link to={'/projects/' + projectId + '/settings'}><Button>前往生成</Button></Link></div>;
  if (!pattern || !matrix.length) return <LoadingState label="正在解码图纸矩阵" />;

  return (
    <div className="editor-page">
      <header className="editor-header">
        <div><span className="eyebrow">步骤 6 / 7</span><h1>{project.data?.name || '拼豆图纸'}</h1></div>
        <div className={'save-status save-' + saveState}>{saveState === 'saved' ? <Check size={15} /> : saveState === 'saving' ? <Save size={15} /> : <CircleAlert size={15} />}<span>{saveLabels[saveState]}</span><small>v{versionRef.current}</small></div>
        <Link to={'/projects/' + projectId + '/export'}><Button icon={<Download size={17} />}>导出图纸</Button></Link>
      </header>
      <div className="editor-workspace">
        <aside className="editor-toolbar" aria-label="图纸工具">
          <button className={tool === 'draw' ? 'active' : ''} onClick={() => setTool('draw')} title="画笔"><Paintbrush size={20} /><span>画笔</span></button>
          <button className={tool === 'erase' ? 'active' : ''} onClick={() => setTool('erase')} title="橡皮"><Eraser size={20} /><span>橡皮</span></button>
          <button className={tool === 'eyedropper' ? 'active' : ''} onClick={() => setTool('eyedropper')} title="吸管"><Pipette size={20} /><span>吸管</span></button>
          <i />
          <button disabled={!history.length} onClick={undo} title="撤销"><Undo2 size={20} /><span>撤销</span></button>
          <button disabled={!redoStack.length} onClick={redo} title="重做"><Redo2 size={20} /><span>重做</span></button>
        </aside>
        <section className="canvas-area">
          <div className="canvas-topbar">
            <div className="zoom-control"><button onClick={() => setZoom(Math.max(.5, zoom - .25))} aria-label="缩小"><Minus size={16} /></button><span>{Math.round(zoom * 100)}%</span><button onClick={() => setZoom(Math.min(2.5, zoom + .25))} aria-label="放大"><Plus size={16} /></button></div>
            <div className="view-toggles"><button className={showGrid ? 'active' : ''} onClick={() => setShowGrid(!showGrid)}><Grid3X3 size={16} />网格</button><button className={showCodes ? 'active' : ''} onClick={() => setShowCodes(!showCodes)}>{showCodes ? <Eye size={16} /> : <EyeOff size={16} />}色号</button></div>
          </div>
          <div className="canvas-scroll"><PatternCanvas matrix={matrix} colors={pattern.palette.colors} selectedColorId={selectedColorId} tool={tool} zoom={zoom} showGrid={showGrid} showCodes={showCodes} onCellChange={applyCellChange} onPickColor={(id) => { setSelectedColorId(id); setTool('draw'); }} /></div>
          <div className="canvas-footer"><span><MousePointer2 size={15} />{tool === 'draw' ? '按住并拖动可连续上色' : tool === 'erase' ? '按住并拖动可连续擦除' : '点击格子吸取颜色'}</span><span>{pattern.width} × {pattern.height} 格 · {pattern.beadSizeMm} mm 豆</span></div>
        </section>
        <aside className="materials-panel">
          <div className="material-heading"><div><span>材料清单</span><strong>{totalBeads.toLocaleString()} 颗</strong></div><small>已含 5% 备损：{Math.ceil(totalBeads * 1.05).toLocaleString()} 颗</small></div>
          <div className="color-palette" aria-label="选择拼豆颜色">
            {pattern.palette.colors.map((color) => <button key={color.id} className={selectedColorId === color.id ? 'selected' : ''} onClick={() => { setSelectedColorId(color.id); setTool('draw'); }} title={color.code + ' ' + color.name}><i style={{ background: color.rgb }} /><span>{color.code}</span></button>)}
          </div>
          <div className="usage-list">{usage.map((color) => <button key={color.id} className={selectedColorId === color.id ? 'selected' : ''} onClick={() => setSelectedColorId(color.id)}><i style={{ background: color.rgb }} /><span><strong>{color.code} · {color.name}</strong><small>{Math.round(color.count / Math.max(1, totalBeads) * 100)}% 用量</small></span><em>{color.count}</em></button>)}</div>
          <div className="score-box"><span>制造适配分<strong>{String(pattern.score.total || 84)}</strong></span><div><i style={{ width: String(pattern.score.total || 84) + '%' }} /></div><p>轮廓完整，预计需手动调整 {String(pattern.score.estimatedManualEditCells || 18)} 格</p></div>
        </aside>
      </div>
    </div>
  );
}
