# GrPathStencilSettings

> 源文件
> - `src/gpu/ganesh/ops/GrPathStencilSettings.h`

## 概述

`GrPathStencilSettings.h` 是一个头文件，定义了路径渲染中使用的各种预配置模板设置。该文件提供了实现标准路径填充算法（偶奇规则和非零缠绕规则）所需的所有模板配置，包括正常填充和反向填充的情况。

这些模板设置基于经典的 OpenGL Red Book 算法，使用模板缓冲区来确定路径内部和外部的像素。

## 架构位置

在 Skia 的 Ganesh 架构中，该头文件位于：

```
skia/
  src/
    gpu/
      ganesh/
        ops/
          GrPathStencilSettings.h (模板设置定义)
        GrUserStencilSettings.h (模板设置基类)
```

它为路径渲染操作提供了标准的模板配置。

## 主要类与结构体

该文件定义了一系列 `constexpr` 静态模板设置对象，而不是类。

### 偶奇填充规则（Even-Odd Fill Rule）

#### gEOStencilPass

**用途：** 偶奇规则模板遍

```cpp
static constexpr GrUserStencilSettings gEOStencilPass(
    GrUserStencilSettings::StaticInit<
        0xffff,                           // 参考值
        GrUserStencilTest::kAlwaysIfInClip, // 测试：总是通过（如果在裁剪内）
        0xffff,                           // 掩码
        GrUserStencilOp::kInvert,         // 通过操作：反转
        GrUserStencilOp::kKeep,           // 失败操作：保持
        0xffff                            // 写入掩码
    >()
);
```

**工作原理：**
- 每次光栅化路径边界时反转模板位
- 奇数次穿过边界的像素模板值变为非零
- 偶数次穿过边界的像素模板值回到零

#### gEOColorPass

**用途：** 偶奇规则颜色遍（正常填充）

```cpp
static constexpr GrUserStencilSettings gEOColorPass(
    GrUserStencilSettings::StaticInit<
        0x0000,                      // 参考值：0
        GrUserStencilTest::kNotEqual, // 测试：不等于 0
        0xffff,                      // 掩码
        GrUserStencilOp::kZero,      // 通过操作：清零
        GrUserStencilOp::kZero,      // 失败操作：清零
        0xffff                       // 写入掩码
    >()
);
```

**工作原理：**
- 只绘制模板值不等于零的像素
- 绘制后将模板清零（为下次使用做准备）
- 不需要检查裁剪，因为模板遍已经只在裁剪内写入

#### gInvEOColorPass

**用途：** 偶奇规则颜色遍（反向填充）

```cpp
static constexpr GrUserStencilSettings gInvEOColorPass(
    GrUserStencilSettings::StaticInit<
        0x0000,                             // 参考值：0
        GrUserStencilTest::kEqualIfInClip,  // 测试：等于 0（在裁剪内）
        0xffff,                             // 掩码
        GrUserStencilOp::kZero,             // 通过操作：清零
        GrUserStencilOp::kZero,             // 失败操作：清零
        0xffff                              // 写入掩码
    >()
);
```

**工作原理：**
- 绘制模板值等于零的像素（路径外部）
- 必须检查裁剪，因为裁剪外的像素总是零

### 非零缠绕填充规则（Non-Zero Winding Fill Rule）

#### gWindStencilPass

**用途：** 缠绕规则模板遍

```cpp
static constexpr GrUserStencilSettings gWindStencilPass(
    GrUserStencilSettings::StaticInitSeparate<
        0xffff,                             0xffff,
        GrUserStencilTest::kAlwaysIfInClip, kAlwaysIfInClip,
        0xffff,                             0xffff,
        GrUserStencilOp::kIncWrap,          // 正面：递增（带环绕）
        GrUserStencilOp::kKeep,             kKeep,
        0xffff,                             0xffff>()
);
```

**特殊之处：**
- 使用 `StaticInitSeparate`，对正面和背面使用不同操作
- 正面三角形：递增模板值
- 背面三角形：递减模板值
- 缠绕数非零的像素在路径内部

#### gWindColorPass

**用途：** 缠绕规则颜色遍（正常填充）

```cpp
static constexpr GrUserStencilSettings gWindColorPass(
    GrUserStencilSettings::StaticInit<
        0x0000,                           // 参考值：0
        GrUserStencilTest::kLessIfInClip, // 测试："0 < 模板"（等价于"0 != 模板"）
        0xffff,                           // 掩码
        GrUserStencilOp::kZero,           // 通过操作：清零
        GrUserStencilOp::kZero,           // 失败操作：清零
        0xffff                            // 写入掩码
    >()
);
```

**工作原理：**
- 使用 `kLessIfInClip` 测试，当模板值非零时通过
- "0 < stencil" 等价于 "0 != stencil"（因为模板值可正可负）

#### gInvWindColorPass

**用途：** 缠绕规则颜色遍（反向填充）

```cpp
static constexpr GrUserStencilSettings gInvWindColorPass(
    GrUserStencilSettings::StaticInit<
        0x0000,                            // 参考值：0
        GrUserStencilTest::kEqualIfInClip, // 测试：等于 0（在裁剪内）
        0xffff,                            // 掩码
        GrUserStencilOp::kZero,            // 通过操作：清零
        GrUserStencilOp::kZero,            // 失败操作：清零
        0xffff                             // 写入掩码
    >()
);
```

### 直接模板渲染

#### gDirectToStencil

**用途：** 直接渲染到模板缓冲区

```cpp
static constexpr GrUserStencilSettings gDirectToStencil(
    GrUserStencilSettings::StaticInit<
        0x0000,                           // 参考值：0
        GrUserStencilTest::kAlwaysIfInClip, // 测试：总是通过（在裁剪内）
        0xffff,                           // 掩码
        GrUserStencilOp::kZero,           // 通过操作：清零
        GrUserStencilOp::kIncMaybeClamp,  // 失败操作：递增（可能钳位）
        0xffff                            // 写入掩码
    >()
);
```

**使用场景：**
- 某些情况下，可以直接将路径绘制到模板缓冲区
- 无需先解析内部/外部
- 用于特定类型的路径渲染器

## 内部实现细节

### 模板算法原理

**偶奇规则：**
1. 初始化模板为 0
2. 对路径的每条边进行光栅化，每次反转穿过的像素的模板位
3. 最终模板值非零的像素在路径内部

**非零缠绕规则：**
1. 初始化模板为 0
2. 对路径的正面三角形递增模板，背面三角形递减模板
3. 最终缠绕数（模板值）非零的像素在路径内部

### 模板操作选择

**kInvert vs kIncWrap/kDecWrap：**
- 偶奇规则使用 `kInvert`（XOR 操作）
- 缠绕规则使用 `kIncWrap` 和 `kDecWrap`（加减操作）

**kZero：**
- 在颜色遍后清零模板
- 确保模板缓冲区处于清洁状态
- 遵循 Skia 的约定（用户位清除）

### 裁剪集成

**IfInClip 后缀：**
- `kAlwaysIfInClip`：总是通过，但只在裁剪内
- `kEqualIfInClip`：值相等且在裁剪内才通过
- `kLessIfInClip`：值小于参考值且在裁剪内才通过

这些测试确保了模板操作尊重裁剪区域。

### 参考值和掩码

**全 1 掩码（0xffff）：**
- 使用所有模板位
- 最大灵活性

**参考值 0：**
- 颜色遍通常测试"是否非零"
- 0 是自然的参考点

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrUserStencilSettings` | 模板设置基类和实用工具 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `PathRenderer` 实现 | 各种路径渲染器 |
| `PathStencilCoverOp` | 路径模板覆盖操作 |
| `PathInnerTriangulateOp` | 路径内部三角化操作 |
| 其他路径操作 | 需要模板填充的操作 |

## 设计模式与设计决策

### 编译时常量

所有模板设置都是 `constexpr`：
- 零运行时开销
- 编译器可以完全优化
- 类型安全

### 命名约定

**前缀：**
- `g`：全局/静态
- `EO`：Even-Odd（偶奇）
- `Wind`：Winding（缠绕）
- `Inv`：Inverse（反向）

**后缀：**
- `StencilPass`：模板遍
- `ColorPass`：颜色遍

### 分离的正反面操作

```cpp
StaticInitSeparate<...>
```
允许对三角形的正面和背面使用不同的模板操作，这对缠绕规则至关重要。

### 清理协议

所有颜色遍都在通过时清零模板：
```cpp
GrUserStencilOp::kZero
```
确保模板缓冲区在操作后处于已知状态。

## 性能考量

### 最小化模板更新

只有在必要时才使用模板：
- 简单矩形可能不需要模板
- 复杂路径需要完整的两遍算法

### 模板位使用

使用全部 16 位模板（0xffff 掩码）：
- 最大范围，减少环绕问题
- 支持复杂的嵌套和重叠

### 裁剪优化

通过 `IfInClip` 测试集成裁剪：
- 避免额外的裁剪遍
- 减少模板更新次数

### 硬件兼容性

这些设置兼容所有主流 GPU：
- 使用标准模板操作
- 不依赖扩展功能
- 经过广泛测试

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `GrUserStencilSettings.h` | 基础 | 模板设置基类 |
| `PathStencilCoverOp.cpp` | 使用者 | 使用这些设置 |
| `PathInnerTriangulateOp.cpp` | 使用者 | 使用这些设置 |
| `GrPathTessellationShader.h` | 使用者 | 访问模板设置 |
| `PathRenderer.h` | 使用者 | 路径渲染基类 |
