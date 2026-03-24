# GrModulateAtlasCoverageEffect

> 源文件: src/gpu/ganesh/effects/GrModulateAtlasCoverageEffect.h, src/gpu/ganesh/effects/GrModulateAtlasCoverageEffect.cpp

## 概述

`GrModulateAtlasCoverageEffect` 是 Ganesh GPU 后端中用于实现图集（Atlas）覆盖率调制的片段处理器。该效果将输入颜色与存储在纹理图集中的覆盖率值相乘，支持反转覆盖率和边界检查等可选功能。这是一个专门用于路径渲染优化的核心组件，通过将路径的覆盖信息预先存储在图集纹理中，避免在每次渲染时重复计算复杂的几何覆盖关系。

该效果主要用于基于图集的路径渲染技术，特别是在曲面细分（tessellation）路径中。通过将覆盖率信息缓存到纹理图集，可以显著提升重复渲染相同路径的性能。支持的关键特性包括覆盖率反转（用于镂空效果）和边界裁剪（确保采样在有效区域内）。

## 架构位置

`GrModulateAtlasCoverageEffect` 位于 Skia 的 GPU 渲染架构中的效果处理层：

- **层级**: GPU 渲染后端 -> Ganesh 引擎 -> 片段处理器
- **模块**: `src/gpu/ganesh/effects/`
- **功能定位**: 作为片段处理器（Fragment Processor），专门处理基于图集的覆盖率调制
- **渲染管线位置**: 片段着色阶段，用于将图集覆盖率应用到输入颜色
- **应用场景**: 主要用于曲面细分路径渲染系统

该模块继承自 `GrFragmentProcessor` 基类，集成了纹理采样（通过 `GrTextureEffect`）和自定义着色器逻辑。

## 主要类与结构体

### GrModulateAtlasCoverageEffect 类

**继承关系**:
```
GrFragmentProcessor (基类)
    └── GrModulateAtlasCoverageEffect
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fFlags` | `Flags` (枚举) | 控制效果行为的标志位 |
| `fBounds` | `SkIRect` | 设备坐标系中路径的有效边界（仅在 kCheckBounds 时使用） |

### Flags 枚举

位标志枚举，用于控制效果的可选行为：

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| `kNone` | 0 | 无特殊行为 |
| `kInvertCoverage` | 1 << 0 | 反转覆盖率，返回 inputColor * (1 - atlasCoverage) |
| `kCheckBounds` | 1 << 1 | 检查边界，超出有效区域时将覆盖率设为 0 |

### 内部 Impl 类

嵌套在 `onMakeProgramImpl` 方法中的实现类，负责生成实际的着色器代码：

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fBoundsUniform` | `UniformHandle` | 边界矩形的 Uniform 句柄 |
| `fCoverageMaybeInvertUniform` | `UniformHandle` | 覆盖率反转参数的 Uniform 句柄 |

## 公共 API 函数

### 构造函数

```cpp
GrModulateAtlasCoverageEffect(Flags flags,
                              std::unique_ptr<GrFragmentProcessor> inputFP,
                              GrSurfaceProxyView atlasView,
                              const SkMatrix& devToAtlasMatrix,
                              const SkIRect& devIBounds);
```

**功能**: 创建一个图集覆盖率调制效果。

**参数说明**:
- `flags`: 控制反转和边界检查的标志位
- `inputFP`: 输入的片段处理器，其输出将与覆盖率相乘
- `atlasView`: 包含覆盖率信息的图集纹理视图
- `devToAtlasMatrix`: 从设备坐标到图集纹理坐标的变换矩阵
- `devIBounds`: 设备坐标系中的有效边界（用于边界检查）

**初始化行为**:
- 注册输入片段处理器为第一个子处理器（索引 0）
- 创建并注册纹理采样效果为第二个子处理器（索引 1）
- 设置优化标志 `kCompatibleWithCoverageAsAlpha_OptimizationFlag`
- 仅在启用 `kCheckBounds` 时存储边界信息

### 拷贝构造函数

```cpp
GrModulateAtlasCoverageEffect(const GrModulateAtlasCoverageEffect& that);
```

**功能**: 创建效果的副本，用于克隆操作。

### name

```cpp
const char* name() const override;
```

**返回**: 字符串 `"GrModulateAtlasCoverageFP"`，用于调试和日志。

### clone

```cpp
std::unique_ptr<GrFragmentProcessor> clone() const override;
```

**功能**: 创建当前效果的深拷贝。

## 内部实现细节

### 着色器代码生成

`Impl::emitCode` 方法生成的着色器逻辑：

1. **初始化覆盖率**: 将 `coverage` 初始化为 0
2. **边界检查**（可选）:
   ```glsl
   if (all(greaterThan(sk_FragCoord.xy, bounds.xy)) &&
       all(lessThan(sk_FragCoord.xy, bounds.zw)))
   ```
3. **图集采样**: 使用 `sk_FragCoord.xy` 从图集纹理采样，获取 alpha 通道作为覆盖率
4. **反转处理**: 使用线性公式 `coverage = coverage * x + y`
   - 不反转: `x=1, y=0` → `coverage`
   - 反转: `x=-1, y=1` → `1 - coverage`
5. **颜色调制**: 返回 `inputColor * coverage`

### 子处理器注册

```cpp
this->registerChild(std::move(inputFP));  // 索引 0
this->registerChild(GrTextureEffect::Make(...),
                    SkSL::SampleUsage::Explicit());  // 索引 1
```

- **索引 0**: 输入片段处理器，使用默认采样（继承父坐标）
- **索引 1**: 纹理效果，使用显式采样（通过 `sk_FragCoord.xy`）

### Uniform 数据管理

`Impl::onSetData` 方法在渲染时设置 Uniform 值：

```cpp
// 边界检查
if (fp.fFlags & Flags::kCheckBounds) {
    pdman.set4fv(fBoundsUniform, 1, SkRect::Make(fp.fBounds).asScalars());
}

// 覆盖率反转
if (fp.fFlags & Flags::kInvertCoverage) {
    pdman.set2f(fCoverageMaybeInvertUniform, -1, 1);  // 1 - coverage
} else {
    pdman.set2f(fCoverageMaybeInvertUniform, 1, 0);   // coverage
}
```

### 着色器键生成

`onAddToKey` 方法仅添加 `kCheckBounds` 标志到着色器键：

```cpp
b->add32(fFlags & Flags::kCheckBounds);
```

这意味着是否反转覆盖率不影响着色器编译，而是通过 Uniform 动态控制。

## 依赖关系

### 依赖的模块

| 模块 | 类型 | 用途 |
|------|------|------|
| `GrFragmentProcessor` | Ganesh 核心类 | 基类，提供片段处理器框架 |
| `GrTextureEffect` | Ganesh 效果 | 从图集纹理采样覆盖率 |
| `GrSurfaceProxyView` | Ganesh 纹理系统 | 表示图集纹理视图 |
| `SkMatrix` | Skia 核心 | 坐标变换矩阵 |
| `SkIRect` | Skia 核心 | 整数矩形，表示边界 |
| `GrSamplerState` | Ganesh 采样 | 纹理采样参数（最近邻过滤） |
| `GrGLSLFragmentShaderBuilder` | GLSL 生成 | 构建片段着色器代码 |
| `GrGLSLProgramDataManager` | GLSL 运行时 | 管理 Uniform 数据 |

### 被依赖的模块

| 模块 | 关系 | 用途 |
|------|------|------|
| 曲面细分路径渲染器 | 主要使用者 | 将路径覆盖率存储在图集中渲染 |
| GPU 操作生成器 | 效果链 | 将该效果加入渲染管线 |
| 路径缓存系统 | 图集管理 | 管理图集纹理的分配和更新 |
| 抗锯齿路径渲染 | 应用场景 | 使用图集存储平滑覆盖率 |

## 设计模式与设计决策

### 片段处理器模式

继承 `GrFragmentProcessor` 并实现标准接口：
- **统一框架**: 与其他效果无缝集成
- **子处理器链**: 支持效果组合和嵌套
- **着色器生成**: 通过 `ProgramImpl` 分离接口与实现

### 位标志设计

使用位标志 `Flags` 控制可选功能：
- **灵活组合**: 可以同时启用反转和边界检查
- **内存高效**: 单个整数存储多个布尔选项
- **可扩展**: 可以轻松添加新标志位

### 延迟着色器编译

仅将影响着色器代码的标志加入键（`kCheckBounds`）：
- **着色器重用**: `kInvertCoverage` 通过 Uniform 控制，不产生新着色器变体
- **减少编译**: 降低着色器程序的组合爆炸问题
- **运行时切换**: 可以动态切换反转模式而不重新编译

### 显式采样策略

纹理子处理器使用显式采样 `SkSL::SampleUsage::Explicit()`：
- **坐标独立**: 直接使用 `sk_FragCoord.xy` 而非继承父坐标
- **图集映射**: 通过 `devToAtlasMatrix` 将设备坐标映射到纹理空间
- **精确对齐**: 确保采样位置与实际像素位置一致

### 优化标志

设置 `kCompatibleWithCoverageAsAlpha_OptimizationFlag`：
- **混合优化**: 表示该效果可以与覆盖率混合兼容
- **渲染优化**: 允许渲染管线进行特定优化

## 性能考量

### 图集纹理访问

- **缓存友好**: 使用最近邻过滤（`kNearest`），避免多次纹理读取
- **带宽优化**: 仅读取单通道（alpha），减少内存带宽
- **对齐访问**: 使用整数像素坐标，利用纹理缓存

### 边界检查开销

- **条件分支**: `if` 语句可能导致 GPU 线程分支
- **优化建议**: 仅在必要时启用 `kCheckBounds`
- **替代方案**: 可以通过图集布局避免边界检查

### Uniform 更新成本

- **动态反转**: 通过 Uniform 而非着色器变体实现反转
- **CPU 开销**: 每次绘制调用需要更新 Uniform
- **trade-off**: CPU 侧少量开销换取 GPU 侧着色器编译减少

### 子处理器调用

- **两次子调用**: 调用输入处理器和纹理效果
- **内联优化**: 着色器编译器可能内联简单子处理器
- **寄存器压力**: 需要存储中间结果（inputColor, atlasCoverage）

### 线性反转公式

使用 `coverage * x + y` 统一处理反转和不反转：
- **避免分支**: GPU 执行线性计算比分支快
- **SIMD 友好**: 适合向量化执行
- **寄存器占用**: 仅需一个额外的 float2 Uniform

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/GrFragmentProcessor.h` | 基类 | 片段处理器基类 |
| `src/gpu/ganesh/effects/GrTextureEffect.h` | 依赖 | 纹理采样效果 |
| `src/gpu/ganesh/GrSurfaceProxyView.h` | 依赖 | 纹理视图封装 |
| `src/gpu/ganesh/GrSamplerState.h` | 依赖 | 纹理采样状态 |
| `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h` | 依赖 | 着色器代码生成 |
| `src/gpu/ganesh/tessellate/` | 上层使用 | 曲面细分路径渲染系统 |
| `include/core/SkMatrix.h` | 依赖 | 坐标变换矩阵 |
| `include/core/SkRect.h` | 依赖 | 矩形边界表示 |
| `src/gpu/KeyBuilder.h` | 依赖 | 着色器键构建 |
