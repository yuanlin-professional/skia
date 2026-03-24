# TSKit 绑定框架头文件

> 源文件: `experimental/tskit/bindings/bindings.h`

## 概述

`bindings.h` 是 TSKit WebAssembly 绑定系统的核心头文件，定义了 `TS_EXPORT` 和 `TS_PRIVATE_EXPORT` 两个宏，用于标记暴露给 JavaScript/TypeScript 的 API。这些宏被代码生成工具解析，自动生成 TypeScript 类型声明、Closure 编译器 externs 和 API 文档。

## 架构位置

位于 `experimental/tskit/bindings/` 目录，是 TSKit 绑定系统的基础设施层。所有绑定源文件（`core.cpp`、`extension.cpp`）都包含此头文件。

## 主要类与结构体

无类定义。包含 Emscripten 头文件并引入命名空间。

## 公共 API 函数

### 宏定义
- **`TS_EXPORT(ts_code)`**: 标记公共 API，出现在以下三种生成文件中：
  1. Ambient namespace 文件（如 `core.d.ts`）
  2. Closure 编译器 externs 文件（`externs.js`）
  3. API 汇总文档（`index.d.ts`）
  - 要求前方必须有 `/** ... */` JSDoc 注释
- **`TS_PRIVATE_EXPORT(ts_code)`**: 标记私有 API，仅出现在前两种文件中

## 内部实现细节

1. 两个宏在 C++ 编译时都展开为空（不产生运行时代码）
2. 宏参数中的 TypeScript 声明用于代码生成工具解析
3. 类方法使用 `ClassName::` 前缀标识所属类（如 `Canvas::drawPaint(p: Paint): void`）
4. 包含 `<emscripten.h>` 和 `<emscripten/bind.h>` 并引入 `emscripten` 命名空间

## 依赖关系

- Emscripten SDK: `<emscripten.h>`, `<emscripten/bind.h>`

## 设计模式与设计决策

- **元编程宏模式**: 宏同时服务于 C++ 编译（无操作）和外部工具（类型提取）
- **公私分离**: 两级导出控制允许内部实现细节不暴露在公共 API 文档中
- **文档即代码**: JSDoc 注释嵌入 C++ 源码，通过自动化工具提取到 TypeScript 声明文件
- Include guard 使用传统 `#ifndef` 宏

## 性能考量

宏展开为空，无运行时开销。

## 相关文件

- `experimental/tskit/bindings/core.cpp`: 使用这些宏的核心绑定
- `experimental/tskit/bindings/extension.cpp`: 使用这些宏的扩展绑定
- `modules/canvaskit/`: CanvasKit 中使用相同宏的生产代码
