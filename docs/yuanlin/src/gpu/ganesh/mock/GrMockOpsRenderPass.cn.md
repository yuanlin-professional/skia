# GrMockOpsRenderPass

> 源文件
> - src/gpu/ganesh/mock/GrMockOpsRenderPass.h

## 概述

`GrMockOpsRenderPass` 是 Skia 图形库中 Mock 后端的渲染通道实现,继承自 `GrOpsRenderPass`。该类提供了一个空操作(no-op)的渲染通道,用于测试渲染管线的调用流程而无需真正执行 GPU 绘制。它记录绘制调用次数,并在必要时标记渲染目标的脏状态。

## 架构位置

```
Skia Graphics Library
└── src/gpu/ganesh/
    ├── GrOpsRenderPass        (渲染通道基类)
    └── mock/
        ├── GrMockGpu          (Mock GPU)
        ├── GrMockOpTarget     (Mock绘制目标)
        └── GrMockOpsRenderPass (Mock渲染通道) ← 当前类
```

## 主要类与结构体

### GrMockOpsRenderPass

Mock 渲染通道,所有绘制命令转换为状态更新。

**继承关系:**
- 基类: `GrOpsRenderPass`

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` | `GrMockGpu*` | Mock GPU 实例指针 |
| `fColorLoadOp` | `GrLoadOp` | 颜色加载操作 |
| `fNumDraws` | `int` | 绘制调用计数器 |

## 公共 API 函数

### 构造函数

```cpp
GrMockOpsRenderPass(GrMockGpu* gpu,
                    GrRenderTarget* rt,
                    GrSurfaceOrigin origin,
                    LoadAndStoreInfo colorInfo);
```

### 状态查询

```cpp
int numDraws() const;  // 返回绘制调用次数
GrGpu* gpu() override;  // 返回 GPU 实例
```

## 内部实现细节

### 绘制调用处理

所有绘制方法重定向到 `noopDraw()`:

```cpp
void onDraw(int, int) override { this->noopDraw(); }
void onDrawIndexed(int, int, uint16_t, uint16_t, int) override {
    this->noopDraw();
}
void onDrawInstanced(int, int, int, int) override {
    this->noopDraw();
}
void onDrawIndexedInstanced(int, int, int, int, int) override {
    this->noopDraw();
}
void onDrawIndirect(const GrBuffer*, size_t, int) override {
    this->noopDraw();
}
void onDrawIndexedIndirect(const GrBuffer*, size_t, int) override {
    this->noopDraw();
}
```

### 状态更新逻辑

```cpp
void noopDraw() {
    this->markRenderTargetDirty();  // 标记渲染目标需更新 mipmap
    ++fNumDraws;                    // 增加绘制计数
}

void markRenderTargetDirty() {
    if (auto* tex = fRenderTarget->asTexture()) {
        tex->markMipmapsDirty();    // 标记 mipmap 需重新生成
    }
}
```

### 渲染通道生命周期

```cpp
void onBegin() override {
    if (GrLoadOp::kClear == fColorLoadOp) {
        this->markRenderTargetDirty();  // Clear 操作也视为修改
    }
}
```

### 空操作方法

以下方法返回成功但不执行任何操作:

```cpp
bool onBindPipeline(const GrProgramInfo&, const SkRect&) override {
    return true;  // 假装绑定成功
}
void onSetScissorRect(const SkIRect&) override {}
bool onBindTextures(const GrGeometryProcessor&,
                   const GrSurfaceProxy* const[],
                   const GrPipeline&) override {
    return true;
}
void onBindBuffers(sk_sp<const GrBuffer>, sk_sp<const GrBuffer>,
                  sk_sp<const GrBuffer>, GrPrimitiveRestart) override {}
void onClear(const GrScissorState&, std::array<float, 4>) override {
    this->markRenderTargetDirty();
}
void onClearStencilClip(const GrScissorState&, bool) override {}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrOpsRenderPass` | 基类接口 |
| `GrMockGpu` | GPU 管理器 |
| `GrRenderTarget` | 渲染目标 |
| `GrTexture` | 纹理管理 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrMockGpu` | 创建渲染通道实例 |
| 单元测试 | 验证渲染调用序列 |

## 设计模式与设计决策

### 空对象模式
实现所有接口方法但不执行实际操作,避免测试中的 GPU 依赖。

### 状态追踪模式
通过 `fNumDraws` 计数器和 `markMipmapsDirty()` 记录关键状态变更,供测试验证。

### 最小实现原则
仅实现必要的状态更新逻辑,复杂的 GPU 操作直接返回成功。

## 性能考量

### 零开销绘制
所有绘制调用仅增加计数器,无实际 GPU 命令编码开销。

### 测试效率
测试可快速执行,不受 GPU 调度和同步影响。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrOpsRenderPass.h` | 基类 | 渲染通道抽象 |
| `src/gpu/ganesh/mock/GrMockGpu.h` | 管理者 | 创建渲染通道 |
| `src/gpu/ganesh/GrRenderTarget.h` | 协作 | 渲染目标管理 |
| `src/gpu/ganesh/GrTexture.h` | 协作 | 纹理状态管理 |
