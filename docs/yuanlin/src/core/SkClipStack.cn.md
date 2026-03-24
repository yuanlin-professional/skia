# SkClipStack

> 源文件: src/core/SkClipStack.h, src/core/SkClipStack.cpp

## 概述

`SkClipStack` 是 Skia 图形库中管理裁剪区域栈的核心类。它维护一个裁剪元素的双端队列,支持 save/restore 操作,能够高效地跟踪绘图过程中的裁剪状态。该类将保存计数(save count)和裁剪元素分开存储,允许单个 save/restore 状态包含多个裁剪操作。

该类是 Skia 渲染管线中裁剪系统的基础,用于确定哪些像素可以被绘制。它通过维护一系列裁剪元素的组合,提供快速的边界查询、包含性检测和裁剪状态优化。

## 架构位置

`SkClipStack` 位于 Skia 核心层(src/core),是渲染设备与画布之间的桥梁:
- 被 `SkCanvas` 调用以管理裁剪状态
- 被 `SkDevice` 的子类(如 `SkClipStackDevice`)使用
- 与 GPU 后端(Ganesh/Graphite)交互,为硬件加速提供裁剪信息
- 为光栅化器提供裁剪边界信息

## 主要类与结构体

### SkClipStack::Element

裁剪栈中的单个元素,表示一个裁剪形状及其组合操作。

**继承关系:**
- 无继承关系(独立类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fDeviceSpaceType | DeviceSpaceType | 元素类型(空、矩形、圆角矩形、路径、着色器) |
| fDeviceSpacePath | std::optional&lt;SkPath&gt; | 设备空间路径(类型为 kPath 时) |
| fDeviceSpaceRRect | SkRRect | 设备空间圆角矩形(类型为 kRect/kRRect 时) |
| fShader | sk_sp&lt;SkShader&gt; | 着色器(类型为 kShader 时) |
| fSaveCount | int | 添加此元素时的保存计数 |
| fOp | SkClipOp | 裁剪操作类型(相交、差集) |
| fDoAA | bool | 是否使用抗锯齿 |
| fIsReplace | bool | 是否为替换操作 |
| fFiniteBoundType | BoundsType | 边界类型(普通或内外翻转) |
| fFiniteBound | SkRect | 有限边界矩形 |
| fIsIntersectionOfRects | bool | 是否为矩形相交结果 |
| fGenID | uint32_t | 生成 ID,用于缓存 |

### SkClipStack

主类,管理裁剪元素栈。

**继承关系:**
- 无继承关系

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fDeque | SkDeque | 存储 Element 的双端队列 |
| fSaveCount | int | 当前保存计数 |

### SkClipStack::Iter

迭代器类,支持从底部到顶部或从顶部到底部遍历栈。

### SkClipStack::B2TIter

从底部到顶部的迭代器,私有继承自 Iter。

## 公共 API 函数

### 构造与赋值

```cpp
SkClipStack()
SkClipStack(void* storage, size_t size)  // 使用自定义存储
SkClipStack(const SkClipStack& b)       // 拷贝构造
SkClipStack& operator=(const SkClipStack& b)
```

### Save/Restore 操作

```cpp
void save()                              // 增加保存计数
void restore()                           // 减少保存计数并恢复
int getSaveCount() const                 // 获取当前保存计数
```

### 裁剪操作

```cpp
void clipRect(const SkRect&, const SkMatrix&, SkClipOp, bool doAA)
void clipRRect(const SkRRect&, const SkMatrix&, SkClipOp, bool doAA)
void clipPath(const SkPath&, const SkMatrix&, SkClipOp, bool doAA)
void clipShader(sk_sp<SkShader>)
void clipEmpty()                         // 将裁剪设为空
void replaceClip(const SkRect&, bool doAA)  // 替换整个裁剪
```

### 查询操作

```cpp
void getBounds(SkRect* canvFiniteBound, BoundsType* boundType,
               bool* isIntersectionOfRects = nullptr) const
SkRect bounds(const SkIRect& deviceBounds) const
bool isEmpty(const SkIRect& deviceBounds) const
bool isWideOpen() const                  // 是否为无限平面
bool quickContains(const SkRect&) const  // 快速包含性检测
bool quickContains(const SkRRect&) const
bool isRRect(const SkRect& bounds, SkRRect* rrect, bool* aa) const
uint32_t getTopmostGenID() const         // 获取顶部元素的生成 ID
```

## 内部实现细节

### 元素初始化与优化

`Element` 类提供多种初始化方法,在构造时会自动优化形状:
- `initRect`: 如果矩阵保持矩形特性,直接存储为设备空间矩形;否则转为路径
- `initRRect`: 尝试使用 `SkRRect::transform`,失败则降级为路径
- `initPath`: 检测路径是否为矩形或椭圆,可能升级为更高效的表示

### 边界更新机制

`updateBoundAndGenID` 方法实现裁剪边界的增量更新:
1. 根据当前元素的几何类型设置初始边界
2. 结合前一个元素的边界信息
3. 根据裁剪操作类型(相交/差集)和填充模式(普通/反向)组合边界
4. 生成唯一的 GenID 用于缓存优化

边界类型有两种:
- `kNormal_BoundsType`: 边界内的像素可写
- `kInsideOut_BoundsType`: 边界外的像素可写(用于反向填充)

### 就地合并优化

`pushElement` 方法在添加新元素时会尝试就地合并:
- 空裁剪与任何相交/差集操作合并后仍为空
- 同一保存层级内的矩形相交可以直接更新前一个元素
- 着色器裁剪可以通过 `SkShaders::Blend` 组合
- 不相交的边界可以直接设为空

### Generation ID 系统

使用原子递增的 GenID 跟踪裁剪状态变化:
- `kInvalidGenID` (0): 无效 ID
- `kEmptyGenID` (1): 空裁剪
- `kWideOpenGenID` (2): 全开裁剪
- 其他 ID: 从 3 开始递增,用于缓存验证

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkClipOp.h | 裁剪操作类型定义 |
| include/core/SkMatrix.h | 矩阵变换 |
| include/core/SkPath.h | 路径几何 |
| include/core/SkRRect.h | 圆角矩形 |
| include/core/SkRect.h | 矩形 |
| include/core/SkShader.h | 着色器裁剪 |
| include/private/base/SkDeque.h | 双端队列容器 |
| src/core/SkRectPriv.h | 矩形工具函数 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| SkCanvas | 通过 SkDevice 间接使用裁剪栈 |
| SkClipStackDevice | 直接包含并管理裁剪栈 |
| SkDevice | 子类可能使用裁剪栈 |
| GPU 后端 | 查询裁剪信息进行硬件加速 |

## 设计模式与设计决策

### 分离保存计数与裁剪元素

设计决策:将 `fSaveCount` 与 `fDeque` 分开存储,而不是为每个保存层级创建一个栈帧。
- **优点**: 单个 save/restore 可以包含多个裁剪操作,节省内存
- **实现**: 每个 Element 记录其对应的 saveCount,restore 时删除 saveCount 大于目标值的元素

### 增量边界计算

每次添加新元素时增量更新边界,而不是重新计算整个栈:
- 使用 `fFiniteBound` 和 `fFiniteBoundType` 记录当前裁剪的保守边界
- 支持内外翻转边界(inside-out bounds)处理反向填充路径
- 追踪 `fIsIntersectionOfRects` 标志以识别精确的矩形裁剪

### 多态形状表示

使用 `DeviceSpaceType` 枚举而非虚函数实现多态:
- 避免虚函数调用开销
- 允许 Element 在栈上分配
- 使用 `std::optional<SkPath>` 延迟路径创建

### 就地优化策略

`canBeIntersectedInPlace` 和 `rectRectIntersectAllowed` 方法实现智能合并:
- 减少元素数量,提高查询性能
- 检测抗锯齿(AA)兼容性,避免错误的边缘混合
- 特殊处理着色器裁剪的组合

## 性能考量

### 预分配策略

```cpp
static const int kDefaultElementAllocCnt = 8;
```
双端队列一次性分配 8 个 Element 大小的块,平衡了内存占用与分配开销。

### 快速路径优化

- `isWideOpen()`: O(1) 检测无裁剪情况
- `quickContains()`: 自顶向下快速检测包含性,避免完整栈遍历
- `isRRect()`: 检测整个栈是否等价于单个圆角矩形裁剪,限制检查 17 个元素

### GenID 缓存

客户端可以缓存基于 GenID 的裁剪表示:
- 相同的 GenID 表示相同的裁剪状态
- 支持 GPU 后端缓存裁剪路径的光栅化结果
- 使用原子操作确保线程安全

### 内存效率

- `SkClipStackDevice` 预分配 16 个元素的内联存储(`fStorage`)
- 使用 placement new 管理 Element 生命周期
- `std::optional<SkPath>` 避免不必要的路径分配

### wyhash 算法

`SkChecksum` 模块使用高性能的 wyhash 算法:
- 64 位和 32 位哈希函数
- 针对小数据量和大数据量优化的分支
- 使用 SIMD 指令(在支持的平台上)

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkClipStackDevice.h/cpp | 使用者 | 基于 SkClipStack 的设备实现 |
| src/core/SkDevice.h | 接口 | 设备基类,定义裁剪相关虚函数 |
| include/core/SkCanvas.h | 客户端 | 通过设备间接使用裁剪栈 |
| src/core/SkRasterClip.h | 替代方案 | 基于区域的裁剪实现 |
| include/core/SkClipOp.h | 枚举定义 | 裁剪操作类型 |
| src/gpu/ganesh/GrClip.h | GPU 适配 | GPU 后端的裁剪抽象 |
| src/core/SkBitmapDevice.h | 光栅设备 | 光栅化设备的裁剪处理 |
