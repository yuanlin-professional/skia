# GrCoverageSetOpXP

> 源文件
> - src/gpu/ganesh/effects/GrCoverageSetOpXP.h
> - src/gpu/ganesh/effects/GrCoverageSetOpXP.cpp

## 概述

`GrCoverageSetOpXP` 是 Ganesh GPU 后端中的一个传输处理器 (Transfer Processor),用于实现基于集合运算的覆盖率混合。它通过使用区域运算符 (如交集、并集、差集等) 直接将源覆盖率与目标值混合,特别适用于使用构造立体几何 (CSG, Constructive Solid Geometry) 技术渲染覆盖率蒙版。该处理器还支持在应用集合运算之前反转源覆盖率。

此模块的核心功能是提供一种高效的方式,在 GPU 上执行基于覆盖率的布尔运算,这对于实现复杂的裁剪、遮罩和合成效果至关重要。

## 架构位置

`GrCoverageSetOpXP` 位于 Skia 图形管线的传输处理器层,具体在 Ganesh GPU 后端的特效 (effects) 子系统中:

```
skia/
└── src/gpu/ganesh/
    └── effects/
        ├── GrCoverageSetOpXP.h    (头文件 - 定义工厂类)
        └── GrCoverageSetOpXP.cpp  (实现文件 - 实现处理器和工厂)
```

在渲染管线中的位置:
- **上游**: 接收来自几何处理器和片段处理器的覆盖率信息
- **层级**: 属于传输处理器阶段,负责像素混合逻辑
- **下游**: 配置 GPU 硬件混合单元,将结果写入帧缓冲区

## 主要类与结构体

### GrCoverageSetOpXPFactory

```cpp
class GrCoverageSetOpXPFactory : public GrXPFactory {
    SkRegion::Op fRegionOp;        // 区域运算类型
    bool         fInvertCoverage;  // 是否反转覆盖率
};
```

**核心职责**:
- 作为传输处理器的工厂类,负责创建 `CoverageSetOpXP` 实例
- 提供静态单例实例,避免重复创建相同配置的对象
- 实现分析属性,用于优化渲染管线

**关键成员**:
- `fRegionOp`: 指定集合运算类型 (替换、交集、并集、异或、差集、反向差集)
- `fInvertCoverage`: 控制是否在混合前反转源覆盖率值

### CoverageSetOpXP

```cpp
class CoverageSetOpXP : public GrXferProcessor {
    SkRegion::Op fRegionOp;        // 区域运算类型
    bool         fInvertCoverage;  // 是否反转覆盖率
};
```

**核心职责**:
- 实际的传输处理器实现
- 生成 GLSL 着色器代码
- 配置 GPU 硬件混合状态

### CoverageSetOpXP::Impl

```cpp
class Impl : public ProgramImpl {
    void emitOutputsForBlendState(const EmitArgs& args) override;
};
```

**核心职责**:
- 生成片段着色器代码,实现覆盖率反转逻辑
- 输出处理后的覆盖率值供硬件混合使用

## 公共 API 函数

### GrCoverageSetOpXPFactory::Get

```cpp
static const GrXPFactory* Get(SkRegion::Op regionOp, bool invertCoverage = false);
```

**功能**: 获取指定配置的传输处理器工厂实例

**参数**:
- `regionOp`: 区域运算类型,支持六种操作
  - `kReplace_Op`: 替换 (直接覆盖)
  - `kIntersect_Op`: 交集
  - `kUnion_Op`: 并集
  - `kXOR_Op`: 异或
  - `kDifference_Op`: 差集
  - `kReverseDifference_Op`: 反向差集
- `invertCoverage`: 是否反转覆盖率 (默认为 false)

**返回值**: 对应配置的静态工厂实例指针

**使用场景**: 在构建渲染管线时,选择合适的覆盖率混合策略

### makeXferProcessor

```cpp
sk_sp<const GrXferProcessor> makeXferProcessor(
    const GrProcessorAnalysisColor&,
    GrProcessorAnalysisCoverage,
    const GrCaps&,
    GrClampType) const override;
```

**功能**: 创建传输处理器实例

**返回值**: 配置好的 `CoverageSetOpXP` 对象的智能指针

### analysisProperties

```cpp
AnalysisProperties analysisProperties(
    const GrProcessorAnalysisColor& color,
    const GrProcessorAnalysisCoverage& coverage,
    const GrCaps&,
    GrClampType) const override;
```

**功能**: 分析传输处理器的属性,用于渲染管线优化

**返回值**: 分析属性标志
- 始终返回 `kIgnoresInputColor` (忽略输入颜色)
- 对于 `kReplace_Op` 额外返回 `kUnaffectedByDstValue` (不受目标值影响)

## 内部实现细节

### 混合模式映射

`onGetBlendInfo` 函数将区域运算映射到 GPU 硬件混合因子:

| 区域运算 | 源混合因子 | 目标混合因子 | 数学表达式 |
|---------|-----------|-------------|-----------|
| Replace | One | Zero | src |
| Intersect | DC | Zero | src × dst |
| Union | One | ISC | src + dst × (1 - src) |
| XOR | IDC | ISC | src × (1 - dst) + dst × (1 - src) |
| Difference | Zero | ISC | dst × (1 - src) |
| ReverseDifference | IDC | Zero | src × (1 - dst) |

**符号说明**:
- `DC`: 目标颜色 (Destination Color)
- `IDC`: 反向目标颜色 (1 - Destination Color)
- `ISC`: 反向源颜色 (1 - Source Color)

### 着色器代码生成

`emitOutputsForBlendState` 生成的 GLSL 代码非常简洁:

```glsl
// 如果反转覆盖率
outputPrimary = 1.0 - inputCoverage;

// 否则
outputPrimary = inputCoverage;
```

着色器仅处理覆盖率值的可选反转,实际的集合运算由硬件混合单元完成。

### 单例模式实现

工厂类使用静态 `constexpr` 对象实现单例模式:
- 12 个静态实例 (6 种运算 × 2 种反转状态)
- 编译期常量,无运行时开销
- 线程安全,无需同步机制

### 键值生成

`onAddToKey` 函数生成唯一标识符用于着色器缓存:
- 仅需存储 `fInvertCoverage` 布尔值
- 区域运算类型通过混合状态隐式编码

## 依赖关系

### 内部依赖

- `GrXferProcessor`: 基类,定义传输处理器接口
- `GrXPFactory`: 工厂基类,定义创建传输处理器的接口
- `GrCaps`: 能力查询类,提供硬件特性信息
- `GrProcessorAnalysis`: 分析类,用于管线优化
- `skgpu::BlendInfo`: 混合信息结构体,配置硬件混合器
- `skgpu::KeyBuilder`: 键值构建器,用于着色器缓存

### 外部依赖

- `SkRegion::Op`: 区域运算枚举,定义集合操作类型
- `SkRefCnt`: 引用计数基类,用于内存管理
- `GrGLSLFragmentShaderBuilder`: GLSL 着色器代码生成器

### 头文件依赖关系图

```
GrCoverageSetOpXP
    ├── SkRefCnt (引用计数)
    ├── SkRegion (区域运算定义)
    ├── GrCaps (能力查询)
    ├── GrProcessorAnalysis (管线分析)
    ├── GrXferProcessor (基类)
    └── glsl/GrGLSLFragmentShaderBuilder (着色器生成)
```

## 设计模式与设计决策

### 1. 工厂模式 (Factory Pattern)

`GrCoverageSetOpXPFactory` 使用工厂模式封装对象创建逻辑:
- **优点**: 集中管理对象创建,支持对象池和缓存
- **实现**: `Get` 方法返回预创建的静态实例

### 2. 单例模式 (Singleton Pattern)

12 个静态 `constexpr` 工厂实例:
- **优点**: 零运行时开销,线程安全,无需动态分配
- **权衡**: 增加二进制体积 (约 12 × sizeof(GrCoverageSetOpXPFactory))

### 3. 策略模式 (Strategy Pattern)

通过 `SkRegion::Op` 参数选择不同的混合策略:
- **优点**: 运行时灵活选择算法,易于扩展
- **实现**: switch 语句映射到不同的混合参数

### 4. 模板方法模式 (Template Method Pattern)

`GrXferProcessor` 定义处理流程框架:
- **抽象方法**: `onAddToKey`, `onGetBlendInfo`, `onIsEqual`
- **具体实现**: `CoverageSetOpXP` 提供具体行为

### 5. 编译期优化

使用 `constexpr` 构造函数和静态对象:
- **优点**: 编译期完成初始化,运行时无开销
- **限制**: 对象必须包含可常量初始化的成员

### 6. 关注点分离

- **工厂类**: 负责对象创建和分析
- **处理器类**: 负责着色器生成和混合配置
- **实现类**: 负责 GLSL 代码生成

## 性能考量

### 1. 内存效率

- **静态单例**: 12 个全局对象,总开销约 200-300 字节
- **无动态分配**: 工厂实例为栈对象或静态对象
- **智能指针开销**: 传输处理器使用 `sk_sp`,每个对象 8 字节引用计数开销

### 2. 计算效率

- **零运行时查找**: `Get` 方法通过 switch 直接返回静态对象指针
- **硬件加速**: 集合运算完全由 GPU 混合单元执行
- **最小着色器开销**: 仅执行可选的覆盖率反转 (单条指令)

### 3. 缓存友好性

- **着色器缓存**: 通过 `onAddToKey` 实现缓存命中
- **对象复用**: 工厂实例全局共享,避免重复创建
- **预测执行**: 编译期优化使分支预测更准确

### 4. 带宽优化

- **覆盖率操作**: 仅处理 alpha 通道,减少内存访问
- **原地混合**: 直接在帧缓冲区执行混合,无需中间缓冲

### 5. 优化建议

1. **Replace 操作**: 标记为 `kUnaffectedByDstValue`,可跳过目标读取
2. **不透明优化**: 注释提示可扩展优化 (如 Union 和 Difference 在全不透明时的优化)
3. **批处理**: 相同混合模式的绘制调用可批量处理

### 6. 测试支持

提供 `TestGet` 函数用于随机化测试:
- 随机选择区域运算和反转标志
- 仅在 `GPU_TEST_UTILS` 宏定义时编译
- 用于模糊测试和覆盖率测试

## 相关文件

### 同目录文件
- `GrPorterDuffXferProcessor`: 标准 Porter-Duff 混合模式处理器
- `GrCustomXfermode`: 自定义混合模式处理器
- `GrDisableColorXP`: 禁用颜色写入的传输处理器

### 依赖的核心文件
- `src/gpu/ganesh/GrXferProcessor.h`: 传输处理器基类
- `src/gpu/ganesh/GrXferProcessor.cpp`: 传输处理器基类实现
- `src/gpu/Blend.h`: 混合模式定义
- `src/gpu/KeyBuilder.h`: 着色器缓存键构建器

### 使用此文件的上层模块
- `GrPaint`: 绘制状态类,选择传输处理器
- `GrPipeline`: 渲染管线类,组装处理器链
- `GrDrawOp`: 绘制操作基类,配置混合模式

### 测试文件
- `tests/ProcessorTest.cpp`: 处理器单元测试
- `tests/BlendTest.cpp`: 混合模式正确性测试
