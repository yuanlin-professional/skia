# SkSVGFeLightSource

> 源文件: modules/svg/src/SkSVGFeLightSource.cpp

## 概述

`SkSVGFeLightSource` 模块实现了 SVG 滤镜效果中的光源相关功能,主要包含三种光源类型的实现:远距离光源(FeDistantLight)、点光源(FePointLight)和聚光灯光源(FeSpotLight)。该模块负责处理这些光源的属性解析以及方向计算,为 SVG 的光照滤镜效果(如 feDiffuseLighting 和 feSpecularLighting)提供基础支持。

光源是 SVG 滤镜系统中实现真实感渲染的重要组成部分,通过模拟不同类型的光照效果,可以为 SVG 图形添加深度感和立体感。该模块通过数学计算将光源的方位角(azimuth)和仰角(elevation)等参数转换为三维空间中的方向向量。

## 架构位置

该模块位于 Skia 的 SVG 模块中,具体属于滤镜效果(Filter Effects)子系统。在整体架构中:

- **上层依赖**: 被 `SkSVGFeLighting.cpp` 等光照滤镜效果类使用
- **同级模块**: 与其他 SVG 滤镜效果实现(如 FeBlend、FeColorMatrix 等)并列
- **下层依赖**: 依赖 `SkSVGAttributeParser` 进行属性解析,使用 Skia 核心的 `SkPoint3` 表示三维空间坐标

在 SVG 标准中,光源元素通常作为光照滤镜的子元素出现,该模块正是实现了这一层次结构的底层支持。

## 主要类与结构体

### SkSVGFeDistantLight
远距离光源类,模拟来自无限远处的平行光(如太阳光)。主要特点:
- **方位角(azimuth)**: 光线在 XY 平面上的角度,默认为 0 度
- **仰角(elevation)**: 光线与 XY 平面的夹角,默认为 0 度
- **方向计算**: 通过 `computeDirection()` 方法将角度转换为三维方向向量

### SkSVGFePointLight
点光源类,模拟从某个点向所有方向发射的光源(如灯泡)。主要特点:
- **位置坐标**: 通过 x, y, z 三个属性定义光源在三维空间中的位置
- **属性可配置**: 支持独立设置每个坐标轴的值

### SkSVGFeSpotLight
聚光灯光源类,模拟带有方向性和照射范围的光源(如手电筒)。主要特点:
- **光源位置**: x, y, z 定义光源位置
- **照射目标**: pointsAtX, pointsAtY, pointsAtZ 定义光线指向的点
- **光强衰减**: specularExponent 控制光强从中心向边缘的衰减速度
- **照射角度**: limitingConeAngle 限制光锥的张角范围

## 公共 API 函数

### SkSVGFeDistantLight::computeDirection()
```cpp
SkPoint3 computeDirection() const
```
计算远距离光源的方向向量。该函数执行两次三维旋转:
1. 首先将向量 [1,0,0] 绕 Y 轴旋转(仰角)
2. 然后将结果绕 Z 轴旋转(方位角)
返回计算得到的单位方向向量。

### parseAndSetAttribute 系列函数
每个光源类都实现了属性解析函数:

```cpp
bool SkSVGFeDistantLight::parseAndSetAttribute(const char* n, const char* v)
```
解析并设置远距离光源的属性(azimuth、elevation)

```cpp
bool SkSVGFePointLight::parseAndSetAttribute(const char* n, const char* v)
```
解析并设置点光源的位置属性(x、y、z)

```cpp
bool SkSVGFeSpotLight::parseAndSetAttribute(const char* n, const char* v)
```
解析并设置聚光灯的全部属性,包括位置、目标点、光强参数等

所有解析函数都遵循链式调用模式,先调用父类的解析函数,如果匹配失败再尝试解析自己的属性。

## 内部实现细节

### 方向计算的数学原理
`computeDirection()` 函数的实现基于旋转矩阵的复合:
- **旋转矩阵**: 使用 Rz*Ry 的第一列向量作为最终方向
- **角度转换**: 使用 `SkDegreesToRadians()` 将角度制转换为弧度制
- **三角函数**: 通过 `sinf()` 和 `cosf()` 计算旋转后的坐标分量

计算公式推导:
```
direction.x = cos(azimuth) * cos(elevation)
direction.y = sin(azimuth) * cos(elevation)
direction.z = sin(elevation)
```

这个简化的公式避免了显式构造完整的旋转矩阵,提高了计算效率。

### 属性解析模式
所有光源类的属性解析都使用了统一的模板:
1. 调用 `INHERITED::parseAndSetAttribute()` 处理基类属性
2. 使用 `SkSVGAttributeParser::parse<>()` 模板函数解析特定类型
3. 通过逻辑或运算符(||)实现短路求值,找到匹配的属性即返回

这种模式确保了属性解析的高效性和可扩展性。

## 依赖关系

### 外部依赖
- **SkScalar.h**: 提供标量类型和角度转换函数
- **SkSVGAttributeParser.h**: 提供属性解析框架
- **SkSVGFeLightSource.h**: 光源类的头文件声明
- **cmath**: 提供三角函数支持

### 被依赖情况
该模块被以下组件使用:
- `SkSVGFeLighting`: 光照滤镜效果的主实现
- `SkSVGFeSpecularLighting`: 镜面反射光照效果
- `SkSVGFeDiffuseLighting`: 漫反射光照效果

### 数据流向
SVG 属性字符串 → AttributeParser → LightSource 对象 → Lighting 滤镜 → ImageFilter

## 设计模式与设计决策

### 继承层次设计
所有光源类都继承自共同的基类(通过 `INHERITED` 宏可以推断),这种设计:
- **多态性**: 允许光照滤镜通过统一接口处理不同类型的光源
- **代码复用**: 公共属性解析逻辑可以在基类中实现
- **扩展性**: 添加新的光源类型只需继承基类并实现特定方法

### 属性解析策略
使用链式属性解析模式的优势:
- **短路求值**: 找到匹配的属性后立即返回,避免不必要的比较
- **可维护性**: 新增属性只需在链中添加新的解析分支
- **可读性**: 解析逻辑清晰,一目了然

### 数学计算优化
`computeDirection()` 方法直接计算结果向量而不是构造完整矩阵:
- **性能优势**: 减少了不必要的矩阵乘法运算
- **内存效率**: 避免分配临时矩阵存储空间
- **精度保持**: 直接计算减少了浮点运算的累积误差

## 性能考量

### 计算效率
- **三角函数调用**: `computeDirection()` 中调用了 4 次三角函数,这是光源方向计算的必要代价
- **缓存可能性**: 如果光源属性不变,方向向量可以被缓存以避免重复计算
- **内联优化**: 简短的 getter/setter 方法适合编译器内联优化

### 内存占用
- **轻量级对象**: 每个光源对象只存储必要的数值属性
- **无虚拟继承**: 避免了虚表指针的额外开销
- **紧凑布局**: 使用 float/double 类型存储数值,内存对齐效率高

### 优化建议
1. **方向缓存**: 可以为 `FeDistantLight` 添加缓存机制,只在属性改变时重新计算
2. **SIMD 优化**: 批量处理多个光源时可以使用向量化指令
3. **常量折叠**: 对于静态定义的光源,编译时就可以计算出方向向量

## 相关文件

### 头文件
- `modules/svg/include/SkSVGFeLightSource.h` - 光源类的声明
- `modules/svg/include/SkSVGAttributeParser.h` - 属性解析器
- `include/core/SkScalar.h` - 标量和角度转换工具

### 实现文件
- `modules/svg/src/SkSVGFeLighting.cpp` - 光照滤镜效果实现
- `modules/svg/src/SkSVGFeDiffuseLighting.cpp` - 漫反射光照实现
- `modules/svg/src/SkSVGFeSpecularLighting.cpp` - 镜面反射光照实现

### 相关规范
- W3C SVG Filter Effects Specification - 定义了光源元素的标准行为
- SVG 1.1/2.0 Lighting Effects - 详细说明了各种光源的参数和计算方法

该模块是 Skia SVG 滤镜系统中不可或缺的基础组件,为实现符合标准的光照效果提供了完整的光源模型支持。
