# GrGLGLSL

> 源文件: src/gpu/ganesh/gl/GrGLGLSL.h, src/gpu/ganesh/gl/GrGLGLSL.cpp

## 概述

`GrGLGLSL` 模块提供 OpenGL 着色器语言(GLSL)版本检测功能,是 Skia 图形库 Ganesh OpenGL 后端中负责确定着色器编译目标版本的核心工具。该模块根据 OpenGL/OpenGL ES/WebGL 的版本信息,推断出最合适的 GLSL 版本代次(Generation),并处理各种边缘情况和驱动兼容性问题。

该模块的主要任务是将底层 OpenGL 的复杂版本信息映射为 Skia 内部统一的 GLSL 版本枚举,为着色器编译器提供正确的版本指令。

## 架构位置

`GrGLGLSL` 位于 Skia GPU 渲染架构的 OpenGL 工具层:

```
skia/
└── src/gpu/ganesh/gl/
    ├── GrGLGLSL.h/cpp     <- 本模块
    ├── GrGLUtil.h         <- OpenGL 工具函数
    ├── GrGLContext.cpp    <- 使用本模块确定 GLSL 版本
    └── GrGLTypes.h        <- OpenGL 类型定义
```

该模块被 `GrGLContext` 在初始化时调用,用于确定上下文的 GLSL 版本。

## 主要类与结构体

### 无类定义

该模块仅提供自由函数,不定义任何类或结构体。

### 相关数据结构

| 类型 | 定义位置 | 说明 |
|------|---------|------|
| `GrGLDriverInfo` | `GrGLUtil.h` | 包含 OpenGL 版本、GLSL 版本、标准类型等驱动信息 |
| `SkSL::GLSLGeneration` | `src/sksl/SkSLGLSL.h` | GLSL 版本枚举(k110, k330, k100es 等) |

## 公共 API 函数

### GrGLGetGLSLGeneration

```cpp
bool GrGLGetGLSLGeneration(const GrGLDriverInfo& info,
                           SkSL::GLSLGeneration* generation);
```

**功能**: 根据驱动信息确定 GLSL 版本代次

**参数**:
- `info`: OpenGL 驱动信息,包含 GL 版本、GLSL 版本、标准类型
- `generation`: 输出参数,返回推断的 GLSL 版本

**返回值**:
- `true`: 成功确定 GLSL 版本
- `false`: 版本无效或不支持

**支持的 GLSL 版本**:

#### Desktop OpenGL
- `k110` - GLSL 1.10
- `k130` - GLSL 1.30
- `k140` - GLSL 1.40
- `k150` - GLSL 1.50
- `k330` - GLSL 3.30
- `k400` - GLSL 4.00
- `k420` - GLSL 4.20

#### OpenGL ES
- `k100es` - GLSL ES 1.00
- `k300es` - GLSL ES 3.00
- `k310es` - GLSL ES 3.10
- `k320es` - GLSL ES 3.20

#### WebGL
- `k100es` - WebGL 1.0 (GLSL ES 1.00)
- `k300es` - WebGL 2.0 (GLSL ES 3.00)

## 内部实现细节

### 版本映射算法

#### 1. Adreno 308 驱动修正

针对 Adreno 308 设备上的版本报告 bug:

```cpp
uint32_t glMajor = GR_GL_MAJOR_VER(info.fVersion);
uint32_t glMinor = GR_GL_MINOR_VER(info.fVersion);
GrGLSLVersion ver = std::min(info.fGLSLVersion, GR_GLSL_VER(glMajor, 10 * glMinor));
```

**问题**: Adreno 308 在 Android 9 上报告 GL 3.0 但 GLSL 3.1,使用 310 着色器会失败。

**解决方案**: 将 GLSL 版本限制为不超过 GL 版本对应的 GLSL 版本(GL 3.0 对应 GLSL 3.0)。

**版本映射逻辑**:
- GL 主版本号 × 100 + 次版本号 × 10 = GLSL 版本号
- 例: GL 3.0 → GLSL 300

#### 2. Desktop OpenGL 版本判定

```cpp
if (GR_IS_GR_GL(info.fStandard)) {
    if (ver >= GR_GLSL_VER(4,20))      return k420;
    else if (ver >= GR_GLSL_VER(4,00)) return k400;
    else if (ver >= GR_GLSL_VER(3,30)) return k330;
    else if (ver >= GR_GLSL_VER(1,50)) return k150;
    else if (ver >= GR_GLSL_VER(1,40)) return k140;
    else if (ver >= GR_GLSL_VER(1,30)) return k130;
    else                               return k110;
}
```

**特点**: 向下兼容,选择最高支持的版本代次。

#### 3. OpenGL ES 版本判定

```cpp
if (GR_IS_GR_GL_ES(info.fStandard)) {
    if (ver >= GR_GLSL_VER(3,20))      return k320es;
    else if (ver >= GR_GLSL_VER(3,10)) return k310es;
    else if (ver >= GR_GLSL_VER(3,00)) return k300es;
    else                               return k100es;
}
```

**断言检查**: `SkASSERT(ver >= GR_GLSL_VER(1,00))` - 确保至少支持 GLSL ES 1.00。

#### 4. WebGL 版本判定

```cpp
if (GR_IS_GR_WEBGL(info.fStandard)) {
    if (ver >= GR_GLSL_VER(2,0)) return k300es;  // WebGL 2.0
    else                         return k100es;  // WebGL 1.0
}
```

**映射关系**:
- WebGL 1.0 (GLSL 1.0) → GLSL ES 1.00
- WebGL 2.0 (GLSL 2.0) → GLSL ES 3.00

### 错误处理

```cpp
if (info.fGLSLVersion == GR_GLSL_INVALID_VER) {
    return false;
}
```

拒绝无效的 GLSL 版本,防止后续错误。

### 版本号宏定义

```cpp
#define GR_GLSL_VER(major, minor) ((major) * 100 + (minor))
#define GR_GL_MAJOR_VER(version) ((version) / 100)
#define GR_GL_MINOR_VER(version) (((version) / 10) % 10)
```

**示例**:
- `GR_GLSL_VER(3, 30)` → 330
- `GR_GL_MAJOR_VER(330)` → 3
- `GR_GL_MINOR_VER(330)` → 3

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLUtil.h` | `GrGLDriverInfo` 结构体定义,版本宏 |
| `GrGLTypes.h` | OpenGL 类型定义(`GrGLSLVersion`) |
| `SkSL::GLSLGeneration` | GLSL 版本枚举定义 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLContext` | 在 `Make()` 中调用 `GrGLGetGLSLGeneration()` |
| `GrGLCaps` | 使用 GLSL 版本确定着色器功能 |
| `GrGLProgram` | 使用 GLSL 版本生成着色器代码 |

## 设计模式与设计决策

### 1. 自由函数设计

选择自由函数而非类成员函数:

**优点**:
- 无状态,易于测试
- 避免不必要的对象创建
- 清晰的输入输出语义

**适用性**: 该模块仅执行纯计算,无需维护状态。

### 2. 向下兼容策略

使用 `>=` 而非 `==` 进行版本比较:

```cpp
if (ver >= GR_GLSL_VER(4,20)) *generation = k420;
```

**设计理念**: 选择最高的兼容版本,充分利用硬件功能。

### 3. 版本约束机制

针对 Adreno 308 bug 的修正使用 `std::min`:

```cpp
GrGLSLVersion ver = std::min(info.fGLSLVersion, GR_GLSL_VER(glMajor, 10 * glMinor));
```

**设计思想**: 保守估计,避免使用不受支持的版本。

### 4. 三路分支判定

根据 OpenGL 标准类型分为三个独立分支:

- Desktop GL
- OpenGL ES
- WebGL

**优点**: 清晰的逻辑分离,易于维护和扩展。

### 5. 错误优先处理

在开始版本判定前先检查无效版本:

```cpp
if (info.fGLSLVersion == GR_GLSL_INVALID_VER) {
    return false;
}
```

**设计理念**: 快速失败,避免在无效数据上浪费计算。

## 性能考量

### 1. 纯计算函数

无副作用,无 IO 操作:

- **时间复杂度**: O(1)
- **调用成本**: 几十个 CPU 周期
- **调用频率**: 仅在上下文初始化时调用一次

### 2. 版本号比较优化

使用整数比较而非字符串解析:

```cpp
ver >= GR_GLSL_VER(4,20)  // 整数比较,极快
```

**优势**: 避免字符串解析的开销,编译器可内联优化。

### 3. 分支预测友好

使用 `if-else if-else` 链:

```cpp
if (ver >= 420)      return k420;
else if (ver >= 400) return k400;
// ...
```

**优化效果**: 现代 CPU 可有效预测分支,降低流水线停顿。

### 4. 无内存分配

整个函数不进行任何堆内存分配:

- 所有操作在栈上完成
- 无 GC 压力
- 确定性执行时间

### 5. 常量折叠

版本号宏在编译时展开:

```cpp
GR_GLSL_VER(4,20)  // 编译时计算为 420
```

**优势**: 零运行时成本。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/ganesh/gl/GrGLContext.cpp` | 调用本模块确定 GLSL 版本 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | 提供版本宏和驱动信息结构 |
| `include/gpu/ganesh/gl/GrGLTypes.h` | OpenGL 类型定义 |
| `src/sksl/SkSLGLSL.h` | GLSL 版本枚举定义 |
| `src/gpu/ganesh/gl/GrGLCaps.cpp` | 使用 GLSL 版本确定功能集合 |
| `src/gpu/ganesh/gl/builders/GrGLShaderStringBuilder.cpp` | 使用 GLSL 版本生成 `#version` 指令 |
