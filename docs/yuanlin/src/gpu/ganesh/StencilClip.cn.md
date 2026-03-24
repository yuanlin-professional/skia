# StencilClip

> 源文件: src/gpu/ganesh/StencilClip.h

## 概述

`StencilClip` 是 Skia Ganesh GPU 后端中实现基于模板缓冲区裁剪的核心类。它结合了现有的模板缓冲区内容和 `GrFixedClip`(包含剪刀矩形和窗口矩形)来实现硬件裁剪。该类作为 `GrHardClip` 的最终实现,为 GPU 渲染操作提供高效的裁剪支持。

## 架构位置

`StencilClip` 位于 Skia GPU 裁剪层次结构的底层:
- **上层**: 被裁剪栈和绘制操作使用
- **同层**: 实现 `GrHardClip` 接口
- **下层**: 封装 `GrFixedClip` 提供的基础裁剪功能
- **协作**: 与 `StencilMaskHelper` 配合生成和使用模板蒙版

## 主要类与结构体

### StencilClip 类
```cpp
class StencilClip final : public GrHardClip {
public:
    explicit StencilClip(const SkISize& rtDims, uint32_t stencilStackID = SK_InvalidGenID);
    StencilClip(const SkISize& rtDims, const SkIRect& scissorRect,
                uint32_t stencilStackID = SK_InvalidGenID);

    const GrFixedClip& fixedClip() const;
    GrFixedClip& fixedClip();

    uint32_t stencilStackID() const;
    bool hasStencilClip() const;
    void setStencilClip(uint32_t stencilStackID);

    // GrHardClip 接口实现
    SkIRect getConservativeBounds() const final;
    Effect apply(GrAppliedHardClip* out, SkIRect* bounds) const final;
    PreClipResult preApply(const SkRect& drawBounds, GrAA aa) const final;
};
```

**继承关系**:
- 基类: `GrHardClip` (通过 `GrClip` 继承)
- 相关类: `GrFixedClip` (组合)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFixedClip` | `GrFixedClip` | 固定裁剪,包含剪刀矩形和窗口矩形 |
| `fStencilStackID` | `uint32_t` | 模板栈 ID,用于标识和缓存模板蒙版 |

## 公共 API 函数

### 构造函数

**StencilClip(rtDims, stencilStackID)**
```cpp
explicit StencilClip(const SkISize& rtDims, uint32_t stencilStackID = SK_InvalidGenID);
```
创建一个带可选模板栈 ID 的模板裁剪对象。

**StencilClip(rtDims, scissorRect, stencilStackID)**
```cpp
StencilClip(const SkISize& rtDims, const SkIRect& scissorRect,
            uint32_t stencilStackID = SK_InvalidGenID);
```
创建带初始剪刀矩形和模板栈 ID 的模板裁剪对象。

### 访问器

| 函数 | 返回类型 | 说明 |
|------|---------|------|
| `fixedClip()` | `const GrFixedClip&` / `GrFixedClip&` | 获取固定裁剪对象的引用 |
| `stencilStackID()` | `uint32_t` | 获取模板栈 ID |
| `hasStencilClip()` | `bool` | 检查是否有有效的模板裁剪 |

### 修改器

**setStencilClip**
```cpp
void setStencilClip(uint32_t stencilStackID);
```
设置模板栈 ID,关联到特定的模板蒙版。

### GrHardClip 接口实现

**getConservativeBounds**
```cpp
SkIRect getConservativeBounds() const final;
```
返回裁剪的保守边界矩形。委托给 `fFixedClip.getConservativeBounds()`。

**apply**
```cpp
Effect apply(GrAppliedHardClip* out, SkIRect* bounds) const final;
```
将裁剪应用到给定边界。实现逻辑:
1. 首先应用固定裁剪(`fFixedClip.apply`)
2. 如果固定裁剪已完全裁剪掉,直接返回 `kClippedOut`
3. 如果有模板裁剪(`hasStencilClip()`),添加模板裁剪并返回 `kClipped`
4. 否则返回固定裁剪的效果

**preApply**
```cpp
PreClipResult preApply(const SkRect& drawBounds, GrAA aa) const final;
```
在实际应用裁剪前进行预判断:
- 如果有模板裁剪,调用基类的通用实现
- 否则委托给 `fFixedClip.preApply`,可能提前判断完全可见或完全裁剪

## 内部实现细节

### 模板栈 ID 的意义

`fStencilStackID` 是模板蒙版的唯一标识符:
- **SK_InvalidGenID**: 表示没有模板裁剪
- **有效 ID**: 标识特定的模板蒙版状态
- **缓存键**: 用于判断是否需要重新生成模板蒙版

### 裁剪组合逻辑

`StencilClip` 实现了三层裁剪的组合:
1. **剪刀矩形**: 快速的矩形裁剪,由 `GrFixedClip` 提供
2. **窗口矩形**: 排除特定矩形区域,由 `GrFixedClip` 提供
3. **模板裁剪**: 基于模板缓冲区的任意形状裁剪

这三层裁剪按以下顺序应用:
- 剪刀矩形: 最快,硬件直接支持
- 窗口矩形: 中等速度,硬件支持但有数量限制
- 模板测试: 相对较慢,但支持任意形状

### 效果枚举

`apply` 方法返回的 `Effect` 枚举:
- **kClippedOut**: 绘制边界完全在裁剪外,可跳过绘制
- **kUnclipped**: 绘制边界完全在裁剪内,无需裁剪
- **kClipped**: 需要应用裁剪

### PreClipResult

`preApply` 返回的结果包含:
- `fEffect`: 预判断的效果(clipped out, unclipped, 或 clipped)
- `fIsRRect`: 如果裁剪是简单的圆角矩形
- `fRRect`, `fAA`: 圆角矩形的详细信息

对于有模板裁剪的情况,无法简化为圆角矩形,因此使用基类的保守实现。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrHardClip` | 提供裁剪接口定义 |
| `GrFixedClip` | 提供剪刀矩形和窗口矩形功能 |
| `GrAppliedClip` | 封装应用后的裁剪状态 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `StencilMaskHelper` | 使用 `StencilClip` 管理模板渲染的裁剪状态 |
| `SurfaceDrawContext` | 使用 `StencilClip` 应用模板裁剪到绘制操作 |
| 裁剪栈实现 | 创建和管理 `StencilClip` 对象 |

## 设计模式与设计决策

### 设计模式

1. **组合模式**: 组合 `GrFixedClip` 和模板栈 ID 提供完整的裁剪功能
2. **委托模式**: 大部分功能委托给 `fFixedClip` 处理
3. **适配器模式**: 将模板缓冲区概念适配到 `GrHardClip` 接口

### 设计决策

**为什么继承 GrHardClip?**
- `GrHardClip` 表示在片段着色器之前应用的硬件裁剪
- 模板测试在片段着色器之前执行,属于硬件裁剪
- 与软件裁剪(在着色器中实现)区分开

**为什么组合而非继承 GrFixedClip?**
- `StencilClip` 是 `GrFixedClip` 的增强版本
- 组合保持了灵活性,可以独立修改两个类
- 避免了多重继承的复杂性

**模板栈 ID 而非直接引用模板缓冲区?**
- 模板缓冲区是渲染目标的一部分,已经存在
- ID 用于标识模板内容的状态,而非资源本身
- 支持缓存验证,避免重复渲染

**为什么 final 类?**
- `StencilClip` 是具体实现,不需要进一步派生
- `final` 关键字允许编译器优化虚函数调用
- 明确设计意图,防止错误使用

### 与其他裁剪类的关系

| 类 | 特点 | 用途 |
|---|------|------|
| `GrClip` | 抽象基类 | 定义裁剪接口 |
| `GrHardClip` | `GrClip` 子类 | 硬件裁剪 |
| `GrFixedClip` | `GrHardClip` 子类 | 剪刀矩形 + 窗口矩形 |
| `StencilClip` | `GrHardClip` 子类 | 固定裁剪 + 模板裁剪 |
| `GrSoftClip` | `GrClip` 子类 | 着色器中的软件裁剪 |

## 性能考量

### 优化策略

1. **硬件加速**:
   - 剪刀测试: 最快的裁剪方式
   - 窗口矩形: 硬件排除指定区域
   - 模板测试: 虽慢但硬件支持

2. **提前退出**:
   - `preApply` 在可能的情况下提前判断
   - 避免不必要的几何体生成和渲染

3. **缓存验证**:
   - 通过 `stencilStackID` 重用模板蒙版
   - 避免昂贵的模板蒙版重新生成

4. **组合优化**:
   - 剪刀矩形快速剔除大部分像素
   - 减少模板测试的像素数量

### 性能特征

**成本排序**(从低到高):
1. 无裁剪
2. 仅剪刀矩形
3. 剪刀矩形 + 窗口矩形
4. 上述 + 模板裁剪

**何时使用 StencilClip**:
- 复杂路径裁剪
- 多个裁剪元素的布尔组合
- 圆角矩形裁剪(当不能简化为抗锯齿路径时)

**何时避免**:
- 简单矩形裁剪(使用 `GrFixedClip`)
- 每帧变化的裁剪(模板蒙版重新生成开销大)

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrClip.h` | 基类 | 裁剪抽象基类 |
| `src/gpu/ganesh/GrHardClip.h` | 基类 | 硬件裁剪接口 |
| `src/gpu/ganesh/GrFixedClip.h` | 成员 | 固定裁剪实现 |
| `src/gpu/ganesh/GrAppliedClip.h` | 依赖 | 应用后的裁剪状态 |
| `src/gpu/ganesh/StencilMaskHelper.h/.cpp` | 协作 | 生成模板蒙版 |
| `src/gpu/ganesh/SurfaceDrawContext.h/.cpp` | 使用者 | 使用裁剪进行绘制 |
