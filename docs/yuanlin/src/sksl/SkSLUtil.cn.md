# SkSL::ShaderCaps / SkSLUtil - SkSL 着色器能力与工具

> 源文件: `src/sksl/SkSLUtil.h`, `src/sksl/SkSLUtil.cpp`

## 概述

`SkSL::ShaderCaps` 是一个描述目标 GPU 着色器能力和驱动程序特性的结构体。SkSL 编译器在编译和代码生成过程中参考这些能力来决定语言特性可用性、是否需要多补丁（polyfill）和是否需要绕过驱动程序缺陷。`SkSLUtil.h` 还提供了 `ShaderCapsFactory`（测试用的预定义能力集）和类型转换工具函数。

## 架构位置

```
SkSL::Compiler
  └── SkSL::Context
        └── SkSL::ShaderCaps (着色器能力描述)

SkSL::ShaderCapsFactory
  ├── Default() (默认测试能力)
  └── Standalone() (独立模式能力)
```

`ShaderCaps` 是编译器配置的核心组成部分，影响词法分析到代码生成的所有阶段。

## 主要类与结构体

### `ShaderCaps`
包含丰富的着色器能力标志，分为以下几类：

**基础能力**
- GLSL 版本 (`fGLSLGeneration`)
- 整数支持、矩阵支持、着色器导数支持
- 精度修饰符、平坦插值、双源混合等

**高级混合**
- `AdvBlendEqInteraction`: 高级混合方程支持级别
- `mustEnableAdvBlendEqs()`: 是否需要声明混合支持

**纹理和采样**
- 外部纹理支持、显式 LOD 支持
- 帧缓冲获取支持及相关配置

**驱动程序缺陷绕过标志**
- `fCanUseMinAndAbsTogether`: min 和 abs 能否一起使用
- `fMustForceNegatedAtanParamToFloat`: atan 参数取反问题
- `fAtan2ImplementedAsAtanYOverX`: atan2 实现缺陷
- `fMustDoOpBetweenFloorAndAbs`: floor 和 abs 之间需要操作
- `fMustGuardDivisionEvenAfterExplicitZeroCheck`: 除法守卫
- `fAddAndTrueToLoopCondition`: 循环条件需要 `&& true`
- `fUnfoldShortCircuitAsTernary`: 短路运算展开为三元
- `fRewriteMatrixVectorMultiply`: 矩阵向量乘法重写
- `fRewriteMatrixComparisons`: 矩阵比较重写
- 等等

### `ShaderCapsFactory`
提供预定义的能力集用于测试：
- `Default()`: GLSL 400，开启着色器导数
- `Standalone()`: 完整能力集（独立编译模式）

## 公共 API 函数

### ShaderCaps 查询
- `mustEnableAdvBlendEqs()`: 是否需要启用高级混合
- `mustDeclareFragmentShaderOutput()`: 是否需要声明片段着色器输出
- `shaderDerivativeExtensionString()`: 导数扩展名称
- `externalTextureExtensionString()`: 外部纹理扩展名称
- `supportedSkSLVerion()`: 支持的 SkSL 版本（100 或 300）
- `supportsDistanceFieldText()`: 是否支持距离场文本

### 工具函数
- `type_to_sksltype(const Context&, const Type&, SkSLType*)`: 将 SkSL 内部类型映射到 `SkSLType` 枚举
- `write_stringstream(const StringStream&, OutputStream&)`: 将 StringStream 内容写入 OutputStream

## 内部实现细节

### 类型映射 (`type_to_sksltype`)
通过逐一匹配 41 种 SkSL 内置类型到对应的 `SkSLType` 枚举值：
```cpp
static_assert(kSkSLTypeCount == 41);
if (type.matches(*context.fTypes.fVoid)) { *outType = SkSLType::kVoid; return true; }
if (type.matches(*context.fTypes.fBool)) { *outType = SkSLType::kBool; return true; }
// ... 39 more types
```

### ShaderCapsFactory 的条件编译
在独立模式或非 Ganesh 构建中，启用更多的默认能力；在 Ganesh 构建中，使用最小化的默认值。

### SkSL 版本确定
```cpp
SkSL::Version supportedSkSLVerion() const {
    if (fShaderDerivativeSupport && fNonsquareMatrixSupport && fIntegerSupport &&
        fGLSLGeneration >= SkSL::GLSLGeneration::k330) {
        return SkSL::Version::k300;
    }
    return SkSL::Version::k100;
}
```
SkSL 300 需要导数、非方阵、整数运算和 GLSL 330 以上版本。

## 依赖关系

- `SkSLVersion.h`: SkSL 版本定义
- `SkSLGLSL.h`: GLSL 版本枚举
- `SkSLBuiltinTypes.h`: 内置类型系统
- `SkSLContext.h`: 编译器上下文
- `SkSLType.h`: SkSL 类型 IR
- `SkSLOutputStream.h` / `SkSLStringStream.h`: 输出流

## 设计模式与设计决策

### 配置对象模式
`ShaderCaps` 是一个纯数据结构体（POD），存储所有能力标志，便于序列化和复制。

### 缺陷数据库
大量的布尔标志本质上是一个 GPU 驱动程序缺陷数据库，每个标志对应一个已知的驱动程序问题和绕过方案。

### 测试支持
`ShaderCapsFactory` 使用 `static` 单例模式（通过 lambda 构造）提供测试用的固定能力集。

### 前向兼容
注释中提到 Graphite 将来可能有自己的能力系统，当前设计允许平滑过渡。

## 性能考量

- `ShaderCaps` 是纯数据结构，查询均为直接成员访问，O(1) 时间
- `type_to_sksltype` 使用线性搜索 41 个类型，但通常在内联后被编译器优化
- `write_stringstream` 直接转发底层字符串数据，无额外拷贝

## 相关文件

- `include/sksl/SkSLVersion.h`: SkSL 版本枚举
- `src/sksl/SkSLGLSL.h`: GLSL 版本枚举
- `src/sksl/SkSLContext.h`: 编译器上下文（持有 ShaderCaps）
- `src/sksl/SkSLCompiler.h`: 编译器（使用 ShaderCaps 指导编译）
- `src/sksl/codegen/SkSLGLSLCodeGenerator.h`: GLSL 代码生成器（大量使用 ShaderCaps）
- `src/gpu/ganesh/GrShaderCaps.h`: Ganesh 的扩展能力类
