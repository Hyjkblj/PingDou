import { useMutation, useQuery } from '@tanstack/react-query';
import {
  ArrowRight, Check, ImageIcon, Layers3, RefreshCw, Scissors, Sparkles,
  UploadCloud, WandSparkles,
} from 'lucide-react';
import { type ChangeEvent, type DragEvent, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/services';
import type { AsyncJob } from '../api/types';
import { ApiErrorCallout } from './AuthPages';
import { Button } from '../components/ui/Button';
import { Field, Select } from '../components/ui/Field';
import { ProgressBar, StatusBadge } from '../components/ui/Status';
import { BeadArtwork } from '../components/visual/BeadArtwork';
import { useWorkspaceStore } from '../stores/workspace';

const EMPTY_WORKSPACE = {};

function ProjectStageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <header className="stage-header"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></header>;
}

function ImagePreview({ src, processed = false }: { src?: string; processed?: boolean }) {
  return (
    <div className={'image-preview ' + (processed ? 'processed' : '')}>
      {src ? <img src={src} alt="用户上传的原图预览" /> : <div className="portrait-placeholder"><div className="portrait-head" /><div className="portrait-body" /></div>}
    </div>
  );
}

export function AnalysisPage() {
  const { projectId = '' } = useParams();
  const navigate = useNavigate();
  const workspace = useWorkspaceStore((s) => s.projects[projectId] ?? EMPTY_WORKSPACE);
  const update = useWorkspaceStore((s) => s.updateProject);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [localPreview, setLocalPreview] = useState<string | undefined>(workspace.assetPreview);
  const project = useQuery({ queryKey: ['project', projectId], queryFn: () => api.project(projectId) });
  const [result, setResult] = useState<AsyncJob | null>(null);
  const upload = useMutation({
    mutationFn: (file: File) => api.uploadAsset(projectId, file, setProgress),
    onSuccess: (asset) => update(projectId, { assetId: asset.id, assetName: asset.fileName, assetPreview: localPreview }),
  });
  const analyze = useMutation({
    mutationFn: () => api.analyze(projectId, workspace.assetId!),
    onSuccess: setResult,
  });
  const acceptFile = (file?: File) => {
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return alert('请选择 JPG、PNG 或 WebP 图片');
    if (file.size > 20 * 1024 * 1024) return alert('图片不能超过 20 MB');
    const url = URL.createObjectURL(file);
    setLocalPreview(url);
    upload.mutate(file);
  };
  const assetId = workspace.assetId || project.data?.sourceAssets?.[0]?.id;
  const analysis = result?.result;

  return (
    <div className="stage-page page-container">
      <ProjectStageHeader eyebrow="步骤 1 / 7" title="上传并分析图片" description="先判断主体、背景复杂度和转图纸风险，再决定是否需要抠图或 AI 优化。" />
      <div className="stage-layout">
        <section className="stage-main-panel">
          {!assetId ? (
            <label
              className={'dropzone ' + (dragging ? 'dragging' : '')}
              onDragOver={(e: DragEvent) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e: DragEvent) => { e.preventDefault(); setDragging(false); acceptFile(e.dataTransfer.files[0]); }}
            >
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e: ChangeEvent<HTMLInputElement>) => acceptFile(e.target.files?.[0])} />
              <span className="drop-icon"><UploadCloud size={28} /></span>
              <strong>拖入图片，或点击选择</strong><p>JPG、PNG、WebP · 最大 20 MB · 建议主体清晰</p>
            </label>
          ) : (
            <div className="uploaded-asset">
              <ImagePreview src={localPreview || workspace.assetPreview} />
              <div className="asset-meta"><span><ImageIcon size={16} />{workspace.assetName || '已上传图片'}</span><StatusBadge status="SUCCEEDED" /></div>
            </div>
          )}
          {upload.isPending && <ProgressBar value={progress} label="正在上传原图" />}
          {upload.error && <ApiErrorCallout error={upload.error} />}
          {assetId && !analysis && <div className="stage-actions"><Button variant="secondary" icon={<RefreshCw size={17} />} onClick={() => location.reload()}>更换图片</Button><Button icon={<WandSparkles size={17} />} loading={analyze.isPending} onClick={() => analyze.mutate()}>开始智能分析</Button></div>}
        </section>
        <aside className="stage-side-panel">
          <h2>图片检查</h2>
          {analysis ? (
            <div className="analysis-result">
              <div className="score-ring"><strong>{analysis.qualityScore}</strong><span>图片质量</span></div>
              <div className="analysis-grid"><span>主体类型<strong>人物 / 宠物</strong></span><span>背景复杂度<strong>中等</strong></span></div>
              <h3>处理建议</h3>
              <ul>{(analysis.reasons || []).map((reason: string) => <li key={reason}><Check size={15} />{reason}</li>)}</ul>
              <Button className="full-button" onClick={() => navigate('../background')}>进入抠图处理 <ArrowRight size={17} /></Button>
            </div>
          ) : (
            <div className="inspection-list"><span><i />分辨率与清晰度</span><span><i />主体边缘完整性</span><span><i />碎色与复杂背景</span><span><i />AI 优化必要性</span></div>
          )}
        </aside>
      </div>
    </div>
  );
}

const backgroundModes = [
  { id: 'WHITE_PREVIEW', label: '白底展示', note: '背景不计豆', color: '#fff' },
  { id: 'TRANSPARENT', label: '透明留空', note: '背景不计豆', color: 'checker' },
  { id: 'KEEP_ORIGINAL', label: '保留原背景', note: '按原图计算', color: '#c8d6ce' },
  { id: 'SOLID_WHITE_BEADS', label: '白色实体豆', note: '背景参与计豆', color: '#f4f3eb' },
];

export function BackgroundPage() {
  const { projectId = '' } = useParams();
  const navigate = useNavigate();
  const workspace = useWorkspaceStore((s) => s.projects[projectId] ?? EMPTY_WORKSPACE);
  const update = useWorkspaceStore((s) => s.updateProject);
  const [strength, setStrength] = useState('STANDARD');
  const [mode, setMode] = useState(workspace.backgroundMode || 'WHITE_PREVIEW');
  const [job, setJob] = useState<AsyncJob | null>(null);
  const remove = useMutation({
    mutationFn: () => api.removeBackground(projectId, workspace.assetId || 'asset-source', strength),
    onSuccess: (value) => {
      setJob(value);
      update(projectId, { foregroundAssetId: value.result?.foregroundAssetId, maskAssetId: value.result?.maskAssetId });
    },
  });
  const preview = useMutation({
    mutationFn: () => api.createPreview(projectId, {
      sourceAssetId: workspace.assetId || 'asset-source', foregroundAssetId: workspace.foregroundAssetId,
      maskAssetId: workspace.maskAssetId,
      crop: { x: 0, y: 0, width: 1, height: 1, rotation: 0, flipX: false, flipY: false },
      background: { mode, paletteColorId: null },
    }),
    onSuccess: (value) => { update(projectId, { previewId: value.id, backgroundMode: mode }); navigate('../ai'); },
  });
  const removed = Boolean(job?.result || workspace.foregroundAssetId);
  return (
    <div className="stage-page page-container">
      <ProjectStageHeader eyebrow="步骤 2 / 7" title="抠出主体，确定背景语义" description="白底可以只用于看清轮廓，也可以作为实体白豆填满背景，两种模式会产生不同材料数量。" />
      <div className="background-layout">
        <section className="comparison-panel">
          <div className="comparison-item"><span>原图</span><ImagePreview src={workspace.assetPreview} /></div>
          <div className="comparison-item"><span>抠图结果</span><ImagePreview src={workspace.assetPreview} processed={removed} />{!removed && <div className="preview-overlay"><Scissors size={22} /><span>等待抠图</span></div>}</div>
        </section>
        <aside className="background-controls">
          <h2>主体边缘</h2>
          <Field label="抠图强度"><Select value={strength} onChange={(e) => setStrength(e.target.value)}><option value="PRESERVE">保留发丝 / 毛发</option><option value="STANDARD">标准</option><option value="STRONG">强力去背景</option></Select></Field>
          <Button variant="secondary" className="full-button" icon={<Scissors size={17} />} loading={remove.isPending} onClick={() => remove.mutate()}>{removed ? '重新抠图' : '开始抠图'}</Button>
          {job && <div className="edge-score"><span>边缘质量</span><strong>{job.result?.edgeQualityScore || 92} / 100</strong></div>}
          <hr /><h2>背景方式</h2>
          <div className="mode-list">{backgroundModes.map((item) => <button key={item.id} className={mode === item.id ? 'selected' : ''} onClick={() => setMode(item.id)}><i className={item.color === 'checker' ? 'checker' : ''} style={item.color !== 'checker' ? { background: item.color } : undefined} /><span><strong>{item.label}</strong><small>{item.note}</small></span>{mode === item.id && <Check size={17} />}</button>)}</div>
          <div className={'semantic-note ' + (mode.startsWith('SOLID_') ? 'counted' : '')}><Layers3 size={18} /><span><strong>{mode.startsWith('SOLID_') ? '背景参与计豆' : '背景不计豆'}</strong><small>{mode === 'WHITE_PREVIEW' ? '画布显示为白色，但图纸背景仍是透明格。' : mode.startsWith('SOLID_') ? '背景格会匹配对应色号并进入材料表。' : '透明区域不会进入豆子统计。'}</small></span></div>
          {(remove.error || preview.error) && <ApiErrorCallout error={(remove.error || preview.error)!} />}
          <Button className="full-button" disabled={!removed} loading={preview.isPending} onClick={() => preview.mutate()}>确认背景并继续</Button>
        </aside>
      </div>
    </div>
  );
}

export function AiPage() {
  const { projectId = '' } = useParams();
  const navigate = useNavigate();
  const workspace = useWorkspaceStore((s) => s.projects[projectId] ?? EMPTY_WORKSPACE);
  const update = useWorkspaceStore((s) => s.updateProject);
  const [style, setStyle] = useState('ANIME');
  const [similarity, setSimilarity] = useState('HIGH');
  const [selected, setSelected] = useState<string | null>(null);
  const [job, setJob] = useState<AsyncJob | null>(null);
  const palettes = useQuery({ queryKey: ['palettes'], queryFn: api.palettes });
  const generate = useMutation({
    mutationFn: () => api.generateAi({
      projectId, sourceAssetId: workspace.assetId || 'asset-source', maskAssetId: workspace.maskAssetId,
      style, similarity, detailLevel: 'STANDARD', composition: 'PORTRAIT',
      backgroundMode: workspace.backgroundMode || 'WHITE_PREVIEW',
      constraints: { targetGrid: { width: 32, height: 32 }, beadSizeMm: 5, paletteId: palettes.data?.[0]?.id || 'palette-pingdou', paletteVersion: palettes.data?.[0]?.version || 'PINGDOU-2026.1', maxColors: 20, outlineProtection: 'STANDARD' },
      candidateCount: 2,
    }),
    onSuccess: (value) => { setJob(value); setSelected(value.result?.candidates?.[0]?.assetId || null); },
  });
  const candidates = job?.result?.candidates || [];
  const continueWith = (assetId?: string) => { if (assetId) update(projectId, { assetId, previewId: undefined }); navigate('../base-image'); };
  return (
    <div className="stage-page page-container">
      <ProjectStageHeader eyebrow="步骤 3 / 7 · 可选" title="为拼豆重新组织画面" description="AI 优化会减少杂乱细节、保护主体轮廓，并让有限网格上的识别度更高。" />
      {!job ? (
        <div className="ai-setup">
          <section className="ai-preview"><div className="original-label">当前基底</div><ImagePreview src={workspace.assetPreview} processed /></section>
          <aside className="ai-controls"><span className="feature-tag"><Sparkles size={15} />包含 2 张候选图</span><h2>优化参数</h2><Field label="视觉风格"><div className="segment-control"><button className={style === 'ANIME' ? 'active' : ''} onClick={() => setStyle('ANIME')}>动漫卡通</button><button className={style === 'PIXEL_ART' ? 'active' : ''} onClick={() => setStyle('PIXEL_ART')}>像素插画</button></div></Field><Field label="主体相似度"><div className="segment-control"><button className={similarity === 'HIGH' ? 'active' : ''} onClick={() => setSimilarity('HIGH')}>高</button><button className={similarity === 'BALANCED' ? 'active' : ''} onClick={() => setSimilarity('BALANCED')}>均衡</button></div></Field><div className="ai-benefits"><span><Check size={15} />减少孤立碎色</span><span><Check size={15} />保护人物和宠物特征</span><span><Check size={15} />按目标色板约束生成</span></div>{generate.error && <ApiErrorCallout error={generate.error} />}<Button className="full-button" icon={<Sparkles size={17} />} loading={generate.isPending} onClick={() => generate.mutate()}>生成 2 张候选图</Button><Button className="full-button" variant="ghost" onClick={() => continueWith()}>跳过，使用当前图片</Button></aside>
        </div>
      ) : (
        <div className="candidate-section"><div className="candidate-heading"><div><h2>选择一个版本作为图纸基底</h2><p>制造适配评分低于 60 分的候选图不建议继续。</p></div><Button variant="secondary" icon={<RefreshCw size={16} />} onClick={() => generate.mutate()}>重新生成</Button></div><div className="candidate-grid">{candidates.map((item: any, index: number) => <button key={item.assetId} className={selected === item.assetId ? 'candidate selected' : 'candidate'} onClick={() => setSelected(item.assetId)}><div className={'candidate-art candidate-art-' + index}><BeadArtwork size={320} variant={index ? 'portrait' : 'cat'} /></div><div className="candidate-info"><span><strong>{item.score}</strong> 制造适配分</span>{item.recommended && <em>推荐</em>}<p>{item.label}</p></div></button>)}</div><div className="candidate-footer"><span>{selected ? '已选择候选图，可继续调整构图' : '请选择一个候选版本'}</span><Button disabled={!selected} onClick={() => continueWith(selected!)}>使用这个版本 <ArrowRight size={17} /></Button></div></div>
      )}
    </div>
  );
}

export function BaseImagePage() {
  const { projectId = '' } = useParams();
  const navigate = useNavigate();
  const workspace = useWorkspaceStore((s) => s.projects[projectId] ?? EMPTY_WORKSPACE);
  const update = useWorkspaceStore((s) => s.updateProject);
  const [rotation, setRotation] = useState(0);
  const preview = useMutation({ mutationFn: () => api.createPreview(projectId, { sourceAssetId: workspace.assetId || 'asset-source', foregroundAssetId: workspace.foregroundAssetId, maskAssetId: workspace.maskAssetId, crop: { x: 0, y: 0, width: 1, height: 1, rotation, flipX: false, flipY: false }, background: { mode: workspace.backgroundMode || 'WHITE_PREVIEW', paletteColorId: null } }) });
  const confirmBase = useMutation({
    mutationFn: async () => { const previewId = workspace.previewId || (await preview.mutateAsync()).id; return api.confirmBase(projectId, previewId); },
    onSuccess: (value) => { update(projectId, { baseImageVersionId: value.id }); navigate('../settings'); },
  });
  return (
    <div className="stage-page page-container"><ProjectStageHeader eyebrow="步骤 4 / 7" title="确认最终图片基底" description="此版本将冻结为图纸转换依据，后续仍可回看原图和 AI 候选图。" /><div className="base-layout"><section className="base-canvas"><div className="crop-frame" style={{ transform: 'rotate(' + rotation + 'deg)' }}><ImagePreview src={workspace.assetPreview} processed /></div><div className="crop-guides"><span /><span /></div></section><aside className="base-controls"><h2>构图调整</h2><Field label={'旋转角度 · ' + rotation + '°'}><input type="range" min="-15" max="15" value={rotation} onChange={(e) => setRotation(Number(e.target.value))} /></Field><div className="base-summary"><span>背景语义<strong>{workspace.backgroundMode === 'SOLID_WHITE_BEADS' ? '白色实体豆' : '白底展示'}</strong></span><span>建议网格<strong>32 × 32</strong></span><span>基底版本<strong>确认后冻结</strong></span></div><div className="semantic-note"><Layers3 size={18} /><span><strong>确认前检查边缘</strong><small>尤其留意白色毛发、发丝与透明区域是否被误删。</small></span></div>{(preview.error || confirmBase.error) && <ApiErrorCallout error={(preview.error || confirmBase.error)!} />}<Button className="full-button" loading={confirmBase.isPending || preview.isPending} onClick={() => confirmBase.mutate()}>确认基底并设置图纸</Button></aside></div></div>
  );
}
