# GrMatrixEffect

> 源文件: src/gpu/ganesh/effects/GrMatrixEffect.h, src/gpu/ganesh/effects/GrMatrixEffect.cpp

## 概述

`GrMatrixEffect` 是 Ganesh GPU 后端中用于对子片段处理器的采样坐标应用矩阵变换的片段处理器。它是一个装饰器模式的实现，包装一个子处理器并在采样时对坐标进行变换。这是实现各种坐标空间变换效果的基础设施，包括平移、旋转、缩放、透视等变换。

该模块的设计核心是提供一种通用的、可组合的方式来修改片段处理器的采样坐标。通过矩阵变换，可以实现纹理映射、效果偏移、图像畸变等多种效果。特别值得注意的是，该模块实现了智能的矩阵合并优化，当多个 `GrMatrixEffect` 嵌套时会自动合并矩阵，避免重复变换的开销。

## 架构位置

`GrMatrixEffect` 位于 Skia GPU 渲染架构的片段处理器层：

- **层级**: GPU 渲染后端 -> Ganesh 引擎 -> 片段处理器
- **模块**: `src/gpu/ganesh/effects/`
- **功能定位**: 坐标变换装饰器，修改子处理器的采样坐标
- **渲染管线位置**: 片段着色阶段，影响子处理器的坐标计算
- **设计模式**: 装饰器模式，包装并增强子处理器功能

该模块是 Ganesh 片段处理器系统中的基础设施组件，被广泛用于实现各种需要坐标变换的效果。

## 主要类与结构体

### GrMatrixEffect 类

**继承关系**:
```
GrFragmentProcessor (基类)
    └── GrMatrixEffect
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fMatrix` | `SkMatrix` | 应用于采样坐标的 3x3 变换矩阵 |

**优化标志**:
- 继承子处理器的优化标志（通过 `ProcessorOptimizationFlags(child.get())`）
- 不添加额外的优化或限制

### Impl 内部类

嵌套在 `onMakeProgramImpl` 方法中的着色器实现类：

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fMatrixVar` | `UniformHandle` | 矩阵变换的 Uniform 句柄 |

**关键方法**:
- `emitCode`: 生成着色器代码，调用子处理器时应用矩阵变换
- `onSetData`: 设置矩阵 Uniform 数据，处理纹理效果的坐标调整

## 公共 API 函数

### Make 工厂函数

```cpp
static std::unique_ptr<GrFragmentProcessor> Make(
    const SkMatrix& matrix,
    std::unique_ptr<GrFragmentProcessor> child);
```

**功能**: 创建一个对子处理器应用矩阵变换的片段处理器。

**参数说明**:
- `matrix`: 要应用的 3x3 变换矩阵（支持透视）
- `child`: 子片段处理器，将对其采样坐标应用变换

**返回值**: 返回新创建的 `GrMatrixEffect` 或优化后的子处理器

**智能优化逻辑**:

1. **矩阵合并优化**: 如果子处理器本身就是 `GrMatrixEffect`，则尝试合并矩阵
   ```cpp
   if (child->classID() == kGrMatrixEffect_ClassID) {
       auto me = static_cast<GrMatrixEffect*>(child.get());
       // 检查透视兼容性
       if (me->fMatrix.hasPerspective() || !matrix.hasPerspective()) {
           me->fMatrix.preConcat(matrix);  // 合并矩阵
           return child;  // 返回优化后的子处理器
       }
   }
   ```

2. **透视限制**: 如果原矩阵无透视但新矩阵有透视，无法合并（因为采样模式已记录）

3. **新建处理器**: 无法优化时创建新的 `GrMatrixEffect`

**使用场景**:
- 对纹理应用变换
- 实现效果偏移或旋转
- 组合多个坐标变换

### name

```cpp
const char* name() const override { return "MatrixEffect"; }
```

**返回**: 字符串 `"MatrixEffect"`，用于调试和日志。

### clone

```cpp
std::unique_ptr<GrFragmentProcessor> clone() const override;
```

**功能**: 创建当前效果的深拷贝，包括矩阵和子处理器。

### constantOutputForConstantInput

```cpp
SkPMColor4f constantOutputForConstantInput(const SkPMColor4f& inputColor) const override;
```

**功能**: 对于常量输入，委托给子处理器计算输出。

**实现**: 直接调用 `ConstantOutputForConstantInput(this->childProcessor(0), inputColor)`

**意义**: 矩阵变换不改变颜色值，仅改变采样位置

## 内部实现细节

### 子处理器注册

构造函数中注册子处理器时指定采样模式：

```cpp
this->registerChild(std::move(child),
                    SkSL::SampleUsage::UniformMatrix(matrix.hasPerspective()));
```

**采样模式**: `UniformMatrix` 表示使用 Uniform 存储的矩阵进行变换

**透视标记**: `matrix.hasPerspective()` 决定是否需要透视除法

### 着色器代码生成

`Impl::emitCode` 生成的着色器逻辑极其简单：

```cpp
void emitCode(EmitArgs& args) override {
    // 添加矩阵 Uniform
    fMatrixVar = args.fUniformHandler->addUniform(
        &args.fFp,
        kFragment_GrShaderFlag,
        SkSLType::kFloat3x3,
        SkSL::SampleUsage::MatrixUniformName());  // 标准名称 "matrix"

    // 调用子处理器时应用矩阵变换
    args.fFragBuilder->codeAppendf("return %s;\n",
        this->invokeChildWithMatrix(0, args).c_str());
}
```

**核心机制**: `invokeChildWithMatrix` 生成类似以下的 GLSL 代码：
```glsl
uniform float3x3 matrix;
// ...
return child_0(matrix * sk_FragCoord.xy);  // 实际会处理齐次坐标
```

### Uniform 数据设置

`Impl::onSetData` 处理矩阵数据的特殊逻辑：

```cpp
void onSetData(const GrGLSLProgramDataManager& pdman,
               const GrFragmentProcessor& proc) override {
    const GrMatrixEffect& mtx = proc.cast<GrMatrixEffect>();

    // 特殊处理纹理效果
    if (auto te = mtx.childProcessor(0)->asTextureEffect()) {
        SkMatrix m = te->coordAdjustmentMatrix();  // 获取纹理坐标调整矩阵
        m.preConcat(mtx.fMatrix);  // 与用户矩阵合并
        pdman.setSkMatrix(fMatrixVar, m);
    } else {
        pdman.setSkMatrix(fMatrixVar, mtx.fMatrix);
    }
}
```

**纹理坐标调整**: `GrTextureEffect` 可能有内部的坐标调整矩阵（如纹理翻转、子区域映射），需要与用户矩阵合并。

### 矩阵合并优化

`Make` 方法中的矩阵合并逻辑：

```cpp
me->fMatrix.preConcat(matrix);
```

使用 `preConcat` 而非 `postConcat`，意味着新矩阵在前（先应用）：
```
result = child_matrix * input_matrix * coord
```

**透视兼容性检查**:
```cpp
if (me->fMatrix.hasPerspective() || !matrix.hasPerspective()) {
    // 可以合并
}
```

- **已有透视**: 可以添加任何变换（包括新透视）
- **无透视但新增透视**: 无法合并，因为采样模式已记录为非透视

### 等价性判断

`onIsEqual` 方法仅比较矩阵：

```cpp
bool onIsEqual(const GrFragmentProcessor& other) const override {
    const GrMatrixEffect& that = other.cast<GrMatrixEffect>();
    return fMatrix == that.fMatrix;
}
```

**注意**: 不比较子处理器，因为基类会自动比较子处理器链。

### 着色器键生成

```cpp
void onAddToKey(const GrShaderCaps& caps, skgpu::KeyBuilder* b) const override {}
```

**空实现**: 矩阵数据通过 Uniform 传递，不影响着色器编译，因此不需要添加到着色器键。

**优势**: 相同的着色器可用于不同的矩阵，减少着色器变体数量。

## 依赖关系

### 依赖的模块

| 模块 | 类型 | 用途 |
|------|------|------|
| `GrFragmentProcessor` | Ganesh 核心 | 片段处理器基类 |
| `SkMatrix` | Skia 核心 | 3x3 变换矩阵 |
| `SkSL::SampleUsage` | SkSL 编译 | 采样模式描述 |
| `GrTextureEffect` | Ganesh 效果 | 纹理效果（特殊处理） |
| `GrGLSLFragmentShaderBuilder` | GLSL 生成 | 着色器代码构建 |
| `GrGLSLProgramDataManager` | GLSL 运行时 | Uniform 数据管理 |

### 被依赖的模块

| 模块 | 关系 | 用途 |
|------|------|------|
| 效果链构建器 | 上层使用 | 构建包含坐标变换的效果链 |
| 纹理映射 | 常见用途 | 对纹理应用变换 |
| 特效系统 | 应用场景 | 实现各种坐标变换特效 |
| 绘制操作 | 渲染管线 | 在绘制时应用坐标变换 |
| 图层合成 | 高级应用 | 图层变换和合成 |

## 设计模式与设计决策

### 装饰器模式

`GrMatrixEffect` 是典型的装饰器模式：

- **包装对象**: 包装任意子片段处理器
- **增强功能**: 添加坐标变换能力
- **透明传递**: 颜色处理完全委托给子处理器
- **可组合**: 支持多层嵌套（通过矩阵合并优化）

### 智能合并优化

自动检测并合并嵌套的 `GrMatrixEffect`：

- **减少层次**: 避免多层嵌套导致的性能损失
- **统一变换**: 将多个变换合并为单一矩阵乘法
- **保持等价**: 合并后结果与嵌套调用完全一致

### 延迟计算

矩阵通过 Uniform 传递，支持动态更新：

- **无重新编译**: 矩阵改变不需要重新编译着色器
- **批处理友好**: 可以在绘制循环中动态修改矩阵
- **内存高效**: 仅存储一个 3x3 矩阵（9 个浮点数）

### 纹理坐标特殊处理

识别并优化纹理效果的坐标调整：

- **合并调整矩阵**: 将纹理内部坐标调整与用户矩阵合并
- **减少运算**: 避免在着色器中进行两次矩阵乘法
- **透明优化**: 对用户完全透明，自动进行

### 透视感知

明确区分透视和非透视变换：

- **采样模式记录**: 在注册子处理器时记录是否有透视
- **合并限制**: 防止不兼容的透视变换合并
- **着色器优化**: 非透视情况可以使用更高效的 2D 变换

### 优化标志继承

```cpp
ProcessorOptimizationFlags(child.get())
```

继承子处理器的优化标志：

- **透明包装**: 不改变子处理器的优化特性
- **信息传递**: 将子处理器的能力传递给上层
- **正确性保证**: 确保优化决策基于实际处理器能力

## 性能考量

### 矩阵合并优化

- **减少变换次数**: 多个嵌套变换合并为一次
- **CPU 侧计算**: 合并在 CPU 侧完成，GPU 仅执行一次矩阵乘法
- **示例**: `MatrixEffect(A, MatrixEffect(B, child))` → `MatrixEffect(A*B, child)`

### 着色器变体控制

- **零变体**: 矩阵通过 Uniform 传递，不产生着色器变体
- **重用着色器**: 不同的矩阵值可以共享同一个编译好的着色器
- **减少编译**: 大幅减少着色器编译时间和内存占用

### GPU 指令开销

- **矩阵乘法**: 3x3 矩阵乘以 3D 齐次坐标（约 9 次乘法 + 6 次加法）
- **透视除法**: 如果有透视，需要额外的除法操作
- **寄存器占用**: 矩阵占用 3 个 float3（9 个寄存器），加上临时变量

### Uniform 更新成本

- **CPU 侧开销**: 每次绘制调用设置 9 个浮点数
- **纹理效果优化**: CPU 侧合并矩阵，减少 GPU 计算
- **缓存友好**: 连续的浮点数数组，缓存访问高效

### 内存占用

- **处理器对象**: 除基类外，仅一个 `SkMatrix`（约 36 字节）
- **Uniform 数据**: 每个绘制调用 36 字节（9 个 float）
- **着色器代码**: 固定大小，不随矩阵变化

### 坐标变换精度

- **浮点精度**: 使用 float 类型，精度约 7 位有效数字
- **累积误差**: 多次变换可能累积误差（但通过合并优化减轻）
- **透视陷阱**: 透视变换接近奇异点时精度下降

### 批处理影响

- **Uniform 变化**: 矩阵改变会打断批处理
- **优化建议**: 尽量将相同矩阵的绘制操作分组
- **动态批处理**: 某些后端可能支持动态 Uniform 更新而不打断批处理

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/GrFragmentProcessor.h` | 基类 | 片段处理器基类，提供子处理器机制 |
| `include/core/SkMatrix.h` | 依赖 | 3x3 变换矩阵定义 |
| `include/private/SkSLSampleUsage.h` | 依赖 | 采样模式枚举和工具 |
| `src/gpu/ganesh/effects/GrTextureEffect.h` | 相关 | 纹理效果，特殊处理目标 |
| `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h` | 依赖 | 着色器代码生成 |
| `src/gpu/ganesh/glsl/GrGLSLProgramDataManager.h` | 依赖 | Uniform 数据管理 |
| `src/gpu/ganesh/GrPaint.h` | 上层使用 | 绘制参数可能包含矩阵效果 |
| `src/gpu/ganesh/GrProcessorAnalysis.h` | 分析工具 | 效果链分析 |
