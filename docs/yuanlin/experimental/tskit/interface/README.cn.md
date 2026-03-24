# tskit/interface - TypeScript 接口定义

## 概述

`interface/` 包含 tskit 的 TypeScript 接口定义文件，定义了 CanvasKit WASM
模块的公共 TypeScript API。

## 目录结构

```
interface/
├── core.ts          # 核心接口（Canvas、Paint、Image 等）
├── extension.ts     # 扩展接口（特殊效果、滤镜等）
├── load.ts          # 模块加载接口
├── memory.ts        # WebAssembly 内存管理接口
└── public_api.d.ts  # 公共 API 总类型声明
```

## 关键文件

- **core.ts**: 定义 Skia 核心绘图 API 的 TypeScript 类型
- **memory.ts**: 定义 WASM 内存分配和释放的接口
- **load.ts**: 定义 CanvasKit 模块的异步加载接口

## 相关文档与参考

- C++ 绑定层: `../bindings/`
- CanvasKit JS API: `modules/canvaskit/`
