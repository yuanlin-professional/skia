# SkBlender

> 源文件: `include/core/SkBlender.h`

## 概述

SkBlender 是 Skia 渲染管线中表示自定义混合函数的基类。它负责将源颜色(绘制结果)与目标颜色(画布上的现有颜色)混合成最终颜色,为高级混合效果提供了可扩展的框架。

## 架构位置

SkBlender 位于 Skia 核心图形系统的绘制层,属于颜色混合子系统。它继承自 SkFlattenable,这使得混合器可以被序列化和反序列化,支持在不同进程间传递混合配置。该类是混合系统的公共接口,实际实现由私有的 SkBlenderBase 类族提供。

## 主要类与结构体

### SkBlender

**职责描述**: 作为混合功能的抽象基类,定义了混合器的公共接口,并提供创建标准混合模式混合器的工厂方法。

**继承关系**: SkFlattenable → SkBlender

**关键成员变量**:
该类没有公开的成员变量,所有状态由子类管理。

## 公共 API 函数

### `static sk_sp<SkBlender> Mode(SkBlendMode mode)`

- **功能**: 创建一个实现指定混合模式的混合器对象
- **参数**:
  - `mode`: 枚举类型 SkBlendMode,指定要使用的混合模式(如 Multiply、Screen、Overlay 等)
- **返回值**: 返回智能指针 sk_sp<SkBlender>,指向新创建的混合器对象

**使用场景**: 当需要使用 Skia 内置的标准混合模式时,通过此工厂方法创建对应的混合器,而无需自定义混合逻辑。

## 内部实现细节

### 构造与友元设计

SkBlender 采用私有构造函数设计,防止用户直接实例化基类。构造函数为 `default`,表示使用编译器生成的默认构造逻辑。

友元类 SkBlenderBase 拥有访问 SkBlender 私有成员的权限,这是典型的 "pImpl" 模式变体:
- 公共类 (SkBlender) 提供稳定的 API 接口
- 私有实现类 (SkBlenderBase) 封装具体实现细节

### 混合器生命周期

混合器通过智能指针 `sk_sp` 管理,使用引用计数自动管理内存:
1. 通过 `Mode()` 工厂方法创建
2. 智能指针自动追踪引用
3. 最后一个引用销毁时自动释放资源

### 序列化能力

继承自 SkFlattenable 赋予 SkBlender 序列化能力:
- 可以将混合器配置序列化为字节流
- 支持跨进程传递混合设置
- 可用于保存和恢复绘制状态

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkBlendMode.h | 定义标准混合模式枚举 |
| SkFlattenable.h | 提供序列化基类 |
| SkTypes.h | 基础类型定义和 SK_API 宏 |

### 被依赖的模块

SkBlender 是混合系统的核心抽象,被以下模块依赖:
- SkPaint: 绘制配置中可包含混合器
- SkShader: 着色器可能需要自定义混合
- SkRuntimeEffect: 运行时着色器可创建自定义混合器
- Graphite/Ganesh 后端: GPU 渲染时转换混合器为着色器代码

## 设计模式与设计决策

### 工厂模式

`Mode()` 静态方法采用工厂模式,隐藏具体混合器类型的创建细节。用户只需指定混合模式,无需了解内部实现类。

### 策略模式

SkBlender 体现了策略模式:
- 定义混合算法的公共接口
- 不同子类实现不同的混合策略
- 在运行时可动态切换混合器

### 不可变对象设计

SkBlender 对象创建后不可修改:
- 无公共 setter 方法
- 混合配置在创建时确定
- 简化并发场景下的使用

### 友元类分离设计

将实现细节封装在友元类 SkBlenderBase 中的优点:
- 保持公共 API 简洁稳定
- 实现细节可自由修改不影响用户代码
- 减少头文件依赖,加快编译速度

## 性能考量

### 轻量级接口

SkBlender 本身只是一个薄接口层:
- 无虚函数开销在公共接口层
- 通过智能指针高效传递
- 引用计数开销最小

### 缓存友好

混合器对象通常可重用:
- 相同混合模式的多个绘制操作可共享同一个混合器
- 智能指针使共享变得安全高效

### GPU 优化

混合器最终会被转换为 GPU 着色器代码:
- Mode() 创建的混合器对应高效的 GPU 混合操作
- 自定义混合器会生成对应的片段着色器

## 使用示例

```cpp
// 创建一个 Multiply 混合模式的混合器
sk_sp<SkBlender> blender = SkBlender::Mode(SkBlendMode::kMultiply);

// 在 Paint 中使用混合器
SkPaint paint;
paint.setBlender(blender);

// 使用该 paint 绘制时,会应用 Multiply 混合效果
canvas->drawRect(rect, paint);
```

## 扩展性

虽然这个头文件只提供了基于 SkBlendMode 的工厂方法,Skia 还支持通过以下方式创建自定义混合器:
- **SkRuntimeEffect**: 使用 SkSL 语言编写自定义混合逻辑
- **内部扩展**: SkBlenderBase 子类可实现复杂的混合算法

## 相关文件

| 文件 | 关系 |
|------|------|
| include/core/SkBlendMode.h | 定义标准混合模式枚举 |
| include/core/SkFlattenable.h | 基类,提供序列化能力 |
| include/core/SkPaint.h | 使用混合器进行绘制配置 |
| src/core/SkBlenderBase.h | 私有实现基类 |
| include/effects/SkRuntimeEffect.h | 创建自定义混合器的运行时 API |
