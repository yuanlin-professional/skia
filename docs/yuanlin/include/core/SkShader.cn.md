# SkShader

> 源文件: `include/core/SkShader.h`

## 概述
SkShader 是 Skia 着色器系统的抽象基类，定义了为绘制操作生成源颜色的接口。着色器可以生成纯色、渐变、图案、图像纹理等多种颜色效果，是 Skia 图形管线中实现复杂填充效果的核心机制。

## 架构位置
位于 Skia 核心模块 (`include/core`)，作为渲染管线的着色阶段抽象。它与 SkPaint 紧密配合，为绘制的每个像素提供源颜色，是实现渐变、纹理映射、图案填充等高级效果的基础。

## 主要类与结构体

### SkShader
抽象基类，定义着色器接口契约。

**继承关系**: `SkFlattenable` → `SkShader`
- 继承自 SkFlattenable，支持序列化和反序列化

**设计特点**:
- 纯虚基类，具体功能由子类实现
- 不可变对象语义（所有方法返回新实例）
- 支持组合和变换

## 公共 API 函数

### 查询函数

#### `isOpaque()`
```cpp
virtual bool isOpaque() const { return false; }
```
- **功能**: 返回着色器是否保证生成不透明颜色
- **默认实现**: 返回 false（保守策略）
- **优化**: 子类可覆盖以启用特定优化（如跳过混合）

#### `isAImage()`
```cpp
SkImage* isAImage(SkMatrix* localMatrix, SkTileMode xy[2]) const
bool isAImage() const
```
- **功能**: 检查着色器是否由单个图像支持
- **参数**:
  - `localMatrix`: 输出参数，返回局部变换矩阵
  - `xy`: 输出参数，返回 X/Y 方向的平铺模式
- **返回值**: 图像指针（需要 ref），若非图像着色器返回 nullptr
- **注意**: 调用者需要 ref() 保持图像生命周期

### 变换与组合

#### `makeWithLocalMatrix()`
```cpp
sk_sp<SkShader> makeWithLocalMatrix(const SkMatrix&) const
```
- **功能**: 创建应用了局部变换矩阵的新着色器
- **参数**: 变换矩阵，在当前着色器的矩阵之前应用
- **返回值**: 新的着色器实例
- **用途**: 平移、旋转、缩放着色器效果

#### `makeWithColorFilter()`
```cpp
sk_sp<SkShader> makeWithColorFilter(sk_sp<SkColorFilter>) const
```
- **功能**: 创建应用了颜色滤镜的新着色器
- **流程**: 先执行着色器生成颜色，再应用颜色滤镜
- **返回值**: 新的着色器实例
- **用途**: 色调调整、饱和度变换、颜色映射

#### `makeWithWorkingColorSpace()`
```cpp
sk_sp<SkShader> makeWithWorkingColorSpace(
    sk_sp<SkColorSpace> inputCS,
    sk_sp<SkColorSpace> outputCS = nullptr
) const
```
- **功能**: 指定着色器的工作色彩空间
- **参数**:
  - `inputCS`: 子着色器返回值应转换到的输入色彩空间
  - `outputCS`: 着色器最终输出值所在的色彩空间（默认为 inputCS）
- **返回值**: 新的着色器实例
- **用途**:
  - 替换 Skia 默认的色彩管理
  - 自定义着色器实现色彩空间转换
  - 避免不必要或错误的转换

## SkShaders 命名空间工厂函数

### 基础着色器

#### `Empty()`
```cpp
SK_API sk_sp<SkShader> Empty();
```
- **功能**: 创建空着色器，不生成任何颜色
- **用途**: 占位符、禁用着色

#### `Color()`
```cpp
SK_API sk_sp<SkShader> Color(SkColor);
SK_API sk_sp<SkShader> Color(const SkColor4f&, sk_sp<SkColorSpace>);
```
- **功能**: 创建纯色着色器
- **重载**:
  - `SkColor` 版本：sRGB 颜色
  - `SkColor4f` 版本：支持宽色域和指定色彩空间

### 混合着色器

#### `Blend()`
```cpp
SK_API sk_sp<SkShader> Blend(SkBlendMode mode, sk_sp<SkShader> dst, sk_sp<SkShader> src);
SK_API sk_sp<SkShader> Blend(sk_sp<SkBlender>, sk_sp<SkShader> dst, sk_sp<SkShader> src);
```
- **功能**: 混合两个着色器的输出
- **参数**:
  - `mode/blender`: 混合模式或自定义混合器
  - `dst`: 目标着色器（底层）
  - `src`: 源着色器（上层）
- **用途**: 实现复杂的颜色组合效果

### 坐标约束

#### `CoordClamp()`
```cpp
SK_API sk_sp<SkShader> CoordClamp(sk_sp<SkShader>, const SkRect& subset);
```
- **功能**: 将着色器的采样坐标限制在指定矩形内
- **参数**:
  - `shader`: 被约束的着色器
  - `subset`: 有效坐标范围
- **用途**: 防止纹理超出边界采样

### 图像着色器

#### `Image()`
```cpp
SK_API sk_sp<SkShader> Image(
    sk_sp<SkImage> image,
    SkTileMode tmx, SkTileMode tmy,
    const SkSamplingOptions& options,
    const SkMatrix* localMatrix = nullptr
);
```
- **功能**: 从图像创建着色器（等价于 SkImage::makeShader）
- **参数**:
  - `image`: 源图像
  - `tmx/tmy`: X/Y 方向的平铺模式
  - `options`: 采样选项（过滤、mipmap 等）
  - `localMatrix`: 可选的局部变换
- **用途**: 纹理填充、图案绘制

#### `RawImage()`
```cpp
SK_API sk_sp<SkShader> RawImage(
    sk_sp<SkImage> image,
    SkTileMode tmx, SkTileMode tmy,
    const SkSamplingOptions& options,
    const SkMatrix* localMatrix = nullptr
);
```
- **功能**: 创建"原始"图像着色器，最小化处理（等价于 SkImage::makeRawShader）
- **差异**: 跳过某些色彩管理步骤
- **用途**: 性能优化、特定色彩流程

## 核心概念

### 着色器管线
```
SkPaint → SkShader → 像素颜色 → Alpha 调制 → 混合
```

1. SkShader 生成源颜色
2. SkPaint 的 alpha 调制颜色
3. 与目标颜色混合

### 局部矩阵
着色器可以有独立的坐标系统：
```
屏幕坐标 → Canvas 变换 → 局部矩阵 → 着色器坐标
```

这允许着色器独立于画布变换进行平移/旋转/缩放。

### 不可变性
所有变换和组合方法返回新实例：
```cpp
sk_sp<SkShader> original = SkShaders::Color(SK_ColorRED);
sk_sp<SkShader> transformed = original->makeWithLocalMatrix(matrix);
// original 未被修改
```

### 色彩管理
默认情况下，Skia 自动管理色彩空间：
- 着色器输出转换到目标色彩空间
- `makeWithWorkingColorSpace()` 允许自定义此行为

## 使用场景

### 基本用法
```cpp
SkPaint paint;
paint.setShader(SkShaders::Color(SK_ColorBLUE));
canvas->drawRect(rect, paint);
```

### 渐变着色器（非本文件）
```cpp
// 线性渐变（定义在其他文件）
SkPoint pts[] = {{0, 0}, {100, 100}};
SkColor colors[] = {SK_ColorRED, SK_ColorBLUE};
auto gradient = SkGradientShader::MakeLinear(pts, colors, nullptr, 2, SkTileMode::kClamp);
paint.setShader(gradient);
```

### 图像纹理
```cpp
auto shader = SkShaders::Image(
    image,
    SkTileMode::kRepeat, SkTileMode::kRepeat,
    SkSamplingOptions(SkFilterMode::kLinear)
);
paint.setShader(shader);
canvas->drawRect(rect, paint); // 用图像平铺填充
```

### 着色器变换
```cpp
// 旋转渐变
SkMatrix rotateMatrix;
rotateMatrix.setRotate(45);
auto rotatedShader = gradientShader->makeWithLocalMatrix(rotateMatrix);
```

### 着色器混合
```cpp
auto redShader = SkShaders::Color(SK_ColorRED);
auto blueShader = SkShaders::Color(SK_ColorBLUE);
auto blended = SkShaders::Blend(SkBlendMode::kMultiply, redShader, blueShader);
```

### 颜色滤镜应用
```cpp
auto colorFilter = SkColorFilters::Blend(SK_ColorGREEN, SkBlendMode::kModulate);
auto filteredShader = shader->makeWithColorFilter(colorFilter);
```

## 内部实现细节

### SkShaderBase
注释中提到"friend class SkShaderBase"，表明：
- 真正的实现在 SkShaderBase 中
- SkShader 是公共接口层
- 这种分离允许内部扩展而不影响公共 API

### 默认构造函数
```cpp
private:
    SkShader() = default;
```
- 私有默认构造，防止直接实例化
- 只能通过工厂函数或子类创建

### INHERITED 模式
```cpp
using INHERITED = SkFlattenable;
```
- Skia 的代码风格，简化基类引用

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `include/core/SkColor.h` | 颜色类型 |
| `include/core/SkColorSpace.h` | 色彩空间管理 |
| `include/core/SkFlattenable.h` | 序列化支持 |
| `include/core/SkRefCnt.h` | 引用计数 |
| `include/private/base/SkAPI.h` | API 导出宏 |

### 被依赖的模块
- **SkPaint**: 持有着色器引用
- **SkCanvas**: 通过 Paint 间接使用
- **渐变着色器**: SkGradientShader 等子类
- **图像着色器**: SkImageShader
- **着色器效果**: 各种特殊效果着色器

## 设计模式与设计决策

### 策略模式
SkShader 是策略模式的应用：
- 抽象策略：SkShader 定义接口
- 具体策略：颜色着色器、图像着色器、渐变着色器等
- 上下文：SkPaint 使用着色器

### 装饰器模式
变换方法如 `makeWithColorFilter()` 实现装饰器模式：
- 包装现有着色器，添加新行为
- 保持接口一致
- 支持链式装饰

### 工厂模式
SkShaders 命名空间提供工厂方法：
- 隐藏具体类型
- 统一创建接口
- 返回智能指针管理生命周期

### 不可变对象模式
所有修改操作返回新实例：
- 线程安全
- 易于缓存和共享
- 函数式编程风格

## 性能考量

### 着色器复杂度
不同着色器的性能差异：
1. 纯色：最快（常量输出）
2. 图像：中等（纹理采样）
3. 渐变：中等（插值计算）
4. 程序化：取决于复杂度

### 局部矩阵开销
每次坐标变换都有计算成本：
- 简单变换（平移）：开销小
- 复杂变换（透视）：开销大
- 考虑在 Canvas 层面变换

### 色彩管理
色彩空间转换可能涉及：
- 查找表
- 矩阵乘法
- Gamma 校正

`makeWithWorkingColorSpace()` 可优化特定场景。

### 着色器缓存
Skia 内部可能缓存着色器的编译结果（尤其是 GPU）：
- 重用相同着色器可提高性能
- 避免在每帧创建新着色器实例

## 线程安全

### 不可变性保证线程安全
SkShader 实例一旦创建即不可变：
- 多线程可安全共享
- 无需锁保护
- 引用计数是线程安全的

### 创建操作
工厂方法和变换方法创建新对象：
- 在不同线程创建不同实例是安全的
- 共享实例在多线程中使用是安全的

## 序列化支持

### SkFlattenable 继承
继承自 SkFlattenable 提供：
- 序列化到字节流
- 从字节流反序列化
- 跨进程传输着色器

### 使用场景
- 保存图形状态
- 远程渲染
- 延迟渲染（SkPicture）

## 最佳实践

### 着色器选择
- **纯色填充**: 使用 SkShaders::Color()
- **纹理填充**: 使用 SkShaders::Image()
- **复杂效果**: 组合多个着色器

### 性能优化
- 重用着色器实例，避免重复创建
- 优先使用简单着色器
- 考虑使用 isOpaque() 优化

### 坐标变换
- 在可能的情况下使用 Canvas 变换而非局部矩阵
- 局部矩阵适用于着色器独立变换的场景

## 相关文件
| 文件 | 关系 |
|------|------|
| `include/core/SkPaint.h` | 使用 SkShader |
| `include/core/SkCanvas.h` | 通过 Paint 间接使用 |
| `include/core/SkImage.h` | makeShader() 方法 |
| `include/effects/SkGradientShader.h` | 渐变着色器子类 |
| `src/core/SkShaderBase.h` | 内部实现基类 |
| `include/core/SkBlendMode.h` | 混合模式定义 |
| `include/core/SkColorFilter.h` | 颜色滤镜 |
