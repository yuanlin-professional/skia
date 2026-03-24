# SkMatrixColorFilter

> 源文件
> - `src/effects/colorfilters/SkMatrixColorFilter.h`
> - `src/effects/colorfilters/SkMatrixColorFilter.cpp`

## 概述

`SkMatrixColorFilter` 是 Skia 中实现基于矩阵变换的颜色过滤器。它通过 4x5 矩阵对颜色进行线性变换和平移，支持在 RGBA 和 HSLA 两种色彩空间中操作。该过滤器可以实现多种颜色效果，如色调调整、饱和度控制、亮度变化、对比度调整等。

矩阵变换的形式为：
```
[R']   [m00 m01 m02 m03 m04]   [R]
[G'] = [m10 m11 m12 m13 m14] × [G]
[B']   [m20 m21 m22 m23 m24]   [B]
[A']   [m30 m31 m32 m33 m34]   [A]
                                [1]
```

这种矩阵变换方式是图形学中最基本和最灵活的颜色处理方法之一。

## 架构位置

```
skia/
├── include/
│   ├── core/
│   │   └── SkColorFilter.h           # 颜色过滤器公共接口
│   └── effects/
│       └── SkColorMatrix.h            # 颜色矩阵辅助类
├── src/
│   ├── core/
│   │   ├── SkRasterPipeline.h        # 光栅化管线
│   │   └── SkRasterPipelineOpList.h  # 管线操作列表
│   └── effects/
│       └── colorfilters/
│           ├── SkColorFilterBase.h        # 颜色过滤器基类
│           ├── SkMatrixColorFilter.h      # 本模块头文件
│           └── SkMatrixColorFilter.cpp    # 本模块实现
```

`SkMatrixColorFilter` 是最常用的颜色过滤器之一，它位于 Skia 效果系统的核心位置，被许多高级效果和工具使用。

## 主要类与结构体

### SkMatrixColorFilter

矩阵颜色过滤器类。

```cpp
class SkMatrixColorFilter final : public SkColorFilterBase {
public:
    // 色彩空间域枚举
    enum class Domain : uint8_t {
        kRGBA,  // RGB 色彩空间
        kHSLA   // HSL 色彩空间
    };

    // 钳位模式（来自 SkColorFilters）
    using Clamp = SkColorFilters::Clamp;

    explicit SkMatrixColorFilter(const float array[20], Domain, Clamp);

    bool appendStages(const SkStageRec& rec, bool shaderIsOpaque) const override;
    bool onIsAlphaUnchanged() const override { return fAlphaIsUnchanged; }

    // 属性访问器
    Domain domain() const { return fDomain; }
    SkColorFilters::Clamp clamp() const { return fClamp; }
    const float* matrix() const { return fMatrix; }

private:
    float fMatrix[20];           // 4x5 变换矩阵
    bool fAlphaIsUnchanged;      // Alpha 通道是否保持不变
    Domain fDomain;              // 色彩空间域
    Clamp fClamp;               // 是否钳位输出值
};
```

**成员说明**：
- `fMatrix[20]` - 存储 4x5 矩阵的 20 个元素
- `fAlphaIsUnchanged` - 优化标志，指示 alpha 是否不变
- `fDomain` - 指定在 RGBA 或 HSLA 空间中操作
- `fClamp` - 控制输出值是否被钳位到 [0, 1] 范围

## 公共 API 函数

### SkColorFilters::Matrix (RGBA)

```cpp
sk_sp<SkColorFilter> SkColorFilters::Matrix(const float array[20], Clamp clamp);
sk_sp<SkColorFilter> SkColorFilters::Matrix(const SkColorMatrix& cm, Clamp clamp);
```

创建在 RGBA 色彩空间中操作的矩阵颜色过滤器。

**参数**：
- `array` / `cm` - 4x5 矩阵（20 个浮点数）
- `clamp` - 是否将输出钳位到 [0, 1] 范围（`Clamp::kYes` 或 `Clamp::kNo`）

**返回值**：颜色过滤器智能指针，如果矩阵包含无效值则返回 nullptr

**使用示例**：
```cpp
// 创建灰度过滤器
float grayMatrix[20] = {
    0.2126f, 0.7152f, 0.0722f, 0, 0,
    0.2126f, 0.7152f, 0.0722f, 0, 0,
    0.2126f, 0.7152f, 0.0722f, 0, 0,
    0, 0, 0, 1, 0
};
auto filter = SkColorFilters::Matrix(grayMatrix);
```

### SkColorFilters::HSLAMatrix

```cpp
sk_sp<SkColorFilter> SkColorFilters::HSLAMatrix(const float array[20]);
sk_sp<SkColorFilter> SkColorFilters::HSLAMatrix(const SkColorMatrix& cm);
```

创建在 HSLA 色彩空间中操作的矩阵颜色过滤器。

**参数**：
- `array` / `cm` - 4x5 矩阵（20 个浮点数）

**注意**：HSLA 模式总是使用 `Clamp::kYes`，忽略 clamp 参数

**特点**：
- 更适合调整色调、饱和度和亮度
- 能够实现自然的颜色调整效果
- 自动处理 RGB 和 HSL 之间的转换

## 内部实现细节

### Alpha 不变性检测

```cpp
static bool is_alpha_unchanged(const float matrix[20]) {
    const float* srcA = matrix + 15;  // Alpha 行起始位置

    return SkScalarNearlyZero(srcA[0]) &&      // 不依赖 R
           SkScalarNearlyZero(srcA[1]) &&      // 不依赖 G
           SkScalarNearlyZero(srcA[2]) &&      // 不依赖 B
           SkScalarNearlyEqual(srcA[3], 1) &&  // A' = A
           SkScalarNearlyZero(srcA[4]);        // 无平移
}
```

**用途**：
- 如果 alpha 不变且输入已经是不透明的，可以跳过预乘和反预乘步骤
- 这是一个重要的性能优化

**判断条件**：检查矩阵的第四行（alpha 行）是否为 `[0, 0, 0, 1, 0]`

### 光栅管线构建

`appendStages` 方法构建完整的颜色转换管线：

```cpp
bool SkMatrixColorFilter::appendStages(const SkStageRec& rec, bool shaderIsOpaque) const {
    const bool willStayOpaque = shaderIsOpaque && fAlphaIsUnchanged;
    const bool hsla = fDomain == Domain::kHSLA;
    const bool clamp = fClamp == Clamp::kYes;

    SkRasterPipeline* p = rec.fPipeline;

    // 1. 如果输入不是不透明的，需要反预乘
    if (!shaderIsOpaque) {
        p->append(SkRasterPipelineOp::unpremul);
    }

    // 2. 如果是 HSLA 模式，转换到 HSL 空间
    if (hsla) {
        p->append(SkRasterPipelineOp::rgb_to_hsl);
    }

    // 3. 应用矩阵变换
    p->append(SkRasterPipelineOp::matrix_4x5, fMatrix);

    // 4. 如果是 HSLA 模式，转换回 RGB 空间
    if (hsla) {
        p->append(SkRasterPipelineOp::hsl_to_rgb);
    }

    // 5. 钳位输出值
    if (clamp) {
        p->append(SkRasterPipelineOp::clamp_01);     // 钳位所有通道
    } else {
        p->append(SkRasterPipelineOp::clamp_a_01);   // 仅钳位 alpha
    }

    // 6. 如果需要，重新预乘
    if (!willStayOpaque) {
        p->append(SkRasterPipelineOp::premul);
    }

    return true;
}
```

**关键设计点**：

1. **预乘处理**：Skia 内部使用预乘 alpha，矩阵运算需要在非预乘空间进行
2. **色彩空间转换**：HSLA 模式需要在 RGB 和 HSL 之间转换
3. **钳位策略**：Alpha 总是被钳位，以保证有效的颜色值
4. **优化路径**：当着色器不透明且 alpha 不变时，跳过预乘步骤

### 序列化与反序列化

```cpp
void SkMatrixColorFilter::flatten(SkWriteBuffer& buffer) const {
    buffer.writeScalarArray(fMatrix);      // 写入矩阵
    buffer.writeBool(fDomain == Domain::kRGBA);  // 写入域标志
    buffer.writeBool(fClamp == Clamp::kYes);     // 写入钳位标志
}

sk_sp<SkFlattenable> SkMatrixColorFilter::CreateProc(SkReadBuffer& buffer) {
    float matrix[20];
    if (!buffer.readScalarArray(matrix)) {
        return nullptr;
    }

    auto is_rgba = buffer.readBool();

    // 版本兼容性处理
    Clamp clamp = buffer.isVersionLT(SkPicturePriv::kUnclampedMatrixColorFilter)
                          ? Clamp::kYes
                          : (buffer.readBool() ? Clamp::kYes : Clamp::kNo);

    // 对于 HSL 域过滤器，忽略 clamp 选项
    return is_rgba ? SkColorFilters::Matrix(matrix, clamp)
                   : SkColorFilters::HSLAMatrix(matrix);
}
```

**版本兼容性**：
- 旧版本的 Skia 总是钳位输出
- 新版本支持可选的非钳位模式
- 反序列化时根据版本号选择正确的默认行为

### 向后兼容性

```cpp
void SkRegisterMatrixColorFilterFlattenable() {
    SK_REGISTER_FLATTENABLE(SkMatrixColorFilter);
    // 注册旧名称以保持兼容性
    SkFlattenable::Register("SkColorFilter_Matrix",
                           SkMatrixColorFilter::CreateProc);
}
```

支持读取使用旧类名序列化的对象。

## 依赖关系

### 内部依赖

| 组件 | 用途 |
|-----|------|
| `SkColorFilterBase` | 颜色过滤器基类 |
| `SkRasterPipeline` | 构建图形管线 |
| `SkRasterPipelineOp` | 管线操作定义 |
| `SkEffectPriv` | 效果私有工具 |
| `SkReadBuffer` / `SkWriteBuffer` | 序列化支持 |

### 外部依赖

| 组件 | 用途 |
|-----|------|
| `SkColorMatrix` | 颜色矩阵辅助类 |
| `SkColorFilter` | 公共接口 |

## 设计模式与设计决策

### 1. 策略模式（Strategy Pattern）

通过 `Domain` 枚举支持两种处理策略：
- **RGBA 策略**：直接在 RGB 空间进行矩阵变换
- **HSLA 策略**：在 HSL 空间进行矩阵变换

这两种策略通过相同的接口使用，但内部行为不同。

### 2. 不可变对象设计

`SkMatrixColorFilter` 一旦创建就不可修改：
- 所有数据成员都是私有的
- 没有提供修改方法
- 通过工厂函数创建新实例

**优势**：
- 线程安全
- 可以安全地共享和缓存
- 简化内存管理

### 3. 验证模式（Validation Pattern）

在创建时验证输入：
```cpp
static sk_sp<SkColorFilter> MakeMatrix(const float array[20],
                                       SkMatrixColorFilter::Domain domain,
                                       SkColorFilters::Clamp clamp) {
    if (!SkIsFinite(array, 20)) {
        return nullptr;  // 拒绝无效输入
    }
    return sk_make_sp<SkMatrixColorFilter>(array, domain, clamp);
}
```

这避免了创建无效的对象。

### 4. 延迟求值与管线化

不直接计算颜色，而是构建计算管线：
- 允许与其他操作组合优化
- 支持向量化和并行执行
- 可以在 GPU 上高效执行

## 性能考量

### 1. Alpha 不变性优化

```cpp
const bool willStayOpaque = shaderIsOpaque && fAlphaIsUnchanged;
if (!willStayOpaque) {
    p->append(SkRasterPipelineOp::premul);  // 仅在必要时预乘
}
```

**节省的开销**：
- 跳过 `unpremul` 操作
- 跳过 `premul` 操作
- 对于不透明图像处理，这能显著提升性能

### 2. 矩阵操作向量化

`matrix_4x5` 管线操作支持 SIMD 优化：
- 可以一次处理多个像素
- 利用现代 CPU 的向量指令（SSE、AVX、NEON）
- 典型加速比为 4-8 倍

### 3. 内存布局

```cpp
float fMatrix[20];  // 连续内存布局
```

**优势**：
- 缓存友好
- 易于复制（`memcpy`）
- 直接传递给管线操作

### 4. 钳位策略选择

```cpp
if (clamp) {
    p->append(SkRasterPipelineOp::clamp_01);     // 钳位所有通道
} else {
    p->append(SkRasterPipelineOp::clamp_a_01);   // 仅钳位 alpha
}
```

- `clamp_01` 适用于需要保证输出范围的场景
- `clamp_a_01` 允许 RGB 超出范围，适用于 HDR 渲染
- Alpha 总是被钳位以保证有效性

### 5. HSLA 转换开销

HSLA 模式需要额外的色彩空间转换：
```cpp
p->append(SkRasterPipelineOp::rgb_to_hsl);  // 转换
p->append(SkRasterPipelineOp::matrix_4x5, fMatrix);
p->append(SkRasterPipelineOp::hsl_to_rgb);  // 转换回来
```

**权衡**：
- 增加了计算成本（约 2-3 倍）
- 但提供了更直观的色彩控制
- 适用于需要调整色调和饱和度的场景

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/effects/SkColorMatrix.h` | 颜色矩阵辅助类，提供预定义效果 |
| `src/effects/colorfilters/SkColorFilterBase.h` | 颜色过滤器基类 |
| `src/core/SkRasterPipeline.h` | 光栅化管线实现 |
| `src/core/SkRasterPipelineOpList.h` | 管线操作定义 |
| `src/effects/colorfilters/SkComposeColorFilter.cpp` | 组合颜色过滤器，可组合多个矩阵 |
| `include/core/SkColorFilter.h` | 颜色过滤器公共接口 |
| `src/core/SkReadBuffer.h` | 反序列化支持 |
| `src/core/SkWriteBuffer.h` | 序列化支持 |
| `src/core/SkEffectPriv.h` | 效果私有工具 |
