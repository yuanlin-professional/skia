# Gradient

> 源文件: modules/skottie/src/layers/shapelayer/Gradient.cpp

## 概述

`Gradient.cpp` 实现了 Skottie 形状层系统中的渐变填充和描边功能。该模块支持线性和径向渐变,处理复杂的颜色和不透明度停止点合并,支持径向渐变的高光参数。这是 After Effects 渐变效果在 Skottie 中的核心实现。

## 架构位置

- **模块**: `modules/skottie/src/layers/shapelayer/`
- **命名空间**: `skottie::internal`
- **角色**: 渐变绘制,通过 `ShapeBuilder` 创建渐变填充/描边节点

## 主要类与结构体

### GradientAdapter
```cpp
class GradientAdapter final : public AnimatablePropertyContainer
```

渐变适配器,管理渐变属性的动画和复杂的停止点合并逻辑。

**Type 枚举**:
```cpp
enum class Type { kLinear, kRadial };
```

**成员变量**:
- `fGradient`: SkSG 渐变节点智能指针
- `fType`: 渐变类型(线性/径向)
- `fStopCount`: 颜色停止点数量
- `fStops`: 停止点数据向量
- `fStartPoint`, `fEndPoint`: 起止点
- `fHighlightLength`, `fHighlightAngle`: 高光参数(径向渐变)

**核心方法**:
- `Make()`: 静态工厂方法,解析 JSON 并创建适配器
- `onSync()`: 同步渐变参数和停止点到 SkSG 节点

### ColorRec / OpacityRec
```cpp
struct ColorRec { float t, r, g, b; };      // 颜色停止点
struct OpacityRec { float t, a; };          // 不透明度停止点
```

## 公共 API 函数

### AttachGradientFill
```cpp
sk_sp<sksg::PaintNode> ShapeBuilder::AttachGradientFill(
    const skjson::ObjectValue& jgrad,
    const AnimationBuilder* abuilder)
```
创建渐变填充绘制节点。

### AttachGradientStroke
```cpp
sk_sp<sksg::PaintNode> ShapeBuilder::AttachGradientStroke(
    const skjson::ObjectValue& jgrad,
    const AnimationBuilder* abuilder)
```
创建渐变描边绘制节点。

**JSON 参数**:
- `"t"`: 类型(Type)
  - `1`: 线性渐变
  - `2`: 径向渐变
- `"s"`: 起点(Start Point)
- `"e"`: 终点(End Point)
- `"h"`: 高光长度(Highlight Length,径向渐变)
- `"a"`: 高光角度(Highlight Angle,径向渐变)
- `"g"`: 渐变对象
  - `"p"`: 停止点数量
  - `"k"`: 停止点数据向量

## 内部实现细节

### 线性渐变配置
```cpp
auto* grad = static_cast<sksg::LinearGradient*>(fGradient.get());
grad->setStartPoint(s_point);
grad->setEndPoint(e_point);
```

### 径向渐变配置
```cpp
// 焦点计算
const SkPoint rotated_e_point = SkMatrix::RotateDeg(fHighlightAngle, s_point).mapPoint(e_point);
const float h_len = SkTPin(fHighlightLength * 0.01f, -1 + eps, 1 - eps);
const SkPoint focal_point = s_point + (rotated_e_point - s_point) * h_len;

auto* grad = static_cast<sksg::RadialGradient*>(fGradient.get());
grad->setStartCenter(focal_point);    // 焦点
grad->setEndCenter(s_point);          // 中心
grad->setStartRadius(0);
grad->setEndRadius(SkPoint::Distance(s_point, rotated_e_point));
```

**高光参数语义**:
- **长度**: 沿 start→end 向量的位置,0% 为起点,100% 为终点
- **角度**: 围绕起点旋转终点
- **范围**: [-100%, 100%],负值镜像正值
- **边界处理**: 使用 epsilon 避免焦点正好在圆上(触发特殊 SVG 行为)

### 停止点数据结构
```
fStops = [ColorRec × fColorStopCount] + [OpacityRec × N]
```

**颜色记录**: `(t, r, g, b)` × `fColorStopCount`
**不透明度记录**: `(t, a)` × `(fStops.size() - c_size) / 2`

### 停止点合并算法
```cpp
// 归并排序颜色和不透明度停止点,必要时 LERP 中间通道值
while (c_rec || o_rec) {
    // 1. 计算相对位置和插值系数
    const auto t_c = SkTPin(sk_ieee_float_divide(o_pos_rel, c_pos_rel), 0.0f, 1.0f),
               t_o = SkTPin(sk_ieee_float_divide(c_pos_rel, o_pos_rel), 0.0f, 1.0f);

    // 2. LERP 计算当前停止点颜色
    current_stop = {
        std::min(c_pos, o_pos),
        {
            lerp(current_stop.fColor.fR, cs.r, t_c),
            lerp(current_stop.fColor.fG, cs.g, t_c),
            lerp(current_stop.fColor.fB, cs.b, t_c),
            lerp(current_stop.fColor.fA, os.a, t_o)
        }
    };

    // 3. 消费停止点记录
    if (c_pos <= o_pos) c_rec = next_rec<ColorRec>(c_rec, c_end);
    if (o_pos <= c_pos) o_rec = next_rec<OpacityRec>(o_rec, o_end);
}
```

**算法特点**:
- 归并排序两个独立的停止点数组
- 处理不同位置的颜色和不透明度停止点
- LERP 插值缺失的通道值
- 保持单调递增的停止点位置

### 停止点位置限制
```cpp
const auto c_pos = std::max(cs.t, current_stop.fPosition),
           o_pos = std::max(os.t, current_stop.fPosition);
```
确保停止点位置单调递增,避免渲染问题。

### 内存优化
```cpp
stops.shrink_to_fit();
```
合并完成后收缩向量容量,减少内存占用。

## 依赖关系

- **Skia 核心**: `SkMatrix`, `SkPoint`, `SkColor`
- **SkSG**: `sksg::Gradient`, `sksg::LinearGradient`, `sksg::RadialGradient`, `sksg::ShaderPaint`
- **Skottie**: `AnimatablePropertyContainer`, `Vec2Value`, `VectorValue`, `FillStroke`

## 设计模式与设计决策

### 工厂方法模式
`Make()` 静态方法根据 JSON 数据创建适配器实例。

### 策略模式
`Type` 枚举实现不同的渐变类型(线性/径向)配置策略。

### 归并算法
停止点合并使用经典的归并排序思想,高效合并两个有序数组。

### 类型擦除
使用 `reinterpret_cast` 将平坦数组解释为结构化数据:
```cpp
const auto* c_rec = reinterpret_cast<const ColorRec*>(fStops.data());
```
避免额外的内存分配和复制。

## 性能考量

- **停止点预留**: `stops.reserve(c_count)` 避免动态增长
- **内存收缩**: `shrink_to_fit()` 释放多余容量
- **安全除法**: `sk_ieee_float_divide` 处理除零
- **移动语义**: `std::move(stops)` 避免向量复制
- **数据局部性**: 停止点数据紧密排列在连续内存
- **LERP 优化**: 内联 lambda 函数可被编译器优化
- **早期验证**: 在 `Make()` 中验证数据有效性,避免无效对象创建

## 相关文件

- `modules/sksg/include/SkSGGradient.h`: 渐变节点实现
- `modules/sksg/include/SkSGPaint.h`: `ShaderPaint` 实现
- `modules/skottie/src/layers/shapelayer/FillStroke.cpp`: 填充/描边实现
- `modules/skottie/src/SkottieValue.h`: `VectorValue`, `Vec2Value` 定义
- `modules/skottie/src/animator/Animator.h`: `AnimatablePropertyContainer` 基类
