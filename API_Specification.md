# 拼豆图纸生成平台接口文档

> 文档版本：V1.0  
> 文档日期：2026-08-04  
> 基础路径：`/api/v1`  
> 需求基线：[PingDou_PRD.md](./PingDou_PRD.md) V1.1  
> 使用方：[Frontend_Development_Guide.md](./Frontend_Development_Guide.md)、[Backend_Development_Guide.md](./Backend_Development_Guide.md)

## 1. 文档目的

本文档是前后端独立开发的接口契约。P0 接口的路径、状态枚举、字段含义、错误码和幂等规则在开发开始后冻结。后端以 OpenAPI 为机器可读源，本文档用于解释业务语义和提供示例。

## 2. 通用约定

### 2.1 请求

```http
Content-Type: application/json
Authorization: Bearer <access_token>
X-Request-ID: <optional-client-request-id>
Idempotency-Key: <required-for-create-or-consume-operations>
```

- `Authorization` 在公开接口中可省略。
- `Idempotency-Key` 建议使用 UUID，有效期至少 24 小时。
- 日期时间使用 ISO 8601 UTC，例如 `2026-08-04T08:30:00Z`。
- 金额使用人民币分，例如 `1990` 表示 ¥19.90。
- ID 使用 UUID 字符串。
- 枚举使用大写下划线格式。
- 未提供的可选字段使用 `null`，不使用空字符串代替。

### 2.2 成功响应

```json
{
  "requestId": "req_8c2e8fd2",
  "data": {},
  "meta": null
}
```

分页响应：

```json
{
  "requestId": "req_8c2e8fd2",
  "data": [],
  "meta": {
    "nextCursor": "cursor_xxx",
    "hasMore": true
  }
}
```

### 2.3 错误响应

```json
{
  "requestId": "req_8c2e8fd2",
  "error": {
    "code": "CODE_ALREADY_REDEEMED",
    "message": "该业务码已经兑换",
    "retryable": false,
    "details": {
      "projectId": "5ee30f87-7df7-40f9-b453-2589ee4ddab4"
    }
  }
}
```

前端依据 `code` 决定交互，不解析 `message`。

### 2.4 HTTP 状态码

| 状态码 | 使用场景 |
| ---: | --- |
| 200 | 查询、更新、幂等重放成功 |
| 201 | 资源创建成功 |
| 202 | 异步任务已接受 |
| 204 | 删除或无响应体操作成功 |
| 400 | 参数或业务前置条件错误 |
| 401 | 未登录或令牌失效 |
| 403 | 无权限或服务权益不可用 |
| 404 | 资源不存在 |
| 409 | 幂等冲突、版本冲突、并发兑换冲突 |
| 413 | 文件过大 |
| 422 | Schema 校验失败 |
| 429 | 请求频率超过限制 |
| 500 | 未分类服务端错误 |
| 502 | 第三方服务失败 |
| 503 | 服务暂时不可用 |

## 3. 公共枚举

### 3.1 业务码状态

```text
UNREDEEMED
BOUND
IN_SERVICE
GENERATED
COMPLETED
VOIDED
EXPIRED
```

### 3.2 订单状态

```text
PENDING_PAYMENT
PAID
CLOSED
REFUNDED
```

### 3.3 服务权益状态

```text
AVAILABLE
ACTIVE
GENERATED
COMPLETED
VOIDED
```

### 3.4 异步任务状态

```text
QUEUED
RUNNING
REVIEWING
SUCCEEDED
FAILED
CANCELLED
```

### 3.5 背景模式

```text
WHITE_PREVIEW
TRANSPARENT
KEEP_ORIGINAL
SOLID_WHITE_BEADS
SOLID_CUSTOM_BEADS
```

### 3.6 项目状态

```text
DRAFT
ANALYZING
BASE_IMAGE_PENDING
PATTERN_PENDING
EDITING
COMPLETED
DELETED
```

### 3.7 资产类型

```text
SOURCE_IMAGE
FOREGROUND_IMAGE
SUBJECT_MASK
WHITE_PREVIEW
AI_CANDIDATE
PATTERN_PREVIEW
EXPORT_FILE
```

## 4. 公共 Schema

### 4.1 `ApiError`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | 稳定错误码 |
| message | string | 是 | 用户可理解的默认文案 |
| retryable | boolean | 是 | 是否允许原请求重试 |
| details | object/null | 是 | 结构化上下文 |

### 4.2 `AsyncJob`

```json
{
  "id": "fb0cd2d1-76e8-473d-aacf-c8063f2cb996",
  "type": "AI_GENERATION",
  "status": "RUNNING",
  "progress": 45,
  "stage": "GENERATING_CANDIDATES",
  "createdAt": "2026-08-04T08:30:00Z",
  "updatedAt": "2026-08-04T08:30:24Z",
  "result": null,
  "error": null
}
```

`progress` 范围为 0 至 100，只用于展示，业务判断以 `status` 为准。

### 4.3 `Asset`

```json
{
  "id": "4ef982f2-d1b7-4f4c-b84c-00411638dbbf",
  "type": "SOURCE_IMAGE",
  "fileName": "portrait.png",
  "mimeType": "image/png",
  "size": 824512,
  "width": 2048,
  "height": 2048,
  "previewUrl": "https://signed.example/preview",
  "createdAt": "2026-08-04T08:30:00Z"
}
```

### 4.4 `ManufacturabilityScore`

```json
{
  "total": 84,
  "recognizability": 90,
  "outlineIntegrity": 86,
  "colorEconomy": 78,
  "connectivity": 82,
  "costAndSize": 76,
  "estimatedManualEditCells": 42,
  "isolatedCellRatio": 0.012,
  "engineVersion": "engine-1.0.0"
}
```

## 5. 接口优先级总览

| 优先级 | 接口范围 |
| --- | --- |
| P0-A | 鉴权、商品、订单、支付结果、业务码、服务权益、通用任务 |
| P0-B | 项目、上传、图片分析、抠图、白底预览 |
| P0-C | AI 候选图、基底确认、色板、图纸生成 |
| P0-D | 图纸矩阵、增量编辑、统计、项目保存、导出 |
| P1 | 三方案、CSV 导入、自定义色板、库存、制作进度 |
| P2 | AR、社区、授权交易和团队空间 |

## 6. 鉴权接口

### 6.1 发送短信验证码

`POST /auth/sms/send`

权限：公开。需要频率限制。

请求：

```json
{
  "phone": "13800000000",
  "scene": "LOGIN"
}
```

响应：

```json
{
  "requestId": "req_xxx",
  "data": {
    "cooldownSeconds": 60
  },
  "meta": null
}
```

### 6.2 手机号登录

`POST /auth/sms/login`

请求：

```json
{
  "phone": "13800000000",
  "code": "123456"
}
```

响应：

```json
{
  "requestId": "req_xxx",
  "data": {
    "accessToken": "jwt_access",
    "expiresIn": 7200,
    "refreshToken": "jwt_refresh",
    "user": {
      "id": "1bf2a3b0-1d7c-483c-87b0-f739ed9cbe56",
      "phoneMasked": "138****0000"
    }
  },
  "meta": null
}
```

### 6.3 刷新令牌

`POST /auth/refresh`

### 6.4 当前用户

`GET /users/me`

## 7. 商品、订单与支付

### 7.1 查询当前商品

`GET /products/current`

权限：公开。

响应：

```json
{
  "requestId": "req_xxx",
  "data": {
    "id": "5a508dcb-bc14-4078-8f2f-3d460c0147ef",
    "name": "AI 拼豆图纸制作兑换码",
    "priceCents": 1290,
    "listPriceCents": 1990,
    "currency": "CNY",
    "sourceAssetLimit": 1,
    "aiCandidateCount": 2,
    "editWindowHours": 72,
    "downloadRetentionDays": 30,
    "codeValidityDays": 180,
    "exportFormats": ["PNG", "PDF", "CSV"],
    "refundPolicyVersion": "2026-08-01"
  },
  "meta": null
}
```

### 7.2 创建订单

`POST /orders`

权限：登录。`Idempotency-Key` 必填。

请求：

```json
{
  "productId": "5a508dcb-bc14-4078-8f2f-3d460c0147ef",
  "channel": "WECHAT_PAY"
}
```

响应 `201`：

```json
{
  "requestId": "req_xxx",
  "data": {
    "id": "5f91b6b2-7abe-437d-97c4-390a10dbe08f",
    "status": "PENDING_PAYMENT",
    "amountCents": 1290,
    "payment": {
      "channel": "WECHAT_PAY",
      "payload": {
        "prepayId": "wx_xxx"
      },
      "expiresAt": "2026-08-04T09:00:00Z"
    }
  },
  "meta": null
}
```

客户端不得提交金额。

### 7.3 查询订单

`GET /orders/{orderId}`

响应：

```json
{
  "requestId": "req_xxx",
  "data": {
    "id": "5f91b6b2-7abe-437d-97c4-390a10dbe08f",
    "status": "PAID",
    "amountCents": 1290,
    "paidAt": "2026-08-04T08:40:00Z",
    "redemptionCode": {
      "code": "PD-7K4M-X9Q2-H6TR",
      "status": "UNREDEEMED",
      "expiresAt": "2027-01-31T08:40:00Z"
    }
  },
  "meta": null
}
```

完整业务码只对订单所属用户、且业务码仍为 `UNREDEEMED` 时返回。后端使用 KMS 加密副本完成交付，兑换、退款、作废或过期后只返回 `maskedCode`，不得进入日志和埋点。

### 7.4 支付回调

`POST /payments/callback/{channel}`

权限：支付渠道签名，不使用用户 JWT。该接口仅供渠道访问，不由前端调用。

要求：

- 验证签名、商户、订单号和金额。
- 重复回调返回渠道要求的成功响应。
- 订单与发码通过事务和 Outbox 保证最终一致。

## 8. 业务码与服务权益

### 8.1 兑换业务码

`POST /redemption-codes/redeem`

权限：登录并绑定手机号。`Idempotency-Key` 必填。

请求：

```json
{
  "code": "PD-7K4M-X9Q2-H6TR"
}
```

响应 `201`：

```json
{
  "requestId": "req_xxx",
  "data": {
    "redemptionCodeStatus": "BOUND",
    "project": {
      "id": "5ee30f87-7df7-40f9-b453-2589ee4ddab4",
      "status": "DRAFT"
    },
    "entitlement": {
      "id": "23951021-a68f-4f88-92dd-a7a606d443f5",
      "status": "AVAILABLE",
      "sourceAssetLimit": 1,
      "aiJobsTotal": 1,
      "aiJobsUsed": 0,
      "editExpiresAt": null,
      "downloadExpiresAt": null
    }
  },
  "meta": null
}
```

已由当前用户兑换时返回 `200` 和相同项目；被其他用户兑换时返回 `409 CODE_ALREADY_REDEEMED`。

### 8.2 查询服务权益

`GET /service-entitlements/{entitlementId}`

响应字段：

```json
{
  "id": "23951021-a68f-4f88-92dd-a7a606d443f5",
  "projectId": "5ee30f87-7df7-40f9-b453-2589ee4ddab4",
  "status": "ACTIVE",
  "sourceAssetLimit": 1,
  "sourceAssetsUsed": 1,
  "aiJobsTotal": 1,
  "aiJobsUsed": 0,
  "editExpiresAt": null,
  "downloadExpiresAt": null
}
```

## 9. 项目接口

### 9.1 项目列表

`GET /projects?cursor=&limit=20&status=&query=`

### 9.2 项目详情

`GET /projects/{projectId}`

响应包含当前状态、权益 ID、源图、确认基底、当前图纸版本和保存状态摘要，不默认返回完整矩阵。

### 9.3 更新项目

`PATCH /projects/{projectId}`

请求：

```json
{
  "name": "小明头像拼豆"
}
```

### 9.4 删除项目

`DELETE /projects/{projectId}`

响应 `204`，执行软删除。

### 9.5 复制项目

`POST /projects/{projectId}/duplicate`

P1。复制项目不会复制原业务码权益；创建独立可编辑图纸时需要新的服务权益。

## 10. 文件上传

### 10.1 初始化上传

`POST /assets/upload-init`

权限：登录且拥有项目权益。`Idempotency-Key` 必填。

请求：

```json
{
  "projectId": "5ee30f87-7df7-40f9-b453-2589ee4ddab4",
  "fileName": "portrait.png",
  "mimeType": "image/png",
  "size": 824512,
  "sha256": "f17a..."
}
```

响应：

```json
{
  "requestId": "req_xxx",
  "data": {
    "uploadId": "ce2da3b4-5216-4ab9-8b26-9a4566017ba9",
    "method": "PUT",
    "uploadUrl": "https://signed.example/upload",
    "headers": {
      "Content-Type": "image/png"
    },
    "expiresAt": "2026-08-04T08:45:00Z"
  },
  "meta": null
}
```

### 10.2 确认上传完成

`POST /assets/upload-complete`

请求：

```json
{
  "uploadId": "ce2da3b4-5216-4ab9-8b26-9a4566017ba9"
}
```

响应 `201` 返回 `Asset`。服务端完成 MIME、文件头、尺寸和图片解码校验后才标记可用。

## 11. 通用任务接口

### 11.1 查询任务

`GET /jobs/{jobId}`

返回 `AsyncJob`。

### 11.2 任务事件流

`GET /jobs/{jobId}/events`

响应类型：`text/event-stream`。

事件示例：

```text
event: job.progress
data: {"status":"RUNNING","progress":45,"stage":"GENERATING_CANDIDATES"}

event: job.completed
data: {"status":"SUCCEEDED","progress":100}
```

客户端断开后可以使用 `GET /jobs/{jobId}` 轮询。服务端不保证 SSE 事件永久保存。

### 11.3 取消任务

`POST /jobs/{jobId}/cancel`

只允许取消仍处于 `QUEUED` 或 Provider 支持取消的 `RUNNING` 任务。取消不等于退款，权益处理按任务类型返回。

## 12. 图片分析

### 12.1 创建分析任务

`POST /image-analysis/jobs`

权限：项目权益。`Idempotency-Key` 必填。

请求：

```json
{
  "projectId": "5ee30f87-7df7-40f9-b453-2589ee4ddab4",
  "sourceAssetId": "4ef982f2-d1b7-4f4c-b84c-00411638dbbf"
}
```

响应 `202`：返回 `AsyncJob`。

成功结果：

```json
{
  "suitabilityScore": 62,
  "recommendation": "AI_RECOMMENDED",
  "issues": [
    {
      "code": "BACKGROUND_COMPLEX",
      "severity": "MEDIUM",
      "message": "背景颜色和纹理较复杂"
    }
  ],
  "suggestedActions": ["BACKGROUND_REMOVAL", "CARTOONIZE"]
}
```

`recommendation`：`DIRECT`、`LIGHT_OPTIMIZATION`、`AI_RECOMMENDED`、`REJECTED`。

## 13. 抠图和白底服务

### 13.1 创建抠图任务

`POST /background-removal/jobs`

请求：

```json
{
  "projectId": "5ee30f87-7df7-40f9-b453-2589ee4ddab4",
  "sourceAssetId": "4ef982f2-d1b7-4f4c-b84c-00411638dbbf",
  "strength": "STANDARD"
}
```

成功结果：

```json
{
  "foregroundAsset": {},
  "maskAsset": {},
  "whitePreviewAsset": {},
  "edgeQualityScore": 88,
  "suggestedCrop": {
    "x": 0.12,
    "y": 0.08,
    "width": 0.76,
    "height": 0.84
  }
}
```

坐标使用 0 至 1 的归一化值。

### 13.2 更新蒙版资产

前端局部修正蒙版后，先通过上传接口上传新的 `SUBJECT_MASK` 资产，再在创建基底预览时引用，不传输大量笔刷操作日志。

### 13.3 创建基底预览

`POST /projects/{projectId}/base-image-previews`

请求：

```json
{
  "sourceAssetId": "4ef982f2-d1b7-4f4c-b84c-00411638dbbf",
  "foregroundAssetId": "f894d535-f3fd-47fc-9536-31b70d52fb7f",
  "maskAssetId": "a889a3e7-af3b-44e5-9814-843833731c3b",
  "crop": {
    "x": 0.12,
    "y": 0.08,
    "width": 0.76,
    "height": 0.84,
    "rotation": 0,
    "flipX": false,
    "flipY": false
  },
  "background": {
    "mode": "WHITE_PREVIEW",
    "paletteColorId": null
  }
}
```

规则：

- `SOLID_WHITE_BEADS` 和 `SOLID_CUSTOM_BEADS` 必须传 `paletteColorId`。
- `WHITE_PREVIEW` 和 `TRANSPARENT` 的 `paletteColorId` 必须为 `null`。
- 返回预览资产和预估背景豆子数量。

### 13.4 确认基底

`POST /projects/{projectId}/base-images/confirm`

`Idempotency-Key` 必填。

请求：

```json
{
  "baseImagePreviewId": "7fb215c7-bb82-4be8-a24d-9eb05911d88d"
}
```

响应 `201` 返回不可变 `BaseImageVersion`。

## 14. AI 美化

### 14.1 创建 AI 任务

`POST /ai-generation/jobs`

权限：项目权益。`Idempotency-Key` 必填。

请求：

```json
{
  "projectId": "5ee30f87-7df7-40f9-b453-2589ee4ddab4",
  "sourceAssetId": "4ef982f2-d1b7-4f4c-b84c-00411638dbbf",
  "maskAssetId": "a889a3e7-af3b-44e5-9814-843833731c3b",
  "style": "ANIME",
  "similarity": "HIGH",
  "detailLevel": "STANDARD",
  "composition": "PORTRAIT",
  "backgroundMode": "WHITE_PREVIEW",
  "constraints": {
    "targetGrid": { "width": 80, "height": 80 },
    "beadSizeMm": 5,
    "paletteId": "23626fac-a188-4785-8c74-8b3fe84e159b",
    "paletteVersion": "MARD-2026.1",
    "maxColors": 24,
    "outlineProtection": "STANDARD"
  },
  "candidateCount": 2,
  "addonEntitlementId": null
}
```

规则：

- `candidateCount` P0 固定为 2。
- 首次包含的 AI 权益由服务端根据项目权益自动判断。
- 追加付费候选图必须传有效的 `addonEntitlementId`，不能由客户端声明免费类型绕过计费。
- 服务端根据权益和商品快照做最终裁决。

成功结果：

```json
{
  "candidates": [
    {
      "id": "3cbfd3f7-87fe-412f-907c-306e382af83e",
      "asset": {},
      "score": {},
      "recommended": true
    }
  ],
  "systemRetryUsed": false,
  "entitlement": {
    "aiJobsUsed": 1,
    "aiJobsTotal": 1
  }
}
```

## 15. 色板

### 15.1 色板列表

`GET /palettes`

查询参数：`brand`、`status`。

### 15.2 色板颜色

`GET /palettes/{paletteId}/colors?version=MARD-2026.1`

响应项：

```json
{
  "id": "b1634dbb-80e4-43d5-9200-3395f042caaa",
  "code": "M12",
  "name": "奶油白",
  "rgb": "#F4F0E6",
  "lab": [94.2, 0.8, 5.3],
  "attributes": ["OPAQUE"],
  "enabled": true
}
```

## 16. 图纸生成

### 16.1 创建图纸任务

`POST /patterns/generation-jobs`

权限：有效项目权益。`Idempotency-Key` 必填。

请求：

```json
{
  "projectId": "5ee30f87-7df7-40f9-b453-2589ee4ddab4",
  "baseImageVersionId": "a916ab21-7fa2-4577-976a-d97768905241",
  "grid": {
    "width": 80,
    "height": 80,
    "beadSizeMm": 5
  },
  "palette": {
    "id": "23626fac-a188-4785-8c74-8b3fe84e159b",
    "version": "MARD-2026.1",
    "disabledColorIds": []
  },
  "options": {
    "maxColors": 24,
    "mergeStrength": 30,
    "dithering": "OFF",
    "outlineEnhancement": "STANDARD",
    "smallRegionThreshold": 2,
    "skinToneProtection": true,
    "optimizationTarget": "BALANCED"
  }
}
```

成功结果：

```json
{
  "patternId": "ae1e5c02-c38d-4350-a54f-658677cc3068",
  "patternVersion": 1,
  "matrixChecksum": "sha256:9a67...",
  "score": {},
  "colorCount": 18,
  "beadCount": 2840,
  "previewAsset": {},
  "autoRepairApplied": true
}
```

## 17. 图纸读取与编辑

### 17.1 图纸元数据

`GET /patterns/{patternId}`

返回参数、色板、版本、统计、评分和矩阵下载信息。

```json
{
  "id": "ae1e5c02-c38d-4350-a54f-658677cc3068",
  "version": 18,
  "width": 80,
  "height": 80,
  "paletteVersion": "MARD-2026.1",
  "matrix": {
    "encoding": "RLE_UINT16_BASE64",
    "data": "AAECA...",
    "checksum": "sha256:9a67..."
  },
  "lockedCells": {
    "encoding": "BITSET_BASE64",
    "data": "AAA..."
  },
  "score": {},
  "colorUsage": []
}
```

### 17.2 增量修改格子

`PATCH /patterns/{patternId}/cells`

`Idempotency-Key` 必填。

请求：

```json
{
  "patternVersion": 18,
  "operationId": "8fa0161b-a3d9-46a2-849c-f471454926e3",
  "changes": [
    {
      "row": 12,
      "column": 18,
      "fromColorId": "b1634dbb-80e4-43d5-9200-3395f042caaa",
      "toColorId": "4d063846-1417-4b43-b09e-e21e58ff6116"
    },
    {
      "row": 12,
      "column": 19,
      "fromColorId": "b1634dbb-80e4-43d5-9200-3395f042caaa",
      "toColorId": null
    }
  ]
}
```

响应：

```json
{
  "requestId": "req_xxx",
  "data": {
    "patternVersion": 19,
    "appliedChanges": 2,
    "beadCount": 2839,
    "colorUsageDelta": [
      { "colorId": "b1634dbb-80e4-43d5-9200-3395f042caaa", "delta": -2 },
      { "colorId": "4d063846-1417-4b43-b09e-e21e58ff6116", "delta": 1 }
    ]
  },
  "meta": null
}
```

版本冲突响应 `409 PATTERN_VERSION_CONFLICT`：

```json
{
  "requestId": "req_xxx",
  "error": {
    "code": "PATTERN_VERSION_CONFLICT",
    "message": "图纸已在其他位置更新",
    "retryable": false,
    "details": {
      "currentVersion": 21
    }
  }
}
```

### 17.3 整色替换

`POST /patterns/{patternId}/replace-color`

请求包含 `patternVersion`、`operationId`、`fromColorId`、`toColorId` 和 `respectLockedCells`。

### 17.4 创建版本

`POST /patterns/{patternId}/versions`

请求：

```json
{
  "patternVersion": 19,
  "name": "最终导出版本",
  "note": "调整了肤色和背景"
}
```

### 17.5 颜色用量

`GET /patterns/{patternId}/color-usage?version=19&wasteRate=0.05`

响应项：

```json
{
  "colorId": "b1634dbb-80e4-43d5-9200-3395f042caaa",
  "code": "M12",
  "name": "奶油白",
  "rgb": "#F4F0E6",
  "netCount": 320,
  "wasteRate": 0.05,
  "recommendedCount": 336,
  "percentage": 0.1127
}
```

## 18. 导出

### 18.1 创建导出任务

`POST /export-jobs`

权限：项目权益和有效下载期。`Idempotency-Key` 必填。

请求：

```json
{
  "patternId": "ae1e5c02-c38d-4350-a54f-658677cc3068",
  "patternVersion": 19,
  "format": "PDF",
  "options": {
    "paperSize": "A4",
    "orientation": "PORTRAIT",
    "pagination": "AUTO",
    "showGrid": true,
    "showColorCodes": true,
    "showCoordinates": true,
    "includeMaterialList": true,
    "wasteRate": 0.05,
    "watermark": false
  }
}
```

成功结果：

```json
{
  "exportId": "25577465-3d9a-4695-8073-fdb1aa757df4",
  "format": "PDF",
  "fileName": "小明头像拼豆-v19.pdf",
  "fileSize": 2482912,
  "pageCount": 6,
  "downloadUrl": "https://signed.example/download",
  "downloadUrlExpiresAt": "2026-08-04T09:30:00Z",
  "retainedUntil": "2026-09-03T08:30:00Z"
}
```

### 18.2 查询导出任务

`GET /export-jobs/{exportId}`

任务成功但签名 URL 过期时，服务端返回新的短期下载 URL，不重新生成文件。

## 19. 管理端接口

管理端使用 `/api/v1/admin`，P0 至少包含：

```text
GET  /admin/orders
GET  /admin/redemption-codes
GET  /admin/jobs
POST /admin/jobs/{jobId}/retry
POST /admin/entitlements/{entitlementId}/restore
GET  /admin/palettes
POST /admin/palettes/{paletteId}/versions
GET  /admin/cost-metrics
```

管理接口需要独立角色权限、审计原因和操作记录。

## 20. 错误码

### 20.1 鉴权

| 错误码 | HTTP | 说明 |
| --- | ---: | --- |
| `AUTH_REQUIRED` | 401 | 未登录 |
| `TOKEN_EXPIRED` | 401 | 访问令牌过期 |
| `SMS_CODE_INVALID` | 400 | 验证码错误 |
| `RATE_LIMITED` | 429 | 请求过于频繁 |

### 20.2 订单与业务码

| 错误码 | HTTP | 说明 |
| --- | ---: | --- |
| `PRODUCT_UNAVAILABLE` | 400 | 商品不可购买 |
| `ORDER_NOT_PAID` | 400 | 订单尚未支付 |
| `PAYMENT_AMOUNT_MISMATCH` | 400 | 支付金额不一致 |
| `CODE_INVALID` | 400 | 业务码格式或内容错误 |
| `CODE_EXPIRED` | 400 | 业务码已过期 |
| `CODE_VOIDED` | 400 | 业务码已作废 |
| `CODE_ALREADY_REDEEMED` | 409 | 已由其他用户兑换 |
| `ENTITLEMENT_UNAVAILABLE` | 403 | 服务权益不可用 |
| `AI_QUOTA_EXHAUSTED` | 403 | 已使用包含的 AI 次数 |
| `EDIT_WINDOW_EXPIRED` | 403 | 编辑期已结束 |

### 20.3 文件和图片

| 错误码 | HTTP | 说明 |
| --- | ---: | --- |
| `FILE_TOO_LARGE` | 413 | 文件超过限制 |
| `FILE_TYPE_UNSUPPORTED` | 400 | 文件格式不支持 |
| `IMAGE_DECODE_FAILED` | 400 | 图片无法解析 |
| `IMAGE_TOO_SMALL` | 400 | 图片分辨率过低且无法继续 |
| `CONTENT_REJECTED` | 403 | 内容审核未通过 |
| `BACKGROUND_REMOVAL_FAILED` | 502 | 抠图服务失败 |
| `BACKGROUND_COLOR_REQUIRED` | 400 | 实体背景缺少色号 |

### 20.4 AI 和任务

| 错误码 | HTTP | 说明 |
| --- | ---: | --- |
| `JOB_NOT_FOUND` | 404 | 任务不存在 |
| `JOB_NOT_CANCELLABLE` | 409 | 当前状态不能取消 |
| `AI_PROVIDER_TIMEOUT` | 502 | AI 服务超时，可重试 |
| `AI_GENERATION_FAILED` | 502 | AI 生成失败 |
| `AI_CANDIDATES_UNUSABLE` | 502 | 候选图均未达到最低评分 |

### 20.5 图纸和导出

| 错误码 | HTTP | 说明 |
| --- | ---: | --- |
| `PALETTE_VERSION_NOT_FOUND` | 404 | 色板版本不存在 |
| `PATTERN_GENERATION_FAILED` | 500 | 图纸生成失败 |
| `PATTERN_VERSION_CONFLICT` | 409 | 图纸版本冲突 |
| `CELL_OUT_OF_RANGE` | 400 | 单元格坐标越界 |
| `COLOR_NOT_IN_PALETTE` | 400 | 色号不属于锁定色板 |
| `LOCKED_CELL_MODIFICATION` | 409 | 尝试修改锁定格 |
| `EXPORT_FAILED` | 500 | 导出失败 |
| `DOWNLOAD_EXPIRED` | 403 | 项目下载期已结束 |

## 21. 幂等规则

| 接口 | 幂等范围 | 重放行为 |
| --- | --- | --- |
| `POST /orders` | 用户 + 幂等键 | 返回原订单 |
| `POST /redemption-codes/redeem` | 用户 + 幂等键 | 返回原项目和权益 |
| `POST /assets/upload-init` | 项目 + 文件哈希 + 幂等键 | 返回原上传会话 |
| `POST /*/jobs` | 项目 + 任务类型 + 幂等键 | 返回原任务 |
| `PATCH /patterns/{id}/cells` | 图纸 + operationId | 返回原应用结果 |
| `POST /export-jobs` | 图纸版本 + 参数 + 幂等键 | 返回原导出任务 |

幂等重放返回首次请求的业务结果和当前资源状态，不再次消耗权益。

## 22. 限流建议

| 接口 | 建议限制 |
| --- | --- |
| 短信发送 | 每手机号 60 秒 1 次，每日 10 次 |
| 登录验证 | 每 IP 每分钟 20 次 |
| 业务码兑换 | 每用户每分钟 10 次，每 IP 每分钟 30 次 |
| 上传初始化 | 每用户每分钟 20 次 |
| AI 创建 | 每项目同时 1 个，每用户同时 2 个 |
| 图纸生成 | 每项目同时 1 个 |
| 增量保存 | 每项目每秒 5 个批次 |
| 导出 | 每项目同时 2 个 |

## 23. 前后端契约测试

### 23.1 后端

- 每个接口响应必须通过 OpenAPI Schema 校验。
- 错误场景必须返回文档定义的稳定错误码。
- 固定夹具的响应保存为契约快照。

### 23.2 前端

- MSW Handler 使用与 OpenAPI 相同的 DTO 类型。
- 不得在 Mock 中增加真实接口不存在的字段。
- 每个 P0 错误码至少存在一个组件或 E2E 测试。

### 23.3 兼容规则

- 新增可选字段属于兼容变更。
- 删除字段、改名、改变类型或枚举含义属于破坏性变更，需要发布 `/api/v2` 或协商迁移期。
- 新增枚举值前，前端必须具备未知枚举兜底。

## 24. P0 联调顺序

1. 鉴权、商品、订单、支付结果、业务码和权益。
2. 项目、上传、分析、抠图和白底预览。
3. AI 任务、候选图评分和基底确认。
4. 色板、图纸任务、矩阵和颜色统计。
5. 增量保存、版本冲突、导出和下载。

每一阶段先通过 OpenAPI 和契约测试，再进入页面联调，不等待所有 P0 接口完成。
