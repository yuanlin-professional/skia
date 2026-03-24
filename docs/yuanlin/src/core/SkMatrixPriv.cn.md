# SkMatrixPriv

> 源文件: src/core/SkMatrixPriv.h

## 概述

`SkMatrixPriv` 是 Skia 矩阵内部实现的辅助工具类,提供了一系列非公开但在 Skia 内部广泛使用的矩阵操作。该类包括序列化/反序列化、逆变换映射、带步长的点变换、矩阵分解、差分面积缩放计算等高级功能,这些功能对外部用户隐藏但对 Skia 内部实现至关重要。

该模块是 `SkMatrix` 和 `SkM44` 公共 API 的补充,暴露了一些性能关键或实现细节相关的功能。它采用静态方法类设计,所有方法为纯函数,通过友元机制访问矩阵的私有成员。

## 架构位置

`SkMatrixPriv` 位于 Skia 核心层的内部接口层:

```
include/core/
├── SkMatrix.h          # 3x3 矩阵公共 API
└── SkM44.h             # 4x4 矩阵公共 API

src/core/
├── SkMatrixPriv.h      # 矩阵私有辅助(本模块)
├── SkMatrixInvert.h    # 矩阵求逆
├── SkMatrixUtils.h     # 矩阵工具函数
└── SkDraw.cpp          # 使用 SkMatrixPriv 的绘图代码

使用关系:
SkCanvas/SkDevice → SkMatrixPriv → SkMatrix/SkM44(私有成员)
```

该模块是 Skia 内部代码访问矩阵高级功能的桥梁,不包含在公共 API 头文件中。

## 主要类与结构体

### SkMatrixPriv

工具类,所有方法为静态函数,无实例。

**关键成员函数**:

| 类别 | 函数数量 | 典型函数 |
|------|---------|---------|
| 序列化 | 2 | `WriteToMemory`, `ReadFromMemory` |
| 映射函数获取 | 1 | `GetMapPtsProc` |
| 逆变换 | 1 | `InverseMapRect` |
| 带步长点映射 | 3 | `MapPointsWithStride`, `MapHomogeneousPointsWithStride` |
| 矩阵操作 | 2 | `PostIDiv`, `CheapEqual` |
| SkM44 辅助 | 4 | `M44ColMajor`, `IsScaleTranslateAsM33`, `MapRect`, `DifferentialAreaScale` |
| 透视检测 | 1 | `NearlyAffine` |
| 笔画缩放 | 1 | `ComputeResScaleForStroking` |

## 公共 API 函数

### 序列化函数

#### WriteToMemory

```cpp
static size_t WriteToMemory(const SkMatrix& matrix, void* buffer)
```

**功能**: 将矩阵序列化到内存缓冲区。

**参数**:
- `matrix`: 要序列化的矩阵
- `buffer`: 目标缓冲区,如果为 `nullptr` 则仅返回所需大小

**返回值**: 写入的字节数,最大为 `kMaxFlattenSize`(44 字节)。

**格式**: 包含类型掩码和必要的矩阵元素,优化后的矩阵(如单位矩阵)占用更少空间。

#### ReadFromMemory

```cpp
static size_t ReadFromMemory(SkMatrix* matrix, const void* buffer, size_t length)
```

**功能**: 从内存缓冲区反序列化矩阵。

**参数**:
- `matrix`: 输出矩阵
- `buffer`: 源缓冲区
- `length`: 缓冲区大小

**返回值**: 读取的字节数,失败返回 0。

### 映射函数

#### GetMapPtsProc

```cpp
static MapPtsProc GetMapPtsProc(const SkMatrix& matrix)
```

**功能**: 根据矩阵类型返回最优的点映射函数指针。

**返回值**: `MapPtsProc` 函数指针,可以是:
- `Identity_pts`
- `Trans_pts`
- `Scale_pts`
- `ScaleTrans_pts`
- `Rot_pts`
- `RotTrans_pts`
- `Persp_pts`

**性能优化**: 避免在循环中重复类型检查。

### 逆变换映射

#### InverseMapRect

```cpp
[[nodiscard]] static bool InverseMapRect(const SkMatrix& mx,
                                         SkRect* dst,
                                         const SkRect& src)
```

**功能**: 将矩形通过矩阵的逆变换映射,优化的实现避免了完整的矩阵求逆。

**参数**:
- `mx`: 变换矩阵
- `dst`: 输出逆变换后的矩形
- `src`: 输入矩形

**返回值**: 成功返回 `true`,矩阵不可逆返回 `false`。

**优化路径**:
1. **缩放+平移**: 直接计算逆变换,无需求逆矩阵
2. **一般仿射**: 求逆矩阵后调用 `mapRect`

**特殊处理**:
- 负缩放时交换矩形边界保持排序
- 零缩放因子返回 `false`(不可逆)

### 带步长的点映射

#### MapPointsWithStride (原地版本)

```cpp
static void MapPointsWithStride(const SkMatrix& mx,
                                SkPoint pts[],
                                size_t stride,
                                int count)
```

**功能**: 原地变换点数组,支持自定义步长(用于交错数组)。

**参数**:
- `mx`: 变换矩阵
- `pts`: 点数组
- `stride`: 步长(字节),必须 ≥ `sizeof(SkPoint)`
- `count`: 点数量

**应用场景**: 顶点缓冲区中点坐标与其他属性(颜色、纹理坐标)交错存储。

**优化**: 根据矩阵类型选择特化路径(平移/一般仿射/透视)。

#### MapPointsWithStride (源/目标版本)

```cpp
static void MapPointsWithStride(const SkMatrix& mx,
                                SkPoint dst[], size_t dstStride,
                                const SkPoint src[], size_t srcStride,
                                int count)
```

**功能**: 将源点数组变换到目标数组,支持不同步长。

#### MapHomogeneousPointsWithStride

```cpp
static void MapHomogeneousPointsWithStride(const SkMatrix& mx,
                                           SkPoint3 dst[], size_t dstStride,
                                           const SkPoint3 src[], size_t srcStride,
                                           int count)
```

**功能**: 变换齐次坐标点(3D 点,用于透视变换)。

**齐次坐标**: `(x, y, w)`,实际 2D 坐标为 `(x/w, y/w)`。

### 矩阵比较

#### CheapEqual

```cpp
static bool CheapEqual(const SkMatrix& a, const SkMatrix& b)
```

**功能**: 快速比较两个矩阵是否相等,通过内存比较而非逐元素比较。

**实现**:
```cpp
return &a == &b || 0 == memcmp(a.fMat, b.fMat, sizeof(a.fMat));
```

**注意**: 不处理 `NaN` 的特殊比较规则。

### SkM44 辅助函数

#### M44ColMajor

```cpp
static const SkScalar* M44ColMajor(const SkM44& m)
```

**功能**: 返回 4x4 矩阵的列主序数据指针。

**用途**: 传递给 OpenGL/Vulkan API。

#### IsScaleTranslateAsM33

```cpp
static bool IsScaleTranslateAsM33(const SkM44& m)
```

**功能**: 检查 4x4 矩阵的左上角 3x3 部分是否为纯缩放+平移(忽略 Z 轴)。

**检查条件**:
```
m.rc(1,0) == 0 && m.rc(3,0) == 0 &&
m.rc(0,1) == 0 && m.rc(3,1) == 0 &&
m.rc(3,3) == 1
```

**注意**: 仅检查 2D 属性,可能有 Z 轴剪切。

#### MapRect (SkM44 版本)

```cpp
static SkRect MapRect(const SkM44& m, const SkRect& r)
```

**功能**: 通过 4x4 矩阵映射 2D 矩形,处理透视投影。

**实现**: 映射矩形四角(假设 z=0, w=1),计算投影后的包围盒,裁剪 w≤0 的点。

#### DifferentialAreaScale

```cpp
static SkScalar DifferentialAreaScale(const SkMatrix& m, const SkPoint& p)
```

**功能**: 计算点 `p` 处的微分面积缩放因子,即雅可比行列式的绝对值。

**数学背景**: `|det(J)| = |∂x'/∂x * ∂y'/∂y - ∂x'/∂y * ∂y'/∂x|`

**应用**:
- 计算变换后的像素密度
- LOD 选择
- 抗锯齿决策

**特殊情况**: 透视变换时,缩放因子与位置相关;仿射变换时为常数。

#### NearlyAffine

```cpp
static bool NearlyAffine(const SkMatrix& m,
                         const SkRect& bounds,
                         SkScalar tolerance = SK_ScalarNearlyZero)
```

**功能**: 判断矩阵在指定边界内是否可以近似为仿射变换。

**原理**: 检查边界角点的透视分量(w)是否接近 1。

**应用**: 对轻微透视效果的变换使用更快的仿射路径。

### 笔画缩放

#### ComputeResScaleForStroking

```cpp
static SkScalar ComputeResScaleForStroking(const SkMatrix& matrix)
```

**功能**: 计算用于笔画宽度调整的缩放因子。

**实现**(推测): 提取矩阵的平均缩放,类似 `sqrt(|det(M)|)`。

**应用**: 确保变换后的笔画宽度在设备空间中正确。

## 内部实现细节

### InverseMapRect 优化路径

```cpp
if (mx.isScaleTranslate()) {
    // 快速路径:直接计算逆变换
    auto inverted = skvx::float4::Load(&src.fLeft);
    inverted -= skvx::float4(tx, ty, tx, ty);
    inverted *= skvx::float4(1/sx, 1/sy, 1/sx, 1/sy);

    // 处理负缩放(交换边界)
    if (sx < 0 && sy < 0) {
        inverted = skvx::shuffle<2, 3, 0, 1>(inverted);
    }
    // ...
}
```

使用 SIMD 向量化处理四个边界值。

### MapPointsWithStride 优化

```cpp
SkMatrix::TypeMask tm = mx.getType();

if (SkMatrix::kIdentity_Mask == tm) {
    return;  // 单位矩阵,无需操作
}
if (SkMatrix::kTranslate_Mask == tm) {
    // SIMD 平移
    skvx::float2 trans(tx, ty);
    for (int i = 0; i < count; ++i) {
        (skvx::float2::Load(&pts->fX) + trans).store(&pts->fX);
        pts = (SkPoint*)((intptr_t)pts + stride);
    }
    return;
}
// 一般路径
```

针对常见变换类型提供快速路径。

### 齐次坐标映射

```cpp
// 3x3 矩阵应用到 (x, y, w)
x' = m[0]*x + m[1]*y + m[2]*w
y' = m[3]*x + m[4]*y + m[5]*w
w' = m[6]*x + m[7]*y + m[8]*w
```

输出的齐次坐标可能需要归一化。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkMatrix.h` | 3x3 矩阵类 |
| `include/core/SkM44.h` | 4x4 矩阵类 |
| `include/core/SkPoint.h` | 2D 点类型 |
| `include/core/SkRect.h` | 矩形类型 |
| `src/base/SkVx.h` | SIMD 向量运算 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `SkCanvas` | 逆变换映射,点变换 |
| `SkDevice` | 带步长的顶点变换 |
| `SkPath` | 点映射,面积缩放 |
| `SkStroke` | 笔画缩放计算 |
| `SkPicture` | 序列化矩阵 |
| `SkVertices` | 齐次坐标映射 |

## 设计模式与设计决策

### 静态工具类模式

```cpp
class SkMatrixPriv {
public:
    static size_t WriteToMemory(...);
    static bool InverseMapRect(...);
    // 所有方法为静态
private:
    SkMatrixPriv() = delete;  // 禁止实例化
};
```

优点:
- 明确表示工具函数集合
- 避免不必要的对象创建
- 清晰的命名空间

### 友元访问 vs 公共接口

`SkMatrixPriv` 通过友元访问私有成员而非增加公共接口:
- 保持 `SkMatrix` 公共 API 简洁
- 内部代码可访问优化路径
- 避免暴露实现细节

### 性能优先的多态

`GetMapPtsProc` 返回函数指针而非虚函数:
- 避免虚函数调用开销
- 类型检查一次,多次调用零成本
- 编译器可内联函数指针调用

### SIMD 优化

多个函数使用 `skvx` 向量类型:
- `InverseMapRect`: 四个边界值同时处理
- `MapPointsWithStride`: 批量平移优化

## 性能考量

### InverseMapRect 性能

- **缩放+平移路径**: ~10 条指令,约 5 周期
- **一般仿射路径**: 矩阵求逆(~50 周期) + `mapRect`(~20 周期)

对频繁调用的场景,缩放+平移优化显著。

### MapPointsWithStride 性能

- **单位矩阵**: 零成本(提前返回)
- **平移**: SIMD 加法,每点约 2 周期
- **一般仿射**: 每点约 10-15 周期
- **透视**: 每点约 20-30 周期(包含除法)

### CheapEqual 性能

```cpp
memcmp(a.fMat, b.fMat, sizeof(a.fMat))  // 36 字节
```

- 现代 CPU: ~5 周期(SIMD 比较)
- 比逐元素比较快 2-3 倍

## 使用示例

### 序列化矩阵

```cpp
SkMatrix matrix = ...;
size_t size = SkMatrixPriv::WriteToMemory(matrix, nullptr);
void* buffer = malloc(size);
SkMatrixPriv::WriteToMemory(matrix, buffer);

// 反序列化
SkMatrix restored;
SkMatrixPriv::ReadFromMemory(&restored, buffer, size);
```

### 逆变换矩形

```cpp
SkMatrix ctm = ...;
SkRect deviceRect = {0, 0, 100, 100};
SkRect localRect;
if (SkMatrixPriv::InverseMapRect(ctm, &localRect, deviceRect)) {
    // 成功获取局部坐标系中的矩形
}
```

### 带步长的点变换

```cpp
struct Vertex {
    SkPoint pos;
    SkColor color;
};
Vertex vertices[100];

// 仅变换位置,跳过颜色
SkMatrixPriv::MapPointsWithStride(
    matrix,
    &vertices[0].pos,
    sizeof(Vertex),
    100
);
```

### 计算面积缩放

```cpp
SkMatrix matrix = ...;
SkPoint point = {50, 50};
SkScalar areaScale = SkMatrixPriv::DifferentialAreaScale(matrix, point);

// 调整采样率
int mipLevel = (int)log2(areaScale);
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkMatrix.h` | 依赖 | 3x3 矩阵公共 API |
| `include/core/SkM44.h` | 依赖 | 4x4 矩阵公共 API |
| `src/core/SkMatrixInvert.h` | 协作 | 矩阵求逆算法 |
| `src/core/SkMatrixUtils.h` | 同级 | 公共工具函数 |
| `src/core/SkDraw.cpp` | 使用者 | 绘图引擎 |
| `src/core/SkCanvas.cpp` | 使用者 | Canvas 实现 |

## 注意事项

1. **内部 API**: 该头文件不包含在公共 SDK 中,仅供 Skia 内部使用
2. **ABI 稳定性**: 作为内部接口,可能在版本间变化,不保证二进制兼容
3. **步长对齐**: `MapPointsWithStride` 要求步长是 `sizeof(SkScalar)` 的倍数
4. **浮点精度**: `InverseMapRect` 的缩放检查使用精确比较,可能受浮点误差影响
5. **齐次坐标归一化**: `MapHomogeneousPointsWithStride` 不自动归一化,调用者需处理
6. **NaN 处理**: `CheapEqual` 不遵循 IEEE 754 NaN 比较规则(`NaN != NaN`)
7. **透视裁剪**: `MapRect(SkM44)` 裁剪 w≤0 的点,可能导致结果为空矩形
8. **性能假设**: 许多优化路径假设编译器内联和 SIMD 优化,关闭优化时性能下降

该模块是 Skia 内部实现的重要组成部分,展示了如何在保持公共 API 简洁的同时提供高性能的内部接口。其设计思想对构建大型 C++ 库具有参考价值。
