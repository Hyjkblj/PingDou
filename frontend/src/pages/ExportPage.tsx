import { useMutation, useQuery } from '@tanstack/react-query';
import { Check, Download, FileImage, FileSpreadsheet, FileText, PackageCheck } from 'lucide-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/services';
import type { ExportJob } from '../api/types';
import { ErrorState, LoadingState } from '../components/feedback/States';
import { Button } from '../components/ui/Button';
import { Field, Select } from '../components/ui/Field';
import { formatDate } from '../lib/utils';
import { useWorkspaceStore } from '../stores/workspace';
import { ApiErrorCallout } from './AuthPages';

const EMPTY_WORKSPACE = {};

const formats = [
  { id: 'PDF', label: 'PDF 图纸包', detail: '分页图纸、色号与材料清单', icon: FileText },
  { id: 'PNG', label: '高清 PNG', detail: '适合屏幕查看与打印', icon: FileImage },
  { id: 'CSV', label: 'CSV 材料表', detail: '逐格色号矩阵与数量统计', icon: FileSpreadsheet },
];

export function ExportPage() {
  const { projectId = '' } = useParams();
  const workspace = useWorkspaceStore((state) => state.projects[projectId] ?? EMPTY_WORKSPACE);
  const project = useQuery({ queryKey: ['project', projectId], queryFn: () => api.project(projectId) });
  const patternId = workspace.patternId || project.data?.latestPatternId || project.data?.pattern?.id;
  const pattern = useQuery({ queryKey: ['pattern', patternId], queryFn: () => api.pattern(patternId!), enabled: Boolean(patternId) });
  const [format, setFormat] = useState('PDF');
  const [paperSize, setPaperSize] = useState('A4');
  const [includeCodes, setIncludeCodes] = useState(true);
  const [includeMaterials, setIncludeMaterials] = useState(true);
  const [result, setResult] = useState<ExportJob | null>(null);
  const exportMutation = useMutation({
    mutationFn: () => api.exportPattern({
      patternId, patternVersion: pattern.data!.version, format,
      options: { paperSize, orientation: 'PORTRAIT', includeGrid: true, includeCoordinates: true, includeColorCodes: includeCodes, includeMaterialList: includeMaterials, wasteRate: 0.05 },
    }),
    onSuccess: setResult,
  });
  const download = async () => {
    if (!result) return;
    if (result.downloadUrl?.startsWith('data:')) {
      const anchor = document.createElement('a'); anchor.href = result.downloadUrl; anchor.download = result.fileName || 'pingdou-export.' + format.toLowerCase(); anchor.click(); return;
    }
    const response = await api.downloadExport(result.exportId);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = result.fileName || 'pingdou-export.' + format.toLowerCase(); anchor.click(); URL.revokeObjectURL(url);
  };

  if (project.isLoading || pattern.isLoading) return <LoadingState label="正在准备导出数据" />;
  if (project.error || pattern.error) return <ErrorState error={(project.error || pattern.error)!} onRetry={() => location.reload()} />;
  if (!pattern.data) return <div className="state-block"><strong>图纸尚未生成</strong><Link to={'/projects/' + projectId + '/settings'}><Button>前往生成</Button></Link></div>;

  return (
    <div className="export-page page-container">
      <header className="stage-header"><span className="eyebrow">步骤 7 / 7</span><h1>导出与备料</h1><p>导出内容基于当前保存版本 v{pattern.data.version}，白底展示区域不会被计入材料数量。</p></header>
      <div className="export-layout">
        <section className="export-options">
          <h2>选择文件格式</h2><div className="format-list">{formats.map(({ id, label, detail, icon: Icon }) => <button key={id} className={format === id ? 'selected' : ''} onClick={() => { setFormat(id); setResult(null); }}><Icon size={22} /><span><strong>{label}</strong><small>{detail}</small></span>{format === id && <Check size={18} />}</button>)}</div>
          {format === 'PDF' && <Field label="纸张尺寸"><Select value={paperSize} onChange={(event) => setPaperSize(event.target.value)}><option value="A4">A4 纵向</option><option value="A3">A3 纵向</option></Select></Field>}
          <div className="check-options"><label><input type="checkbox" checked={includeCodes} onChange={(e) => setIncludeCodes(e.target.checked)} /><span><strong>格内显示色号</strong><small>打印图纸更易逐格核对</small></span></label><label><input type="checkbox" checked={includeMaterials} onChange={(e) => setIncludeMaterials(e.target.checked)} /><span><strong>附带材料清单</strong><small>净用量与 5% 备损建议</small></span></label></div>
        </section>
        <aside className="export-summary">
          <div className="export-preview"><FileText size={42} /><span>{format}</span><div className="preview-lines"><i /><i /><i /><i /></div></div>
          <h2>{project.data?.name}</h2><div className="export-meta"><span>图纸版本<strong>v{pattern.data.version}</strong></span><span>网格尺寸<strong>{pattern.data.width} × {pattern.data.height}</strong></span><span>色板版本<strong>{pattern.data.palette.version}</strong></span></div>
          {exportMutation.error && <ApiErrorCallout error={exportMutation.error} />}
          {!result ? <Button className="full-button" icon={<PackageCheck size={17} />} loading={exportMutation.isPending} onClick={() => exportMutation.mutate()}>生成 {format} 文件</Button> : <div className="export-ready"><span className="ready-icon"><Check size={22} /></span><strong>文件已准备好</strong><p>{result.fileName} · {result.fileSize ? Math.ceil(result.fileSize / 1024) + ' KB' : ''}</p><Button className="full-button" icon={<Download size={17} />} onClick={download}>下载文件</Button><small>下载链接有效至 {formatDate(result.downloadUrlExpiresAt)}</small></div>}
          <Link className="text-link centered" to={'/projects/' + projectId + '/editor'}>返回编辑图纸</Link>
        </aside>
      </div>
    </div>
  );
}
