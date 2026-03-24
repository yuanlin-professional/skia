# SkShader — 着色器基类实现

> 源文件: `src/shaders/SkShader.cpp`

## 概述

`SkShader.cpp` 实现了 Skia 着色器基类 `SkShader` 的核心方法。`SkShader` 是 Skia 中用于定义像素颜色生成规则的抽象基类，所有具体的着色器（如图像着色器、渐变着色器、颜色着色器等）都继承自它。

该文件实现了四个关键的着色器组合和查询方法：
- 查询着色器是否基于图像
- 为着色器添加局部变换矩阵
- 为着色器附加颜色过滤器
- 为着色器指定工作色彩空间

这些方法体现了 Skia 着色器系统的装饰器模式设计——通过包装现有着色器来添加新功能，而非修改原始着色器。

## 架构位置

```
Skia
├── include/core/
│   └── SkShader.h                    // 公共 API 声明
├── src/shaders/
│   ├── SkShader.cpp                  // 本文件：基类实现
│   ├── SkShaderBase.h                // 内部扩展基类
│   ├── SkLocalMatrixShader.h         // 局部矩阵装饰器
│   ├── SkColorFilterShader.h         // 颜色过滤器装饰器
│   ├── SkWorkingColorSpaceShader.h   // 色彩空间装饰器
│   ├── SkImageShader.h               // 图像着色器
│   └── ...                           // 其他具体着色器
```

`SkShader` 是 Skia 渲染管线的核心组件之一，被 `SkPaint` 引用来定义绘制操作的颜色来源。

## 主要类与结构体

### `SkShader`

公共基类，定义着色器的公共接口。具体实现由继承自 `SkShaderBase`（内部基类）的子类提供。

关键的内部转换宏 `as_SB(this)` 将 `SkShader*` 转换为 `SkShaderBase*`，与 `SkImage`/`SkImage_Base` 的设计模式一致。

## 公共 API 函数

### `SkImage* SkShader::isAImage(SkMatrix* localMatrix, SkTileMode xy[2]) const`

- **功能**: 查询该着色器是否本质上是一个图像着色器
- **参数**:
  - `localMatrix` (输出): 如果是图像着色器，返回其局部变换矩阵
  - `xy` (输出): 如果是图像着色器，返回 X/Y 方向的平铺模式
- **返回值**: 如果是图像着色器，返回底层 `SkImage*`；否则返回 `nullptr`

### `sk_sp<SkShader> SkShader::makeWithLocalMatrix(const SkMatrix& localMatrix) const`

- **功能**: 创建带有额外局部变换矩阵的新着色器
- **实现细节**:
  - 首先尝试通过 `makeAsALocalMatrixShader()` 获取已有的局部矩阵着色器包装
  - 如果已有包装，则合并两个矩阵（`ConcatLocalMatrices`），避免嵌套
  - 如果没有，则创建新的 `SkLocalMatrixShader` 包装
- **优化**: 通过矩阵合并避免了不必要的着色器嵌套层次

### `sk_sp<SkShader> SkShader::makeWithColorFilter(sk_sp<SkColorFilter> filter) const`

- **功能**: 创建在当前着色器输出上应用颜色过滤器的新着色器
- **实现**: 委托给 `SkColorFilterShader::Make`，alpha 系数固定为 1.0f

### `sk_sp<SkShader> SkShader::makeWithWorkingColorSpace(sk_sp<SkColorSpace> inputCS, sk_sp<SkColorSpace> outputCS) const`

- **功能**: 创建在指定工作色彩空间中运行的新着色器
- **参数**: 输入和输出色彩空间
- **实现**: 委托给 `SkWorkingColorSpaceShader::Make`

## 内部实现细节

### 局部矩阵优化

`makeWithLocalMatrix` 中有一个重要的优化：如果当前着色器已经是 `SkLocalMatrixShader` 的包装，函数会将新矩阵与现有矩阵合并，而不是创建嵌套的包装。这避免了多次调用 `makeWithLocalMatrix` 时产生深层嵌套的着色器链。

### 装饰器模式

所有 `makeWith*` 方法都返回新的着色器对象，不修改原始着色器。这保持了 `SkShader` 的不可变性，同时通过组合实现功能扩展。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkShader.h` | 公共 API 声明 |
| `SkShaderBase.h` | 内部基类（`as_SB()` 宏） |
| `SkColorFilter.h` | 颜色过滤器 |
| `SkMatrix.h` | 变换矩阵 |
| `SkLocalMatrixShader.h` | 局部矩阵装饰器着色器 |
| `SkColorFilterShader.h` | 颜色过滤器装饰器着色器 |
| `SkWorkingColorSpaceShader.h` | 色彩空间装饰器着色器 |

## 设计模式与设计决策

1. **装饰器模式（Decorator）**: `makeWithLocalMatrix`、`makeWithColorFilter`、`makeWithWorkingColorSpace` 都是装饰器——通过包装现有着色器来添加新功能
2. **桥接模式（Bridge）**: `SkShader`（公共接口）通过 `as_SB()` 委托给 `SkShaderBase`（实现接口）
3. **不可变性**: 所有方法返回新的着色器，不修改 `this`
4. **嵌套优化**: `makeWithLocalMatrix` 主动检测并合并已有的局部矩阵包装，避免深层嵌套
5. **组合优于继承**: 通过着色器组合（装饰器链）实现功能扩展，而非通过继承层次

## 性能考量

- `makeWithLocalMatrix` 通过矩阵合并减少着色器嵌套层数，降低渲染时的间接调用开销
- 所有 `makeWith*` 方法仅创建轻量级包装对象，不复制像素数据
- `isAImage` 查询是 O(1) 操作，通过虚函数分派直接判断

## 相关文件

- `include/core/SkShader.h` — 公共 API 声明
- `src/shaders/SkShaderBase.h` — 内部扩展基类
- `src/shaders/SkLocalMatrixShader.h` — 局部矩阵着色器
- `src/shaders/SkColorFilterShader.h` — 颜色过滤器着色器
- `src/shaders/SkWorkingColorSpaceShader.h` — 色彩空间着色器
- `src/shaders/SkImageShader.h` — 图像着色器
