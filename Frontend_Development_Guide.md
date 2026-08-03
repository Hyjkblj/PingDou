# 拼豆图纸生成平台前端开发文档

> 文档版本：V1.0  
> 文档日期：2026-08-04  
> 需求基线：[PingDou_PRD.md](./PingDou_PRD.md) V1.1  
> 开发原则：契约优先、Mock 先行、前后端独立开发

## 1. 文档目标

本文档用于指导 Web 前端独立完成拼豆图纸生成平台的页面、状态管理、Canvas 编辑器、异步任务交互、订单与业务码流程以及自动化测试。

前端不依赖后端实现进度。接口字段以 [API_Specification.md](./API_Specification.md) 为唯一契约，开发期间通过 MSW 和固定夹具模拟接口、支付结果、AI 任务、图纸任务和导出任务。

## 2. 前端职责边界

### 2.1 前端负责

- 页面路由、响应式布局和交互状态。
- 图片选择、文件格式及大小的前置校验。
- 裁剪、旋转、缩放、主体位置调整和蒙版局部修正交互。
- 白底展示、透明留空、保留原背景、实体背景的预览表达。
- AI、抠图、图纸和导出异步任务的进度展示与错误恢复。
- 拼豆网格 Canvas 渲染和手动编辑。
- 前端增量豆子统计和服务端统计结果核对。
- 自动保存、离线暂存、版本冲突提示。
- 埋点、错误上报、性能采样和用户反馈入口。

### 2.2 前端不负责

- 业务码真实性、可用性和并发兑换裁决。
- 支付结果判定和服务权益最终状态。
- AI 服务商调用、提示词模板和内容安全审核。
- 抠图算法、色板匹配、可制造性评分和最终豆子统计权威结果。
- PDF、CSV、高清 PNG 的服务端生成。
- 对象存储签名、文件病毒检查和数据保留策略执行。

## 3. 推荐技术栈

| 领域 | 推荐方案 | 说明 |
| --- | --- | --- |
| 基础框架 | React + TypeScript + Vite | 前后端完全分离，构建和部署简单 |
| 路由 | React Router | 支持项目和任务深链接 |
| 服务端状态 | TanStack Query | 缓存、轮询、重试和请求失效 |
| 本地状态 | Zustand | 编辑器、工具栏和临时交互状态 |
| 表单 | React Hook Form + Zod | 与接口 Schema 对齐 |
| UI | Tailwind CSS + shadcn/ui | 使用稳定基础组件并保持可访问性 |
| 图标 | lucide-react | 统一工具栏和命令图标 |
| Canvas | 原生 Canvas 2D + OffscreenCanvas | 避免为每个格子创建 DOM 节点 |
| 裁剪 | Cropper.js 或 react-easy-crop | 裁剪、缩放和旋转 |
| Mock | MSW | 浏览器、单元测试和 Storybook 共用接口模拟 |
| 测试 | Vitest + Testing Library + Playwright | 单元、组件和端到端测试 |
| 监控 | Sentry 或等价服务 | JS 错误、接口异常和性能追踪 |

依赖版本在项目初始化时锁定，不在业务代码中依赖未封装的第三方 API。Canvas、上传、任务订阅和埋点必须通过本地适配层访问。

## 4. 独立开发机制

### 4.1 接口契约

- 接口基路径统一为 `/api/v1`。
- 后端维护 OpenAPI 文件，前端通过生成器产生请求类型和 DTO 类型。
- 在 OpenAPI 文件可用前，前端按 [API_Specification.md](./API_Specification.md) 手工维护临时类型。
- DTO 类型不得直接作为页面状态类型，必须经过 mapper 转换。
- 已冻结字段只能新增，不能在同一 API 版本中改名或改变语义。

### 4.2 Mock 模式

前端必须支持以下启动模式：

```text
VITE_API_MODE=mock   使用 MSW 和本地夹具
VITE_API_MODE=real   请求真实后端
```

Mock 层需要模拟：

- 正常返回、空数据、权限不足、业务码失效和版本冲突。
- 上传、抠图、AI、图纸、导出任务的排队、处理中、成功、失败和超时。
- SSE 断开后的轮询降级。
- 技术失败恢复服务权益。
- 白底展示与实体白豆背景的不同统计结果。

### 4.3 固定夹具

前后端共用以下语义化夹具名称：

| 夹具 | 场景 |
| --- | --- |
| `portrait_clean` | 单人、背景简单、可直接转换 |
| `portrait_complex` | 真人、背景复杂、建议 AI 美化 |
| `pet_white_fur` | 白色毛发，用于白底边缘测试 |
| `transparent_logo` | 透明背景图案 |
| `large_pattern_150` | 150×150 大网格性能测试 |
| `code_valid` | 可正常兑换的业务码 |
| `code_redeemed` | 已绑定其他项目的业务码 |
| `job_retry_then_success` | 首次失败、技术重试后成功 |

## 5. 前端目录建议

```text
src/
  app/
    router/
    providers/
    config/
  api/
    generated/
    client.ts
    mappers/
    queryKeys.ts
  features/
    auth/
    checkout/
    redemption/
    projects/
    upload/
    imageAnalysis/
    backgroundRemoval/
    aiGeneration/
    baseImage/
    palettes/
    patternGeneration/
    patternEditor/
    exports/
  components/
    ui/
    feedback/
    layout/
  canvas/
    renderer/
    tools/
    commands/
    workers/
  mocks/
    handlers/
    fixtures/
    scenarios/
  telemetry/
  test/
```

模块之间通过公开入口文件导出能力。`patternEditor` 不得直接依赖订单页面，服务权益通过统一的 `EntitlementContext` 或查询结果传入。

## 6. 路由规划

| 路由 | 页面 | 权限 |
| --- | --- | --- |
| `/` | 首页、上传入口、业务码入口 | 公开 |
| `/checkout` | 单次服务购买页 | 公开 |
| `/orders/:orderId` | 支付及发码结果 | 当前用户 |
| `/redeem` | 业务码兑换 | 登录或手机号绑定 |
| `/projects` | 我的项目 | 登录 |
| `/projects/:projectId/analysis` | 图片分析和优化建议 | 有项目权益 |
| `/projects/:projectId/background` | 抠图和白底确认 | 有项目权益 |
| `/projects/:projectId/ai` | AI 候选图选择 | 有项目权益 |
| `/projects/:projectId/base-image` | 图片基底确认 | 有项目权益 |
| `/projects/:projectId/settings` | 网格、色板和高级参数 | 有项目权益 |
| `/projects/:projectId/editor` | 拼豆编辑器 | 有项目权益 |
| `/projects/:projectId/export` | 导出设置和下载 | 有项目权益 |

页面刷新后必须能够仅凭 URL 和接口数据恢复状态，不依赖上一个页面保留的内存对象。

## 7. 优先级开发规划

### 7.1 P0-A 工程基础与契约层

目标：在无后端环境下启动完整前端骨架。

交付内容：

- React、TypeScript、路由、Query、Zustand、样式和测试框架初始化。
- API Client、统一错误类型、请求 ID 和鉴权拦截器。
- MSW、夹具、异步任务模拟器和场景切换面板。
- 页面级错误边界、Toast、确认弹窗、空状态和加载骨架。
- OpenAPI 类型生成脚本占位。

验收标准：

- `mock` 模式不依赖任何后端即可访问全部 P0 页面。
- 可在开发环境切换正常、失败、超时和冲突场景。
- 页面刷新后 Mock 数据可重新恢复。

### 7.2 P0-B 登录、下单、发码与兑换

依赖：P0-A。

交付内容：

- 手机号登录或绑定流程。
- 商品说明、价格、服务范围和退款规则展示。
- 下单、支付结果轮询、业务码展示和复制。
- 业务码兑换、状态错误和已绑定项目跳转。
- 服务权益状态条，展示原图数量、AI 配额和编辑截止时间。

前端独立开发方式：使用 `code_valid`、`code_redeemed`、`code_expired` 等 Mock 场景。

验收标准：

- 重复点击下单不会创建多个前端请求。
- 兑换提交期间按钮保持稳定尺寸并防止重复提交。
- 已兑换业务码显示关联项目入口，不要求用户再次输入。

### 7.3 P0-C 上传、图片分析、抠图与白底服务

依赖：P0-A，兑换权益可使用 Mock。

交付内容：

- 拖拽上传、文件选择、格式、大小和分辨率校验。
- 上传进度、取消和失败重试。
- 图片质量分析结果和优化建议。
- 抠图任务进度、前景蒙版、边缘强度控制和局部恢复/擦除。
- 白底展示、透明留空、保留原背景、实体白豆、自定义实体背景模式。
- 明确显示“背景不计豆”或“背景参与计豆”。

验收标准：

- 白底展示仅改变预览合成，不修改前景蒙版。
- 实体背景模式必须要求选择色号。
- 白色毛发夹具在白底下可以切换透明对照检查。
- 切换背景模式后重新请求预转换结果和统计。

### 7.4 P0-D 拼豆专用 AI 与基底确认

依赖：P0-C。

交付内容：

- AI 推荐原因、是否包含在业务码权益、预计耗时展示。
- 风格、背景、相似度、构图和细节参数。
- 两张候选图异步生成、可制造性评分和原图对比。
- 低于 60 分候选图的警示，80 分及以上显示推荐状态。
- 追加候选图付费确认占位，不在前端伪造价格。
- 裁剪、旋转、镜像、缩放、主体移动和最终基底确认。

验收标准：

- 未确认付费或权益时不得创建额外 AI 任务。
- 任务失败后仍可选择原图继续。
- 确认基底后保存不可变版本 ID，并可回看历史候选图。

### 7.5 P0-E 参数设置、图纸生成与 Canvas 编辑器

依赖：P0-A，图纸接口可完全 Mock。

交付内容：

- 网格尺寸、豆子规格、物理尺寸和底板预设。
- 品牌色板、最大颜色数、合并强度、轮廓增强和背景语义。
- 图纸异步生成及可制造性评分展示。
- Canvas 渲染、缩放、平移、网格、坐标和色号显示。
- 画笔、橡皮、填充、吸管、整色替换、高亮、锁定、撤销和重做。
- 实时颜色用量和总豆子数。

验收标准：

- 150×150 网格的画笔反馈 P95 小于 50 ms。
- 缩放和平移不改变图纸矩阵。
- 透明格和白底展示均不计豆。
- 实体白豆背景准确进入统计。
- 撤销和重做至少保存 100 步。

### 7.6 P0-F 自动保存、项目历史与导出

依赖：P0-B、P0-E。

交付内容：

- 停止操作 2 秒后的增量自动保存。
- 保存中、已保存、失败、离线和冲突状态。
- 项目列表、搜索、筛选、重命名、复制和删除。
- PNG、PDF、CSV 导出配置和任务进度。
- 下载有效期、重复下载和失败重试。

验收标准：

- 页面关闭或切换项目之前触发强制保存。
- 网络恢复后自动提交离线操作。
- 导出失败不改变服务权益状态。
- 白底展示 PDF 的材料表不包含背景白豆。

### 7.7 P1

- 还原、均衡、制作优先三方案对比。
- CSV 和项目文件导入导出。
- 自定义色板、禁用未持有颜色和库存差额。
- 选区、复制粘贴、镜像、旋转和制作进度。
- 移动端轻编辑。

### 7.8 P2

- 小程序和桌面端适配。
- 完整移动端编辑器。
- AR 制作辅助。
- 图纸社区、授权和交易。

## 8. 核心状态模型

### 8.1 业务码与权益

```ts
type RedemptionCodeStatus =
  | 'UNREDEEMED'
  | 'BOUND'
  | 'IN_SERVICE'
  | 'GENERATED'
  | 'COMPLETED'
  | 'VOIDED'
  | 'EXPIRED';

type ServiceEntitlementStatus =
  | 'AVAILABLE'
  | 'ACTIVE'
  | 'GENERATED'
  | 'COMPLETED'
  | 'VOIDED';

interface ServiceEntitlementView {
  id: string;
  projectId: string;
  status: ServiceEntitlementStatus;
  sourceAssetLimit: 1;
  aiJobsRemaining: number;
  editExpiresAt: string | null;
  downloadExpiresAt: string | null;
}
```

前端只展示服务端返回的权益结果，不自行推导是否应当消耗或恢复业务码。

### 8.2 背景语义

```ts
type BackgroundMode =
  | 'WHITE_PREVIEW'
  | 'TRANSPARENT'
  | 'KEEP_ORIGINAL'
  | 'SOLID_WHITE_BEADS'
  | 'SOLID_CUSTOM_BEADS';
```

`WHITE_PREVIEW` 的 Canvas 清屏色为白色，但网格矩阵背景值仍为透明。只有 `SOLID_WHITE_BEADS` 和 `SOLID_CUSTOM_BEADS` 可以产生背景色号格子。

### 8.3 异步任务

```ts
type JobStatus =
  | 'QUEUED'
  | 'RUNNING'
  | 'REVIEWING'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'CANCELLED';

interface AsyncJob<T> {
  id: string;
  type: string;
  status: JobStatus;
  progress: number;
  stage: string | null;
  result: T | null;
  error: ApiError | null;
}
```

优先通过 SSE 接收状态，连接断开后使用 2 秒、3 秒、5 秒的退避轮询，任务结束后停止请求。

## 9. Canvas 编辑器设计

### 9.1 数据与视图分离

- 权威编辑数据为紧凑色号索引矩阵，不以 Canvas 像素作为数据源。
- Canvas 仅负责绘制颜色、网格、色号、坐标、高亮和选区。
- 色板索引 `0` 保留为空格，其他索引映射到项目锁定的色板版本。
- 单元格编辑以命令对象保存，用于撤销、重做和增量保存。

### 9.2 推荐数据结构

```ts
interface PatternDocument {
  patternId: string;
  version: number;
  width: number;
  height: number;
  paletteVersion: string;
  cells: Uint16Array;
  locked: Uint8Array;
}

interface CellChangeCommand {
  operationId: string;
  indexes: Uint32Array;
  before: Uint16Array;
  after: Uint16Array;
}
```

### 9.3 渲染策略

- 使用单个 Canvas 绘制颜色层，另一个 Canvas 绘制网格、坐标和交互覆盖层。
- 缩放较小时不绘制格内色号，达到可读阈值后再绘制文本。
- 仅重绘脏矩形或受影响区域，不在每次画笔移动时全量重绘。
- 统计计算放入 Web Worker，主线程只提交变更索引。
- 150×150 以上图纸避免创建逐格 React 组件。

### 9.4 编辑命令

- `PaintCellsCommand`
- `EraseCellsCommand`
- `FillRegionCommand`
- `ReplaceColorCommand`
- `LockCellsCommand`
- `ApplyAutoRepairCommand`

每个命令必须支持 `apply`、`revert`、`serialize`。自动修复作为单独命令，用户可以一次性撤销。

### 9.5 保存策略

- 前端将 2 秒内的连续画笔操作合并为批次。
- 每个批次携带 `operationId` 和当前 `patternVersion`。
- 收到 `409 VERSION_CONFLICT` 时暂停自动保存，拉取服务端最新版本并展示冲突处理。
- IndexedDB 保存未同步命令，不能只使用 localStorage。

## 10. 服务端状态管理

### 10.1 Query Key

```text
['me']
['order', orderId]
['entitlement', entitlementId]
['projects', filters]
['project', projectId]
['job', jobId]
['palettes']
['paletteColors', paletteId, version]
['pattern', patternId, version]
['colorUsage', patternId, version]
['exportJob', exportJobId]
```

### 10.2 缓存原则

- 色板和品牌信息使用长缓存，并按色板版本作为 Key。
- 任务状态使用短缓存，成功后立即失效对应项目查询。
- 图纸矩阵不放入全局 Query Cache 反复复制，加载后进入编辑器 Store。
- 页面卸载前清理大型 TypedArray 引用。

## 11. 错误与恢复

| 场景 | 前端行为 |
| --- | --- |
| 业务码无效 | 保留输入并展示明确错误码说明 |
| 业务码已兑换 | 展示关联项目入口 |
| 上传失败 | 保留文件信息，允许重试上传 |
| 抠图失败 | 允许重试或保留原背景继续 |
| AI 失败 | 允许使用原图或技术重试 |
| 图纸生成失败 | 保留参数，恢复服务权益状态后重试 |
| 自动保存失败 | 本地暂存并持续显示未同步状态 |
| 版本冲突 | 禁止静默覆盖，提供加载最新或另存版本 |
| SSE 断开 | 自动切换轮询，不提示技术术语 |
| 导出失败 | 保留导出配置并允许重试 |

错误文案来自前端错误码映射表，不直接展示服务端堆栈、第三方服务商名称或原始异常信息。

## 12. 性能要求

- 首屏核心交互资源 gzip 后建议小于 300 KB，Canvas 和编辑器模块按路由懒加载。
- 150×150 图纸首次绘制目标小于 500 ms。
- 画笔反馈 P95 小于 50 ms。
- 增量统计目标小于 100 ms。
- 项目列表使用分页或虚拟列表。
- 大图、蒙版和候选图使用缩略图，放大时再请求原图。
- 图片处理页面离开后释放 Object URL、ImageBitmap 和 Worker。

## 13. 可访问性与兼容性

- 支持最近两个大版本的 Chrome、Edge 和 Safari。
- Canvas 工具按钮必须提供文本 Tooltip 和可访问名称。
- 颜色信息不能只通过色块表达，同时显示色号和名称。
- 所有弹窗具备焦点锁定、Esc 关闭和返回焦点。
- 键盘可执行撤销、重做、缩放、保存等主要命令。
- 移动端 P0 允许查看和轻编辑，复杂工具显示桌面端建议。

## 14. 安全要求

- 不在 localStorage 保存业务码明文、手机号、访问令牌或签名下载地址。
- 业务码输入框关闭浏览器自动填充和日志采集。
- 上传文件名仅用于展示，渲染时进行转义。
- 下载地址按服务端有效期使用，不进行永久缓存。
- 埋点不得包含业务码、原图 URL、完整提示词和手机号。

## 15. 测试策略

### 15.1 单元测试

- 背景模式与计豆规则。
- 网格坐标和色号索引转换。
- 增量统计、撤销、重做和命令合并。
- API DTO 到视图模型的 mapper。
- 错误码到文案和恢复动作的映射。

### 15.2 组件测试

- 业务码兑换表单。
- 上传与进度状态。
- AI 候选图评分卡。
- 背景模式控制和材料统计变化。
- 导出设置弹窗。

### 15.3 端到端测试

P0 必须覆盖：

1. 支付完成、发码、兑换、上传、白底确认、直接转图、编辑和导出。
2. 建议 AI、美化成功、选择候选图、生成和导出。
3. AI 技术失败后恢复权益并使用原图继续。
4. 白底展示不计豆，切换实体白豆后统计增加。
5. 编辑器离线保存、恢复网络并同步。
6. 业务码已兑换时跳转关联项目。

### 15.4 性能测试

- 29×29、100×100、150×150、300×300 四档网格。
- 连续画笔 10 秒、整色替换、填充大区域和 100 步撤销重做。
- Canvas 截图像素检查，确保非空白、无错位和文字重叠。

## 16. 埋点与监控

前端实现 PRD 中的事件，并统一附带：

```text
request_id
session_id
project_id
entitlement_id
page
app_version
api_mode
```

禁止附带原图、业务码、完整手机号和内部 AI 提示词。Canvas 长任务、接口 P95、任务等待时间和自动保存失败需要单独监控。

## 17. 联调门禁

| 门禁 | 前端准备 | 后端准备 | 通过条件 |
| --- | --- | --- | --- |
| G1 账号与兑换 | Mock 流程和错误状态完成 | 登录、订单、发码、兑换接口 | 契约测试和并发兑换通过 |
| G2 图片处理 | 上传、分析、白底页面完成 | 上传、分析、抠图任务 | 白底语义和蒙版字段一致 |
| G3 AI | 候选图和任务状态完成 | AI Gateway 和评分结果 | 失败恢复权益一致 |
| G4 图纸 | 参数页和 Canvas 完成 | 色板、生成、矩阵和统计 | 固定夹具输出一致 |
| G5 保存导出 | 自动保存和导出页完成 | 版本控制、导出任务 | 冲突、重试和下载通过 |

前后端在每个门禁前分别通过自己的测试，不等待对方完成全部 P0。

## 18. 前端完成定义

一个 P0 功能只有满足以下条件才算完成：

- Mock 和真实 API 模式均可运行。
- 正常、加载、空、失败、超时和无权限状态齐全。
- TypeScript 无错误，Lint 和单元测试通过。
- 核心交互具有 Playwright 测试。
- 接口字段未绕过 mapper 直接散落在组件中。
- 埋点、错误上报和请求 ID 已接入。
- 移动端和桌面端没有文字溢出或控件重叠。
- 对应 [API_Specification.md](./API_Specification.md) 契约版本已记录。
