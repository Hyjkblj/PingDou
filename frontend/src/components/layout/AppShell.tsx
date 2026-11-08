import { useState } from 'react';
import { FolderKanban, LogIn, LogOut, Menu, Plus, TicketCheck, X } from 'lucide-react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/auth';
import { Button } from '../ui/Button';

export function AppShell() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const isEditor = location.pathname.endsWith('/editor');
  const { isAuthenticated, user, logout } = useAuthStore();
  const links = [
    { to: '/projects', label: '我的项目', icon: FolderKanban },
    { to: '/redeem', label: '兑换业务码', icon: TicketCheck },
  ];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/" className="brand" aria-label="拼豆工作台首页">
            <span className="brand-grid" aria-hidden="true"><i /><i /><i /><i /></span>
            <span><strong>拼豆</strong><small>图纸工作台</small></span>
          </Link>
          <nav className={'main-nav ' + (open ? 'main-nav-open' : '')} aria-label="主导航">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} onClick={() => setOpen(false)} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <Icon size={17} />{label}
              </NavLink>
            ))}
            <NavLink to="/checkout" onClick={() => setOpen(false)} className="nav-link nav-buy"><Plus size={17} />购买服务</NavLink>
          </nav>
          <div className="topbar-actions">
            {isAuthenticated ? (
              <button className="user-menu" onClick={logout} title="退出登录">
                <span>{user?.phoneMasked}</span><LogOut size={16} />
              </button>
            ) : (
              <Link to="/login"><Button variant="secondary" size="sm" icon={<LogIn size={16} />}>登录</Button></Link>
            )}
            <button className="menu-button" onClick={() => setOpen(!open)} aria-label={open ? '关闭导航' : '打开导航'}>
              {open ? <X size={21} /> : <Menu size={21} />}
            </button>
          </div>
        </div>
      </header>
      <main className="page-main"><Outlet /></main>
      {!isEditor && <footer className="footer"><span>拼豆图纸工作台</span><span>背景展示色与实体豆色独立计算</span></footer>}
    </div>
  );
}
