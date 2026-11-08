import { Check, ChevronRight } from 'lucide-react';
import { Link, Outlet, useLocation, useParams } from 'react-router-dom';

const steps = [
  ['analysis', '图片分析'], ['background', '抠图与背景'], ['ai', 'AI 优化'],
  ['base-image', '确认基底'], ['settings', '图纸参数'], ['editor', '编辑图纸'], ['export', '导出'],
];

export function ProjectShell() {
  const { projectId = '' } = useParams();
  const location = useLocation();
  const current = Math.max(0, steps.findIndex(([path]) => location.pathname.includes('/' + path)));
  return (
    <div className="project-page">
      <div className="project-trail" aria-label="项目制作进度">
        {steps.map(([path, label], index) => (
          <div key={path} className={'trail-item ' + (index === current ? 'current' : index < current ? 'done' : '')}>
            <Link to={'/projects/' + projectId + '/' + path}>
              <span>{index < current ? <Check size={13} /> : index + 1}</span>{label}
            </Link>
            {index < steps.length - 1 && <ChevronRight size={14} />}
          </div>
        ))}
      </div>
      <Outlet />
    </div>
  );
}
