# SkCamera

> 源文件: include/utils/SkCamera.h, src/utils/SkCamera.cpp

## 概述

SkCamera 是 Skia 提供的 3D 相机系统,用于实现 3D 变换和透视投影。该模块包含三个核心类:SkPatch3D(3D 面片)、SkCamera3D(3D 相机)和 Sk3DView(3D 视图)。这些工具允许在 2D Canvas 上模拟 3D 效果,通过 3D 变换将 3D 空间中的对象投影到 2D 平面。

**重要提示**: 整个模块已被标记为 DEPRECATED(废弃),将从 Skia 中移除。Skia 现在通过 SkM44(4x4 矩阵)和 SkCanvas 的内置支持提供 3D 变换功能。

主要功能:
- 3D 面片变换和法线计算
- 3D 相机位置和方向管理
- 3D 到 2D 的透视投影
- 3D 视图的保存/恢复机制
- 旋转、平移等 3D 变换操作

## 架构位置

SkCamera 位于 Skia 的 utils 模块中,提供遗留的 3D 支持:

```
Skia Graphics Library
├── Core
│   ├── SkCanvas (2D 绘图接口)
│   ├── SkMatrix (3x3 矩阵)
│   └── SkM44 (4x4 矩阵,新的 3D 支持)
├── Utils (遗留工具)
│   └── SkCamera (3D 相机系统) ← 当前模块 (DEPRECATED)
│       ├── SkPatch3D (3D 面片)
│       ├── SkCamera3D (3D 相机)
│       └── Sk3DView (3D 视图)
└── Private
    └── SkNoncopyable (不可复制基类)
```

该模块曾用于 Android Framework 和一些遗留应用,但现在推荐使用 SkM44。

## 主要类与结构体

### SkPatch3D

**类型**: 3D 面片类(DEPRECATED)

**继承关系**:
- 无继承,独立的数据结构类

**关键成员变量**:

| 成员类型 | 名称 | 访问性 | 说明 |
|---------|------|--------|------|
| SkV3 | fU | public | U 方向向量(局部 X 轴) |
| SkV3 | fV | public | V 方向向量(局部 Y 轴) |
| SkV3 | fOrigin | public | 原点位置 |

**特性**:
- 表示 3D 空间中的一个坐标系
- fU 和 fV 定义面片的局部坐标系
- 法线方向为 fU × fV (叉乘)

### SkCamera3D

**类型**: 3D 相机类(DEPRECATED)

**继承关系**:
- 无继承,独立的相机类

**关键成员变量**:

| 成员类型 | 名称 | 访问性 | 说明 |
|---------|------|--------|------|
| SkV3 | fLocation | public | 相机空间的原点 |
| SkV3 | fAxis | public | 视线方向(向前) |
| SkV3 | fZenith | public | 向上方向 |
| SkV3 | fObserver | public | 观察者眼睛位置 |
| SkMatrix | fOrientation | mutable | 方向矩阵(缓存) |
| bool | fNeedToUpdate | mutable | 更新标志 |

**特性**:
- fLocation 和 fObserver 可以不同(模拟偏心投影)
- fOrientation 是延迟计算的(仅在需要时更新)

### Sk3DView

**类型**: 3D 视图类(DEPRECATED)

**继承关系**:
```
SkNoncopyable
  └── Sk3DView
```

**关键成员变量**:

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| Rec* | fRec | 当前变换记录指针 |
| Rec | fInitialRec | 初始变换记录 |
| SkCamera3D | fCamera | 相机实例 |

**内部结构 Rec**:

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| Rec* | fNext | 下一个记录(链表) |
| SkM44 | fMatrix | 4x4 变换矩阵 |

**特性**:
- 使用链表实现保存/恢复栈
- 累积 3D 变换到矩阵
- 最终通过相机投影到 2D

## 公共 API 函数

### SkPatch3D 方法

#### 构造函数

```cpp
SkPatch3D();
```

**功能**: 创建面片并调用 reset()。

#### reset

```cpp
void reset();
```

**功能**: 重置面片到默认状态。

**默认值**:
- `fOrigin = {0, 0, 0}`
- `fU = {1, 0, 0}` (X 轴)
- `fV = {0, -1, 0}` (负 Y 轴,Skia 坐标系)

#### transform

```cpp
void transform(const SkM44& m, SkPatch3D* dst = nullptr) const;
```

**功能**: 使用 4x4 矩阵变换面片。

**参数**:
- `m`: 变换矩阵
- `dst`: 目标面片(nullptr 表示就地变换)

**实现**:
- fU 和 fV 作为方向向量变换(齐次坐标 w=0)
- fOrigin 作为点变换(齐次坐标 w=1)

#### dotWith

```cpp
SkScalar dotWith(SkScalar dx, SkScalar dy, SkScalar dz) const;
SkScalar dotWith(const SkV3& v) const;
```

**功能**: 计算给定向量与面片法线的点积。

**实现**:
```cpp
// 法线 = fU × fV (叉乘)
cx = fU.y * fV.z - fU.z * fV.y
cy = fU.z * fV.x - fU.x * fV.y  // 注意:代码中疑似错误,应为 fV.z
cz = fU.x * fV.y - fU.y * fV.x
return cx * dx + cy * dy + cz * dz
```

**应用**: 背面剔除、光照计算。

#### rotate/rotateDegrees (废弃)

```cpp
void rotate(SkScalar x, SkScalar y, SkScalar z) {}
void rotateDegrees(SkScalar x, SkScalar y, SkScalar z) {}
```

**状态**: 空实现,保留用于 animator 兼容性。

### SkCamera3D 方法

#### 构造函数

```cpp
SkCamera3D();
```

**功能**: 创建相机并调用 reset()。

#### reset

```cpp
void reset();
```

**功能**: 重置相机到默认状态。

**默认值**:
- `fLocation = {0, 0, -576}` (向后 8 英寸,72dpi × 8)
- `fAxis = {0, 0, 1}` (向前看)
- `fZenith = {0, -1, 0}` (向上)
- `fObserver = {0, 0, -576}` (与 location 相同)
- `fNeedToUpdate = true`

#### update

```cpp
void update();
```

**功能**: 标记相机需要重新计算方向矩阵。

**实现**: 仅设置 `fNeedToUpdate = true`。

#### patchToMatrix

```cpp
void patchToMatrix(const SkPatch3D& patch, SkMatrix* matrix) const;
```

**功能**: 将 3D 面片通过相机投影到 2D 矩阵。

**核心算法**:
1. 如果需要,调用 doUpdate() 更新方向矩阵
2. 计算面片原点到相机位置的差向量
3. 计算差向量在视轴上的投影长度(dot)
4. 构建矩阵: `matrix = fOrientation * [patch.fU | patch.fV | diff] / dot`

**矩阵含义**:
- 将面片的局部坐标系变换到相机空间
- 然后投影到 2D 平面
- 除以 dot 进行透视归一化

### Sk3DView 方法

#### 构造函数和析构函数

```cpp
Sk3DView();
~Sk3DView();
```

**功能**:
- 构造: 初始化链表头为 fInitialRec
- 析构: 释放所有链表节点(除 fInitialRec)

#### save

```cpp
void save();
```

**功能**: 保存当前变换状态。

**实现**:
- 分配新的 Rec 节点
- 复制当前矩阵
- 插入链表头部

#### restore

```cpp
void restore();
```

**功能**: 恢复到上一个保存的状态。

**实现**:
- 断言不能恢复初始状态(fRec != &fInitialRec)
- 移除当前节点
- 恢复到 fNext 指向的节点

#### translate

```cpp
void translate(SkScalar x, SkScalar y, SkScalar z);
```

**功能**: 应用 3D 平移。

**实现**: `fRec->fMatrix.preTranslate(x, y, z)`

#### rotateX/Y/Z

```cpp
void rotateX(SkScalar deg);
void rotateY(SkScalar deg);
void rotateZ(SkScalar deg);
```

**功能**: 绕各轴旋转指定角度(度数)。

**实现**:
- 转换角度为弧度: `deg * SK_ScalarPI / 180`
- 使用 SkM44::Rotate 生成旋转矩阵
- 预乘到当前矩阵: `fRec->fMatrix.preConcat(rotation)`

**旋转轴**:
- X 轴: `{1, 0, 0}`
- Y 轴: `{0, -1, 0}` (注意负号,Skia 坐标系)
- Z 轴: `{0, 0, 1}`

#### setCameraLocation (Android Framework)

```cpp
#ifdef SK_BUILD_FOR_ANDROID_FRAMEWORK
void setCameraLocation(SkScalar x, SkScalar y, SkScalar z);
SkScalar getCameraLocationX() const;
SkScalar getCameraLocationY() const;
SkScalar getCameraLocationZ() const;
#endif
```

**功能**: 设置/获取相机位置(单位:英寸)。

**实现**:
- 输入单位为英寸,内部转换为点(乘以 72.0f)
- 同时更新 fLocation 和 fObserver
- 调用 fCamera.update()

#### getMatrix

```cpp
void getMatrix(SkMatrix* matrix) const;
```

**功能**: 获取最终的 2D 投影矩阵。

**流程**:
1. 创建默认面片
2. 使用累积的 3D 变换变换面片
3. 通过相机投影面片到 2D 矩阵

#### applyToCanvas

```cpp
void applyToCanvas(SkCanvas* canvas) const;
```

**功能**: 将 3D 变换应用到 Canvas。

**实现**:
```cpp
SkMatrix matrix;
this->getMatrix(&matrix);
canvas->concat(matrix);
```

#### dotWithNormal

```cpp
SkScalar dotWithNormal(SkScalar x, SkScalar y, SkScalar z) const;
```

**功能**: 计算向量与变换后面片法线的点积。

**应用**: 判断面片是否朝向观察者。

## 内部实现细节

### SkScalarDotDiv 辅助函数

```cpp
static SkScalar SkScalarDotDiv(int count, const SkScalar a[], int step_a,
                               const SkScalar b[], int step_b,
                               SkScalar denom) {
    SkScalar prod = 0;
    for (int i = 0; i < count; i++) {
        prod += a[0] * b[0];
        a += step_a;
        b += step_b;
    }
    return prod / denom;
}
```

**用途**: 计算两个向量的点积并除以分母,用于矩阵计算。

### SkCamera3D::doUpdate 实现

构建方向矩阵的核心算法:

```cpp
void SkCamera3D::doUpdate() const {
    // 1. 归一化视轴
    axis = fAxis.normalize();

    // 2. 构造正交的天顶向量(Gram-Schmidt 正交化)
    zenith = fZenith - (axis * fZenith) * axis;
    zenith = zenith.normalize();

    // 3. 计算叉向量(完成右手坐标系)
    cross = axis.cross(zenith);

    // 4. 构建方向矩阵
    // 这是一个组合变换:透视投影 + Z-shear
    auto [x, y, z] = fObserver;

    orien[kMScaleX]  = x * axis.x - z * cross.x
    orien[kMSkewX]   = x * axis.y - z * cross.y
    orien[kMTransX]  = x * axis.z - z * cross.z
    orien[kMSkewY]   = y * axis.x - z * zenith.x
    orien[kMScaleY]  = y * axis.y - z * zenith.y
    orien[kMTransY]  = y * axis.z - z * zenith.z
    orien[kMPersp0]  = axis.x
    orien[kMPersp1]  = axis.y
    orien[kMPersp2]  = axis.z
}
```

**矩阵含义**:
- 前两行: 基于观察者位置的 Z-shear 和缩放
- 第三行: 透视参数(视轴方向)
- 整体实现透视投影

### patchToMatrix 详细实现

```cpp
void SkCamera3D::patchToMatrix(const SkPatch3D& quilt, SkMatrix* matrix) const {
    // 1. 更新方向矩阵(如果需要)
    if (fNeedToUpdate) {
        this->doUpdate();
        fNeedToUpdate = false;
    }

    // 2. 计算面片原点相对相机的差向量
    SkV3 diff = quilt.fOrigin - fLocation;

    // 3. 计算差向量在视轴上的投影(透视深度)
    SkScalar dot = diff.dot({mapPtr[6], mapPtr[7], mapPtr[8]});

    // 4. 构建最终矩阵: M = fOrientation * [U V diff] / dot
    // 对于矩阵的每个元素 (i, j):
    // matrix[i][j] = dot(fOrientation[i], [U V diff][j]) / dot

    // 第一列(U)
    matrix[kMScaleX] = SkScalarDotDiv(3, &quilt.fU.x, 1, &mapPtr[0], 1, dot);
    matrix[kMSkewY]  = SkScalarDotDiv(3, &quilt.fU.x, 1, &mapPtr[3], 1, dot);
    matrix[kMPersp0] = SkScalarDotDiv(3, &quilt.fU.x, 1, &mapPtr[6], 1, dot);

    // 第二列(V)
    matrix[kMSkewX]  = SkScalarDotDiv(3, &quilt.fV.x, 1, &mapPtr[0], 1, dot);
    matrix[kMScaleY] = SkScalarDotDiv(3, &quilt.fV.x, 1, &mapPtr[3], 1, dot);
    matrix[kMPersp1] = SkScalarDotDiv(3, &quilt.fV.x, 1, &mapPtr[6], 1, dot);

    // 第三列(diff)
    matrix[kMTransX] = SkScalarDotDiv(3, &diff.x, 1, &mapPtr[0], 1, dot);
    matrix[kMTransY] = SkScalarDotDiv(3, &diff.x, 1, &mapPtr[3], 1, dot);
    matrix[kMPersp2] = SK_Scalar1;
}
```

**除以 dot 的原因**: 归一化到规范空间,类似于齐次除法。

### Sk3DView 保存/恢复机制

链表结构:

```
fRec ──> [Rec3] ──> [Rec2] ──> [Rec1] ──> [fInitialRec] ──> NULL
          ^
          └─ 当前状态
```

保存时:
```cpp
void save() {
    Rec* newRec = new Rec;
    newRec->fNext = fRec;
    newRec->fMatrix = fRec->fMatrix;  // 复制
    fRec = newRec;
}
```

恢复时:
```cpp
void restore() {
    Rec* next = fRec->fNext;
    delete fRec;
    fRec = next;
}
```

### 坐标系约定

Skia 的 Y 轴向下:
- 默认 fZenith = {0, -1, 0} (向上在屏幕坐标中是负 Y)
- rotateY 使用负 Y 轴 {0, -1, 0}

### 透视投影原理

面片局部坐标 (u, v) 到屏幕坐标 (x, y) 的映射:

1. 面片坐标系中的点: `P = origin + u * fU + v * fV`
2. 相机空间: `P' = fOrientation * (P - fLocation)`
3. 透视除法: `(x, y) = (P'.x / P'.z, P'.y / P'.z) * scale`
4. 编码在矩阵中,通过齐次坐标实现

## 依赖关系

### 依赖的模块

| 模块 | 类型 | 说明 |
|-----|------|------|
| SkCanvas | 核心接口 | applyToCanvas 的目标 |
| SkMatrix | 核心几何 | 2D 投影矩阵 |
| SkM44 | 核心几何 | 4x4 变换矩阵 |
| SkV3 | 核心类型 | 3D 向量 |
| SkNoncopyable | 基类工具 | 禁止复制 |

### 被依赖的模块

| 模块 | 使用场景 | 说明 |
|-----|---------|------|
| Android Framework | 卡片翻转动画 | View 的 3D 旋转效果 |
| 遗留应用 | 3D 效果 | 老代码中的 3D 视图 |
| Animator | 动画系统 | 保留的旋转方法兼容性 |

**注意**: 新代码应使用 SkM44 和 SkCanvas 的原生 3D 支持。

## 设计模式与设计决策

### 延迟计算 (Lazy Evaluation)

SkCamera3D 的方向矩阵:
- 使用 mutable 成员和标志位
- 仅在 patchToMatrix 需要时计算
- 避免不必要的三角函数和归一化计算

### 保存/恢复栈

Sk3DView 使用链表实现栈:
- **优势**: 动态大小,无固定深度限制
- **劣势**: 堆分配开销
- **权衡**: 3D 视图通常嵌套深度不大

### 分离关注点

三个类的职责:
- **SkPatch3D**: 表示 3D 几何(面片)
- **SkCamera3D**: 表示观察者(相机)
- **Sk3DView**: 管理变换栈(视图)

清晰的职责划分便于理解和维护。

### 矩阵预乘 (Pre-multiplication)

Sk3DView 使用 preTranslate, preConcat:
- 变换按应用顺序累积
- 符合直觉的变换组合
- 最后应用的变换在矩阵链的左侧

### 观察者与位置分离

SkCamera3D 允许 fLocation 和 fObserver 不同:
- 支持偏心投影
- 模拟真实相机的光学中心偏移
- 大多数情况下两者相同

### Android 特定 API

setCameraLocation 仅在 Android 构建中可用:
- 使用英寸单位(适合物理设备)
- 内部转换为点(72 dpi)
- 保持与 Android Framework 的兼容性

### 废弃策略

保留 API 但标记为 DEPRECATED:
- 允许现有代码继续编译
- 文档中明确指出替代方案(SkM44)
- 逐步迁移,避免破坏性变更

## 性能考量

### 三角函数开销

doUpdate 中的向量归一化:
- 涉及平方根计算
- 通过 fNeedToUpdate 标志避免重复计算
- 仅在相机参数改变时更新

### 矩阵计算

patchToMatrix 的复杂度:
- 大量浮点乘法和加法
- 每个矩阵元素需要 3 次乘加操作
- 现代 CPU 的 SIMD 优化可以加速

### 堆分配

Sk3DView::save 每次调用 new:
- 在频繁保存/恢复时产生开销
- 可以使用对象池优化(未实现)
- 实际应用中保存深度通常不大

### 内存占用

```
sizeof(Sk3DView) ≈ sizeof(Rec*) + sizeof(Rec) + sizeof(SkCamera3D)
                 ≈ 8 + (8 + 64) + (12 + 12 + 12 + 12 + 36 + 1)
                 ≈ 165 bytes
```

轻量级,适合栈分配。

### SkScalarDotDiv 性能

循环展开机会:
- count 通常为 3(固定值)
- 编译器可以完全展开循环
- 手动展开可能更快(未实现)

### 链表遍历

析构函数需要遍历链表:
- O(n) 时间,n 为保存深度
- 大多数情况下 n 很小(<10)
- 不是性能瓶颈

### 替代方案性能

SkM44 的优势:
- 直接使用 4x4 矩阵,避免中间转换
- 更好的 SIMD 优化
- 与 GPU 管线一致

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/utils/SkCamera.h | 公共 API 声明 |
| src/utils/SkCamera.cpp | 实现代码 |
| include/core/SkCanvas.h | Canvas 接口 |
| include/core/SkMatrix.h | 3x3 矩阵 |
| include/core/SkM44.h | 4x4 矩阵(推荐替代) |
| include/private/base/SkNoncopyable.h | 不可复制基类 |
| include/core/SkScalar.h | 标量类型 |
