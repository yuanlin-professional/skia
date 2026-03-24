# tskit - TypeScript 版 CanvasKit 绑定

## 概述

`experimental/tskit/` 是 CanvasKit 的实验性 TypeScript 绑定版本。该项目尝试用
TypeScript 替代传统的 JavaScript 绑定代码，以获得更好的类型安全性和开发体验。
它包含 C++ 绑定层、TypeScript 接口定义、构建工具和 npm 发布配置。

## 目录结构

```
tskit/
├── package.json             # npm 包配置
├── package-lock.json        # 依赖锁定文件
├── tsconfig.json            # TypeScript 编译配置
├── compile.sh               # 编译脚本
├── Makefile                 # Make 构建配置
├── bindings/                # C++/embind 绑定代码
│   ├── bindings.h           # 绑定头文件
│   ├── core.cpp             # 核心绑定实现
│   ├── core.d.ts            # 核心类型声明
│   ├── embind.d.ts          # embind 类型声明
│   ├── extension.cpp        # 扩展绑定实现
│   └── extension.d.ts       # 扩展类型声明
├── build/                   # 构建输出
│   └── externs.js           # Closure Compiler 外部声明
├── go/                      # Go 类型生成工具
│   └── gen_types             # 类型生成器
├── interface/               # TypeScript 接口定义
│   ├── core.ts              # 核心接口
│   ├── extension.ts         # 扩展接口
│   ├── load.ts              # 加载接口
│   ├── memory.ts            # 内存管理接口
│   └── public_api.d.ts      # 公共 API 类型声明
└── npm_build/               # npm 发布构建
    ├── example.html         # 使用示例页面
    └── types/               # 类型定义文件
```

## 关键文件

- **package.json**: 定义 `tskit` 包，使用 TypeScript 4.2+、ESLint 和 Airbnb 规范
- **bindings/core.cpp**: C++ 侧的 Emscripten embind 绑定
- **interface/core.ts**: TypeScript 核心接口定义
- **compile.sh**: 完整编译流程脚本

## 依赖关系

- TypeScript 4.2+
- ESLint 及 `@typescript-eslint` 插件
- Emscripten（WebAssembly 编译）
- Go 工具链（类型生成器）
- Skia 核心库

## 相关文档与参考

- CanvasKit 模块: `modules/canvaskit/`
- Emscripten 文档: https://emscripten.org/
