# GrMtlFramebuffer

> 源文件
> - src/gpu/ganesh/mtl/GrMtlFramebuffer.h
> - src/gpu/ganesh/mtl/GrMtlFramebuffer.mm

## 概述

`GrMtlFramebuffer` 是 Skia 图形库中 Metal 后端的帧缓冲对象封装类,继承自 `SkRefCnt`。它管理一组附件(颜色、解析、模板),表示一个完整的渲染目标配置。该类用于简化渲染通道的附件管理,确保附件生命周期的正确性。

## 架构位置

```
Skia Graphics Library
└── src/gpu/ganesh/mtl/
    ├── GrMtlAttachment        (附件封装)
    └── GrMtlFramebuffer       (帧缓冲) ← 当前类
```

## 主要类与结构体

### GrMtlFramebuffer

Metal 帧缓冲管理类,持有一组附件的引用。

**继承关系:**
- 基类: `SkRefCnt`
- 派生类: 无(终端类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fColorAttachment` | `sk_sp<GrMtlAttachment>` | 颜色附件(必需) |
| `fResolveAttachment` | `sk_sp<GrMtlAttachment>` | MSAA 解析附件(可选) |
| `fStencilAttachment` | `sk_sp<GrMtlAttachment>` | 模板附件(可选) |

## 公共 API 函数

### 工厂方法

```cpp
static sk_sp<const GrMtlFramebuffer> Make(
    GrMtlAttachment* colorAttachment,
    GrMtlAttachment* resolveAttachment,
    GrMtlAttachment* stencilAttachment
);
```
创建帧缓冲对象,至少需要颜色附件。

**参数要求:**
- `colorAttachment`: 必需,不能为 nullptr
- `resolveAttachment`: 可选,用于 MSAA 解析
- `stencilAttachment`: 可选,用于深度/模板测试

### 访问器

```cpp
GrMtlAttachment* colorAttachment();
GrMtlAttachment* resolveAttachment();
GrMtlAttachment* stencilAttachment();
```
获取各类附件的指针。

## 内部实现细节

### 构造与验证

```cpp
sk_sp<const GrMtlFramebuffer> GrMtlFramebuffer::Make(
    GrMtlAttachment* colorAttachment,
    GrMtlAttachment* resolveAttachment,
    GrMtlAttachment* stencilAttachment
) {
    // 至少需要颜色附件
    SkASSERT(colorAttachment);

    auto fb = new GrMtlFramebuffer(
        sk_ref_sp(colorAttachment),
        sk_ref_sp(resolveAttachment),
        sk_ref_sp(stencilAttachment)
    );

    return sk_sp<const GrMtlFramebuffer>(fb);
}
```

### 私有构造函数

```cpp
GrMtlFramebuffer::GrMtlFramebuffer(
    sk_sp<GrMtlAttachment> colorAttachment,
    sk_sp<GrMtlAttachment> resolveAttachment,
    sk_sp<GrMtlAttachment> stencilAttachment
)
    : fColorAttachment(std::move(colorAttachment))
    , fResolveAttachment(std::move(resolveAttachment))
    , fStencilAttachment(std::move(stencilAttachment)) {
}
```

使用 `std::move` 转移智能指针所有权,避免引用计数增减开销。

### 生命周期管理

```cpp
GrMtlFramebuffer::~GrMtlFramebuffer() = default;
```
使用默认析构函数,智能指针自动释放附件。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrMtlAttachment` | 附件封装 |
| `SkRefCnt` | 引用计数基类 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrMtlRenderTarget` | 渲染目标持有帧缓冲 |
| `GrMtlOpsRenderPass` | 配置渲染通道 |

## 设计模式与设计决策

### 组合模式
将多个附件组合为单一的帧缓冲对象,简化接口和管理。

### 不可变性
返回 `sk_sp<const GrMtlFramebuffer>`,一旦创建不可修改,保证线程安全。

### 智能指针管理
使用 `sk_sp` 自动管理附件生命周期,避免手动内存管理。

### 最小接口
仅提供访问器方法,无复杂逻辑,符合单一职责原则。

## 性能考量

### 轻量级对象
- 仅存储 3 个智能指针(24 字节)
- 无虚函数表开销(除 SkRefCnt 的)
- 构造和析构开销极小

### 引用计数优化
使用 `std::move` 在构造时避免引用计数操作。

### 缓存友好
小对象尺寸适合缓存行,访问附件无额外间接层。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/mtl/GrMtlAttachment.h` | 组合 | 附件封装类 |
| `include/core/SkRefCnt.h` | 基类 | 引用计数基类 |
| `src/gpu/ganesh/mtl/GrMtlRenderTarget.h` | 使用者 | 渲染目标 |
| `src/gpu/ganesh/mtl/GrMtlOpsRenderPass.h` | 使用者 | 渲染通道 |
