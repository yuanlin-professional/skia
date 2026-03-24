# npm_build - CanvasKit npm 包发布目录

## 概述

`npm_build` 目录是 `canvaskit-wasm` npm 包的发布根目录，包含包的元数据配置、类型定义、
使用示例和文档。该 npm 包是 CanvasKit 的主要分发渠道，当前版本为 0.41.0，以 BSD-3-Clause
许可证发布。

npm 包提供三种构建变体以满足不同场景需求：默认版（`bin/canvaskit.js`）提供核心功能，体积
较小；完整版（`bin/full/canvaskit.js`）包含 Skottie 动画等完整功能集；性能分析版
（`bin/profiling/canvaskit.js`）保留完整的 WASM 函数名，便于性能调优。包同时提供
TypeScript 类型定义（`types/index.d.ts`）以支持类型安全的开发体验。

该目录还包含丰富的 HTML 示例文件，演示了 CanvasKit 的各种用法，包括基本绘制、文本排版、
Skottie 动画播放、Canvas 2D 兼容等场景。这些示例也是本地开发调试的入口页面。

## 架构图

```
+--------------------------------------------------+
|              canvaskit-wasm npm 包                 |
+--------------------------------------------------+
|                                                  |
|  package.json (包元数据、入口点、导出配置)          |
|                                                  |
|  +--------------------------------------------+  |
|  |           bin/ (WASM 构建产物)               |  |
|  |  +------------------+                      |  |
|  |  | canvaskit.js     | <-- 默认版（精简）     |  |
|  |  | canvaskit.wasm   |                      |  |
|  |  +------------------+                      |  |
|  |  +------------------+                      |  |
|  |  | full/            | <-- 完整版            |  |
|  |  |   canvaskit.js   |     (含 Skottie 等)   |  |
|  |  |   canvaskit.wasm |                      |  |
|  |  +------------------+                      |  |
|  |  +------------------+                      |  |
|  |  | profiling/       | <-- 性能分析版         |  |
|  |  |   canvaskit.js   |     (含函数名)        |  |
|  |  |   canvaskit.wasm |                      |  |
|  |  +------------------+                      |  |
|  +--------------------------------------------+  |
|                                                  |
|  +--------------------------------------------+  |
|  |          types/ (TypeScript 类型定义)         |  |
|  |  index.d.ts                                |  |
|  |  canvaskit-wasm-tests.ts                   |  |
|  |  tsconfig.json                             |  |
|  +--------------------------------------------+  |
|                                                  |
|  +--------------------------------------------+  |
|  |           示例文件                            |  |
|  |  example.html      (核心 API 演示)           |  |
|  |  extra.html        (扩展功能演示)             |  |
|  |  shaping.html      (文本整形演示)             |  |
|  |  paragraphs.html   (段落排版演示)             |  |
|  |  bidi.html         (双向文本演示)             |  |
|  |  multicanvas.html  (多画布演示)               |  |
|  |  node.example.js   (Node.js 使用示例)        |  |
|  +--------------------------------------------+  |
|                                                  |
|  LICENSE / CODE_OF_CONDUCT.md / CONTRIBUTING.md  |
+--------------------------------------------------+
```

## 目录结构

```
npm_build/
|-- package.json              # npm 包配置（名称、版本、入口、导出）
|-- package-lock.json         # 依赖锁定
|-- LICENSE                   # BSD-3-Clause 许可证
|-- README.md                 # npm 包英文说明文档
|-- CODE_OF_CONDUCT.md        # 行为准则
|-- CONTRIBUTING.md           # 贡献指南
|-- .gitignore                # Git 忽略规则（bin/ 不提交）
|
|-- example.html              # 核心 API 使用示例（Canvas2D 对比、绘制演示）
|-- extra.html                # 扩展功能示例（Skottie、SkSL 等）
|-- shaping.html              # 文本整形示例
|-- paragraphs.html           # 段落排版示例
|-- bidi.html                 # 双向文本排版示例
|-- multicanvas.html          # 多画布同时渲染示例
|-- node.example.js           # Node.js 环境使用示例
|-- textapi_utils.js          # 文本 API 工具函数
|
|-- types/                    # TypeScript 类型定义子目录
|   |-- index.d.ts            # 完整的 TS 类型定义文件
|   |-- canvaskit-wasm-tests.ts  # 类型定义测试文件
|   |-- tsconfig.json         # TS 编译配置
|   |-- tslint.json           # TS lint 配置
|   |-- README.md             # 类型定义说明
```

## 关键类与函数

### package.json 导出配置

```json
{
  "name": "canvaskit-wasm",
  "version": "0.41.0",
  "main": "bin/canvaskit.js",
  "types": "./types/index.d.ts",
  "exports": {
    ".":          "./bin/canvaskit.js",       // 默认
    "./full":     "./bin/full/canvaskit.js",  // 完整
    "./profiling":"./bin/profiling/canvaskit.js" // 分析
  }
}
```

### 初始化方式

```javascript
// CommonJS
const CanvasKitInit = require('canvaskit-wasm/bin/canvaskit.js');

// ES6 Module
import CanvasKitInit from 'canvaskit-wasm';
import CanvasKitInit from 'canvaskit-wasm/full';

// 初始化
const CanvasKit = await CanvasKitInit({
    locateFile: (file) => '/path/to/' + file,
});
```

### TypeScript 类型定义 (types/index.d.ts)

```typescript
export default function CanvasKitInit(opts?: CanvasKitInitOptions): Promise<CanvasKit>;

export interface CanvasKit {
    Color(r: number, g: number, b: number, a?: number): Color;
    Color4f(r: number, g: number, b: number, a?: number): Color;
    MakeWebGLCanvasSurface(canvas: string | HTMLCanvasElement): Surface;
    MakeCanvas(width: number, height: number): HTMLCanvas;
    // ... 完整 API 接口
}
```

## 依赖关系

- **运行时依赖**: `@webgpu/types` (0.1.21) - WebGPU 类型定义
- **开发依赖**: `dtslint` (4.2.1) - TypeScript 类型定义检查工具
- **开发依赖**: `typescript` (4.7.4) - TypeScript 编译器
- **构建产物**: 由 `Makefile` 的 `npm` 目标从构建输出目录复制

## 设计模式分析

### 多入口点模式
`package.json` 利用 Node.js 的 `exports` 字段定义了多个入口点，允许用户根据需求导入不同
变体，而无需了解内部目录结构。

### 类型优先设计
`types/index.d.ts` 提供了完整的 TypeScript 类型定义，不仅用于类型检查，同时也作为 API
文档的参考来源。

### WebPack 兼容
文档中提供了 WebPack 的兼容配置方案，包括使用 CopyWebpackPlugin 处理 WASM 文件、以及
解决 `fs` 模块缺失的配置。

## 数据流

```
make npm (构建流程)
    |
    +---> ./compile.sh release (精简版)
    |         |
    |         v
    |     bin/canvaskit.js + bin/canvaskit.wasm
    |
    +---> ./compile.sh release (完整版)
    |         |
    |         v
    |     bin/full/canvaskit.js + bin/full/canvaskit.wasm
    |
    +---> ./compile.sh profiling (分析版)
              |
              v
          bin/profiling/canvaskit.js + bin/profiling/canvaskit.wasm

npm publish (发布)
    |
    v
https://www.npmjs.com/package/canvaskit-wasm
    |
    v
用户: npm install canvaskit-wasm
```

## 相关文档与参考

- **npm 包**: https://www.npmjs.com/package/canvaskit-wasm
- **unpkg CDN**: https://unpkg.com/canvaskit-wasm@latest/bin/canvaskit.js
- **TypeScript 类型**: `types/index.d.ts`
- **Skia CanvasKit 文档**: https://skia.org/docs/user/modules/canvaskit
- **构建入口**: `Makefile` 的 `npm` 目标
