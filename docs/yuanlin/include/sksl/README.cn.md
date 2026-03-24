# sksl - SkSL 着色语言 API

## 概述

`include/sksl` 目录定义了 Skia 着色语言（SkSL，Skia Shading Language）的公共 API。
SkSL 是 Skia 自研的着色语言，语法类似于 GLSL（OpenGL Shading Language），但经过
专门设计以适配 Skia 的跨平台图形管线。SkSL 代码可以被编译为 GLSL、Metal Shading
Language、SPIR-V 以及 Skia 内部的软件光栅化管线（SkRP）所使用的字节码。

该目录仅包含两个头文件，定义了 SkSL 的版本信息和调试追踪接口。这些是供
`SkRuntimeEffect`（位于 `include/effects/SkRuntimeEffect.h`）使用的基础类型。
`SkRuntimeEffect` 是 SkSL 面向用户的主要入口点，允许开发者编写自定义着色器、
颜色滤镜和混合器。

SkSL 支持两个版本级别：`k100`（对应 GLSL ES 1.00 / Desktop GLSL 1.10）和 `k300`
（对应 GLSL ES 3.00 / Desktop GLSL 3.30）。默认的运行时效果使用 ES2 级别（k100），
以确保最广泛的硬件兼容性。更高级别的功能（如数组操作和控制流）需要显式启用。

`SkSL::DebugTrace` 提供了着色器执行的调试追踪能力。当与 `SkRuntimeEffect::MakeTraced`
配合使用时，可以记录着色器在特定像素坐标处的执行过程，生成可供调试器使用的完整
执行追踪信息。此功能目前仅在光栅（非 GPU）画布上可用。

## 架构图

```
+------------------------------------------------------------------+
|                         应用层                                     |
|  编写 SkSL 源码，通过 SkRuntimeEffect 创建效果                     |
+------------------------------------------------------------------+
         |
         v
+-------------------+
| SkRuntimeEffect   |    (include/effects/SkRuntimeEffect.h)
| - MakeForShader   |    vec4 main(vec2 coord)
| - MakeForColor    |    vec4 main(vec4 color)
|   Filter          |
| - MakeForBlender  |    vec4 main(vec4 src, vec4 dst)
| - MakeTraced      |    创建带调试追踪的着色器
+-------------------+
         |
    +----+----+
    |         |
    v         v
+--------+ +----------------+
| SkSL:: | | SkSL::         |
| Version| | DebugTrace     |
| 版本   | | 调试追踪        |
+--------+ +----------------+
| k100   | | dump()         |
| k300   | | -> SkWStream   |
+--------+ +----------------+
         |
         v
+-----------------------------------------------------------+
|              SkSL 编译器 (src/sksl/)                        |
|  SkSL 源码 --> IR --> 目标代码                               |
+-----------------------------------------------------------+
    |          |           |           |
    v          v           v           v
+-------+  +-------+  +--------+  +-------+
| GLSL  |  | Metal |  | SPIR-V |  | SkRP  |
| 桌面/  |  | Apple |  | Vulkan |  | 软件  |
| 移动端 |  | 平台  |  |        |  | 管线  |
+-------+  +-------+  +--------+  +-------+
```

## 目录结构

```
include/sksl/
  BUILD.bazel          # Bazel 构建配置
  SkSLVersion.h        # SkSL 版本枚举（k100/k300）
  SkSLDebugTrace.h     # 调试追踪基类
```

## 关键类与函数

### SkSL::Version - 版本枚举

```cpp
enum class Version {
    k100,  // Desktop GLSL 1.10, GLSL ES 1.00, WebGL 1.0
    k300,  // Desktop GLSL 3.30, GLSL ES 3.00, WebGL 2.0
};
```

`k100` 版本是 SkRuntimeEffect 的默认限制级别，提供以下特性：
- 基本数据类型（float、half、int、bool 及其向量/矩阵变体）
- 内置函数（mix、clamp、step、smoothstep、length、normalize 等）
- 子着色器采样（`child.eval(coord)`）
- uniform 变量

`k300` 版本额外提供：
- 更灵活的数组操作
- switch 语句
- 整数位运算
- 更多内置函数

### SkSL::DebugTrace - 调试追踪

```cpp
class DebugTrace : public SkRefCnt {
public:
    virtual void dump(SkWStream* o) const = 0;
};
```

继承自 `SkRefCnt` 的引用计数基类。`dump()` 方法将执行追踪以人类可读的格式
输出到指定的输出流。

配合 `SkRuntimeEffect::MakeTraced()` 使用：

```cpp
struct TracedShader {
    sk_sp<SkShader> shader;
    sk_sp<SkSL::DebugTrace> debugTrace;
};
static TracedShader MakeTraced(sk_sp<SkShader> shader, const SkIPoint& traceCoord);
```

## 依赖关系

- **内部依赖**：`include/core`（SkRefCnt、SkWStream）
- **被依赖**：`include/effects/SkRuntimeEffect.h`（主要用户接口）
- **编译器实现**：`src/sksl/`（SkSL 编译器完整实现）

## 相关文档与参考

- SkSL 语言规范（Skia 官方文档）
- GLSL ES 1.00 规范：https://www.khronos.org/registry/OpenGL/specs/es/2.0/GLSL_ES_Specification_1.00.pdf
- GLSL ES 3.00 规范：https://www.khronos.org/registry/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf
- SkRuntimeEffect API 文档
- 编译器源码位于 `src/sksl/` 目录
- 运行时效果源码位于 `src/core/SkRuntimeEffect.cpp`
