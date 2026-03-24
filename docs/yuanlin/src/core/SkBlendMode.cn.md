# SkBlendMode

> 源文件: include/core/SkBlendMode.h, src/core/SkBlendMode.cpp

## 概述

`SkBlendMode` 定义了 Skia 中的混合模式枚举和相关辅助函数。混合模式描述如何将源色(source)和目标色(destination)组合生成最终颜色,包含 28 种标准模式:15 种 Porter-Duff 系数模式和 13 种高级混合模式。本模块提供混合模式到系数转换、光栅管线集成、快速路径优化等核心功能,是 Skia 颜色合成系统的基础。

## 架构位置

```
include/core/
  └── SkBlendMode.h          # 混合模式枚举定义

src/core/
  ├── SkBlendMode.cpp        # 混合模式实现
  ├── SkBlendModePriv.h      # 私有辅助函数
  └── SkRasterPipeline.h     # 光栅管线集成
```

本模块位于 Skia 核心层,作为颜色合成的数学定义,被绘制、着色、滤镜等高层模块广泛使用。

## 主要类与结构体

### SkBlendMode 枚举

```cpp
enum class SkBlendMode {
    // Porter-Duff 基础模式
    kClear,      // r = 0
    kSrc,        // r = s
    kDst,        // r = d
    kSrcOver,    // r = s + (1-sa)*d
    kDstOver,    // r = d + (1-da)*s
    kSrcIn,      // r = s * da
    kDstIn,      // r = d * sa
    kSrcOut,     // r = s * (1-da)
    kDstOut,     // r = d * (1-sa)
    kSrcATop,    // r = s*da + d*(1-sa)
    kDstATop,    // r = d*sa + s*(1-da)
    kXor,        // r = s*(1-da) + d*(1-sa)
    kPlus,       // r = min(s + d, 1)
    kModulate,   // r = s*d
    kScreen,     // r = s + d - s*d

    // 分离混合模式
    kOverlay,    // 叠加
    kDarken,     // 变暗
    kLighten,    // 变亮
    kColorDodge, // 颜色减淡
    kColorBurn,  // 颜色加深
    kHardLight,  // 强光
    kSoftLight,  // 柔光
    kDifference, // 差值
    kExclusion,  // 排除
    kMultiply,   // 正片叠底

    // 非分离混合模式
    kHue,        // 色相
    kSaturation, // 饱和度
    kColor,      // 颜色
    kLuminosity, // 明度

    kLastCoeffMode = kScreen,      // 最后一个系数模式
    kLastSeparableMode = kMultiply, // 最后一个分离模式
    kLastMode = kLuminosity,       // 最后一个有效模式
};
```

### SkBlendModeCoeff 系数枚举

```cpp
enum class SkBlendModeCoeff {
    kZero,  // 0
    kOne,   // 1
    kSC,    // 源颜色
    kISC,   // 反源颜色 (1 - sc)
    kDC,    // 目标颜色
    kIDC,   // 反目标颜色 (1 - dc)
    kSA,    // 源透明度
    kISA,   // 反源透明度 (1 - sa)
    kDA,    // 目标透明度
    kIDA,   // 反目标透明度 (1 - da)
    kCoeffCount
};
```

## 公共 API 函数

### 系数查询

```cpp
SK_API bool SkBlendMode_AsCoeff(SkBlendMode mode,
                                 SkBlendModeCoeff* src,
                                 SkBlendModeCoeff* dst);
```

**功能:** 查询混合模式是否为系数模式,返回源/目标系数。

**示例:**
```cpp
SkBlendModeCoeff src, dst;
if (SkBlendMode_AsCoeff(SkBlendMode::kSrcOver, &src, &dst)) {
    // src = kOne, dst = kISA
    // 公式: result = 1*s + (1-sa)*d
}
```

### 名称转换

```cpp
SK_API const char* SkBlendMode_Name(SkBlendMode blendMode);
```

**功能:** 返回混合模式的字符串名称,用于调试和日志。

### 覆盖率预缩放判断

```cpp
bool SkBlendMode_ShouldPreScaleCoverage(SkBlendMode mode, bool rgb_coverage);
bool SkBlendMode_SupportsCoverageAsAlpha(SkBlendMode mode);
```

**功能:** 判断混合模式是否支持用覆盖率预乘源色。

**规则:**
- 允许预缩放: `kDst`, `kDstOver`, `kPlus` (无 sa 项)
- RGB 覆盖率时禁止: `kDstOut`, `kSrcATop`, `kSrcOver`, `kXor` (有 sa 项)

### 光栅管线集成

```cpp
void SkBlendMode_AppendStages(SkBlendMode mode, SkRasterPipeline* p);
```

**功能:** 将混合模式添加为光栅管线阶段。

**示例:**
```cpp
SkRasterPipeline_<256> p;
p.append(SkRasterPipelineOp::load_f32, &srcCtx);
SkBlendMode_AppendStages(SkBlendMode::kMultiply, &p);
p.append(SkRasterPipelineOp::store_f32, &dstCtx);
p.run(0, 0, 1, 1);
```

### 单像素混合

```cpp
SkPMColor4f SkBlendMode_Apply(SkBlendMode mode,
                               const SkPMColor4f& src,
                               const SkPMColor4f& dst);
```

**功能:** 对单个像素应用混合模式,返回结果色。

### 快速路径检查

```cpp
SkBlendFastPath CheckFastPath(const SkPaint& paint, bool dstIsOpaque);
```

**功能:** 根据混合模式和绘制属性选择优化路径。

**返回值:**
- `kSrcOver`: 标准 SrcOver 路径
- `kSkipDrawing`: 跳过绘制(如 `kDst` 模式)
- `kNormal`: 通用路径

## 内部实现细节

### 系数表定义

```cpp
bool SkBlendMode_AsCoeff(SkBlendMode mode, SkBlendModeCoeff* src, SkBlendModeCoeff* dst) {
    static constexpr CoeffRec kCoeffs[] = {
        // src coeff           dst coeff             blend mode
        { kZero,               kZero              }, // Clear
        { kOne,                kZero              }, // Src
        { kZero,               kOne               }, // Dst
        { kOne,                kISA               }, // SrcOver
        { kIDA,                kOne               }, // DstOver
        { kDA,                 kZero              }, // SrcIn
        { kZero,               kSA                }, // DstIn
        { kIDA,                kZero              }, // SrcOut
        { kZero,               kISA               }, // DstOut
        { kDA,                 kISA               }, // SrcATop
        { kIDA,                kSA                }, // DstATop
        { kIDA,                kISA               }, // Xor
        { kOne,                kOne               }, // Plus
        { kZero,               kSC                }, // Modulate
        { kOne,                kISC               }, // Screen
    };

    if (mode > SkBlendMode::kScreen) return false;
    *src = kCoeffs[(int)mode].fSrc;
    *dst = kCoeffs[(int)mode].fDst;
    return true;
}
```

### 光栅管线操作映射

```cpp
void SkBlendMode_AppendStages(SkBlendMode mode, SkRasterPipeline* p) {
    switch (mode) {
        case SkBlendMode::kClear:      p->append(SkRasterPipelineOp::clear); return;
        case SkBlendMode::kSrc:        return;  // 空操作
        case SkBlendMode::kDst:        p->append(SkRasterPipelineOp::move_dst_src); return;
        case SkBlendMode::kSrcOver:    p->append(SkRasterPipelineOp::srcover); return;
        case SkBlendMode::kMultiply:   p->append(SkRasterPipelineOp::multiply); return;
        case SkBlendMode::kHue:        p->append(SkRasterPipelineOp::hue); return;
        // ... 其他模式映射
    }
}
```

### 快速路径优化

```cpp
SkBlendFastPath CheckFastPath(const SkPaint& paint, bool dstIsOpaque) {
    auto bm = paint.asBlendMode();
    if (!bm) return SkBlendFastPath::kNormal;

    switch (*bm) {
        case SkBlendMode::kSrcOver:
            return SkBlendFastPath::kSrcOver;

        case SkBlendMode::kSrc:
            if (just_solid_color(paint)) {
                return SkBlendFastPath::kSrcOver;  // 退化为 SrcOver
            }
            return SkBlendFastPath::kNormal;

        case SkBlendMode::kDst:
            return SkBlendFastPath::kSkipDrawing;

        case SkBlendMode::kDstOver:
            if (dstIsOpaque) {
                return SkBlendFastPath::kSkipDrawing;
            }
            return SkBlendFastPath::kNormal;

        case SkBlendMode::kSrcIn:
            if (dstIsOpaque && just_solid_color(paint)) {
                return SkBlendFastPath::kSrcOver;
            }
            return SkBlendFastPath::kNormal;

        default:
            return SkBlendFastPath::kNormal;
    }
}
```

### SrcOver 特化实现

```cpp
SkPMColor4f SkBlendMode_Apply(SkBlendMode mode,
                               const SkPMColor4f& src,
                               const SkPMColor4f& dst) {
    switch (mode) {
        case SkBlendMode::kClear:
            return SK_PMColor4fTRANSPARENT;
        case SkBlendMode::kSrc:
            return src;
        case SkBlendMode::kDst:
            return dst;
        case SkBlendMode::kSrcOver: {
            SkPMColor4f r;
            (skvx::float4::Load(src.vec()) +
             skvx::float4::Load(dst.vec()) * (1 - src.fA)).store(&r);
            return r;
        }
        default:
            // 回退到通用管线
            break;
    }
    // ... 完整管线实现
}
```

### 覆盖率预缩放逻辑

```cpp
bool SkBlendMode_ShouldPreScaleCoverage(SkBlendMode mode, bool rgb_coverage) {
    // 原则:
    // 1. 从不对涉及 sa 项的模式使用 RGB 覆盖率预缩放
    // 2. 总是对 Plus 预缩放

    switch (mode) {
        case SkBlendMode::kDst:        // d (无 sa)
        case SkBlendMode::kDstOver:    // d + s*inv(da) (无 sa)
        case SkBlendMode::kPlus:       // clamp(s+d) (无 sa)
            return true;

        case SkBlendMode::kDstOut:     // d * inv(sa) (有 sa)
        case SkBlendMode::kSrcATop:    // s*da + d*inv(sa) (有 sa)
        case SkBlendMode::kSrcOver:    // s + d*inv(sa) (有 sa)
        case SkBlendMode::kXor:        // s*inv(da) + d*inv(sa) (有 sa)
            return !rgb_coverage;

        default:
            return false;
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRasterPipeline` | 光栅化管线集成 |
| `SkPaint` | 绘制属性 |
| `skvx` | SIMD 向量运算 |
| `SkColorData` | 颜色数据处理 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkPaint` | 设置绘制混合模式 |
| `SkBlender` | 混合器实现基础 |
| `SkImageFilter` | 图像滤镜混合 |
| `SkShader` | 着色器混合 |
| `SkXfermode` (已废弃) | 传统传输模式 |

## 设计模式与设计决策

### 1. 策略枚举模式

使用枚举而非多态类层次,简化接口和序列化。

### 2. 查表优化

系数转换、名称查询、管线映射均使用编译期常量表,零运行时开销。

### 3. 快速路径识别

通过静态分析绘制状态,选择最优实现路径。

### 4. 分层抽象

- **枚举层**: `SkBlendMode` 定义数学公式
- **系数层**: `SkBlendModeCoeff` 描述线性组合
- **管线层**: `SkRasterPipelineOp` 实现像素处理

### 5. 零成本抽象

```cpp
case SkBlendMode::kSrc: return;  // 编译为空操作
```

无效操作在编译期消除。

## 性能考量

### 内联特化

```cpp
case SkBlendMode::kSrcOver:  // 最常用模式
    SkPMColor4f r;
    (skvx::float4::Load(src.vec()) +
     skvx::float4::Load(dst.vec()) * (1 - src.fA)).store(&r);
    return r;
```

避免通用管线开销。

### SIMD 加速

使用 `skvx` 向量化库,4 通道并行计算:
```cpp
skvx::float4 s = skvx::float4::Load(src.vec());
skvx::float4 d = skvx::float4::Load(dst.vec());
skvx::float4 r = s + d * (1 - s[3]);  // SrcOver
```

### 光栅管线批处理

```cpp
p.append(SkRasterPipelineOp::srcover);
p.run(0, 0, width, height);  // 批量处理所有像素
```

一次设置,多次复用。

### 分支消除

编译期常量折叠:
```cpp
if (mode == SkBlendMode::kSrc) {
    // 编译器直接消除分支
}
```

### 快速路径跳过

```cpp
if (mode == SkBlendMode::kDst) {
    return SkBlendFastPath::kSkipDrawing;  // 完全跳过绘制
}
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkBlendModePriv.h` | 混合模式私有函数 |
| `src/core/SkRasterPipeline.h` | 光栅化管线 |
| `src/core/SkRasterPipelineOpContexts.h` | 管线操作上下文 |
| `src/core/SkBlendModeBlender.h` | 混合模式混合器 |
| `include/core/SkPaint.h` | 绘制属性 |
| `include/core/SkBlender.h` | 混合器接口 |
| `src/base/SkVx.h` | SIMD 向量库 |
