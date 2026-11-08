# 拼豆图纸工作台前端

React + TypeScript + Vite 实现的拼豆图纸生成与编辑前端。默认使用 MSW Mock，可独立演示完整 P0 流程；切换环境变量后可连接 FastAPI 后端。

## 启动

    pnpm install
    pnpm dev

访问 http://127.0.0.1:5173。

Mock 登录信息：

- 手机号：13800000000
- 验证码：123456
- 业务码：PD-TEST-CODE-FOR-DEV

## API 模式

默认模式为 Mock。复制 .env.example 为 .env.local 后按需设置：

    VITE_API_MODE=mock
    VITE_API_BASE_URL=/api/v1

连接本地后端时使用：

    VITE_API_MODE=real
    VITE_API_BASE_URL=/api/v1

Vite 会把 /api 请求代理到 http://127.0.0.1:8000。

## 检查

    pnpm lint
    pnpm test
    pnpm build

图纸编辑器使用 Canvas 2D 渲染，按路由懒加载；格子操作停止 2 秒后自动批量保存，并通过图纸版本处理并发冲突。
