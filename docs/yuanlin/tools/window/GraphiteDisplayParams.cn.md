# GraphiteDisplayParams - Graphite 显示参数

> 源文件: `tools/window/GraphiteDisplayParams.h`

## 概述

`GraphiteDisplayParams` 是 Skia 窗口工具库中为 Graphite 渲染后端设计的显示参数类。它继承自 `DisplayParams`，扩展了对 Graphite 特定测试选项（`TestOptions`）的支持。同时提供了对应的 `GraphiteDisplayParamsBuilder` 构建器类，遵循构建器模式来创建参数实例。

## 架构位置

该类位于 Skia 窗口显示参数体系中：
- 继承自 `DisplayParams` 基类
- 与 Graphite 渲染后端紧密关联
- 被各 Graphite 窗口上下文（如 `GraphiteDawnWindowContext`、`GraphiteMetalWindowContext`）使用
- 位于 `skwindow` 命名空间中

## 主要类与结构体

### `GraphiteDisplayParams`
- 继承自 `DisplayParams`
- 持有 `skiatest::graphite::TestOptions` 成员 `fGraphiteTestOptions`
- 支持从 `TestOptions` 直接构造或从现有 `DisplayParams` 复制构造

### `GraphiteDisplayParamsBuilder`
- 继承自 `DisplayParamsBuilder`
- 用于构建 `GraphiteDisplayParams` 实例
- 提供流式接口设置 Graphite 测试选项

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `GraphiteDisplayParams(const TestOptions&)` | 从 Graphite 测试选项构造 |
| `GraphiteDisplayParams(const DisplayParams*)` | 从现有 DisplayParams 复制构造 |
| `clone()` | 克隆当前参数实例 |
| `graphiteTestOptions()` | 返回 Graphite 测试选项指针 |
| `GraphiteDisplayParamsBuilder()` | 默认构建器 |
| `GraphiteDisplayParamsBuilder(const DisplayParams*)` | 从现有参数构建 |
| `graphiteTestOptions(const TestOptions&)` | 设置 Graphite 测试选项 |

## 内部实现细节

- `GraphiteDisplayParams` 的复制构造函数检查源 `DisplayParams` 是否已有 Graphite 测试选项，若无则使用默认值
- `GraphiteDisplayParamsBuilder::graphiteTestOptions()` 方法使用 `reinterpret_cast` 将基类指针转换为具体类型来设置内部字段
- `SkASSERT_RELEASE` 确保构建器在设置选项时参数对象仍然有效

## 依赖关系

- `include/gpu/graphite/ContextOptions.h` - Graphite 上下文选项
- `src/gpu/graphite/ContextOptionsPriv.h` - Graphite 上下文私有选项
- `tools/graphite/TestOptions.h` - Graphite 测试选项定义
- `tools/window/DisplayParams.h` - 基类显示参数

## 设计模式与设计决策

- **构建器模式**: `GraphiteDisplayParamsBuilder` 提供流式 API 构建参数对象
- **友元类**: `GraphiteDisplayParamsBuilder` 被声明为友元，可直接访问私有成员
- **虚函数多态**: `clone()` 和 `graphiteTestOptions()` 使用 `override` 实现多态行为
- **防御性编程**: 复制构造时检查源对象是否持有 Graphite 选项，若无则提供默认值

## 性能考量

- `clone()` 方法创建完整副本，适用于需要参数隔离的场景
- 构建器中使用 `reinterpret_cast` 避免了额外的动态转换开销
- 参数对象通常在初始化阶段创建，不影响渲染性能

## 相关文件

- `tools/window/DisplayParams.h` - 基类 `DisplayParams`
- `tools/graphite/TestOptions.h` - `TestOptions` 定义
- `include/gpu/graphite/ContextOptions.h` - Graphite 上下文选项
- `tools/window/GraphiteDawnWindowContext.h` - 使用此参数的窗口上下文
- `tools/window/GraphiteNativeMetalWindowContext.h` - Metal Graphite 窗口上下文
