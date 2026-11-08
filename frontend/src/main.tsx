import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/global.css';
import './styles/app.css';

async function bootstrap() {
  if ((import.meta.env.VITE_API_MODE || 'mock') === 'mock') {
    const { worker } = await import('./mocks/browser');
    await worker.start({ onUnhandledRequest: 'bypass' });
  }
  createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
}

bootstrap().catch((error) => {
  const message = error instanceof Error ? error.message : '未知错误';
  document.getElementById('root')!.innerHTML = '<div class="fatal-error"><h1>应用启动失败</h1><p>' + message + '</p></div>';
});
