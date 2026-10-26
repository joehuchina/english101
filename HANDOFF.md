# 项目交接文档

## 项目概览

- **项目名称**：english101（基于 word-atlas fork）
- **本地路径**：`/Users/mac/Documents/codes/englishtest`
- **GitHub 仓库**：https://github.com/joehuchina/english101
- **线上地址**：https://english101.vip（Cloudflare Pages）
- **原始项目**：https://github.com/designfuchen/word-atlas（MIT + CC BY 4.0）

---

## 技术栈

| 层 | 技术 |
|---|---|
| 前端框架 | React 19 + TypeScript |
| 构建工具 | Vite 6 |
| 词汇学习算法 | ts-fsrs（FSRS 间隔复习） |
| 部署平台 | Cloudflare Pages |
| 媒体资源托管 | Cloudflare R2（`english101-media` 桶） |

---

## 本地目录结构

```
englishtest/
├── src/
│   ├── App.tsx              # 根组件，路由/主题/导航
│   ├── atlas/
│   │   ├── data.ts          # 词库加载 + 媒体 URL 构造（R2 相关改动在这里）
│   │   ├── context.tsx      # Atlas React Context
│   │   └── types.ts         # 类型定义
│   ├── pages/
│   │   ├── Today.tsx        # 今日学习页
│   │   ├── Atlas.tsx        # 词汇图鉴页
│   │   ├── Learn.tsx        # 学习页
│   │   ├── Practice.tsx     # 练习页
│   │   ├── Me.tsx           # 我的页面
│   │   ├── About.tsx        # 关于页
│   │   └── Onboarding.tsx   # 新手引导（当前已禁用）
│   ├── store/
│   │   └── store.ts         # 全局状态（localStorage 持久化）
│   ├── ui/                  # 通用 UI 组件
│   │   ├── Splash.tsx       # 启动动画（当前已禁用）
│   │   └── ...
│   └── lib/                 # 工具库（router、audio、motion 等）
├── public/
│   ├── atlas/
│   │   ├── index.json       # 词库索引（7,298 词）
│   │   └── entries/         # 词条详情 JSON（分块）
│   ├── brand/               # 品牌图片（hero.webp 等）
│   └── sfx/                 # 音效文件
│   # 注意：audio/、img/、thumb/ 已从 git 移除，托管在 R2
├── data/
│   ├── word-atlas.json      # 完整词库数据
│   └── word-atlas.csv
├── HANDOFF.md               # 本文件
└── package.json
```

---

## 本地开发

```bash
# 安装依赖
npm install

# 启动开发服务器（http://localhost:5188）
npm run dev

# 构建生产版本
npm run build

# 预览构建产物
npm run preview
```

> 本地开发时图片和音频会 404（因为 audio/、img/、thumb/ 不在 git 里）。
> 如需本地也能看到媒体，把这三个目录从 R2 下载回来放到 `public/atlas/` 下即可。

---

## 今日完成的改动（2026-10-25）

### Git 提交记录

| Commit | 内容 |
|---|---|
| `448408d` | 添加 `public/_redirects`（SPA 路由）和 `public/_headers`（缓存头） |
| `c7acdd0` | 将 `audio/`、`img/`、`thumb/` 从 git 移除，加入 `.gitignore` |
| `c7e892d` | 禁用启动粒子动画（Splash）和新手引导（Onboarding），直接进主界面 |
| `dff8267` | 修改 `src/atlas/data.ts`，媒体资源 URL 改为从 R2 读取 |
| `bc22d529` | 清理 App.tsx 中未使用的 import 和变量（修复 TS 构建报错） |

### 关键改动说明

**1. 媒体资源迁移到 R2**（`src/atlas/data.ts`）

```ts
// 新增 VITE_MEDIA_BASE 环境变量支持
const MEDIA_BASE = (import.meta.env.VITE_MEDIA_BASE || "").replace(/\/$/, "") || BASE;
const mediaUrl = (p: string) => `${MEDIA_BASE}/atlas/${p}`;
// img、thumb、audio 改用 mediaUrl()，其余（index.json、entries/）继续用 url()
```

**2. Cloudflare Pages 环境变量**

在 Pages 项目 Settings → Variables and secrets 中设置：
- `VITE_MEDIA_BASE` = `https://pub-b5f6cdcc0fe641ccb2b5cbc319bd979e.r2.dev`

**3. Splash / Onboarding 已禁用**

`src/App.tsx` 中两行已注释掉，用户打开网站直接进主界面。
如需恢复，在 `Shell` 组件里取消注释即可：
```tsx
// {!onboarded && route.page !== "about" && !splash && <Onboarding />}
// {splash && <Splash onDone={() => setSplash(false)} />}
```

---

## Cloudflare 资源

| 资源 | 说明 |
|---|---|
| Pages 项目 | `english101`，连接 GitHub `joehuchina/english101` main 分支，自动部署 |
| R2 桶 | `english101-media`，公开访问地址：`https://pub-b5f6cdcc0fe641ccb2b5cbc319bd979e.r2.dev` |
| 自定义域名 | `english101.vip`（待在 Pages → Custom domains 绑定） |
| Cloudflare 账号 | joe.humr@gmail.com，Account ID：`5cdb727d3da9582d94508b047fb162b9` |

### R2 桶内容

```
english101-media/
├── atlas/
│   ├── audio/    # 22,905 个 MP3（UK、US、例句三套发音）
│   ├── img/      # 7,298 个 WEBP 插画（512px）
│   └── thumb/    # 7,298 个 WEBP 缩略图
```

---

## 待办事项

- [ ] 在 Cloudflare Pages → Custom domains 绑定 `english101.vip`
- [ ] 验证线上图片和音频正常加载
- [ ] 后续功能改造（根据需求）

---

## 授权说明

- **代码**：MIT License（可自由使用、修改、商用，保留版权声明即可）
- **词库、插画、录音**：CC BY 4.0（需署名：`Word Atlas contributors — CC BY 4.0`）
