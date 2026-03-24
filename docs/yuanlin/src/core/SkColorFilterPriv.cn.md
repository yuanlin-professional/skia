# SkColorFilterPriv

> 源文件: src/core/SkColorFilterPriv.h

## 概述

`SkColorFilterPriv` 是 `SkColorFilter` 的私有扩展 API,提供了一些不适合公开但内部需要的高级颜色过滤器创建方法。这些方法包括高斯模糊过滤器、色彩空间转换过滤器,以及在特定工作色彩格式中运行的过滤器包装器。该文件是 Skia 内部实现的一部分,仅供核心代码使用。

## 架构位置

`SkColorFilterPriv.h` 位于 Skia 核心层(src/core),是私有实现头文件。它扩展了公共的 `SkColorFilter` API,提供内部使用的高级功能。该文件被颜色过滤器实现、着色器和高级图像处理组件使用。

## 主要类与结构体

### SkColorFilterPriv

静态工具类,不包含成员变量,仅提供静态方法。

| 特性 | 说明 |
|------|------|
| 类型 | 工具类 |
| 实例化 | 不可实例化 |
| 命名空间 | 全局(作为类) |

## 公共 API 函数

### 高斯模糊过滤器

```cpp
static sk_sp<SkColorFilter> MakeGaussian();
```

**功能:**
- 创建高斯模糊颜色过滤器
- 用于特殊视觉效果或无障碍功能
- 具体实现细节未公开

**使用场景:**
- 模拟视觉模糊
- 无障碍模式(如色盲辅助)
- 特殊图像效果

### 色彩空间转换过滤器

```cpp
static sk_sp<SkColorFilter> MakeColorSpaceXform(sk_sp<SkColorSpace> src,
                                                sk_sp<SkColorSpace> dst);
```

**功能:**
- 创建将颜色从源色彩空间转换到目标色彩空间的过滤器
- 封装 `SkColorSpaceXformSteps` 功能为颜色过滤器
- 支持 SDR 和 HDR 色彩空间转换

**参数:**
- `src`: 源色彩空间
- `dst`: 目标色彩空间

**使用场景:**
- 跨色彩空间的图像处理
- HDR/SDR 内容混合
- 色彩空间标准化

**实现说明:**
- 可能内部使用 `SkColorSpaceXformSteps`
- 优化常见色彩空间转换路径
- 支持 GPU 加速

### 工作色彩格式包装器

```cpp
static sk_sp<SkColorFilter> WithWorkingFormat(sk_sp<SkColorFilter> child,
                                              const skcms_TransferFunction* tf,
                                              const skcms_Matrix3x3* gamut,
                                              const SkAlphaType* at);
```

**功能:**
- 在不同于通常的工作色彩格式中运行子过滤器
- 默认工作格式:目标表面色彩空间中的预乘颜色
- 每个非 null 参数覆盖色彩格式的对应方面

**参数:**
- `child`: 要包装的子颜色过滤器
- `tf`: 传递函数(null = 使用默认)
- `gamut`: 色域矩阵(null = 使用默认)
- `at`: Alpha 类型(null = 使用默认)

**使用场景:**
- 在线性光照空间中进行颜色运算
- 在特定色域中进行矩阵操作
- 控制预乘/非预乘 alpha 处理

**实现说明:**
- 输入和输出都使用指定的工作格式表示
- 自动进行必要的色彩空间转换
- 可以嵌套使用以创建复杂的处理管线

**示例场景:**

1. **线性空间处理:**
   ```cpp
   // 在线性空间中混合颜色
   auto linearFilter = SkColorFilterPriv::WithWorkingFormat(
       blendFilter,
       &SkNamedTransferFn::kLinear,  // 线性传递函数
       nullptr,  // 保持默认色域
       nullptr   // 保持默认 alpha 类型
   );
   ```

2. **特定色域处理:**
   ```cpp
   // 在 Rec2020 色域中进行矩阵运算
   auto rec2020Filter = SkColorFilterPriv::WithWorkingFormat(
       matrixFilter,
       nullptr,
       &SkNamedGamut::kRec2020,  // Rec2020 色域
       nullptr
   );
   ```

3. **非预乘处理:**
   ```cpp
   // 在非预乘空间中应用查找表
   SkAlphaType unpremul = kUnpremul_SkAlphaType;
   auto tableFilter = SkColorFilterPriv::WithWorkingFormat(
       tableColorFilter,
       nullptr,
       nullptr,
       &unpremul  // 非预乘 alpha
   );
   ```

## 内部实现细节

### 包装器实现

`WithWorkingFormat` 可能实现为包装颜色过滤器:

```cpp
class WorkingFormatColorFilter : public SkColorFilterBase {
    sk_sp<SkColorFilter> fChild;
    skcms_TransferFunction fTF;
    skcms_Matrix3x3 fGamut;
    SkAlphaType fAlphaType;

    SkPMColor4f onFilterColor4f(...) override {
        // 1. 转换输入到工作格式
        // 2. 应用子过滤器
        // 3. 转换输出回目标格式
    }
};
```

### 色彩空间转换优化

`MakeColorSpaceXform` 可能包含以下优化:

- **恒等转换检测**: 如果 src == dst,返回 nullptr 或恒等过滤器
- **常见路径优化**: sRGB ↔ 线性 sRGB 等常见转换的快速路径
- **GPU 着色器生成**: 为常见转换生成优化的着色器代码

### 高斯过滤器实现

`MakeGaussian` 可能使用以下技术:

- **查找表**: 预计算的高斯模糊核
- **分离卷积**: 水平和垂直分离以提高性能
- **近似算法**: 使用快速近似而不是精确高斯计算

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkColorFilter` | 基类和公共 API |
| `SkColorSpace` | 色彩空间定义 |
| `skcms` | 传递函数和矩阵 |
| `SkAlphaType` | Alpha 类型定义 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkColorFilter.cpp` | 实现 `makeWithWorkingColorSpace` |
| 颜色过滤器实现 | 创建高级过滤器 |
| `SkShader` | 在着色器中使用颜色过滤器 |
| 图像处理管线 | 色彩空间管理 |

## 设计模式与设计决策

### 私有 API 分离

将高级功能放在私有头文件:
- 避免公共 API 膨胀
- 灵活更改内部接口
- 明确内部使用边界

### 静态工具类

使用静态方法而不是全局函数:
- 命名空间管理
- 避免符号冲突
- 明确 API 边界

### 可选参数模式

`WithWorkingFormat` 使用指针允许可选参数:
- null 表示使用默认值
- 避免参数组合爆炸
- 清晰表达意图

### 装饰器模式

`WithWorkingFormat` 实现装饰器模式:
- 不修改原始过滤器
- 可以嵌套多层包装
- 职责清晰分离

## 性能考量

### 色彩空间转换缓存

色彩空间转换过滤器可能缓存转换矩阵:
- 避免重复计算
- 预计算逆传递函数
- 优化常见路径

### GPU 优化

工作格式包装器在 GPU 上的优化:
- 合并多个色彩空间转换
- 减少着色器中的分支
- 利用硬件色彩空间转换

### 惰性创建

某些过滤器可能延迟创建内部资源:
- 仅在首次使用时初始化
- 减少不必要的开销
- 支持条件优化

### 传递优化

编译器可能内联小型过滤器:
- 静态工厂方法便于内联
- 简单过滤器直接展开
- 减少虚函数调用

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkColorFilter.h` | 公共 API | 基础颜色过滤器接口 |
| `src/core/SkColorFilter.cpp` | 实现 | 使用私有 API |
| `src/effects/colorfilters/SkColorFilterBase.h` | 基类 | 过滤器基类 |
| `include/core/SkColorSpace.h` | 依赖 | 色彩空间定义 |
| `modules/skcms/skcms.h` | 依赖 | 色彩管理 |
| `src/core/SkColorSpaceXformSteps.h` | 可能使用 | 色彩空间转换 |
