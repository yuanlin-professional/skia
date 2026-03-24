# SkBlenders

> 源文件: include/effects/SkBlenders.h, src/effects/SkBlenders.cpp

## 概述

SkBlenders 是 Skia 中用于创建高级混合效果的工厂类。该模块提供了 Arithmetic 混合模式,通过四个系数（k1、k2、k3、k4）实现灵活的像素混合公式: `k1*src*dst + k2*src + k3*dst + k4`。它是对标准 SkBlendMode 枚举的补充,支持更复杂的混合效果。实现上使用 SkRuntimeEffect 着色器,并针对常见情况优化为标准混合模式以提高性能。

## 架构位置

SkBlenders 位于 Skia 的效果层混合子系统:

```
include/effects/
  └── SkBlenders.h              # 工厂类接口（本模块）
src/effects/
  └── SkBlenders.cpp            # 实现（本模块）
include/core/
  ├── SkBlender.h               # 混合器基类
  └── SkBlendMode.h             # 标准混合模式
src/core/
  └── SkKnownRuntimeEffects.h  # 预定义运行时效果
```

该模块为客户端提供高级混合能力,超越标准 Porter-Duff 混合模式。

## 主要类与结构体

| 类名 | 继承关系 | 关键成员变量 | 说明 |
|------|---------|------------|------|
| `SkBlenders` | 无 | 无（纯静态类） | 提供静态工厂方法 |

## 公共 API 函数

### 工厂方法

```cpp
class SK_API SkBlenders {
public:
    /**
     * 创建算术混合器: k1*src*dst + k2*src + k3*dst + k4
     * @param k1, k2, k3, k4 四个系数
     * @param enforcePremul 是否强制预乘 alpha（钳制 RGB 到 alpha）
     */
    static sk_sp<SkBlender> Arithmetic(float k1, float k2, float k3,
                                       float k4, bool enforcePremul);

private:
    SkBlenders() = delete;  // 禁止实例化
};
```

### 参数说明

**Arithmetic**
- `k1`: src 和 dst 的乘积系数
- `k2`: src 的系数
- `k3`: dst 的系数
- `k4`: 常量偏移
- `enforcePremul`:
  - `true`: 输出 RGB 钳制到输出 alpha（保证预乘格式）
  - `false`: 不强制钳制
- 返回: `sk_sp<SkBlender>` 智能指针,失败返回 nullptr

## 内部实现细节

### 混合公式

**数学表达式**:
```
output.rgb = k1 * src.rgb * dst.rgb + k2 * src.rgb + k3 * dst.rgb + k4
output.a   = k1 * src.a * dst.a + k2 * src.a + k3 * dst.a + k4
```

**预乘 alpha 强制** (enforcePremul = true):
```
output.rgb = clamp(output.rgb, 0, output.a)
```

### 常见模式优化

**Arithmetic 实现**:
```cpp
sk_sp<SkBlender> SkBlenders::Arithmetic(float k1, float k2, float k3,
                                        float k4, bool enforcePremul) {
    // 参数验证
    if (!SkIsFinite(k1, k2, k3, k4)) {
        return nullptr;
    }

    // 检测是否近似标准混合模式
    const struct {
        float       k1, k2, k3, k4;
        SkBlendMode mode;
    } table[] = {
        { 0, 1, 0, 0, SkBlendMode::kSrc   },  // output = src
        { 0, 0, 1, 0, SkBlendMode::kDst   },  // output = dst
        { 0, 0, 0, 0, SkBlendMode::kClear },  // output = 0
    };

    for (const auto& t : table) {
        if (SkScalarNearlyEqual(k1, t.k1) &&
            SkScalarNearlyEqual(k2, t.k2) &&
            SkScalarNearlyEqual(k3, t.k3) &&
            SkScalarNearlyEqual(k4, t.k4)) {
            return SkBlender::Mode(t.mode);  // 使用快速路径
        }
    }

    // 通用路径: 使用运行时效果着色器
    const SkRuntimeEffect* arithmeticEffect =
        GetKnownRuntimeEffect(StableKey::kArithmetic);

    const float array[] = {
        k1, k2, k3, k4,
        enforcePremul ? 0.0f : 1.0f,  // uniform 参数
    };

    return arithmeticEffect->makeBlender(
        SkData::MakeWithCopy(array, sizeof(array))
    );
}
```

### 运行时效果着色器

**kArithmetic 着色器伪代码**:
```glsl
uniform float4 k_and_flag;  // {k1, k2, k3, k4, enforcePremul}

half4 main(half4 src, half4 dst) {
    half4 result;
    result.rgba = k_and_flag.x * src.rgba * dst.rgba +
                  k_and_flag.y * src.rgba +
                  k_and_flag.z * dst.rgba +
                  k_and_flag.w;

    if (k_and_flag[4] < 0.5) {  // enforcePremul == true
        result.rgb = clamp(result.rgb, 0, result.a);
    }

    return result;
}
```

### 优化决策逻辑

**何时使用标准模式**:
1. `k1=0, k2=1, k3=0, k4=0` → `kSrc` (source-over)
2. `k1=0, k2=0, k3=1, k4=0` → `kDst` (destination)
3. `k1=0, k2=0, k3=0, k4=0` → `kClear` (clear)

**优势**:
- 避免自定义着色器编译
- GPU 硬件原生支持
- 更好的驱动优化

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkBlender.h` | 混合器基类 |
| `include/core/SkBlendMode.h` | 标准混合模式 |
| `include/effects/SkRuntimeEffect.h` | 运行时着色器 |
| `src/core/SkKnownRuntimeEffects.h` | 预编译效果 |
| `include/core/SkData.h` | uniform 数据传递 |
| `include/private/base/SkFloatingPoint.h` | 浮点数工具 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| 客户端绘图代码 | 创建高级混合效果 |
| `SkPaint` | 设置混合器 |
| 图像滤镜 | 组合混合操作 |

## 设计模式与设计决策

### 工厂方法模式

**决策**: 通过静态方法隐藏内部实现

```cpp
static sk_sp<SkBlender> Arithmetic(...);  // 工厂方法
```

**优点**:
- 封装实现细节（运行时效果 vs 标准模式）
- 统一接口返回基类指针
- 支持内部优化决策

### 策略模式

**两种实现策略**:
1. **标准模式**: 使用 `SkBlender::Mode(SkBlendMode)`
2. **自定义着色器**: 使用 `SkRuntimeEffect::makeBlender`

选择标准: 通过系数匹配自动选择最优策略

### 预乘 Alpha 处理

**决策**: 可选的 alpha 钳制

**理由**:
- 保证输出格式一致性（预乘 vs 非预乘）
- 防止无效颜色值（RGB > alpha）
- 兼容不同的像素格式要求

**实现**:
```cpp
enforcePremul ? 0.0f : 1.0f  // 传递给着色器
```

着色器内条件判断开销低（GPU 分支预测）

## 性能考量

### 快速路径优化

**标准模式检测**:
```cpp
if (SkScalarNearlyEqual(k1, 0) && SkScalarNearlyEqual(k2, 1) && ...) {
    return SkBlender::Mode(SkBlendMode::kSrc);  // 硬件加速
}
```

**性能提升**:
- 避免着色器编译（~10-100ms）
- GPU 固定功能管线（更快）
- 减少 uniform 传递

### 运行时效果缓存

**SkKnownRuntimeEffects**:
- 预编译常用着色器
- 全局单例模式
- 减少重复编译开销

### 参数验证

```cpp
if (!SkIsFinite(k1, k2, k3, k4)) {
    return nullptr;  // 快速失败
}
```

防止 NaN/Inf 传播到 GPU

### 内存布局

**Uniform 数组**:
```cpp
const float array[] = {
    k1, k2, k3, k4,
    enforcePremul ? 0.0f : 1.0f,
};
```

紧凑布局（20 字节）,易于传递给 GPU

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkBlender.h` | 依赖 | 混合器基类 |
| `include/core/SkBlendMode.h` | 依赖 | 标准模式枚举 |
| `include/effects/SkRuntimeEffect.h` | 依赖 | 自定义着色器 |
| `src/core/SkKnownRuntimeEffects.h` | 依赖 | 预编译效果 |
| `src/gpu/ganesh/GrBlendInfo.h` | 相关 | GPU 混合配置 |
| `include/core/SkPaint.h` | 使用者 | 应用混合器 |
