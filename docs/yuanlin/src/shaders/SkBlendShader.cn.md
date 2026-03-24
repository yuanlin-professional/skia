# SkBlendShader

> 源文件
> - src/shaders/SkBlendShader.h
> - src/shaders/SkBlendShader.cpp

## 概述

`SkBlendShader` 是 Skia 中用于混合两个着色器输出的组合着色器。它接受两个子着色器(源和目标)以及一个混合模式或混合器,然后在每个像素上应用指定的混合操作。这允许创建复杂的视觉效果,例如将纹理与渐变混合,或者实现自定义的着色器组合逻辑。

该着色器支持两种混合方式:使用内置的 `SkBlendMode` 枚举(如 `kMultiply`、`kScreen` 等),或使用自定义的 `SkBlender` 对象实现更复杂的混合逻辑。它在光栅管线中通过依次评估两个子着色器,然后应用混合操作来实现功能。

## 架构位置

`SkBlendShader` 位于 Skia 的着色器模块中:

- **模块路径**: `src/shaders/`
- **基类**: `SkShaderBase`
- **公共接口**: 通过 `SkShaders::Blend()` 工厂函数创建
- **设计模式**: 组合模式 (Composite Pattern)

在着色器系统的层次结构中,它作为组合节点:
```
SkShader (公共接口)
    ↓
SkShaderBase (内部基类)
    ↓
SkBlendShader (混合着色器)
    ├─ fDst (目标子着色器)
    ├─ fSrc (源子着色器)
    └─ fMode (混合模式)
```

## 主要类与结构体

### SkBlendShader

混合两个着色器的组合着色器。

**核心成员**:
```cpp
sk_sp<SkShader> fDst;   // 目标着色器(混合的"底层")
sk_sp<SkShader> fSrc;   // 源着色器(混合的"顶层")
SkBlendMode fMode;      // 混合模式
```

**主要方法**:
- `SkBlendShader(SkBlendMode mode, sk_sp<SkShader> dst, sk_sp<SkShader> src)`: 构造函数
- `ShaderType type()`: 返回 `ShaderType::kBlend`
- `sk_sp<SkShader> dst()`: 获取目标着色器
- `sk_sp<SkShader> src()`: 获取源着色器
- `SkBlendMode mode()`: 获取混合模式

### 工厂函数

```cpp
namespace SkShaders {
    sk_sp<SkShader> Blend(SkBlendMode mode, sk_sp<SkShader> dst, sk_sp<SkShader> src);
    sk_sp<SkShader> Blend(sk_sp<SkBlender> blender, sk_sp<SkShader> dst, sk_sp<SkShader> src);
}
```

## 公共 API 函数

### SkShaders::Blend(SkBlendMode)

```cpp
sk_sp<SkShader> Blend(SkBlendMode mode, sk_sp<SkShader> dst, sk_sp<SkShader> src)
```

使用内置混合模式创建混合着色器。

**参数**:
- `mode`: 混合模式,如 `kMultiply`、`kScreen`、`kOverlay` 等
- `dst`: 目标着色器(混合的底层)
- `src`: 源着色器(混合的顶层)

**返回值**:
- 成功时返回 `SkBlendShader` 智能指针
- 如果任一子着色器为空,返回 `nullptr`
- 某些模式会返回优化的结果

**优化逻辑**:
```cpp
switch (mode) {
    case SkBlendMode::kClear:
        return Color(0);  // 总是透明
    case SkBlendMode::kDst:
        return dst;       // 只显示目标
    case SkBlendMode::kSrc:
        return src;       // 只显示源
    default:
        break;
}
```

### SkShaders::Blend(SkBlender)

```cpp
sk_sp<SkShader> Blend(sk_sp<SkBlender> blender,
                      sk_sp<SkShader> dst,
                      sk_sp<SkShader> src)
```

使用自定义混合器创建混合着色器。

**参数**:
- `blender`: 自定义混合器对象
- `dst`, `src`: 目标和源着色器

**返回值**: 混合着色器智能指针

**处理逻辑**:
1. 如果 `blender` 为空,默认使用 `kSrcOver` 模式
2. 如果混合器实际上是内置模式,创建 `SkBlendShader`
3. 否则使用运行时效果实现混合:
   ```cpp
   const SkRuntimeEffect* blendEffect = GetKnownRuntimeEffect(StableKey::kBlend);
   SkRuntimeEffect::ChildPtr children[] = {std::move(src), std::move(dst), std::move(blender)};
   return blendEffect->makeShader(/*uniforms=*/{}, children);
   ```

## 内部实现细节

### appendStages() 实现

核心方法,将混合操作添加到光栅管线:

```cpp
bool appendStages(const SkStageRec& rec, const SkShaders::MatrixRec& mRec) const
```

**实现流程**:

1. **评估两个子着色器**:
   ```cpp
   float* res0 = append_two_shaders(rec, mRec, fDst.get(), fSrc.get());
   if (!res0) {
       return false;
   }
   ```

2. **设置混合输入**:
   ```cpp
   rec.fPipeline->append(SkRasterPipelineOp::load_dst, res0);
   ```
   将目标着色器的结果加载为混合的"dst",源着色器的结果已在 "src" 寄存器中。

3. **应用混合模式**:
   ```cpp
   SkBlendMode_AppendStages(fMode, rec.fPipeline);
   ```
   根据混合模式添加相应的管线阶段。

### append_two_shaders() 辅助函数

评估两个子着色器并保存结果:

```cpp
static float* append_two_shaders(const SkStageRec& rec,
                                 const SkShaders::MatrixRec& mRec,
                                 SkShader* s0,
                                 SkShader* s1)
```

**存储结构**:
```cpp
struct Storage {
    float fCoords[2 * SkRasterPipelineContexts::kMaxStride];  // 坐标备份
    float fRes0[4 * SkRasterPipelineContexts::kMaxStride];    // 第一个着色器结果
};
```

**执行流程**:

1. **保存坐标** (如果需要):
   ```cpp
   if (mRec.rasterPipelineCoordsAreSeeded()) {
       rec.fPipeline->append(SkRasterPipelineOp::store_src_rg, storage->fCoords);
   }
   ```
   某些着色器可能修改坐标,需要备份。

2. **评估第一个着色器**:
   ```cpp
   if (!as_SB(s0)->appendStages(rec, mRec)) {
       return nullptr;
   }
   rec.fPipeline->append(SkRasterPipelineOp::store_src, storage->fRes0);
   ```

3. **恢复坐标**:
   ```cpp
   if (mRec.rasterPipelineCoordsAreSeeded()) {
       rec.fPipeline->append(SkRasterPipelineOp::load_src_rg, storage->fCoords);
   }
   ```

4. **评估第二个着色器**:
   ```cpp
   if (!as_SB(s1)->appendStages(rec, mRec)) {
       return nullptr;
   }
   ```

5. **返回第一个着色器结果的指针**,第二个着色器的结果留在寄存器中。

### 坐标备份机制

注释中提到的重要细节:

```cpp
// Note we cannot simply apply mRec here and then unconditionally store the coordinates. When
// building for Android Framework it would interrupt the backwards local matrix concatenation if
// mRec had a pending local matrix and either of the children also had a local matrix.
// b/256873449
```

这是为了保持与 Android Framework 的兼容性,只在必要时备份坐标。

### 序列化实现

**写入 (flatten)**:
```cpp
void flatten(SkWriteBuffer& buffer) const {
    buffer.writeFlattenable(fDst.get());  // 序列化目标着色器
    buffer.writeFlattenable(fSrc.get());  // 序列化源着色器
    buffer.write32((int)fMode);            // 序列化混合模式
}
```

**读取 (CreateProc)**:
```cpp
sk_sp<SkFlattenable> SkBlendShader::CreateProc(SkReadBuffer& buffer)
```

支持两种混合方式:

1. **内置混合模式**:
   ```cpp
   unsigned mode = buffer.read32();
   if (mode <= (unsigned)SkBlendMode::kLastMode) {
       return SkShaders::Blend(static_cast<SkBlendMode>(mode), dst, src);
   }
   ```

2. **自定义混合器** (标记为 `kCustom_SkBlendMode`):
   ```cpp
   if (mode == kCustom_SkBlendMode) {
       sk_sp<SkBlender> blender = buffer.readBlender();
       return SkShaders::Blend(std::move(blender), dst, src);
   }
   ```

### 向后兼容性

```cpp
void SkRegisterBlendShaderFlattenable() {
    SK_REGISTER_FLATTENABLE(SkBlendShader);
    // Previous name
    SkFlattenable::Register("SkShader_Blend", SkBlendShader::CreateProc);
}
```

注册旧名称以支持旧版本的 SKP 文件。

## 依赖关系

### 直接依赖

- **SkShaderBase**: 基类
- **SkBlendMode**: 混合模式枚举
- **SkBlender**: 自定义混合器接口
- **SkRasterPipeline**: 光栅管线
- **SkRuntimeEffect**: 自定义混合器的运行时效果
- **SkKnownRuntimeEffects**: 内置运行时效果库
- **SkArenaAlloc**: 内存分配

### 被依赖关系

可能的使用场景:
- **复杂图形效果**: 纹理与渐变混合
- **图层系统**: 实现图层混合模式
- **滤镜效果**: 作为图像滤镜的一部分
- **用户界面**: UI 元素的混合和合成

### 典型使用模式

```cpp
// 示例:将图像与渐变混合
auto imageShader = SkImageShader::Make(...);
auto gradientShader = SkGradientShader::MakeLinear(...);
auto blendShader = SkShaders::Blend(SkBlendMode::kMultiply, gradientShader, imageShader);
paint.setShader(blendShader);
```

## 设计模式与设计决策

### 组合模式

`SkBlendShader` 是组合模式的典型实现:
- **组合节点**: 包含两个子着色器
- **统一接口**: 实现与其他着色器相同的接口
- **递归结构**: 子着色器可以是任何着色器,包括其他混合着色器

### 策略模式

混合模式作为策略:
- 不同的 `SkBlendMode` 值产生不同的混合行为
- `SkBlender` 允许完全自定义的混合策略
- 运行时选择混合算法

### 懒惰评估

着色器不是在创建时评估,而是在管线执行时:
- 创建时仅存储配置
- `appendStages()` 构建计算图
- 实际计算在光栅化时发生

### 优化优先设计

工厂函数包含多个优化:
- **短路优化**: `kClear`、`kSrc`、`kDst` 直接返回简单结果
- **类型检测**: 检查自定义混合器是否实际上是内置模式
- **运行时效果回退**: 复杂混合器使用通用路径

### 双路径策略

支持两种混合实现:
1. **内置混合模式**: 使用优化的管线操作
2. **自定义混合器**: 使用 SkSL 运行时效果

这在性能和灵活性之间取得平衡。

## 性能考量

### 内存分配

使用竞技场分配器:
```cpp
auto storage = rec.fAlloc->make<Storage>();
```
- 快速分配临时存储
- 统一释放,无碎片
- 缓存友好

### 坐标备份开销

条件性备份坐标:
- 仅在必要时保存和恢复
- 避免不必要的内存流量
- 针对常见情况优化

### 混合模式性能

不同混合模式有不同的成本:
- **简单模式** (如 `kSrc`、`kDst`): 零开销,直接优化掉
- **标准模式** (如 `kMultiply`): 几个管线阶段,高效
- **复杂模式** (如自定义混合器): 可能涉及 SkSL 解释或编译

### 子着色器评估

顺序评估两个子着色器:
- 如果第一个失败,第二个不评估(短路)
- 结果缓存在寄存器中,避免重新计算
- 管线优化器可能进一步优化

### 优化机会

- **常量折叠**: 如果两个子着色器都是常量颜色,可以在构造时计算结果
- **代数简化**: 某些混合模式与特定着色器组合可以简化
- **管线融合**: 混合操作可能与后续操作融合

### SIMD 潜力

混合操作天然适合 SIMD:
- 四通道 RGBA 同时处理
- 管线操作通常是向量化的
- 现代 CPU 上高效执行

## 相关文件

### 核心依赖
- `src/shaders/SkShaderBase.h` - 着色器基类
- `src/shaders/SkShaderBase.cpp` - 着色器基类实现
- `include/core/SkShader.h` - 公共着色器接口
- `include/effects/SkShaders.h` - 着色器工厂函数

### 混合相关
- `include/core/SkBlendMode.h` - 混合模式枚举
- `include/core/SkBlender.h` - 混合器接口
- `src/core/SkBlendModePriv.h` - 混合模式私有工具
- `src/core/SkBlenderBase.h` - 混合器基类

### 运行时效果
- `include/effects/SkRuntimeEffect.h` - 运行时效果接口
- `src/core/SkKnownRuntimeEffects.h` - 内置运行时效果
- `src/core/SkRuntimeEffectPriv.h` - 运行时效果私有API

### 光栅管线
- `src/core/SkRasterPipeline.h` - 光栅管线核心
- `src/core/SkRasterPipelineOpList.h` - 管线操作列表
- `src/core/SkRasterPipelineOpContexts.h` - 管线上下文

### 序列化
- `src/core/SkReadBuffer.h` - 反序列化工具
- `src/core/SkWriteBuffer.h` - 序列化工具
- `include/core/SkFlattenable.h` - 可序列化对象基类

### 内存管理
- `src/base/SkArenaAlloc.h` - 竞技场分配器

### 相关着色器
- `src/shaders/SkColorShader.h` - 纯色着色器(常用于混合)
- `src/shaders/SkImageShader.h` - 图像着色器(常用于混合)
- `src/shaders/gradients/SkGradientBaseShader.h` - 渐变着色器(常用于混合)

### 效果工具
- `src/core/SkEffectPriv.h` - 效果私有工具
