import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, MoreHorizontal, Pencil, Plus, Search, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/services';
import { EmptyState, ErrorState, LoadingState } from '../components/feedback/States';
import { BeadArtwork } from '../components/visual/BeadArtwork';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Field';
import { StatusBadge } from '../components/ui/Status';
import { formatDate } from '../lib/utils';
import { AuthRequired } from './AuthPages';

const resumePath = (project: { status: string; latestPatternId?: string | null }) => {
  if (project.latestPatternId || project.status === 'EDITING' || project.status === 'COMPLETED') return 'editor';
  if (project.status === 'PATTERN_PENDING') return 'settings';
  if (project.status === 'BASE_IMAGE_PENDING') return 'base-image';
  return 'analysis';
};

export function ProjectsPage() {
  const [query, setQuery] = useState('');
  const [menu, setMenu] = useState<string | null>(null);
  const client = useQueryClient();
  const projects = useQuery({ queryKey: ['projects', query], queryFn: () => api.projects(query) });
  const create = useMutation({
    mutationFn: () => api.createProject('未命名拼豆项目'),
    onSuccess: () => client.invalidateQueries({ queryKey: ['projects'] }),
  });
  const remove = useMutation({
    mutationFn: api.deleteProject,
    onSuccess: () => client.invalidateQueries({ queryKey: ['projects'] }),
  });
  const rename = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => api.renameProject(id, name),
    onSuccess: () => client.invalidateQueries({ queryKey: ['projects'] }),
  });

  return (
    <AuthRequired>
      <div className="projects-page page-container">
        <div className="page-heading-row">
          <div><span className="eyebrow">创作记录</span><h1>我的项目</h1><p>从上次保存的位置继续，图纸、材料统计与导出版本会一起恢复。</p></div>
          <Button icon={<Plus size={17} />} loading={create.isPending} onClick={() => create.mutate()}>新建空白项目</Button>
        </div>
        <div className="project-toolbar">
          <label className="search-box"><Search size={17} /><Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索项目名称" /></label>
          <div className="project-count">{projects.data?.length || 0} 个项目</div>
        </div>
        {projects.isLoading ? <LoadingState label="正在读取项目" /> : projects.error ? <ErrorState error={projects.error} onRetry={() => projects.refetch()} /> : !projects.data?.length ? (
          <EmptyState title="还没有项目" description="兑换业务码后会自动创建项目，也可以先建立空白项目。" action={<Link to="/redeem"><Button>兑换业务码</Button></Link>} />
        ) : (
          <div className="projects-grid">
            {projects.data.map((project, index) => (
              <article className="project-list-card" key={project.id}>
                <Link className="project-list-preview" to={'/projects/' + project.id + '/' + resumePath(project)}>
                  <BeadArtwork size={260} variant={index % 3 === 1 ? 'flower' : 'cat'} />
                  <StatusBadge status={project.status} />
                </Link>
                <div className="project-list-info">
                  <div><h2>{project.name}</h2><p>{formatDate(project.updatedAt)} 更新</p></div>
                  <button className="icon-button" aria-label="项目操作" onClick={() => setMenu(menu === project.id ? null : project.id)}><MoreHorizontal size={19} /></button>
                  {menu === project.id && (
                    <div className="context-menu">
                      <button onClick={() => { const name = prompt('新的项目名称', project.name); if (name?.trim()) rename.mutate({ id: project.id, name: name.trim() }); setMenu(null); }}><Pencil size={15} />重命名</button>
                      <button className="danger" onClick={() => { if (confirm('删除后无法恢复，确认删除这个项目？')) remove.mutate(project.id); setMenu(null); }}><Trash2 size={15} />删除</button>
                    </div>
                  )}
                </div>
                <Link className="project-resume" to={'/projects/' + project.id + '/' + resumePath(project)}>继续制作 <ArrowRight size={16} /></Link>
              </article>
            ))}
          </div>
        )}
      </div>
    </AuthRequired>
  );
}
