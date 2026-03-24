# Embind TypeScript 类型声明

> 源文件: `experimental/tskit/bindings/embind.d.ts`

## 概述

`embind.d.ts` 定义了 Emscripten embind 绑定系统提供的基础 TypeScript 类型接口。它声明了 WebAssembly 模块的核心接口 `EmbindModule`（内存管理和堆访问）和所有绑定对象的基类 `EmbindObject`。

## 架构位置

位于 `experimental/tskit/bindings/` 目录，是 TSKit TypeScript 类型系统的基础层。其他绑定文件（`core.d.ts`、`extension.d.ts`）通过三斜杠指令引用此文件。

## 主要类与结构体

- **`EmbindModule`**: Emscripten 运行时模块接口
  - `onRuntimeInitialized()`: 运行时初始化完成回调
  - `_malloc(bytes)` / `_free(ptr)`: 内存分配/释放
  - 堆视图: `HEAPF32`, `HEAPU8`, `HEAPU16`, `HEAPU32`, `HEAP8`, `HEAP16`, `HEAP32`
- **`EmbindObject<T>`**: 泛型绑定对象基接口
  - `clone()`: 克隆对象
  - `delete()` / `deleteAfter()`: 释放资源
  - `isAliasOf(other)`: 检查是否为同一 C++ 对象的别名
  - `isDeleted()`: 检查是否已释放

## 公共 API 函数

接口方法定义，无独立函数。

## 内部实现细节

- 使用 TypeScript `declare namespace` 语法声明环境类型
- `EmbindObject` 使用 F-bounded 多态 (`T extends EmbindObject<T>`) 确保 `clone()` 返回正确类型
- 堆视图类型对应 WebAssembly 线性内存的不同数据视图

## 依赖关系

无外部依赖，作为 TSKit 类型系统的根声明文件。

## 设计模式与设计决策

- 使用泛型自引用模式（F-bounded polymorphism）使派生类型的方法返回自身类型
- 堆访问接口暴露了 WebAssembly 的线性内存，用于高性能数据传递

## 性能考量

直接堆访问（HEAP* 数组）允许 TypeScript 代码零拷贝读写 WebAssembly 内存。

## 相关文件

- `experimental/tskit/bindings/core.d.ts`: 核心模块类型声明
- `experimental/tskit/bindings/extension.d.ts`: 扩展模块类型声明
