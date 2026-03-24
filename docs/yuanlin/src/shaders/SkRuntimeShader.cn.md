# SkRuntimeShader

> 源文件
> - src/shaders/SkRuntimeShader.h
> - src/shaders/SkRuntimeShader.cpp

## 概述

`SkRuntimeShader` 是 Skia 运行时着色器系统的核心实现,它允许在运行时编译和执行自定义的 SkSL (Skia Shading Language) 着色器代码。与预编译的着色器不同,运行时着色器提供了动态灵活性,使开发者能够在不重新编译应用程序的情况下创建和修改着色器效果。

该着色器通过 `SkRuntimeEffect` 管理 SkSL 代码的编译和执行,支持自定义 uniform 变量、子着色器、调试追踪等高级功能。它是实现复杂视觉效果和着色器实验的强大工具,广泛应用于图形渲染、特效处理和可视化开发中。

## 架构位置

`SkRuntimeShader` 位于 Skia 的着色器模块中:

- **模块路径**: `src/shaders/`
- **基类**: `SkShaderBase`
- **核心依赖**: `SkRuntimeEffect` (SkSL 效果管理器)
- **角色**: 将 SkSL 代码转换为可执行的着色器

在着色器系统的层次结构中:
```
SkShader (公共接口)
    ↓
SkShaderBase (内部基类)
    ↓
SkRuntimeShader (运行时着色器实现)
    ↓
SkRuntimeEffect (SkSL 编译器和执行器)
    ↓
SkSL::RP::Program (光栅管线程序)
```

## 主要类与结构体

### SkRuntimeShader

运行时着色器的主要实现类。

**核心成员**:
```cpp
sk_sp<SkRuntimeEffect> fEffect;           // 编译后的 SkSL 效果
sk_sp<SkSL::DebugTracePriv> fDebugTrace;  // 调试追踪信息
sk_sp<const SkData> fUniformData;         // uniform 数据(固定)
UniformsCallback fUniformsCallback;       // uniform 回调(动态)
std::vector<SkRuntimeEffect::ChildPtr> fChildren;  // 子效果(着色器/颜色过滤器)
```

**主要方法**:
- 构造函数(两个重载版本):
  - `SkRuntimeShader(effect, debugTrace, uniforms, children)` - 固定 uniform
  - `SkRuntimeShader(effect, debugTrace, uniformsCallback, children)` - 动态 uniform
- `bool appendStages()`: 将着色器添加到光栅管线
- `void flatten()`: 序列化着色器
- `SkRuntimeEffect::TracedShader makeTracedClone()`: 创建可调试的克隆

### UniformsCallback

动态 uniform 回调函数类型:
```cpp
using UniformsCallback = SkRuntimeEffectPriv::UniformsCallback;
```

允许每次绘制时动态生成 uniform 数据,用于动画和交互效果。

### RuntimeEffectRPCallbacks

光栅管线回调类,处理着色器的子效果和采样。

### SkRuntimeEffect::TracedShader

调试用结构体,包含:
- 着色器实例
- 调试追踪信息

## 公共 API 函数

### 构造函数 (固定 Uniforms)

```cpp
SkRuntimeShader(sk_sp<SkRuntimeEffect> effect,
                sk_sp<SkSL::DebugTracePriv> debugTrace,
                sk_sp<const SkData> uniforms,
                SkSpan<const SkRuntimeEffect::ChildPtr> children)
```

创建具有固定 uniform 数据的运行时着色器。

**参数**:
- `effect`: 编译后的 SkSL 效果
- `debugTrace`: 调试追踪对象(可为空)
- `uniforms`: uniform 变量数据
- `children`: 子效果数组(子着色器或颜色过滤器)

**使用场景**: 静态效果,uniform 值在创建时确定

### 构造函数 (动态 Uniforms)

```cpp
SkRuntimeShader(sk_sp<SkRuntimeEffect> effect,
                sk_sp<SkSL::DebugTracePriv> debugTrace,
                UniformsCallback uniformsCallback,
                SkSpan<const SkRuntimeEffect::ChildPtr> children)
```

创建具有动态 uniform 回调的运行时着色器。

**参数**:
- `uniformsCallback`: 每次绘制时调用以生成 uniform 数据

**使用场景**: 动画效果,需要每帧更新 uniform 值

### makeTracedClone()

```cpp
SkRuntimeEffect::TracedShader makeTracedClone(const SkIPoint& coord)
```

创建用于调试的着色器克隆,可以追踪特定像素的着色过程。

**参数**:
- `coord`: 要追踪的像素坐标

**返回值**: 包含调试着色器和追踪信息的结构体

**实现原理**:
1. 创建未优化的效果克隆
2. 设置调试追踪对象,记录源代码和追踪坐标
3. 创建新的着色器实例

### isOpaque()

```cpp
bool isOpaque() const override
```

检查着色器是否始终产生不透明颜色。

**实现**: 委托给 `fEffect->alwaysOpaque()`

### uniformData()

```cpp
sk_sp<const SkData> uniformData(const SkColorSpace* dstCS) const
```

获取 uniform 数据。

**参数**:
- `dstCS`: 目标色彩空间(用于色彩相关的 uniform 转换)

**返回值**: uniform 数据的智能指针

**行为**:
- 如果有固定数据 (`fUniformData`),直接返回
- 否则调用 `fUniformsCallback` 动态生成

## 内部实现细节

### appendStages() 实现

核心方法,将 SkSL 着色器转换为光栅管线阶段:

```cpp
bool appendStages(const SkStageRec& rec, const SkShaders::MatrixRec& mRec) const
```

**实现流程**:

1. **能力检查**:
   ```cpp
   if (!SkRuntimeEffectPriv::CanDraw(SkCapabilities::RasterBackend().get(), fEffect.get())) {
       return false;
   }
   ```
   验证光栅后端是否支持该效果(目前限制为 SkSL #version 100)。

2. **获取 RP 程序**:
   ```cpp
   if (const SkSL::RP::Program* program = fEffect->getRPProgram(fDebugTrace.get())) {
       // ...
   }
   ```
   从效果中获取编译后的光栅管线程序。

3. **应用矩阵**:
   ```cpp
   std::optional<SkShaders::MatrixRec> newMRec = mRec.apply(rec);
   if (!newMRec.has_value()) {
       return false;
   }
   ```

4. **准备 Uniforms**:
   ```cpp
   SkSpan<const float> uniforms =
       SkRuntimeEffectPriv::UniformsAsSpan(fEffect->uniforms(),
                                           this->uniformData(rec.fDstCS),
                                           /*alwaysCopyIntoAlloc=*/fUniformData == nullptr,
                                           rec.fDstCS,
                                           rec.fAlloc);
   ```
   转换 uniform 数据为 float 数组,如果是动态 uniform 则强制复制到分配器。

5. **设置回调并追加阶段**:
   ```cpp
   RuntimeEffectRPCallbacks callbacks(rec, *newMRec, fChildren, fEffect->fSampleUsages);
   bool success = program->appendStages(rec.fPipeline, rec.fAlloc, &callbacks, uniforms);
   ```

### 序列化实现

**写入 (flatten)**:
```cpp
void flatten(SkWriteBuffer& buffer) const
```

序列化策略:

1. **效果标识**:
   - 如果是 Skia 内置效果,写入稳定密钥
   - 否则写入 0 和完整的 SkSL 源代码

2. **Uniform 数据**: 序列化 uniform 数据字节数组

3. **子效果**: 递归序列化所有子着色器和颜色过滤器

**读取 (CreateProc)**:
```cpp
sk_sp<SkFlattenable> SkRuntimeShader::CreateProc(SkReadBuffer& buffer)
```

反序列化流程:

1. **权限检查**:
   ```cpp
   if (!buffer.validate(buffer.allowSkSL())) {
       return nullptr;
   }
   ```
   验证是否允许加载 SkSL 代码(安全措施)。

2. **效果重建**:
   - 尝试通过稳定密钥加载内置效果
   - 否则编译 SkSL 源代码
   - 使用缓存避免重复编译

3. **宽松反序列化** (调试器模式):
   ```cpp
   if constexpr (kLenientSkSLDeserialization) {
       if (!effect) {
           // 失败时尝试使用子着色器作为后备
       }
   }
   ```

4. **读取数据**:
   - Uniform 数据
   - 旧版本的本地矩阵(如果存在)
   - 子效果

5. **创建着色器**:
   ```cpp
   return effect->makeShader(std::move(uniforms), SkSpan(children), SkOptAddressOrNull(localM));
   ```

### 调试追踪机制

```cpp
SkRuntimeEffect::TracedShader SkRuntimeShader::makeTracedClone(const SkIPoint& coord)
```

调试功能实现:

1. **未优化克隆**: 创建未经优化的效果版本,保留所有调试信息
2. **追踪对象**: 设置源代码和追踪坐标
3. **调试着色器**: 创建具有追踪功能的着色器实例

这允许开发者检查特定像素的着色过程,查看变量值和执行路径。

### 版本兼容性处理

代码中处理多个版本差异:

1. **稳定密钥序列化** (`kSerializeStableKeys`):
   - 新版本:先尝试读取稳定密钥
   - 旧版本:直接读取 SkSL 源代码

2. **本地矩阵移除** (`kNoShaderLocalMatrix`):
   - 旧版本:读取并应用本地矩阵标志
   - 新版本:矩阵在外部处理

### 动态 vs 静态 Uniforms

两种 uniform 管理模式:

**静态模式** (`fUniformData`):
- 构造时传入数据
- 多次绘制使用相同值
- 高效,无额外开销

**动态模式** (`fUniformsCallback`):
- 每次绘制时调用回调
- 支持动画和交互
- 略有回调开销,但强制复制到分配器中以保证数据生命周期

## 依赖关系

### 直接依赖

- **SkRuntimeEffect**: SkSL 编译和执行管理
- **SkSL::RP::Program**: 光栅管线程序
- **SkSL::DebugTracePriv**: 调试追踪
- **SkData**: 数据容器(uniforms)
- **SkShaderBase**: 着色器基类
- **SkRuntimeEffectPriv**: 运行时效果私有工具
- **SkKnownRuntimeEffects**: 内置效果管理

### 子系统集成

- **SkSL 编译器**: 编译 SkSL 源代码
- **光栅管线**: 执行着色计算
- **序列化系统**: SKP 文件支持
- **色彩管理**: Uniform 色彩空间转换

### 被依赖关系

- **SkRuntimeEffect**: 通过 `makeShader()` 创建实例
- **用户代码**: 通过 `SkRuntimeEffect::MakeForShader()` 间接使用

## 设计模式与设计决策

### 策略模式

使用两种 uniform 管理策略:
- 固定数据策略
- 回调策略

通过 `uniformData()` 方法统一访问,隐藏差异。

### 桥接模式

`SkRuntimeShader` 作为桥接:
- **抽象侧**: Skia 着色器接口 (`SkShaderBase`)
- **实现侧**: SkSL 编译器和光栅管线

### 工厂模式

不直接构造,通过 `SkRuntimeEffect::makeShader()` 创建:
- 验证参数匹配
- 管理效果生命周期
- 提供统一接口

### 原型模式

`makeTracedClone()` 实现原型模式:
- 克隆着色器用于调试
- 创建未优化版本
- 共享部分数据(children)

### 安全性设计

多层安全检查:
1. **权限检查**: `buffer.allowSkSL()` 控制是否允许加载 SkSL
2. **能力检查**: `CanDraw()` 验证后端支持
3. **版本检查**: 处理不同 SKP 版本的兼容性

### 宽松 vs 严格模式

调试器构建使用宽松反序列化:
- 失败时尝试后备方案
- 允许部分功能降级
- 提供诊断信息

发布构建使用严格验证:
- 失败立即返回 `nullptr`
- 保证行为一致性

## 性能考量

### SkSL 编译缓存

使用 `SkMakeCachedRuntimeEffect()`:
- 避免重复编译相同代码
- 跨实例共享编译结果
- 减少启动时间

### Uniform 数据处理

**固定 uniform**:
- 零拷贝,直接使用 `fUniformData`
- 多次绘制无额外开销

**动态 uniform**:
- 每次绘制调用回调
- 强制复制到分配器(`alwaysCopyIntoAlloc=true`)
- 确保数据在管线执行期间有效

### 光栅管线集成

- 将 SkSL 编译为高效的 RP 操作
- 支持 SIMD 优化
- 最小化解释开销

### 稳定密钥优化

Skia 内置效果使用稳定密钥:
- 不序列化源代码,节省空间
- 快速查找,无需编译
- 确保跨版本兼容性

### 调试模式权衡

调试功能有开销:
- 未优化克隆禁用优化
- 追踪记录增加内存使用
- 仅在需要时创建

## 相关文件

### 核心依赖
- `include/effects/SkRuntimeEffect.h` - 运行时效果公共接口
- `src/core/SkRuntimeEffectPriv.h` - 运行时效果私有工具
- `src/shaders/SkShaderBase.h` - 着色器基类
- `src/core/SkKnownRuntimeEffects.h` - 内置效果管理

### SkSL 子系统
- `src/sksl/codegen/SkSLRasterPipelineBuilder.h` - RP 代码生成
- `src/sksl/tracing/SkSLDebugTracePriv.h` - 调试追踪实现
- `include/sksl/SkSLDebugTrace.h` - 调试追踪接口
- `include/private/SkSLSampleUsage.h` - 采样使用分析

### 数据与序列化
- `include/core/SkData.h` - 数据容器
- `src/core/SkReadBuffer.h` - 反序列化
- `src/core/SkWriteBuffer.h` - 序列化
- `src/core/SkPicturePriv.h` - SKP 版本管理

### 光栅管线
- `src/core/SkRasterPipeline.h` - 光栅管线核心
- `src/core/SkEffectPriv.h` - 效果私有工具

### 其他依赖
- `include/core/SkCapabilities.h` - 能力查询
- `include/core/SkColorSpace.h` - 色彩空间
- `src/base/SkTLazy.h` - 惰性初始化工具
- `include/private/base/SkTArray.h` - 动态数组
