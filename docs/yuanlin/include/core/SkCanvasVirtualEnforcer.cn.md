# SkCanvasVirtualEnforcer

> 源文件: `include/core/SkCanvasVirtualEnforcer.h`

## 概述

SkCanvasVirtualEnforcer 是一个 C++ 模板类,用于在编译期强制 SkCanvas 子类实现所有关键的虚函数。通过继承此模板类而非直接继承 SkCanvas,开发者可以在编译时发现遗漏的虚函数重载,避免运行时错误。

## 架构位置

SkCanvasVirtualEnforcer 位于 Skia 核心绘制系统的基础架构层,属于画布抽象的编译时辅助工具。它通过 CRTP (Curiously Recurring Template Pattern) 模式包装任何 SkCanvas 派生类,在类型系统层面提供额外的安全保障。

## 主要类与结构体

### SkCanvasVirtualEnforcer<Base>

**职责描述**: 模板化的中间基类,将所有 SkCanvas 的关键虚函数声明为纯虚函数 (= 0),强制派生类必须提供实现。

**继承关系**: Base (通常是 SkCanvas 或其派生类) → SkCanvasVirtualEnforcer<Base> → 用户的 Canvas 类

**模板参数**:
- `Base`: 基类类型,通常是 SkCanvas 或 SkNWayCanvas 等 Canvas 的变体

**关键设计**:
使用 `using Base::Base;` 继承基类的所有构造函数,保持构造接口不变。

## 强制实现的虚函数

### 基础绘制函数

#### `void onDrawPaint(const SkPaint& paint) override = 0`
- **功能**: 绘制填充整个画布的操作
- **参数**: paint - 绘制配置对象

#### `void onDrawRect(const SkRect& rect, const SkPaint& paint) override = 0`
- **功能**: 绘制矩形
- **参数**: rect - 矩形区域, paint - 绘制配置

#### `void onDrawRRect(const SkRRect& rrect, const SkPaint& paint) override = 0`
- **功能**: 绘制圆角矩形
- **参数**: rrect - 圆角矩形, paint - 绘制配置

#### `void onDrawDRRect(const SkRRect& outer, const SkRRect& inner, const SkPaint& paint) override = 0`
- **功能**: 绘制双层圆角矩形(环形)
- **参数**: outer - 外层圆角矩形, inner - 内层圆角矩形, paint - 绘制配置

#### `void onDrawOval(const SkRect& rect, const SkPaint& paint) override = 0`
- **功能**: 绘制椭圆
- **参数**: rect - 椭圆的外接矩形, paint - 绘制配置

#### `void onDrawArc(const SkRect& rect, SkScalar startAngle, SkScalar sweepAngle, bool useCenter, const SkPaint& paint) override = 0`
- **功能**: 绘制圆弧或扇形
- **参数**: rect - 椭圆外接矩形, startAngle - 起始角度, sweepAngle - 扫描角度, useCenter - 是否连接圆心, paint - 绘制配置

#### `void onDrawPath(const SkPath& path, const SkPaint& paint) override = 0`
- **功能**: 绘制任意路径
- **参数**: path - 路径对象, paint - 绘制配置

#### `void onDrawRegion(const SkRegion& region, const SkPaint& paint) override = 0`
- **功能**: 绘制区域(多个矩形的集合)
- **参数**: region - 区域对象, paint - 绘制配置

### 文本绘制函数

#### `void onDrawTextBlob(const SkTextBlob* blob, SkScalar x, SkScalar y, const SkPaint& paint) override = 0`
- **功能**: 绘制文本块
- **参数**: blob - 文本数据对象, x/y - 绘制位置, paint - 绘制配置

### 高级绘制函数

#### `void onDrawPatch(const SkPoint cubics[12], const SkColor colors[4], const SkPoint texCoords[4], SkBlendMode mode, const SkPaint& paint) override = 0`
- **功能**: 绘制三次贝塞尔曲面片(Patch)
- **参数**: cubics - 12 个控制点, colors - 4 个顶点颜色, texCoords - 4 个纹理坐标, mode - 混合模式, paint - 绘制配置

#### `void onDrawPoints(SkCanvas::PointMode mode, size_t count, const SkPoint pts[], const SkPaint& paint) override = 0`
- **功能**: 绘制点、线或多边形
- **参数**: mode - 绘制模式(点/线/多边形), count - 点的数量, pts - 点数组, paint - 绘制配置

#### `void onDrawEdgeAAQuad(const SkRect& rect, const SkPoint clip[4], SkCanvas::QuadAAFlags aaFlags, const SkColor4f& color, SkBlendMode mode) override`
- **功能**: 绘制带边缘抗锯齿的四边形
- **参数**: rect - 矩形, clip - 裁剪点, aaFlags - 抗锯齿标志, color - 颜色, mode - 混合模式
- **平台差异**: Android 框架版本提供空实现 {},非 Android 版本为纯虚函数

### 元数据与特效函数

#### `void onDrawAnnotation(const SkRect& rect, const char key[], SkData* value) override = 0`
- **功能**: 绘制注解(用于 PDF 等格式)
- **参数**: rect - 注解区域, key - 注解键, value - 注解值

#### `void onDrawShadowRec(const SkPath&, const SkDrawShadowRec&) override = 0`
- **功能**: 绘制阴影效果
- **参数**: 路径和阴影参数记录

#### `void onDrawBehind(const SkPaint&) override {}`
- **功能**: 在现有内容后面绘制
- **注释**: 提供空实现,注释表明 Android 更新后将改为纯虚函数

### 复合对象绘制函数

#### `void onDrawDrawable(SkDrawable* drawable, const SkMatrix* matrix) override = 0`
- **功能**: 绘制可绘制对象
- **参数**: drawable - 可绘制对象, matrix - 变换矩阵(可选)

#### `void onDrawPicture(const SkPicture* picture, const SkMatrix* matrix, const SkPaint* paint) override = 0`
- **功能**: 绘制预录制的图像
- **参数**: picture - 图像对象, matrix - 变换矩阵(可选), paint - 绘制配置(可选)

## 内部实现细节

### 纯虚函数强制机制

所有关键的 onDraw* 系列函数都被标记为 `= 0`,使其成为纯虚函数。这意味着:
1. 任何继承 SkCanvasVirtualEnforcer 的类都必须实现这些函数
2. 遗漏任何一个函数都会导致编译失败
3. 在编译期而非运行期发现问题

### CRTP 模式应用

```cpp
template <typename Base>
class SkCanvasVirtualEnforcer : public Base
```

这是 Curiously Recurring Template Pattern 的应用:
- 模板参数 Base 是基类类型
- 允许在不同的 Canvas 基类上应用相同的强制机制
- 零运行时开销,所有检查都在编译期完成

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkCanvas.h | 提供基础 Canvas 接口和类型定义 |

### 被依赖的模块

这个类主要被 Skia 内部的 Canvas 实现使用:
- SkNWayCanvas: 多路画布实现
- SkRecorder: 记录绘制命令的画布
- SkNoDrawCanvas: 不实际绘制的画布
- 测试和调试用的 Canvas 子类

## 设计模式与设计决策

### 编译期强制模式

采用纯虚函数将运行时检查提前到编译期:
- **优点**: 更早发现错误,避免运行时崩溃
- **实现**: 所有关键函数声明为 `= 0`
- **效果**: 必须实现所有函数才能编译通过

### CRTP 泛型设计

使用模板而非具体类的好处:
- 可适用于任何 Canvas 基类
- 不增加继承层次的运行时开销
- 保持类型系统的完整性

### 构造函数转发

`using Base::Base;` 完美转发基类构造函数:
- 避免重复声明构造函数
- 保持基类的构造语义
- 减少维护负担

## 性能考量

### 零运行时开销

SkCanvasVirtualEnforcer 是纯编译期工具:
- 不引入额外的虚函数表
- 不增加对象大小
- 不影响运行时性能

### 内联友好

所有强制机制在编译期完成后,最终的虚函数调用与直接继承 SkCanvas 完全相同,编译器可以正常进行优化。

## 平台相关说明

### Android 框架特殊处理

onDrawEdgeAAQuad 函数在不同平台有不同的处理:

```cpp
#ifdef SK_BUILD_FOR_ANDROID_FRAMEWORK
    void onDrawEdgeAAQuad(...) override {}  // 空实现
#else
    void onDrawEdgeAAQuad(...) override = 0;  // 纯虚函数
#endif
```

**原因**:
- 该功能为 Chrome 开发中,尚未稳定
- Android 框架暂不使用此功能
- 避免强制 Android Canvas 子类实现未稳定的 API

## 使用建议

### 正确的继承方式

```cpp
// 推荐: 使用 SkCanvasVirtualEnforcer
class MyCanvas : public SkCanvasVirtualEnforcer<SkCanvas> {
public:
    using SkCanvasVirtualEnforcer<SkCanvas>::SkCanvasVirtualEnforcer;

protected:
    void onDrawRect(const SkRect& rect, const SkPaint& paint) override {
        // 实现绘制矩形
    }
    // ... 必须实现所有纯虚函数
};

// 不推荐: 直接继承 SkCanvas
class MyCanvas : public SkCanvas {
    // 如果忘记重载某个虚函数,编译器不会报错
    // 但运行时可能调用到错误的默认实现
};
```

### 适用场景

- 实现自定义 Canvas 子类
- 开发 Canvas 代理或包装器
- 创建用于测试的 Mock Canvas

## 相关文件

| 文件 | 关系 |
|------|------|
| include/core/SkCanvas.h | 基类,定义所有虚函数的原始声明 |
| include/utils/SkNWayCanvas.h | 使用此模板的多路画布实现 |
| src/core/SkRecorder.h | 使用此模板的记录画布 |
