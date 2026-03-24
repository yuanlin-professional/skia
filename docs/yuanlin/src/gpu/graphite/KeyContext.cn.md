# KeyContext

> 源文件
> - src/gpu/graphite/KeyContext.h
> - src/gpu/graphite/KeyContext.cpp

## 概述

`KeyContext` 是 Skia Graphite 渲染引擎中用于着色器键（shader key）生成的上下文对象。该类封装了生成唯一着色器标识符所需的所有环境信息和配置参数，包括设备能力、字典、色彩信息、变换矩阵、以及各种生成标志。

`KeyContext` 在两个关键路径中使用：
1. **预编译路径**（Pre-compile）：在没有 Recorder 的情况下生成着色器变体
2. **绘制路径**（ExtractPaintData）：从实际绘制参数提取着色器键和管线数据

该类采用不可变设计，通过创建新的 `KeyContext` 实例来传播上下文变化，支持在处理复杂着色器效果（如 RuntimeEffect）时创建作用域化的子上下文。

## 架构位置

```
Paint/Shader 参数
  └── KeyContext (上下文封装)
      ├── PaintParamsKeyBuilder (键构建)
      ├── PipelineDataGatherer (数据收集)
      ├── ShaderCodeDictionary (代码字典)
      └── RuntimeEffectDictionary (运行时效果字典)
```

`KeyContext` 位于着色器编译管线的核心位置，协调多个组件完成从绘制参数到着色器代码的转换。

## 主要类与结构体

### KeyGenFlags

```cpp
enum class KeyGenFlags : uint8_t {
    kDefault = 0b0,
    kDisableSamplingOptimization       = 0b001,  // 禁用采样优化
    kEnableIdentityColorSpaceXform     = 0b010,  // 启用恒等色彩空间转换
    kDisableAlphaOnlyImageColorization = 0b100,  // 禁用 alpha-only 图像着色
};
```

**用途**：控制着色器键生成的细节行为

**标志说明**：

1. **kDisableSamplingOptimization**：
   - 默认情况下，线性采样在视觉等效时优化为最近邻采样
   - 该标志禁用此优化，强制保留线性采样

2. **kEnableIdentityColorSpaceXform**：
   - 默认情况下，恒等色彩空间转换映射到 `ColorSpaceTransformPremul` 以避免着色器组合爆炸
   - 图像滤镜和运行时效果多次采样图像时，跳过色彩空间转换能显著提升性能

3. **kDisableAlphaOnlyImageColorization**：
   - 默认情况下，alpha-only 图像着色器使用画笔颜色着色
   - 在运行时效果上下文中禁用此行为

### KeyContext

**核心职责**：
- 封装着色器键生成所需的所有上下文信息
- 提供创建作用域子上下文的方法
- 管理色彩信息和变换矩阵的传播

**不可变字段**（整个键生成过程中不变）：

```cpp
const Caps* fCaps;                           // 设备能力
Recorder* fRecorder;                          // 记录器（可为空）
DrawContext* fDC;                             // 绘制上下文（可为空）
FloatStorageManager* fFloatStorageManager;    // 浮点数存储管理
PaintParamsKeyBuilder* fPaintParamsKeyBuilder; // 键构建器
PipelineDataGatherer* fPipelineDataGatherer;   // 管线数据收集器
ShaderCodeDictionary* fDictionary;            // 着色器代码字典
sk_sp<RuntimeEffectDictionary> fRTEffectDict;  // 运行时效果字典
SkM44 fLocal2Dev;                             // 本地到设备变换矩阵
```

**可修改字段**（在处理效果树时可能变化）：

```cpp
SkMatrix* fLocalMatrix = nullptr;             // 局部矩阵（指向 KeyContextWithLocalMatrix）
SkColorInfo fDstColorInfo;                     // 目标色彩信息
SkPMColor4f fPaintColor;                       // 画笔颜色（预乘格式）
SkEnumBitMask<KeyGenFlags> fKeyGenFlags;       // 生成标志
```

### KeyContextWithLocalMatrix

继承自 `KeyContext`，用于在处理带局部矩阵的着色器时创建临时上下文：

```cpp
class KeyContextWithLocalMatrix : public KeyContext {
public:
    KeyContextWithLocalMatrix(const KeyContext& other, const SkMatrix& childLM);
private:
    SkMatrix fStorage;  // 存储连接后的矩阵
};
```

**矩阵连接逻辑**：
```cpp
if (fLocalMatrix) {
    fStorage = SkMatrix::Concat(childLM, *fLocalMatrix);
} else {
    fStorage = childLM;
}
fLocalMatrix = &fStorage;
```

## 公共 API 函数

### 构造函数

#### 预编译路径构造函数

```cpp
KeyContext(const Caps* caps,
           FloatStorageManager* floatStorageManager,
           PaintParamsKeyBuilder* paintParamsKeyBuilder,
           PipelineDataGatherer* pipelineDataGatherer,
           ShaderCodeDictionary* dict,
           sk_sp<RuntimeEffectDictionary> rtEffectDict,
           const SkColorInfo& dstColorInfo);
```

**特点**：
- `fRecorder` 为 `nullptr`
- 无变换矩阵和画笔颜色信息
- 用于生成着色器变体的预编译

#### 绘制路径构造函数

```cpp
KeyContext(Recorder* recorder,
           DrawContext* drawContext,
           FloatStorageManager* floatStorageManager,
           PaintParamsKeyBuilder* paintParamsKeyBuilder,
           PipelineDataGatherer* pipelineDataGatherer,
           const SkM44& local2Dev,
           const SkColorInfo& dstColorInfo,
           SkEnumBitMask<KeyGenFlags> initialFlags,
           const SkColor4f& paintColor);
```

**初始化细节**：
- 从 `recorder->priv()` 获取 `Caps` 和字典
- 存储完整的变换矩阵和色彩信息
- 预处理画笔颜色：

```cpp
fPaintColor = PaintParams::Color4fPrepForDst(paintColor, fDstColorInfo).makeOpaque().premul();
fPaintColor.fA = paintColor.fA;  // 单独存储 alpha
```

#### 拷贝构造函数

```cpp
KeyContext(const KeyContext& other, SkEnumBitMask<KeyGenFlags> xtraFlags = KeyGenFlags::kDefault);
```

复制所有字段，并合并额外的标志：`fKeyGenFlags = other.fKeyGenFlags | xtraFlags`。

### 作用域上下文创建

#### withColorInfo

```cpp
KeyContext withColorInfo(const SkColorInfo& info) const;
```

**功能**：创建使用新色彩信息的子上下文

**色彩空间转换**：
```cpp
SkColorSpaceXformSteps(fDstColorInfo.colorSpace(), kOpaque_SkAlphaType,
                       info.colorSpace(),          kOpaque_SkAlphaType)
        .apply(o.fPaintColor.vec());
```

**技巧**：通过覆盖 alpha 类型为 `kOpaque`，确保转换只影响 RGB 而保留 alpha 值。

#### forRuntimeEffect

```cpp
KeyContext forRuntimeEffect(const SkRuntimeEffect* effect, int child) const;
```

**功能**：为运行时效果的子效果创建上下文

**标志设置**：
1. 总是禁用 alpha-only 图像着色
2. 如果子效果使用显式采样（`isExplicit()`）：
   - 启用恒等色彩空间转换（优化多次采样）
   - 禁用采样优化（保持精度）

```cpp
SkEnumBitMask<KeyGenFlags> xtraFlags = KeyGenFlags::kDisableAlphaOnlyImageColorization;
if (SkRuntimeEffectPriv::ChildSampleUsage(effect, child).isExplicit()) {
    xtraFlags |= KeyGenFlags::kEnableIdentityColorSpaceXform |
                 KeyGenFlags::kDisableSamplingOptimization;
}
```

#### withExtraFlags

```cpp
KeyContext withExtraFlags(SkEnumBitMask<KeyGenFlags> flags) const;
```

创建具有额外标志的上下文，内部调用拷贝构造函数。

### 访问器方法

```cpp
Recorder* recorder() const;
DrawContext* drawContext() const;
const Caps* caps() const;
const SkM44& local2Dev() const;
const SkMatrix* localMatrix() const;
FloatStorageManager* floatStorageManager() const;
PaintParamsKeyBuilder* paintParamsKeyBuilder() const;
PipelineDataGatherer* pipelineDataGatherer() const;
ShaderCodeDictionary* dict() const;
sk_sp<RuntimeEffectDictionary> rtEffectDict() const;
const SkColorInfo& dstColorInfo() const;
const SkPMColor4f& paintColor() const;
SkEnumBitMask<KeyGenFlags> flags() const;
```

所有访问器都是简单的成员访问，提供对封装数据的只读访问。

## 内部实现细节

### 画笔颜色的特殊处理

画笔颜色以预乘格式存储，但 RGB 和 alpha 实际上是独立使用的：

```cpp
// RGB 部分：不透明且预乘
fPaintColor = PaintParams::Color4fPrepForDst(paintColor, fDstColorInfo).makeOpaque().premul();
// Alpha 部分：单独存储
fPaintColor.fA = paintColor.fA;
```

**原因**：
- RGB 用于着色（如 alpha-only 图像）
- Alpha 用于混合
- 分开存储避免在着色器中重复计算

### 色彩空间转换的 Alpha 保护

在 `withColorInfo` 中使用 `kOpaque_SkAlphaType` 技巧：

```cpp
SkColorSpaceXformSteps(oldCS, kOpaque_SkAlphaType, newCS, kOpaque_SkAlphaType)
```

这确保 `SkColorSpaceXformSteps` 只转换 RGB，不触碰 alpha 通道。

### RuntimeEffect 子效果优化

显式采样检测：

```cpp
if (SkRuntimeEffectPriv::ChildSampleUsage(effect, child).isExplicit())
```

**显式采样的含义**：
- 子效果通过显式的 UV 坐标采样（如 `sample(child, uv)`）
- 通常表示数据查找或多次采样
- 值得优化色彩空间转换，代价是禁用采样优化

## 依赖关系

### 核心依赖

| 依赖项 | 作用 |
|--------|------|
| `Caps` | 查询设备能力 |
| `ShaderCodeDictionary` | 管理着色器代码片段 |
| `RuntimeEffectDictionary` | 管理运行时效果 |
| `PaintParamsKeyBuilder` | 构建着色器键 |
| `PipelineDataGatherer` | 收集管线数据 |
| `FloatStorageManager` | 管理浮点数存储策略 |

### 工具类

| 类型 | 用途 |
|------|------|
| `SkColorSpaceXformSteps` | 色彩空间转换 |
| `PaintParams::Color4fPrepForDst` | 准备目标色彩 |
| `SkRuntimeEffectPriv` | 访问运行时效果私有信息 |

### 可选依赖

| 依赖项 | 使用场景 |
|--------|----------|
| `Recorder` | 绘制路径中可用 |
| `DrawContext` | 绘制路径中可用 |

## 设计模式与设计决策

### 1. 上下文对象模式

`KeyContext` 封装了方法调用所需的所有参数，避免函数签名过长。这是经典的上下文对象模式。

### 2. 不可变性和值语义

虽然内部有可修改字段，但对外表现为不可变：通过创建新实例传播变化而非修改现有实例。

```cpp
KeyContext withColorInfo(const SkColorInfo& info) const {
    KeyContext o = *this;  // 拷贝
    o.fDstColorInfo = info; // 修改副本
    return o;               // 返回新实例
}
```

**好处**：
- 线程安全（如果每个线程有自己的 KeyContext）
- 调用栈清晰（每层有自己的上下文副本）

### 3. 策略模式

`KeyGenFlags` 实现策略模式，允许在运行时改变着色器生成行为。

### 4. 建造者模式的辅助

`KeyContext` 与 `PaintParamsKeyBuilder` 协作，提供建造者模式所需的上下文信息。

### 5. 继承用于局部矩阵

`KeyContextWithLocalMatrix` 通过继承扩展 `KeyContext`，使用 RAII 管理局部矩阵的生命周期。

### 6. 位掩码优化

`KeyGenFlags` 使用位掩码实现多个布尔标志的高效存储和组合：

```cpp
SK_MAKE_BITMASK_OPS(KeyGenFlags)  // 启用位运算符重载
```

## 性能考量

### 拷贝开销

`KeyContext` 的拷贝构造相对便宜：
- 大部分字段是指针或小对象
- 唯一较大的成员是 `SkM44` 矩阵（16 个浮点数）
- `sk_sp` 的拷贝只是引用计数增加

### 局部矩阵存储

`KeyContextWithLocalMatrix` 使用栈上的 `fStorage` 避免堆分配：

```cpp
SkMatrix fStorage;  // 9 个浮点数，约 36 字节
```

### 标志组合

使用位掩码而非多个布尔变量：
- 节省内存（1 字节 vs. 3 字节 + 填充）
- 快速组合（位或运算）
- 高效比较

### 色彩空间转换优化

在 `withColorInfo` 中内联转换：
- 避免创建临时 `SkColor4f` 对象
- 直接修改 `fPaintColor.vec()`

### RuntimeEffect 标志推断

`forRuntimeEffect` 的条件逻辑简单，编译器易于优化为分支预测友好的代码。

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/PaintParamsKeyBuilder.h` | 着色器键构建器 |
| `src/gpu/graphite/PipelineDataGatherer.h` | 管线数据收集器 |
| `src/gpu/graphite/ShaderCodeDictionary.h` | 着色器代码字典 |
| `src/gpu/graphite/RuntimeEffectDictionary.h` | 运行时效果字典 |
| `src/gpu/graphite/Caps.h` | 设备能力 |
| `src/gpu/graphite/FloatStorageManager.h` | 浮点数存储管理 |
| `src/gpu/graphite/Recorder.h` | 记录器 |
| `src/gpu/graphite/DrawContext.h` | 绘制上下文 |
| `src/gpu/graphite/PaintParams.h` | 画笔参数 |
| `include/effects/SkRuntimeEffect.h` | 运行时效果公共接口 |
| `src/core/SkRuntimeEffectPriv.h` | 运行时效果私有接口 |
| `src/core/SkColorSpaceXformSteps.h` | 色彩空间转换步骤 |
| `include/core/SkM44.h` | 4x4 矩阵 |
| `include/core/SkMatrix.h` | 3x3 矩阵 |
