# GrDisableColorXP

> 源文件
> - src/gpu/ganesh/effects/GrDisableColorXP.h
> - src/gpu/ganesh/effects/GrDisableColorXP.cpp

## 概述

`GrDisableColorXP` 是 Ganesh GPU 后端中的一个特殊传输处理器 (Transfer Processor),其唯一功能是禁用颜色写入到帧缓冲区。该处理器会忽略所有输入颜色和覆盖率信息,不执行任何混合操作,主要用于仅需要修改模板缓冲区或深度缓冲区的渲染场景,例如模板测试 (stenciling) 操作。

这是 Skia 渲染管线中最简单的传输处理器之一,其存在体现了关注点分离的设计原则:将"不写颜色"这一特殊需求封装为独立的可复用组件。

## 架构位置

`GrDisableColorXP` 位于 Skia 图形管线的传输处理器层:

```
skia/
└── src/gpu/ganesh/
    └── effects/
        ├── GrDisableColorXP.h    (头文件 - 工厂类定义)
        └── GrDisableColorXP.cpp  (实现文件 - 处理器实现)
```

在渲染管线中的位置:
- **输入**: 接收片段着色器的输出 (但会忽略)
- **层级**: 传输处理器阶段,负责配置混合和写入掩码
- **输出**: 配置 GPU 禁用颜色写入,但保留深度/模板写入

典型使用场景:
1. **模板路径渲染**: 构建模板蒙版,不修改颜色缓冲区
2. **深度预通道**: 仅写入深度值,优化后续渲染
3. **遮挡剔除**: 测试几何体可见性,不绘制颜色

## 主要类与结构体

### GrDisableColorXPFactory

```cpp
class GrDisableColorXPFactory : public GrXPFactory {
    constexpr GrDisableColorXPFactory() {}  // 无状态工厂
};
```

**核心职责**:
- 提供全局单例实例 (无状态设计)
- 创建 `DisableColorXP` 处理器实例
- 声明分析属性,用于渲染管线优化

**设计特点**:
- `constexpr` 构造函数,编译期初始化
- 零成员变量,无运行时开销
- 线程安全的单例模式

### DisableColorXP

```cpp
class DisableColorXP : public GrXferProcessor {
    // 无成员变量
};
```

**核心职责**:
- 配置混合信息,禁用颜色写入
- 生成最小化的着色器代码
- 处理硬件特定的兼容性问题

**设计特点**:
- 完全无状态,所有实例等价
- 最小内存占用 (仅基类开销)

### DisableColorXP::Impl

```cpp
class Impl : public ProgramImpl {
    void emitOutputsForBlendState(const EmitArgs& args) override;
    void emitWriteSwizzle(...) const override;
};
```

**核心职责**:
- 生成 GLSL 着色器代码 (处理驱动程序 bug)
- 抑制颜色通道的 swizzle 输出

## 公共 API 函数

### GrDisableColorXPFactory::Get

```cpp
static const GrDisableColorXPFactory* Get();
```

**功能**: 获取全局单例工厂实例

**实现细节**:
```cpp
static constexpr const GrDisableColorXPFactory gDisableColorXPFactory;
return &gDisableColorXPFactory;
```

**特点**:
- 编译期构造,零初始化成本
- 线程安全 (静态局部变量保证)
- 内联实现,无函数调用开销

**使用场景**: 在配置渲染管线时,需要禁用颜色写入

### MakeXferProcessor

```cpp
static sk_sp<const GrXferProcessor> MakeXferProcessor();
```

**功能**: 创建传输处理器实例

**返回值**: `DisableColorXP` 对象的智能指针

**实现**:
```cpp
return sk_make_sp<DisableColorXP>();
```

**注意**: 每次调用创建新对象 (虽然对象无状态)

### analysisProperties

```cpp
AnalysisProperties analysisProperties(
    const GrProcessorAnalysisColor&,
    const GrProcessorAnalysisCoverage&,
    const GrCaps&,
    GrClampType) const override;
```

**功能**: 声明处理器的分析属性

**返回值**:
- `kCompatibleWithCoverageAsAlpha`: 兼容"覆盖率作为 alpha"优化
- `kIgnoresInputColor`: 忽略输入颜色

**作用**: 告知渲染管线可以跳过某些计算,提升性能

## 内部实现细节

### 混合配置

`onGetBlendInfo` 函数设置混合信息:
```cpp
void onGetBlendInfo(skgpu::BlendInfo* blendInfo) const override {
    blendInfo->fWritesColor = false;  // 禁用颜色写入
}
```

**效果**:
- GPU 硬件不会修改颜色缓冲区的任何像素
- 深度和模板缓冲区仍可正常写入
- 混合因子被忽略 (无混合操作)

### 着色器代码生成

**标准情况**:
- 不输出任何颜色值
- `emitOutputsForBlendState` 为空实现

**Nexus 6 驱动程序 bug 修复**:
```glsl
// 仅在必须写入 gl_FragColor 的平台上生成
gl_FragColor = half4(0);
```

**背景**:
- Chromium bug 445377: 某些 Android 设备驱动要求写入 `gl_FragColor`
- 不写入会导致 OpenGL 上下文丢失,渲染失败
- 解决方案: 写入任意值 (此处为零向量)

**检测标志**:
```cpp
if (args.fShaderCaps->fMustWriteToFragColor) { ... }
```

### Swizzle 抑制

`emitWriteSwizzle` 函数为空实现:
```cpp
void emitWriteSwizzle(...) const override {
    // Don't write any swizzling
}
```

**作用**: 确保最终着色器不输出颜色通道,即使启用了通道重排

### 键值生成

`onAddToKey` 为空实现:
```cpp
void onAddToKey(const GrShaderCaps&, skgpu::KeyBuilder*) const override {}
```

**原因**: 处理器无状态,所有实例共享同一着色器程序

### 相等性比较

`onIsEqual` 始终返回 `true`:
```cpp
bool onIsEqual(const GrXferProcessor& xpBase) const override { return true; }
```

**原因**: 所有 `DisableColorXP` 实例功能完全相同

## 依赖关系

### 内部依赖

- `GrXferProcessor`: 基类,定义传输处理器接口
- `GrXPFactory`: 工厂基类
- `GrProcessorAnalysis`: 分析工具,用于优化
- `skgpu::BlendInfo`: 混合信息结构体
- `GrGLSLFragmentShaderBuilder`: GLSL 代码生成器

### 外部依赖

- `GrCaps`: 能力查询接口
- `GrShaderCaps`: 着色器能力查询
- `skgpu::KeyBuilder`: 着色器缓存键构建器
- `skgpu::Swizzle`: 颜色通道重排

### 依赖关系图

```
GrDisableColorXP
    ├── GrXferProcessor (基类)
    ├── GrXPFactory (工厂基类)
    ├── skgpu::BlendInfo (混合配置)
    └── glsl/GrGLSLFragmentShaderBuilder (着色器生成)
```

## 设计模式与设计决策

### 1. 单例模式 (Singleton Pattern)

工厂类使用静态 `constexpr` 单例:
```cpp
static constexpr const GrDisableColorXPFactory gDisableColorXPFactory;
```

**优点**:
- 编译期初始化,零运行时成本
- 线程安全,无需同步
- 内存占用最小 (单个全局对象)

**权衡**:
- 无法延迟初始化 (对于无状态对象无影响)

### 2. 空对象模式 (Null Object Pattern)

`DisableColorXP` 是"不执行操作"的具体实现:
- **优点**: 避免空指针检查,统一接口
- **实现**: 所有方法都是最小实现或空操作
- **场景**: 当需要"无混合"时,使用此对象而非 `nullptr`

### 3. 模板方法模式 (Template Method Pattern)

继承 `GrXferProcessor` 并实现虚函数:
- `onGetBlendInfo`: 配置混合状态
- `onAddToKey`: 生成缓存键
- `onIsEqual`: 判断等价性

### 4. 工厂方法模式 (Factory Method Pattern)

`MakeXferProcessor` 封装对象创建:
- **优点**: 隐藏具体类型,返回基类指针
- **实现**: 使用智能指针管理生命周期

### 5. 编译期优化策略

使用 `constexpr` 和内联:
- **工厂对象**: 编译期构造
- `Get` 方法: 内联实现,无函数调用
- **结果**: 零运行时开销的单例模式

### 6. 兼容性适配层

针对特定硬件的 bug 修复:
- **问题**: Nexus 6 驱动要求写入 `gl_FragColor`
- **方案**: 条件编译生成兼容代码
- **检测**: 运行时查询 `fMustWriteToFragColor` 标志

### 7. 无状态设计哲学

所有类都不包含成员变量:
- **优点**: 对象轻量,无内存开销,易于复用
- **实现**: 功能完全由类型决定,非状态
- **影响**: 简化对象管理和生命周期

## 性能考量

### 1. 内存效率

- **工厂对象**: 单个全局实例,约 8 字节 (虚函数表指针)
- **处理器对象**: 每个实例约 16 字节 (基类 + 虚函数表)
- **智能指针开销**: 额外 8 字节引用计数

### 2. 创建与销毁开销

- **工厂获取**: 内联实现,无函数调用
- **处理器创建**: 一次堆分配 + 智能指针封装
- **销毁**: 自动引用计数管理,无需手动释放

### 3. GPU 状态配置

- **颜色写入掩码**: 设置为 0,禁用所有颜色通道写入
- **混合操作**: 完全跳过,无 GPU 计算
- **带宽节省**: 避免颜色缓冲区的读写操作

### 4. 着色器编译

- **代码最小**: 仅生成必要的兼容性代码 (Nexus 6 修复)
- **缓存命中**: 所有实例共享同一着色器程序
- **编译时间**: 接近零 (几乎无实际代码)

### 5. 运行时性能

- **片段处理**: 最小化或跳过颜色计算
- **混合单元**: 完全禁用,节省 GPU 周期
- **带宽**: 避免帧缓冲区写入,大幅降低内存带宽需求

### 6. 优化建议

**当前优化**:
- `kIgnoresInputColor`: 允许跳过颜色计算
- `kCompatibleWithCoverageAsAlpha`: 兼容覆盖率优化

**潜在改进**:
- 考虑完全跳过片段着色器执行 (硬件限制)
- 早期深度/模板测试优化

### 7. 实际使用场景性能

**模板路径渲染**:
- 绘制复杂路径时,先用此 XP 写入模板
- 节省颜色计算和写入时间 (约 30-50% 性能提升)
- 后续仅渲染可见像素

**深度预通道**:
- 第一遍渲染仅写深度,禁用颜色
- 第二遍渲染利用深度测试剔除隐藏片段
- 适用于复杂场景,减少 overdraw

## 相关文件

### 同目录文件
- `GrCoverageSetOpXP`: 覆盖率集合运算传输处理器
- `GrPorterDuffXferProcessor`: Porter-Duff 混合模式处理器
- `GrCustomXfermode`: 自定义混合模式处理器

### 依赖的核心文件
- `src/gpu/ganesh/GrXferProcessor.h`: 传输处理器基类
- `src/gpu/ganesh/GrXferProcessor.cpp`: 传输处理器基类实现
- `src/gpu/Blend.h`: 混合模式定义
- `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h`: 着色器构建器

### 使用此文件的上层模块
- `GrPaint`: 绘制状态类,选择传输处理器
- `GrStencilAndCoverPathRenderer`: 模板和覆盖路径渲染器
- `GrPipeline`: 渲染管线类,配置传输处理器

### 测试文件
- `tests/ProcessorTest.cpp`: 处理器单元测试
- `tests/StencilTest.cpp`: 模板操作测试

### 相关 bug 报告
- Chromium issue 445377: Nexus 6 驱动程序 bug (要求写入 `gl_FragColor`)
