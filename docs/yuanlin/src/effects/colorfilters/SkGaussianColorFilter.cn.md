# SkGaussianColorFilter

> 源文件
> - `src/effects/colorfilters/SkGaussianColorFilter.h`
> - `src/effects/colorfilters/SkGaussianColorFilter.cpp`

## 概述

`SkGaussianColorFilter` 是 Skia 中一个特殊用途的颜色过滤器，它将输入颜色的 alpha 通道重新映射为高斯斜坡（Gaussian ramp），然后输出使用重新映射的 alpha 的预乘白色。这个过滤器主要用于创建柔和的高斯模糊效果边缘，特别是在文本渲染和抗锯齿场景中。

变换效果：
```
输入：任意颜色 (R, G, B, A)
输出：预乘白色 (A', A', A', A')
其中 A' = gaussian(A)
```

这种特殊的变换使得原本的 alpha 梯度变得更加平滑，产生类似高斯分布的柔和过渡效果。

## 架构位置

```
skia/
├── include/
│   └── core/
│       └── SkColorFilter.h           # 颜色过滤器公共接口
├── src/
│   ├── core/
│   │   ├── SkColorFilterPriv.h       # 颜色过滤器私有 API
│   │   ├── SkRasterPipeline.h        # 光栅化管线
│   │   └── SkRasterPipelineOpList.h  # 管线操作列表
│   └── effects/
│       └── colorfilters/
│           ├── SkColorFilterBase.h        # 颜色过滤器基类
│           ├── SkGaussianColorFilter.h    # 本模块头文件
│           └── SkGaussianColorFilter.cpp  # 本模块实现
```

`SkGaussianColorFilter` 是 Skia 内部使用的专用过滤器，不在公共 API 中暴露，主要通过 `SkColorFilterPriv` 访问。

## 主要类与结构体

### SkGaussianColorFilter

高斯颜色过滤器类。

```cpp
/**
 * 将输入颜色的 alpha 重新映射为高斯斜坡，然后使用重新映射的 alpha 输出预乘白色。
 */
class SkGaussianColorFilter final : public SkColorFilterBase {
public:
    SkGaussianColorFilter();

    bool appendStages(const SkStageRec& rec, bool shaderIsOpaque) const override;

    SkColorFilterBase::Type type() const override {
        return SkColorFilterBase::Type::kGaussian;
    }

protected:
    void flatten(SkWriteBuffer&) const override {}  // 无状态，空实现

private:
    SK_FLATTENABLE_HOOKS(SkGaussianColorFilter)
};
```

**特点**：
- 完全无状态的过滤器
- 固定的变换逻辑，无可配置参数
- 序列化为空（因为没有数据需要保存）
- 极简的实现（整个 cpp 文件只有 34 行）

## 公共 API 函数

### SkColorFilterPriv::MakeGaussian

```cpp
sk_sp<SkColorFilter> SkColorFilterPriv::MakeGaussian();
```

创建一个高斯颜色过滤器实例。

**返回值**：高斯颜色过滤器智能指针

**访问限制**：
- 这是私有 API，不在公共头文件中暴露
- 主要供 Skia 内部使用
- 外部代码通常不应直接使用此过滤器

**使用场景**：
- 文本渲染的抗锯齿处理
- 创建柔和的边缘效果
- 特殊的 alpha 通道处理

## 内部实现细节

### 构造函数

```cpp
SkGaussianColorFilter::SkGaussianColorFilter() : SkColorFilterBase() {}
```

**极简设计**：
- 无任何成员变量
- 无需初始化任何状态
- 只调用基类构造函数

### 管线构建

```cpp
bool SkGaussianColorFilter::appendStages(const SkStageRec& rec,
                                         bool shaderIsOpaque) const {
    rec.fPipeline->append(SkRasterPipelineOp::gauss_a_to_rgba);
    return true;
}
```

**极简实现**：
- 只添加一个管线操作：`gauss_a_to_rgba`
- 不需要任何上下文数据
- 忽略 `shaderIsOpaque` 参数（因为输出总是非不透明的）
- 总是返回 `true`（操作永不失败）

### gauss_a_to_rgba 操作

这个管线操作的语义：
```
输入：(r, g, b, a)
处理：a' = gaussian_ramp(a)
输出：(a', a', a', a')  // 预乘白色
```

**高斯斜坡函数**可能的实现形式：
```cpp
// 伪代码
float gaussian_ramp(float alpha) {
    // 将 alpha 从线性空间映射到高斯分布
    // 通常使用类似误差函数 (erf) 的形式
    float normalized = alpha * 2.0 - 1.0;  // 映射到 [-1, 1]
    return 0.5 + 0.5 * erf(normalized * sqrt(2.0));
}
```

### 序列化

```cpp
void flatten(SkWriteBuffer&) const override {}

sk_sp<SkFlattenable> SkGaussianColorFilter::CreateProc(SkReadBuffer&) {
    return SkColorFilterPriv::MakeGaussian();
}
```

**无状态序列化**：
- `flatten` 不写入任何数据（因为无状态）
- `CreateProc` 不读取任何数据，直接创建新实例
- 序列化开销最小

## 依赖关系

### 内部依赖

| 组件 | 用途 |
|-----|------|
| `SkColorFilterBase` | 颜色过滤器基类 |
| `SkColorFilterPriv` | 提供私有工厂函数 |
| `SkRasterPipeline` | 管线构建 |
| `SkRasterPipelineOp` | 定义 `gauss_a_to_rgba` 操作 |

### 外部依赖

| 组件 | 用途 |
|-----|------|
| `SkColorFilter` | 公共接口基类 |
| `SkFlattenable` | 序列化框架 |

## 设计模式与设计决策

### 1. 单例模式倾向（Singleton-like）

虽然不是严格的单例，但由于完全无状态：
- 所有实例功能完全相同
- 可以安全地创建多个实例
- 理论上可以优化为单例（但当前没有）

### 2. 策略模式（Strategy Pattern）

`gauss_a_to_rgba` 封装了特定的变换策略：
- 策略固定，不可配置
- 通过管线操作实现
- 可以在不同平台上有不同的优化实现

### 3. 最小化设计（Minimalist Design）

整个类的设计极度简化：
- 无状态
- 无配置
- 无数据成员
- 单一职责

**优势**：
- 代码易于理解和维护
- 无内存开销（除了 vtable 指针）
- 序列化开销最小
- 线程完全安全

### 4. 私有 API 设计

通过 `SkColorFilterPriv` 限制访问：
```cpp
sk_sp<SkColorFilter> SkColorFilterPriv::MakeGaussian() {
    return sk_sp<SkColorFilter>(new SkGaussianColorFilter);
}
```

**理由**：
- 特殊用途的过滤器，不适合通用使用
- API 可能在未来版本中改变
- 避免外部代码依赖内部实现细节

## 性能考量

### 1. 零开销抽象

类本身没有任何成员变量：
- 对象大小仅包含基类开销和 vtable 指针
- 通常是 8-16 字节（取决于平台）
- 创建和销毁开销极小

### 2. 单一管线操作

```cpp
rec.fPipeline->append(SkRasterPipelineOp::gauss_a_to_rgba);
```

**性能优势**：
- 管线中只有一个操作，最小化调度开销
- 无需上下文数据，减少内存访问
- 可以高度优化（SIMD、GPU）

### 3. 高斯函数的实现

`gauss_a_to_rgba` 的实际实现可能使用：
- 查找表（LUT）：快速但精度有限
- 多项式近似：平衡速度和精度
- 硬件指令：某些平台有专门的指令

### 4. 与其他过滤器的比较

| 过滤器类型 | 状态大小 | 管线操作数 | 典型用途 |
|----------|---------|-----------|---------|
| `SkGaussianColorFilter` | 0 字节 | 1 | Alpha 高斯化 |
| `SkMatrixColorFilter` | 80 字节 | 5-7 | 线性颜色变换 |
| `SkTableColorFilter` | 1KB | 2-4 | 非线性查找表 |

高斯过滤器在状态大小和操作数上都是最小的。

### 5. 应用场景优化

典型使用场景：
```cpp
// 文本抗锯齿
paint.setColorFilter(SkColorFilterPriv::MakeGaussian());
canvas.drawText(...);
```

**优化点**：
- 过滤器可以被缓存和重用
- 与文本渲染管线紧密集成
- 通常在 GPU 上执行

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkColorFilterPriv.h` | 定义私有工厂函数 `MakeGaussian` |
| `src/effects/colorfilters/SkColorFilterBase.h` | 颜色过滤器基类 |
| `src/core/SkRasterPipeline.h` | 光栅化管线接口 |
| `src/core/SkRasterPipelineOpList.h` | 定义 `gauss_a_to_rgba` 操作 |
| `src/opts/` 目录 | 平台特定的 `gauss_a_to_rgba` 优化实现 |
| `include/core/SkColorFilter.h` | 颜色过滤器公共接口 |
| `src/gpu/ganesh/ops/` | GPU 上的实现 |
