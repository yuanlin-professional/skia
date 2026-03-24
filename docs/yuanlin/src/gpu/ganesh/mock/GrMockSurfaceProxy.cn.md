# GrMockSurfaceProxy

> 源文件
> - src/gpu/ganesh/mock/GrMockSurfaceProxy.h

## 概述

`GrMockSurfaceProxy` 是 Skia 图形库中 Mock 后端的表面代理类,继承自 `GrSurfaceProxy`。该类提供了一个轻量级的代理实现,用于测试 Skia 的延迟资源分配和代理管理机制,而无需创建真实的 GPU 表面资源。

## 架构位置

```
Skia Graphics Library
└── src/gpu/ganesh/
    ├── GrSurfaceProxy         (表面代理基类)
    └── mock/
        └── GrMockSurfaceProxy (Mock表面代理) ← 当前类
```

## 主要类与结构体

### GrMockSurfaceProxy

Mock 表面代理,用于测试的空实现。

**继承关系:**
- 基类: `GrSurfaceProxy`

**关键特点:**
- 固定尺寸 1x1
- 固定格式 RGBA_8888
- 不可实例化(始终返回失败)
- 不分配 GPU 内存

## 公共 API 函数

### 构造函数

```cpp
GrMockSurfaceProxy(SkString name, std::string_view label);
```
创建 Mock 代理,仅在调试模式下保存名称。

**默认属性:**
- 格式: `GrColorType::kRGBA_8888`
- 尺寸: `SkISize::Make(1, 1)`
- 预算: `skgpu::Budgeted::kNo`
- 保护: `skgpu::Protected::kNo`

### 重写方法

```cpp
bool instantiate(GrResourceProvider*) override {
    return false;  // 始终返回失败
}

size_t onUninstantiatedGpuMemorySize() const override {
    return 0;  // 无内存占用
}
```

## 内部实现细节

### 调试支持

仅在调试模式下设置名称:
```cpp
SkDEBUGCODE(this->setDebugName(std::move(name)));
```

### 空实现

```cpp
SkDEBUGCODE(void onValidateSurface(const GrSurface*) override {})

sk_sp<GrSurface> createSurface(GrResourceProvider*) const override {
    return nullptr;  // 不创建表面
}

LazySurfaceDesc callbackDesc() const override {
    SkUNREACHABLE;  // 不支持延迟回调
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrSurfaceProxy` | 基类 |
| `GrBackendFormats` | 格式工厂 |
| `SkBackingFit` | 尺寸适配策略 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrMockRenderTask` | 测试任务依赖追踪 |
| 单元测试 | 验证代理生命周期 |

## 设计模式与设计决策

### 空对象模式
提供符合接口的空实现,用于测试代理管理逻辑。

### 最小化开销
固定最小尺寸和固定格式,避免不必要的配置。

## 性能考量

### 零内存占用
`onUninstantiatedGpuMemorySize()` 返回 0,测试时无内存压力。

### 快速失败
`instantiate()` 立即返回 false,测试可快速验证错误处理路径。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrSurfaceProxy.h` | 基类 | 表面代理抽象 |
| `include/gpu/ganesh/mock/GrMockBackendSurface.h` | 工具 | Mock 后端表面工厂 |
