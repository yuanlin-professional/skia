# GrBaseContextPriv

> 源文件:
> - `src/gpu/ganesh/GrBaseContextPriv.h`

## 概述

`GrBaseContextPriv` 是 Skia Ganesh 渲染引擎中 `GrContext_Base` 的私有访问窗口类。它遵循 Skia 的 "Priv" 设计模式，将仅供内部使用的方法从公开接口中分离出来。通过 `GrContext_Base::priv()` 获取该类的实例，可以访问上下文 ID、能力查询、着色器错误处理、以及上下文类型转换等内部功能。

## 架构位置

```
Ganesh 上下文层级
  └── GrContext_Base (基类)
        ├── priv() -> GrBaseContextPriv (内部访问窗口)
        ├── GrImageContext
        ├── GrRecordingContext
        └── GrDirectContext
```

## 主要类与结构体

### `GrBaseContextPriv`
- 纯粹的访问窗口类，不包含额外的数据成员或虚方法。
- 持有 `GrContext_Base*` 指针（`fContext`），直接委托调用到上下文对象。
- 构造函数为 `protected`，仅 `GrContext_Base` 友元类可创建。
- 禁止拷贝赋值和取地址操作，防止不当使用。

## 公共 API 函数

- **`context()`**：返回底层 `GrContext_Base` 指针（const 和非 const 版本）。
- **`contextID()`**：返回上下文的唯一标识符。
- **`matches(GrContext_Base*)`**：检查给定上下文是否与当前上下文匹配。
- **`options()`**：返回上下文配置选项 `GrContextOptions`。
- **`caps()`**：返回 GPU 能力查询对象 `GrCaps`。
- **`refCaps()`**：返回 `GrCaps` 的强引用 `sk_sp<const GrCaps>`。
- **`asImageContext()`**：转换为 `GrImageContext`。
- **`asRecordingContext()`**：转换为 `GrRecordingContext`。
- **`asDirectContext()`**：转换为 `GrDirectContext`。
- **`getShaderErrorHandler()`**：返回着色器错误处理器。

## 内部实现细节

`GrContext_Base::priv()` 在头文件中内联定义：
- 非 const 版本直接构造 `GrBaseContextPriv(this)`。
- const 版本通过 `const_cast` 移除 const 限定（返回类型为 `const GrBaseContextPriv`），保证 const 安全性。

禁止取地址操作符防止将临时的 Priv 对象存储为指针，确保其只作为临时表达式使用（如 `context->priv().caps()`）。

## 依赖关系

- **Ganesh 核心**: `GrContext_Base`、`GrContextOptions`、`GrCaps`
- **Ganesh 上下文**: `GrDirectContext`、`GrRecordingContext`、`GrImageContext`

## 设计模式与设计决策

1. **Priv 窗口模式**：Skia 标准的内部访问模式，将内部 API 封装在独立的 Priv 类中，不污染公开接口。
2. **零开销窗口**：不添加任何数据成员，所有调用直接委托到被包装的对象。
3. **防滥用保护**：禁止拷贝赋值和取地址，强制只作为临时对象使用。

## 性能考量

- 所有方法为内联调用，编译后等同于直接调用 `GrContext_Base` 的成员函数，无额外开销。

## 相关文件

- `include/private/gpu/ganesh/GrContext_Base.h` - 被包装的基类
- `include/gpu/ganesh/GrContextOptions.h` - 上下文选项
- `src/gpu/ganesh/GrCaps.h` - GPU 能力查询
