# external_test - TypeScript 外部集成测试

## 概述

`external_test` 目录包含 CanvasKit 的 TypeScript 外部集成测试，用于验证 `canvaskit-wasm`
npm 包在真实 TypeScript 项目中的类型兼容性和导入可用性。这些测试模拟了终端用户从 npm 安装
并在 TypeScript 项目中使用 CanvasKit 的实际场景。

目录中包含两种不同的 TypeScript 模块导入方式的测试：
- `typescript_browser` - 传统浏览器 TypeScript 项目（CommonJS 模块解析）
- `typescript_browser_es6` - ES6 模块风格的浏览器 TypeScript 项目

这两种变体确保了 `canvaskit-wasm` 在不同的 TypeScript 模块系统配置下都能正确地提供类型
推断和编译时检查。

## 架构图

```
+---------------------------------------------------+
|              外部集成测试流程                        |
+---------------------------------------------------+
|                                                   |
|  typescript_browser/                              |
|  +---------------------------------------------+ |
|  | package.json (依赖 canvaskit-wasm)           | |
|  | tsconfig.json (CommonJS 模块解析)            | |
|  | module_uses_ck.ts (导入并使用 CanvasKit)     | |
|  | index.html (浏览器加载页)                     | |
|  +---------------------------------------------+ |
|                                                   |
|  typescript_browser_es6/                          |
|  +---------------------------------------------+ |
|  | package.json (依赖 canvaskit-wasm)           | |
|  | tsconfig.json (ES6 模块、package exports)    | |
|  | module_uses_ck.ts (ES6 导入 CanvasKit)       | |
|  | index.html (浏览器加载页)                     | |
|  +---------------------------------------------+ |
|                                                   |
|  Makefile (构建与运行命令)                         |
|  .gitignore (忽略构建产物)                         |
+---------------------------------------------------+
         |                      |
         v                      v
+------------------+  +--------------------+
| npx tsc 编译      |  | npx tsc 编译        |
| (验证类型正确性)   |  | (验证 ES6 类型正确性) |
+------------------+  +--------------------+
         |                      |
         v                      v
+---------------------------------------------------+
|        本地 HTTP 服务器验证运行                     |
|  python3 tools/serve_wasm.py                      |
+---------------------------------------------------+
```

## 目录结构

```
external_test/
|-- Makefile                            # 构建目标定义
|-- .gitignore                          # Git 忽略规则
|
|-- typescript_browser/                 # 传统 TS 浏览器测试
|   |-- package.json                    # npm 依赖配置
|   |-- package-lock.json               # 依赖锁定
|   |-- tsconfig.json                   # TypeScript 编译配置
|   |-- module_uses_ck.ts               # CanvasKit 使用代码
|   |-- index.html                      # 浏览器加载页
|
|-- typescript_browser_es6/             # ES6 模块 TS 浏览器测试
|   |-- package.json                    # npm 依赖配置
|   |-- package-lock.json               # 依赖锁定
|   |-- tsconfig.json                   # TS 编译配置 (resolvePackageJsonExports)
|   |-- module_uses_ck.ts               # ES6 import CanvasKit 使用代码
|   |-- index.html                      # 浏览器加载页
```

## 关键类与函数

### Makefile 构建目标

```makefile
build-es6:                    # 编译 ES6 模块测试
    cd ./typescript_browser_es6 && npx tsc

build-browser:                # 编译传统浏览器测试
    cd ./typescript_browser && npx tsc

serve:                        # 启动本地服务器
    python3 ../../../tools/serve_wasm.py
```

### 测试代码示例 (module_uses_ck.ts)

```typescript
import CanvasKitInit from 'canvaskit-wasm';
// 或
import CanvasKitInit from 'canvaskit-wasm/full';

const CanvasKit = await CanvasKitInit();
// TypeScript 类型推断验证
const surface: Surface = CanvasKit.MakeCanvasSurface('myCanvas');
```

## 依赖关系

- **canvaskit-wasm**: 被测试的 npm 包
- **TypeScript**: TypeScript 编译器
- **types/index.d.ts**: CanvasKit 类型定义文件
- **serve_wasm.py**: Skia 的本地 HTTP 服务器工具

## 设计模式分析

### 端到端类型验证
这些测试不运行实际的 CanvasKit 代码，而是通过 TypeScript 编译器的类型检查来验证
`types/index.d.ts` 中的类型定义与实际 API 的一致性。编译成功即表示类型定义正确。

### 双模块系统覆盖
分别测试 CommonJS 和 ES6 模块解析策略，确保 `package.json` 中的 `exports` 字段
在两种常见的 TypeScript 配置下都能正确工作。

## 数据流

```
module_uses_ck.ts
     |
     v
TypeScript 编译器 (tsc)
     |
     +---> 解析 import 'canvaskit-wasm'
     |         |
     |         v
     |     node_modules/canvaskit-wasm/types/index.d.ts
     |         |
     |         v
     |     类型检查（编译通过 = 类型定义正确）
     |
     v
输出 JS 文件 ---> index.html 加载 ---> 浏览器验证
```

## 相关文档与参考

- **TypeScript exports 支持**: https://www.typescriptlang.org/tsconfig#resolvePackageJsonExports
- **Node.js package exports**: https://nodejs.org/api/packages.html#package-entry-points
- **CanvasKit 类型定义**: `npm_build/types/index.d.ts`
- **类型检查命令**: `make typecheck`（在 canvaskit 根目录）
