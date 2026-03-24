# TestOptions.h - Graphite 测试选项

> 源文件: `tools/graphite/TestOptions.h`

## 概述

定义了 Graphite 测试中使用的 `TestOptions` 结构体,封装了 `ContextOptions` 和 `ContextOptionsPriv`,并包含 Dawn 后端特有的测试选项。

## 架构位置

属于 Skia Graphite 测试工具层,被测试框架用于配置 Graphite 上下文。

## 主要类与结构体

- **`TestOptions`**: 聚合 `ContextOptions`、`ContextOptionsPriv` 及 Dawn 特有选项的结构体

## 公共 API 函数

- **`hasDawnOptions()`**: 检查是否设置了任何 Dawn 特有选项
- 拷贝构造和赋值运算符(确保 `fOptionsPriv` 指针正确设置)

## 内部实现细节

拷贝赋值运算符特别处理了 `fContextOptions.fOptionsPriv` 指针,确保它始终指向自身的 `fOptionsPriv` 成员而非被拷贝源的地址。移动构造和移动赋值被显式删除以防止悬空指针。

## 依赖关系

- `include/gpu/graphite/ContextOptions.h`
- `src/gpu/graphite/ContextOptionsPriv.h`

## 设计模式与设计决策

- 显式禁用移动语义防止指针失效
- Dawn 选项通过条件编译隔离

## 性能考量

轻量级配置结构体,无性能影响。

## 相关文件

- `include/gpu/graphite/ContextOptions.h`
