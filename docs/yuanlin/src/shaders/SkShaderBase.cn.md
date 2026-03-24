# SkShaderBase - 着色器内部基类

> 源文件:
> - `src/shaders/SkShaderBase.h`
> - `src/shaders/SkShaderBase.cpp`

## 概述

SkShaderBase 是 Skia 着色器系统的内部基类，继承自公共的 `SkShader`。它定义了所有着色器实现必须遵循的内部接口，包括类型识别、渐变信息提取、着色器上下文创建、光栅管线集成以及矩阵累积系统。与此类密切关联的 `SkShaders::MatrixRec` 类负责在着色器树遍历过程中跟踪和累积变换矩阵。

## 架构位置

```
Skia 着色器系统
├── SkShader (公共 API)
│   └── SkShaderBase (本模块 - 内部基类)
│       ├── SkColorFilterShader
│       ├── SkImageShader
│       ├── SkGradientShaderBase
│       ├── SkWorkingColorSpaceShader
│       ├── SkTransformShader
│       ├── SkLocalMatrixShader
│       └── ...其他着色器
├── SkShaders::MatrixRec (矩阵累积)
├── SkRasterPipeline (光栅管线)
└── GrFragmentProcessor (GPU 管线)
```

## 主要类与结构体

### `SkShaders::MatrixRec`
- 在着色器树遍历过程中累积和应用变换矩阵。
- **成员变量**:
  - `fCTM` (SkMatrix): 当前变换矩阵。
  - `fTotalLocalMatrix` (SkMatrix): 所有本地矩阵的连接（包括已应用的）。
  - `fPendingLocalMatrix` (SkMatrix): 尚未应用到管线的本地矩阵。
  - `fTotalMatrixIsValid` (bool): 总矩阵是否有效。
  - `fCTMApplied` (bool): CTM 是否已应用。

### `SkShaderBase`
- **成员变量**: `fUniqueID` (uint32_t) - 着色器唯一标识符。
- **关键方法分类**:
  - 类型系统: `ShaderType`, `type()`, `GradientType`, `asGradient()`
  - 上下文系统: `ContextRec`, `Context`, `makeContext()`
  - 管线系统: `appendStages()`, `appendRootStages()`
  - 工具方法: `makeInvertAlpha()`, `makeWithCTM()`, `isConstant()`, `asLuminanceColor()`

### `ShaderType` 枚举
通过宏 `SK_ALL_SHADERS(M)` 生成，包含：Blend, CTM, Color, ColorFilter, CoordClamp, Empty, GradientBase, Image, LocalMatrix, PerlinNoise, Picture, Runtime, Transform, TriColor, WorkingColorSpace。

### `GradientType` 枚举
通过宏 `SK_ALL_GRADIENTS(M)` 生成：None, Conical, Linear, Radial, Sweep。

### `GradientInfo` 结构体
- 用于提取渐变着色器参数。
- 包含颜色数组、颜色偏移、控制点、半径、平铺模式和预乘插值标记。
- `fColorCount` 既是输入（缓冲区大小）也是输出（实际颜色数量）。

### `ContextRec` 结构体
- 着色器上下文的创建参数包。
- 包含画笔 alpha、矩阵记录、目标颜色类型/空间和表面属性。

### `Context` 内部类
- 遗留的着色器上下文基类（`SK_ENABLE_LEGACY_SHADERCONTEXT` 控制）。
- 提供 `shadeSpan()` 虚方法用于逐像素着色。

## 公共 API 函数

### MatrixRec 方法
- `concat(m)`: 返回新的 MatrixRec，pending 和 total 矩阵都与 m 连接。
- `apply(rec, postInv)`: 将待处理矩阵的逆应用到 SkRasterPipeline，如果 CTM 尚未应用则先 seed 坐标。
- `applyForFragmentProcessor(postInv)`: GPU 路径，不应用 CTM（FP 的起始坐标已是本地空间）。
- `applied()`: 返回标记为"已应用"的 MatrixRec（用于 FP 子着色器传递）。
- `totalMatrix()`: 获取总变换矩阵 (CTM * totalLocalMatrix)。
- `markTotalMatrixInvalid()`: 标记总矩阵无效（例如 SkTransformShader 使用）。

### SkShaderBase 方法
- `appendRootStages(rec, ctm)`: 根级着色器的管线入口，创建 MatrixRec 并调用 `appendStages`。
- `appendStages(rec, mRec)`: **纯虚方法**，所有着色器必须实现的管线集成接口。
- `makeContext(rec, alloc)`: 创建遗留的着色器上下文。
- `makeInvertAlpha()`: 创建 alpha 反转的着色器 (1 - alpha)。
- `makeWithCTM(postM)`: 创建带有额外 CTM 的着色器包装。
- `isConstant(color)`: 查询着色器是否产生恒定颜色。
- `asLuminanceColor(color)`: 获取着色器的平均亮度颜色。
- `asGradient(info, localMatrix)`: 提取渐变着色器参数。
- `Deserialize(data, size, procs)`: 反序列化着色器。
- `RegisterFlattenables()`: 注册所有着色器的扁平化工厂。

### 辅助函数
```cpp
inline SkShaderBase* as_SB(SkShader* shader);
inline const SkShaderBase* as_SB(const SkShader* shader);
inline const SkShaderBase* as_SB(const sk_sp<SkShader>& shader);
```
- 将公共 `SkShader` 转换为 `SkShaderBase`。

## 内部实现细节

### 唯一 ID 生成
```cpp
uint32_t next_unique_id() {
    static std::atomic<uint32_t> gNextUniqueID{SK_InvalidUniqueID + 1};
    // ...
}
```
- 使用原子计数器生成全局唯一的着色器 ID。
- 跳过 `SK_InvalidUniqueID` 值以确保有效性。
- 使用 `memory_order_relaxed` 以获得最佳性能。

### MatrixRec::apply 的管线集成
1. 计算待处理的总矩阵：如果 CTM 未应用则包含 CTM。
2. 求逆并与 `postInv` 复合。
3. 如果 CTM 未应用，先追加 `seed_shader` 操作（设置初始设备坐标）。
4. 追加矩阵变换（如果非单位矩阵则追加 `appendMatrix`）。
5. 返回新的 MatrixRec（pending 重置为 identity，CTM 标记为已应用）。

### Android Framework 兼容性
```cpp
static SkMatrix ConcatLocalMatrices(const SkMatrix& parentLM, const SkMatrix& childLM) {
#if defined(SK_BUILD_FOR_ANDROID_FRAMEWORK)
    return SkMatrix::Concat(childLM, parentLM);  // 反向连接
#endif
    return SkMatrix::Concat(parentLM, childLM);  // 标准连接
}
```
- Android Framework 需要反向矩阵连接顺序 (参见 b/256873449)。

### 遗留上下文系统
`makeContext()` 检查总矩阵是否有透视和可逆性，然后委托给 `onMakeContext()`。该系统受 `SK_ENABLE_LEGACY_SHADERCONTEXT` 宏控制，在未来可能被移除。

## 依赖关系

- `include/core/SkShader.h`: 公共着色器接口。
- `include/core/SkMatrix.h`: 矩阵操作。
- `include/core/SkFlattenable.h`: 序列化基础。
- `src/core/SkRasterPipeline.h`: 光栅管线。
- `src/core/SkColorSpaceXformSteps.h`: 色彩空间转换。
- `src/core/SkEffectPriv.h`: `SkStageRec` 定义。
- `src/shaders/SkLocalMatrixShader.h`: CTM 着色器。

## 设计模式与设计决策

1. **NVI 模式**: 公共方法 (`appendRootStages`, `makeContext`) 处理通用逻辑，虚方法处理特定实现。
2. **矩阵累积器**: `MatrixRec` 避免了在着色器树每层都追加独立的矩阵乘法管线操作。
3. **双管线系统**: 同时支持遗留的 `Context/shadeSpan` 和现代的 `appendStages/SkRasterPipeline` 两种着色管线。
4. **类型枚举**: 使用编译时枚举而非 RTTI 进行类型判断，提高效率。
5. **宏生成枚举**: `SK_ALL_SHADERS` 和 `SK_ALL_GRADIENTS` 宏确保类型列表在多个位置保持一致。

## 性能考量

1. **矩阵合并**: `MatrixRec` 将多个矩阵合并为单个管线操作，减少每像素的矩阵乘法次数。
2. **延迟 seed**: CTM 的 seed 操作延迟到真正需要时执行，避免不必要的坐标初始化。
3. **原子 ID 生成**: 使用 `memory_order_relaxed` 的原子操作，在多线程环境下开销最小。
4. **透视检查**: `makeContext()` 在有透视变换时直接返回 null，避免遗留上下文处理透视的复杂性。
5. **identity 矩阵优化**: `appendMatrix` 在矩阵为 identity 时是空操作。

## 相关文件

- `include/core/SkShader.h`: 公共着色器 API。
- `src/shaders/SkLocalMatrixShader.h/.cpp`: 本地矩阵着色器和 CTM 着色器。
- `src/shaders/SkColorFilterShader.h/.cpp`: 颜色滤镜着色器。
- `src/shaders/SkWorkingColorSpaceShader.h/.cpp`: 工作色彩空间着色器。
- `src/shaders/SkTransformShader.h/.cpp`: 变换着色器。
- `src/core/SkRasterPipeline.h`: 光栅管线。
