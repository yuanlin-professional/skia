# SkRuntimeBlender

> 源文件
> - src/core/SkRuntimeBlender.h
> - src/core/SkRuntimeBlender.cpp

## 概述

`SkRuntimeBlender` 是 Skia 中实现动态运行时混合器的核心类。它允许通过 SkSL (Skia Shading Language) 在运行时定义自定义的混合效果,提供比传统固定混合模式更灵活的颜色混合能力。该类继承自 `SkBlenderBase`,支持通过 SkRuntimeEffect 机制动态创建和执行 GPU 或 CPU 上的混合操作。

## 架构位置

`SkRuntimeBlender` 位于 Skia 核心渲染管线的效果层:
- **父类**: `SkBlenderBase` - 所有混合器的基类
- **使用层**: 高层绘图 API (SkPaint, SkCanvas)
- **依赖层**: SkRuntimeEffect (SkSL 编译和执行), SkRasterPipeline (光栅化管线)
- **模块**: src/core - 核心渲染模块

## 主要类与结构体

### SkRuntimeBlender

自定义运行时混合器的实现类。

**继承关系**:
```
SkFlattenable
  └── SkBlenderBase
        └── SkRuntimeBlender
```

**关键成员变量**:

| 变量 | 类型 | 说明 |
|------|------|------|
| fEffect | sk_sp&lt;SkRuntimeEffect&gt; | 编译后的运行时效果 |
| fUniforms | sk_sp&lt;const SkData&gt; | uniform 变量数据 |
| fChildren | std::vector&lt;SkRuntimeEffect::ChildPtr&gt; | 子效果数组 (shader/colorfilter/blender) |

## 公共 API 函数

### 构造与创建

```cpp
SkRuntimeBlender(sk_sp<SkRuntimeEffect> effect,
                 sk_sp<const SkData> uniforms,
                 SkSpan<const SkRuntimeEffect::ChildPtr> children)
```
构造运行时混合器,接受编译的效果、uniform 数据和子效果。

### 查询接口

```cpp
SkRuntimeEffect* asRuntimeEffect() const override
```
返回关联的 SkRuntimeEffect 对象指针。

```cpp
BlenderType type() const override
```
返回混合器类型标识 `BlenderType::kRuntime`。

```cpp
sk_sp<SkRuntimeEffect> effect() const
sk_sp<const SkData> uniforms() const
SkSpan<const SkRuntimeEffect::ChildPtr> children() const
```
获取器方法,访问内部成员。

### 序列化

```cpp
void flatten(SkWriteBuffer& buffer) const override
```
将混合器状态序列化到缓冲区。

```cpp
static sk_sp<SkFlattenable> CreateProc(SkReadBuffer& buffer)
```
从缓冲区反序列化创建混合器实例。

## 内部实现细节

### onAppendStages

```cpp
bool onAppendStages(const SkStageRec& rec) const override
```

核心渲染方法,将混合操作添加到光栅化管线:

1. **兼容性检查**: 验证 SkRuntimeEffect 是否可在当前后端 (SkRP) 执行
   - 当前仅支持 #version 100 (OpenGL ES 2.0 着色语言)
   - 通过 `SkRuntimeEffectPriv::CanDraw` 检查版本

2. **获取 RP 程序**: 调用 `fEffect->getRPProgram()` 获取编译后的 RasterPipeline 程序

3. **准备 uniform 数据**:
   - 使用 `SkRuntimeEffectPriv::UniformsAsSpan` 转换 uniforms
   - 支持颜色空间转换 (dstCS)

4. **设置回调**: 创建 `RuntimeEffectRPCallbacks` 处理子效果采样

5. **执行管线**: 调用 `program->appendStages` 将 SkSL 指令转换为光栅化操作

### 序列化机制

**flatten 流程**:
- 写入 stable key (已知效果) 或完整 SkSL 源码
- 序列化 uniform 数据
- 递归序列化子效果

**CreateProc 流程**:
- 读取 stable key,尝试从已知效果中恢复
- 失败则读取源码并重新编译 (`SkMakeCachedRuntimeEffect`)
- 反序列化 uniforms 和子效果
- 调用 `effect->makeBlender()` 重建实例

### 错误处理

- **调试模式**: `kLenientSkSLDeserialization` 允许编译失败时跳过,仅输出警告
- **发布模式**: 编译失败时直接返回 nullptr,序列化失败

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkRuntimeEffect | SkSL 编译和管理 |
| SkRasterPipeline | 光栅化管线执行 |
| SkCapabilities | 后端能力查询 |
| SkWriteBuffer/SkReadBuffer | 序列化支持 |
| SkKnownRuntimeEffects | 预定义效果缓存 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkPaint | 通过 setBlender() 使用 |
| SkCanvas | 渲染时调用混合逻辑 |
| SkRecorder | 记录绘制命令 |

## 设计模式与设计决策

### 工厂模式

通过 `SkRuntimeEffect::makeBlender()` 创建实例,隐藏构造细节。

### 桥接模式

`SkRuntimeBlender` 作为桥梁,连接高层 API 与底层 SkSL 执行引擎:
- **抽象层**: SkBlenderBase 接口
- **实现层**: SkSL 编译器和 RasterPipeline

### 写时复制 (COW)

SkRuntimeEffect 内部使用引用计数和 stable key 共享已编译程序,避免重复编译。

### 设计权衡

1. **版本限制**: 当前仅支持 #version 100 确保 CPU 端可执行性
2. **缓存机制**: 通过 `SkMakeCachedRuntimeEffect` 缓存编译结果
3. **宽松反序列化**: 调试器环境允许反序列化失败,提高容错性

## 性能考量

### 编译成本

- **首次创建**: 需要 SkSL → SkRP 编译,成本较高
- **后续使用**: 通过缓存和引用计数复用,接近零成本

### 运行时开销

- **CPU 路径**: 通过 SkRasterPipeline 解释执行,比 GPU 慢
- **GPU 路径**: 转换为原生着色器,性能接近固定混合模式

### 优化策略

1. **内联优化**: 小函数会在编译时内联
2. **Uniform 转换**: 仅在需要颜色空间转换时复制数据
3. **子效果重用**: 通过指针共享避免重复创建

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/effects/SkRuntimeEffect.h | 公共 API 头文件 |
| src/core/SkBlenderBase.h | 混合器基类定义 |
| src/core/SkRuntimeEffectPriv.h | 私有辅助函数 |
| src/core/SkKnownRuntimeEffects.h | 预定义效果管理 |
| src/sksl/codegen/SkSLRasterPipelineBuilder.h | SkSL → SkRP 代码生成 |
| src/core/SkEffectPriv.h | 效果层私有工具 |
