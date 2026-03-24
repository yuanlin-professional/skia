# SkBlendModeBlender

> 源文件: src/core/SkBlendModeBlender.h, src/core/SkBlendModeBlender.cpp

## 概述

`SkBlendModeBlender` 是 Skia 中实现标准混合模式的混合器类。该模块将 28 种 Porter-Duff 和高级混合模式封装为 `SkBlender` 的具体实现,通过单例模式优化内存使用,并提供高效的光栅管线集成。混合器负责将源色和目标色按照指定的混合算法合成最终输出色。

## 架构位置

```
src/core/
  ├── SkBlendModeBlender.cpp    # 混合模式实现
  ├── SkBlendModeBlender.h      # 混合器类定义
  ├── SkBlenderBase.h           # 混合器基类
  └── SkBlendModePriv.h         # 混合模式私有函数

include/core/
  ├── SkBlendMode.h             # 混合模式枚举
  └── SkBlender.h               # 混合器公共接口
```

本模块位于 Skia 渲染管线的混合层,作为 `SkPaint` 的混合属性载体,连接高层绘制 API 和底层光栅化实现。

## 主要类与结构体

### SkBlendModeBlender

| **属性** | **说明** |
|---------|---------|
| **继承关系** | `SkBlendModeBlender` → `SkBlenderBase` → `SkFlattenable` → `SkRefCnt` |
| **作用** | 封装标准混合模式的混合器实现 |

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMode` | `SkBlendMode` | 混合模式枚举值 |

**核心方法:**

```cpp
explicit SkBlendModeBlender(SkBlendMode mode) : fMode(mode) {}
BlenderType type() const override { return BlenderType::kBlendMode; }
SkBlendMode mode() const { return fMode; }
```

## 公共 API 函数

### 工厂方法

```cpp
sk_sp<SkBlender> SkBlender::Mode(SkBlendMode mode);
```

**功能:** 创建指定混合模式的混合器,通过单例模式返回共享实例。

**实现:**
```cpp
sk_sp<SkBlender> SkBlender::Mode(SkBlendMode mode) {
    return sk_ref_sp(GetBlendModeSingleton(mode));
}
```

### 序列化支持

```cpp
void flatten(SkWriteBuffer& buffer) const override;
sk_sp<SkFlattenable> CreateProc(SkReadBuffer& buffer);
```

**功能:** 支持混合器的序列化和反序列化,用于跨进程传输或缓存。

### 光栅管线集成

```cpp
bool onAppendStages(const SkStageRec& rec) const override;
```

**功能:** 将混合模式转换为光栅管线的处理阶段,调用 `SkBlendMode_AppendStages()`。

## 内部实现细节

### 单例模式实现

```cpp
const SkBlender* GetBlendModeSingleton(SkBlendMode mode) {
#define RETURN_SINGLETON_BLENDER(m) \
    case m: { \
        static SkNoDestructor<SkBlendModeBlender> sBlender(m); \
        return sBlender.get(); \
    }

    switch (mode) {
        RETURN_SINGLETON_BLENDER(SkBlendMode::kClear)
        RETURN_SINGLETON_BLENDER(SkBlendMode::kSrc)
        RETURN_SINGLETON_BLENDER(SkBlendMode::kDst)
        // ... 共 28 种模式
    }
}
```

**设计要点:**
- 每种混合模式对应一个静态单例
- 使用 `SkNoDestructor` 避免静态析构顺序问题
- 减少内存分配,提升引用效率

### 透明黑色影响判断

```cpp
bool SkBlenderBase::affectsTransparentBlack() const {
    if (auto blendMode = this->asBlendMode()) {
        SkBlendModeCoeff src, dst;
        if (SkBlendMode_AsCoeff(*blendMode, &src, &dst)) {
            // 当源为 (0,0,0,0) 时,判断目标系数是否保持 dst 不变
            return dst != SkBlendModeCoeff::kOne &&
                   dst != SkBlendModeCoeff::kISA &&
                   dst != SkBlendModeCoeff::kISC;
        }
        // 高级混合模式不影响透明黑色
        return false;
    }
    // 非混合模式假定会修改透明黑色
    return true;
}
```

**用途:** 优化绘制流程,跳过不影响透明背景的操作。

### 光栅管线集成

```cpp
bool SkBlendModeBlender::onAppendStages(const SkStageRec& rec) const {
    SkBlendMode_AppendStages(fMode, rec.fPipeline);
    return true;
}
```

**调用链:**
```
SkPaint → SkBlender → SkBlendModeBlender → SkRasterPipeline
                                            ↓
                                    append(SkRasterPipelineOp::srcover)
                                    append(SkRasterPipelineOp::multiply)
                                    ...
```

### 序列化格式

```cpp
void SkBlendModeBlender::flatten(SkWriteBuffer& buffer) const {
    buffer.writeInt((int)fMode);  // 写入混合模式整数值
}

sk_sp<SkFlattenable> SkBlendModeBlender::CreateProc(SkReadBuffer& buffer) {
    SkBlendMode mode = buffer.read32LE(SkBlendMode::kLastMode);  // 读取并验证范围
    return SkBlender::Mode(mode);
}
```

**安全性:** `read32LE()` 确保读取值不超过 `kLastMode`,防止越界。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBlenderBase` | 混合器基类,定义虚函数接口 |
| `SkBlendMode` | 混合模式枚举定义 |
| `SkBlendModePriv` | 混合模式辅助函数(系数转换、管线附加) |
| `SkNoDestructor` | 静态对象安全析构 |
| `SkRasterPipeline` | 光栅化管线 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkPaint` | 设置绘制混合模式 |
| `SkShader` | 着色器混合 |
| `SkImageFilter` | 图像滤镜混合 |
| `SkCanvas` | 图层混合 |

## 设计模式与设计决策

### 1. 单例模式 (Singleton Pattern)

**动机:** 混合模式是无状态的纯函数对象,共享实例节省内存。

**实现:**
```cpp
static SkNoDestructor<SkBlendModeBlender> sBlender(mode);
```

**优势:**
- 避免重复分配 28 个混合器对象
- 简化引用计数管理
- 线程安全的延迟初始化(C++11 静态局部变量)

### 2. 策略模式 (Strategy Pattern)

`SkBlender` 作为抽象策略接口,`SkBlendModeBlender` 实现标准混合策略。

### 3. 享元模式 (Flyweight Pattern)

通过单例共享混合器实例,多个 `SkPaint` 对象可引用同一混合器。

### 4. 类型标记

```cpp
BlenderType type() const override { return BlenderType::kBlendMode; }
```

允许运行时快速识别混合器类型,避免 dynamic_cast 开销。

### 5. 扁平化设计

```cpp
std::optional<SkBlendMode> asBlendMode() const final { return fMode; }
```

提供直接访问混合模式的快速路径,避免虚函数调用。

## 性能考量

### 单例内存优化

**传统方案:** 每个 `SkPaint` 分配独立混合器 → 28N 个对象
**单例方案:** 全局共享 28 个混合器 → 常量内存占用

### 快速类型识别

```cpp
if (blender->type() == BlenderType::kBlendMode) {
    // 直接使用 mode(),避免虚函数开销
}
```

### 光栅管线集成

通过 `onAppendStages()` 直接生成优化的管线操作:
```cpp
case SkBlendMode::kSrcOver: p->append(SkRasterPipelineOp::srcover); return;
```

避免运行时分支判断。

### 序列化效率

仅存储 4 字节整数,反序列化直接返回单例引用,无需重建对象。

### 透明黑色优化

```cpp
if (!blender->affectsTransparentBlack()) {
    // 跳过透明区域的混合操作
}
```

减少不必要的像素处理。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkBlendMode.h` | 混合模式枚举定义 |
| `src/core/SkBlendMode.cpp` | 混合模式辅助函数实现 |
| `include/core/SkBlender.h` | 混合器公共接口 |
| `src/core/SkBlenderBase.h` | 混合器基类 |
| `src/core/SkRasterPipeline.h` | 光栅化管线 |
| `src/core/SkBlendModePriv.h` | 混合模式私有函数 |
| `include/core/SkPaint.h` | 绘制属性容器 |
| `src/base/SkNoDestructor.h` | 静态对象包装器 |
