import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowRight, Gauge, Grid3X3, Palette, Ruler, Sparkles } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/services';
import { ApiErrorCallout } from './AuthPages';
import { Button } from '../components/ui/Button';
import { Field, Select } from '../components/ui/Field';
import { ProgressBar } from '../components/ui/Status';
import { BeadArtwork } from '../components/visual/BeadArtwork';
import { useWorkspaceStore } from '../stores/workspace';

const EMPTY_WORKSPACE = {};

export function SettingsPage() {
  const { projectId = '' } = useParams();
  const navigate = useNavigate();
  const workspace = useWorkspaceStore((s) => s.projects[projectId] ?? EMPTY_WORKSPACE);
  const update = useWorkspaceStore((s) => s.updateProject);
  const project = useQuery({ queryKey: ['project', projectId], queryFn: () => api.project(projectId) });
  const palettes = useQuery({ queryKey: ['palettes'], queryFn: api.palettes });
  const [size, setSize] = useState(32);
  const [maxColors, setMaxColors] = useState(16);
  const [mergeStrength, setMergeStrength] = useState(30);
  const [target, setTarget] = useState('BALANCED');
  const [progress, setProgress] = useState(0);
  const palette = palettes.data?.[0];
  const physical = useMemo(() => (size * 5 / 10).toFixed(1), [size]);
  const generate = useMutation({
    mutationFn: async () => {
      setProgress(18);
      const response = await api.generatePattern({
        projectId,
        baseImageVersionId: workspace.baseImageVersionId || project.data?.baseImageVersion?.id || 'base-' + projectId,
        grid: { width: size, height: size, beadSizeMm: 5 },
        palette: { id: palette?.id || 'palette-pingdou', version: palette?.version || 'PINGDOU-2026.1', disabledColorIds: [] },
        options: { maxColors, mergeStrength, dithering: 'OFF', outlineEnhancement: 'STANDARD', smallRegionThreshold: 2, skinToneProtection: true, optimizationTarget: target },
      });
      setProgress(100);
      return response;
    },
    onSuccess: (job) => {
      const patternId = job.result?.patternId;
      if (patternId) {
        update(projectId, { patternId });
        setTimeout(() => navigate('../editor'), 350);
      }
    },
  });

  return (
    <div className="stage-page page-container settings-page">
      <header className="stage-header"><span className="eyebrow">步骤 5 / 7</span><h1>设置图纸参数</h1><p>先确定成品尺寸与可用色数，生成后仍可逐格修改色号。</p></header>
      <div className="settings-layout">
        <section className="settings-preview">
          <div className="settings-art"><BeadArtwork size={520} /></div>
          <div className="dimension-line"><span>{size} 格</span><i /><strong>{physical} cm</strong><i /><span>{size} 格</span></div>
          <div className="preview-stats"><div><Grid3X3 size={18} /><span>网格<strong>{size} × {size}</strong></span></div><div><Palette size={18} /><span>最大颜色<strong>{maxColors} 色</strong></span></div><div><Ruler size={18} /><span>豆子规格<strong>5 mm</strong></span></div></div>
        </section>
        <aside className="settings-controls">
          <h2>基础参数</h2>
          <Field label="正方形网格"><div className="option-grid">{[24, 32, 48, 64].map((value) => <button key={value} className={size === value ? 'selected' : ''} onClick={() => setSize(value)}><strong>{value} × {value}</strong><small>{(value * .5).toFixed(0)} cm 成品</small></button>)}</div></Field>
          <Field label="色板"><Select value={palette?.id || ''} disabled><option>{palette ? palette.brand + ' · ' + palette.name : '正在载入色板'}</option></Select></Field>
          <Field label={'最大颜色数 · ' + maxColors}><input type="range" min="8" max="32" step="2" value={maxColors} onChange={(event) => setMaxColors(Number(event.target.value))} /><div className="range-labels"><span>更易备料</span><span>细节更多</span></div></Field>
          <Field label={'近似色合并 · ' + mergeStrength}><input type="range" min="0" max="100" value={mergeStrength} onChange={(event) => setMergeStrength(Number(event.target.value))} /><div className="range-labels"><span>保留颜色</span><span>强力合并</span></div></Field>
          <Field label="优化目标"><div className="segment-control"><button className={target === 'BALANCED' ? 'active' : ''} onClick={() => setTarget('BALANCED')}>均衡</button><button className={target === 'EASY_BUILD' ? 'active' : ''} onClick={() => setTarget('EASY_BUILD')}>易制作</button><button className={target === 'DETAIL' ? 'active' : ''} onClick={() => setTarget('DETAIL')}>高细节</button></div></Field>
          <div className="score-preview"><Gauge size={20} /><span><strong>预计适配分 84+</strong><small>生成后会检查孤立豆、轮廓完整度与颜色经济性</small></span></div>
          {generate.isPending && <ProgressBar value={progress || 62} label="正在匹配色板与修复碎格" />}
          {generate.error && <ApiErrorCallout error={generate.error} />}
          <Button className="full-button" icon={<Sparkles size={17} />} loading={generate.isPending} onClick={() => generate.mutate()}>生成拼豆图纸 <ArrowRight size={17} /></Button>
        </aside>
      </div>
    </div>
  );
}
