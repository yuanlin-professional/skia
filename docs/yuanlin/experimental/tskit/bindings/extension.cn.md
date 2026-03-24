# TSKit Extension 绑定

> 源文件: `experimental/tskit/bindings/extension.cpp`

## 概述

`extension.cpp` 是 TSKit 的扩展绑定文件，演示如何在 Skia 的 Emscripten/WebAssembly 绑定系统中定义扩展模块。它包含一个 `Extension` 类、一个 `CompoundObj` 值对象，以及使用指针传递数组数据的私有函数。

## 架构位置

位于 `experimental/tskit/bindings/` 目录，是 TSKit WebAssembly 绑定系统的扩展模块示例。该文件展示了 `TS_EXPORT` 和 `TS_PRIVATE_EXPORT` 宏的使用方式。

## 主要类与结构体

- **`SkRect`**: 内联定义的简化版矩形结构体（避免引入完整的 Skia 头文件）
  - `fLeft`, `fTop`, `fRight`, `fBottom`: 边界值
  - `contains(x, y)`: 点包含测试
- **`Extension`**: 带字符串属性的简单类
  - 默认构造函数设置属性为 "foo"
  - `getProp()` / `setProp()`: 属性访问器
- **`CompoundObj`**: 值对象结构体
  - `alpha: int`, `beta: string`, `gamma: float`

## 公共 API 函数

- **`_privateExtension(rPtr, len)`**: 接收 SkRect 数组指针，返回包含点 (5,5) 的矩形计数
- **`_withObject(obj)`**: 接收 CompoundObj 并打印其内容
- **`Extension` 类**: 通过 embind 暴露构造函数和 getter/setter

## 内部实现细节

1. `EMSCRIPTEN_BINDINGS(Extension)` 宏注册绑定
2. `TS_PRIVATE_EXPORT` 标记私有函数，仅出现在 ambient namespace 文件和 externs.js 中
3. `TS_EXPORT` 标记公共函数，会出现在最终 API 文档中
4. `optional_override` 包装 lambda 实现函数绑定
5. `value_object` 将 C++ 结构体映射为 JS 对象（按值传递）
6. `class_` 将 C++ 类映射为 JS 类（按引用传递）
7. 使用 `uintptr_t` 接收 JS 端传来的原始指针

## 依赖关系

- `experimental/tskit/bindings/bindings.h`: 绑定宏定义
- Emscripten bind 库
- `<string>` 标准库

## 设计模式与设计决策

- 公共/私有分离: `TS_EXPORT` 用于公共 API，`TS_PRIVATE_EXPORT` 用于内部使用
- JSDoc 注释附加在 `TS_EXPORT` 前，会被提取到最终 API 文档中
- `value_object` 用于小型数据传递，避免引用计数开销
- 内联 `SkRect` 定义避免 POC 项目引入完整 Skia 依赖

## 性能考量

- 使用原始指针 (`uintptr_t`) 传递数组数据，避免跨 JS/WASM 边界的逐元素拷贝
- `value_object` 在边界处按值复制，适合小型对象

## 相关文件

- `experimental/tskit/bindings/bindings.h`: 宏定义和框架说明
- `experimental/tskit/bindings/extension.d.ts`: 对应的 TypeScript 类型声明
- `experimental/tskit/bindings/core.cpp`: 核心绑定模块
