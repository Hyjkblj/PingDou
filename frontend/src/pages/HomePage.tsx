import { useQuery } from '@tanstack/react-query';
import { ArrowRight, FolderKanban, ImagePlus, PackageCheck, TicketCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../api/services';
import { BeadArtwork } from '../components/visual/BeadArtwork';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/Status';
import { formatDate } from '../lib/utils';
import { useAuthStore } from '../stores/auth';

export function HomePage() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const projects = useQuery({ queryKey: ['projects', 'home'], queryFn: () => api.projects(), enabled: isAuthenticated });
  const recent = projects.data?.slice(0, 3) || [];

  return (
    <div className="home-page">
      <section className="home-workspace">
        <div className="home-copy">
          <span className="eyebrow">从一张图片开始</span>
          <h1>把喜欢的图，变成真正能拼的图纸。</h1>
          <p>抠图、白底预览、卡通优化、色号匹配与材料清单在同一条制作流程里完成。</p>
          <div className="home-actions">
            <Link to={isAuthenticated ? '/redeem' : '/login?next=/redeem'}>
              <Button icon={<TicketCheck size={18} />}>兑换并开始</Button>
            </Link>
            <Link to="/checkout"><Button variant="secondary" icon={<PackageCheck size={18} />}>购买单次服务</Button></Link>
          </div>
          <div className="service-strip">
            <div><strong>1 张</strong><span>最终图纸</span></div>
            <div><strong>2 版</strong><span>AI 候选</span></div>
            <div><strong>PNG / PDF / CSV</strong><span>完整导出</span></div>
          </div>
        </div>
        <div className="home-art" aria-label="拼豆图纸预览">
          <div className="art-heading"><span>32 × 32</span><strong>Hama 基础色板</strong></div>
          <BeadArtwork size={420} />
          <div className="art-colors">
            {['#f2c39f', '#d99570', '#75462e', '#252525', '#ef8eac'].map((color, i) => (
              <span key={color}><i style={{ background: color }} />H0{i + 3}</span>
            ))}
          </div>
        </div>
      </section>

      <section className="dashboard-band">
        <div className="section-heading">
          <div><span className="eyebrow">继续创作</span><h2>{isAuthenticated ? '最近项目' : '一次清晰的制作流程'}</h2></div>
          {isAuthenticated && <Link to="/projects" className="text-link">查看全部 <ArrowRight size={16} /></Link>}
        </div>
        {isAuthenticated && recent.length ? (
          <div className="project-row">
            {recent.map((project, index) => (
              <Link className="project-card" key={project.id} to={'/projects/' + project.id + (project.latestPatternId ? '/editor' : '/analysis')}>
                <div className={'project-thumb thumb-' + (index % 3)}><BeadArtwork size={180} variant={index === 1 ? 'flower' : 'cat'} /></div>
                <div className="project-card-body"><StatusBadge status={project.status} /><h3>{project.name}</h3><p>{formatDate(project.updatedAt)} 更新</p></div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="workflow-summary">
            <div><span><ImagePlus size={20} /></span><strong>处理图片</strong><p>分析图片后抠出主体，可选择白底展示或实体豆背景。</p></div>
            <div><span><span className="step-number">02</span></span><strong>确认基底</strong><p>按需要生成动漫候选图，确认最终用于转图纸的版本。</p></div>
            <div><span><FolderKanban size={20} /></span><strong>编辑与导出</strong><p>逐格修改色号，实时核对豆子数量并导出材料清单。</p></div>
          </div>
        )}
      </section>
    </div>
  );
}
