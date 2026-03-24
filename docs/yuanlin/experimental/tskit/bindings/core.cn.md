# TSKit Core 绑定

> 源文件: `experimental/tskit/bindings/core.cpp`

## 概述

`core.cpp` 是 TSKit 的核心 C++ 绑定文件，定义了通过 Emscripten embind 暴露给 JavaScript/TypeScript 的基础 API。它包含一个 `Something` 类和两个函数（一个公共、一个私有），演示了 TSKit 绑定系统的核心用法。

## 架构位置

位于 `experimental/tskit/bindings/` 目录，是 TSKit WebAssembly 绑定的核心模块。与 `extension.cpp` 分离，展示了模块化绑定的设计方式。

## 主要类与结构体

- **`Something`**: 带名称属性的简单类
  - 构造函数: `Something(std::string n)`
  - `getName()`: 返回名称
  - `setName(name)`: 设置名称（标记为私有导出）

## 公共 API 函数

- **`_privateFunction(x, y)`**: 私有函数，返回 x * y（`TS_PRIVATE_EXPORT`）
- **`publicFunction(input)`**: 公共函数，打印 "Hello {input}"（`TS_EXPORT`，含 JSDoc）
- **`Something` 类**: 公共类，暴露构造函数和 `getName` 方法

## 内部实现细节

1. `EMSCRIPTEN_BINDINGS(Core)` 宏注册核心模块绑定
2. 私有函数使用 `_` 前缀命名约定（`_privateFunction`）
3. 公共函数和类方法前必须有 `/** ... */` JSDoc 注释
4. `class_<Something>("Something")` 将 C++ 类暴露为 JS 类
5. `.function("_setName", ...)` 中 `_` 前缀表示这是内部方法

## 依赖关系

- `experimental/tskit/bindings/bindings.h`: 绑定框架宏
- Emscripten bind 库
- `<string>` 标准库

## 设计模式与设计决策

- 公共/私有 API 分离通过 `TS_EXPORT` 和 `TS_PRIVATE_EXPORT` 实现
- 核心模块与扩展模块分离，支持模块化的绑定组织
- JSDoc 注释直接嵌入 C++ 源码，通过代码生成工具提取

## 性能考量

无特殊性能考量，此为概念验证代码。

## 相关文件

- `experimental/tskit/bindings/core.d.ts`: 对应的 TypeScript 类型声明
- `experimental/tskit/bindings/extension.cpp`: 扩展绑定模块
- `experimental/tskit/bindings/bindings.h`: 绑定宏定义
