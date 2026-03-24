# SkClipStackDevice

> 源文件: src/core/SkClipStackDevice.h, src/core/SkClipStackDevice.cpp

## 概述

`SkClipStackDevice` 是 Skia 中基于裁剪栈实现的设备基类。它通过维护一个 `SkClipStack` 实例来管理裁剪状态,并提供了设备裁剪操作的完整实现。这个类作为 `SkDevice` 的子类,将抽象的裁剪操作委托给 `SkClipStack` 处理,实现了裁剪功能的模块化。

该类使用内联存储优化,预分配足够的空间来容纳常见情况下的裁剪元素,避免频繁的堆内存分配。

## 架构位置

`SkClipStackDevice` 在 Skia 架构中的位置:
- 继承自 `SkDevice`,实现了裁剪相关的虚函数
- 被具体的设备实现类(如某些 GPU 设备)作为基类
- 使用 `SkClipStack` 作为裁剪状态管理的核心组件
- 连接上层 `SkCanvas` 的裁剪 API 与底层裁剪栈实现

## 主要类与结构体

### SkClipStackDevice

**继承关系:**
```
SkRefCnt
  └── SkDevice
        └── SkClipStackDevice
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fStorage | intptr_t[...] | 预分配的内联存储数组 |
| fClipStack | SkClipStack | 裁剪栈实例,使用 fStorage 作为初始存储 |
| kPreallocCount | static constexpr int | 预分配元素数量(16) |

## 公共 API 函数

### 构造函数

```cpp
SkClipStackDevice(const SkImageInfo& info, const SkSurfaceProps& props)
```
构造设备并初始化裁剪栈,使用内联存储作为初始缓冲区。

### 裁剪栈访问

```cpp
SkClipStack& cs()
const SkClipStack& cs() const
```
直接访问内部裁剪栈,允许外部代码读取或修改裁剪状态。

### 裁剪操作(覆盖自 SkDevice)

```cpp
void pushClipStack() override
void popClipStack() override
void clipRect(const SkRect& rect, SkClipOp op, bool aa) override
void clipRRect(const SkRRect& rrect, SkClipOp op, bool aa) override
void clipPath(const SkPath& path, SkClipOp op, bool aa) override
void clipRegion(const SkRegion& deviceRgn, SkClipOp op) override
void replaceClip(const SkIRect& rect) override
```

### 裁剪状态查询(覆盖自 SkDevice)

```cpp
bool isClipAntiAliased() const override
bool isClipWideOpen() const override
bool isClipEmpty() const override
bool isClipRect() const override
SkIRect devClipBounds() const override
```

### Android 特定功能

```cpp
void android_utils_clipAsRgn(SkRegion* rgn) const override
```
将裁剪栈转换为区域表示,用于 Android 框架集成。

## 内部实现细节

### 内联存储机制

```cpp
static constexpr int kPreallocCount = 16;
intptr_t fStorage[kPreallocCount * sizeof(SkClipStack::Element) / sizeof(intptr_t)];
SkClipStack fClipStack(fStorage, sizeof(fStorage));
```

预分配足够存储 16 个 `SkClipStack::Element` 的空间:
- 避免小型裁剪栈的堆分配
- 当元素超过 16 个时,`SkClipStack` 自动切换到堆分配
- 对齐到 `intptr_t` 确保正确的内存对齐

### 坐标变换处理

```cpp
void clipRect(const SkRect& rect, SkClipOp op, bool aa) {
    fClipStack.clipRect(rect, this->localToDevice(), op, aa);
}
```

所有几何裁剪操作都会:
1. 获取当前的局部到设备空间变换矩阵(`localToDevice()`)
2. 将裁剪形状与变换一起传递给 `SkClipStack`
3. `SkClipStack` 内部将形状变换到设备空间

### 区域裁剪转换

```cpp
void clipRegion(const SkRegion& rgn, SkClipOp op) {
    SkIPoint origin = this->getOrigin();
    SkRegion tmp;
    SkPathBuilder builder;
    rgn.addBoundaryPath(&builder);
    builder.transform(SkMatrix::Translate(-origin));
    fClipStack.clipPath(builder.detach(), SkMatrix::I(), op, false);
}
```

由于 `SkClipStack` 不直接支持区域,实现中:
1. 将区域转换为路径边界
2. 应用设备原点偏移
3. 作为路径裁剪添加到栈中(非抗锯齿)

### 替换裁剪实现

```cpp
void replaceClip(const SkIRect& rect) {
    SkRect deviceRect = SkMatrixPriv::MapRect(this->globalToDevice(), SkRect::Make(rect));
    fClipStack.replaceClip(deviceRect, /*doAA=*/false);
}
```

使用全局到设备的变换矩阵,将全局矩形转换到设备空间后替换整个裁剪。

### Android 区域转换

`android_utils_clipAsRgn` 实现复杂的裁剪栈到区域转换:
1. 检测简单情况:矩形相交的裁剪可以直接转换
2. 复杂情况:遍历栈中每个元素
3. 将元素转为路径,再转为区域
4. 使用区域操作组合结果
5. 特殊处理替换操作(Replace op)

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| src/core/SkClipStack.h | 核心裁剪栈实现 |
| src/core/SkDevice.h | 设备基类 |
| include/core/SkMatrix.h | 坐标变换 |
| include/core/SkRegion.h | 区域裁剪支持 |
| include/core/SkShader.h | 着色器裁剪 |
| src/core/SkMatrixPriv.h | 矩阵私有工具 |
| include/core/SkPathBuilder.h | 路径构建 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| GPU 设备实现 | 可能继承 SkClipStackDevice |
| 测试代码 | 测试裁剪功能 |
| Android 框架 | 使用 android_utils_clipAsRgn |

## 设计模式与设计决策

### 组合优于继承

使用组合(`fClipStack`)而非多重继承:
- 清晰的职责分离:设备管理绘制,裁剪栈管理裁剪
- 允许裁剪栈的独立测试和重用
- 简化了设备子类的实现

### 模板方法模式

`SkDevice` 定义虚函数接口,`SkClipStackDevice` 提供基于裁剪栈的默认实现:
- 子类可以覆盖特定操作以优化
- 大多数情况下可以直接使用默认实现

### 内联存储优化

```cpp
intptr_t fStorage[kPreallocCount * sizeof(SkClipStack::Element) / sizeof(intptr_t)];
```

小对象优化(Small Object Optimization)模式:
- 预分配固定大小存储避免堆分配
- 对常见用例(深度 ≤ 16 的裁剪栈)零堆分配
- 代码简洁:由 `SkClipStack` 构造函数自动处理溢出

### 延迟转换策略

`clipRegion` 和 `android_utils_clipAsRgn` 体现不同的转换策略:
- 输入时转换:区域输入立即转为路径存储在栈中
- 输出时转换:栈在需要时才转为区域,避免不必要的计算

## 性能考量

### 预分配大小选择

```cpp
static constexpr int kPreallocCount = 16;
```

16 个元素是经验值:
- 覆盖大多数实际应用的裁剪深度
- 每个 Element 约 100-200 字节,总计约 2-3 KB 内联存储
- 平衡了内存占用与堆分配避免

### 查询操作优化

```cpp
bool isClipWideOpen() const {
    return fClipStack.quickContains(SkRect::MakeIWH(this->width(), this->height()));
}
```

使用 `quickContains` 而非精确检测:
- O(n) 最坏情况,但通常在栈顶快速返回
- 适用于频繁查询的场景

### 边界计算缓存

```cpp
SkIRect devClipBounds() const {
    SkIRect r = fClipStack.bounds(this->imageInfo().bounds()).roundOut();
    return r;
}
```

利用 `SkClipStack` 内部的边界缓存:
- 栈顶元素已经计算并缓存了保守边界
- 避免每次调用重新遍历整个栈

### 矩形裁剪快速路径

```cpp
bool isClipRect() const {
    if (this->isClipWideOpen()) return true;
    else if (this->isClipEmpty()) return false;

    SkClipStack::BoundsType boundType;
    bool isIntersectionOfRects;
    SkRect bounds;
    fClipStack.getBounds(&bounds, &boundType, &isIntersectionOfRects);
    return isIntersectionOfRects && boundType == SkClipStack::kNormal_BoundsType;
}
```

特殊处理矩形裁剪情况:
- GPU 可以使用硬件裁剪窗口
- 光栅化器可以使用简单的边界检测
- 避免复杂的路径光栅化

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkClipStack.h/cpp | 核心依赖 | 裁剪栈实现 |
| src/core/SkDevice.h | 基类 | 设备抽象接口 |
| src/core/SkBitmapDevice.h | 兄弟类 | 基于位图的设备实现 |
| include/core/SkCanvas.h | 客户端 | 通过设备 API 使用裁剪 |
| src/core/SkRasterClip.h | 替代方案 | 基于区域的裁剪 |
| src/gpu/ganesh/GrDevice.h | 可能子类 | GPU 设备可能继承此类 |
