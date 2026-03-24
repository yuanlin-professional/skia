# SkSLNativeShader

> 源文件: src/sksl/codegen/SkSLNativeShader.h

## 概述

`SkSLNativeShader` 是 Skia 图形库中用于存储原生着色器代码的轻量级数据结构。它定义在 `SkSL` 命名空间中，作为不同着色器后端（Metal、GLSL、HLSL、SPIR-V 等）的统一输出容器。

该结构体设计简洁，只包含两个成员：一个用于存储文本形式的着色器代码（如 Metal、GLSL、HLSL），另一个用于存储二进制形式的着色器代码（目前主要用于 SPIR-V）。通过检查哪个字段非空，可以判断着色器是以文本还是二进制形式存储的。

这个结构体是 SkSL 编译器各个后端代码生成器的统一输出接口，使得上层代码可以用相同的方式处理不同格式的着色器输出。

## 架构位置

`SkSLNativeShader` 在 Skia 着色器编译架构中扮演着接口层的角色，位于代码生成器和着色器消费者之间：

```
SkSL 源代码 → SkSL 编译器 → SkSL IR → [代码生成器]
                                        ├─ ToMetal()   → NativeShader { fText }
                                        ├─ ToGLSL()    → NativeShader { fText }
                                        ├─ ToHLSL()    → NativeShader { fText }
                                        └─ ToSPIRV()   → NativeShader { fBinary }
                                                ↓
                                        NativeShader ← 统一接口
                                                ↓
                                        [着色器使用者]
                                        ├─ GPU 驱动程序
                                        ├─ 图形 API 包装器
                                        └─ 着色器缓存系统
```

**位置特点：**

1. **统一输出接口**：所有后端代码生成器都可以输出到 `NativeShader`
2. **格式无关**：调用者不需要关心底层是文本还是二进制格式
3. **轻量级**：仅包含数据成员，无复杂逻辑

## 主要类与结构体

### NativeShader 结构体

```cpp
struct NativeShader {
    std::string fText;              // 文本形式的着色器代码
    std::vector<uint32_t> fBinary;  // 二进制形式的着色器代码

    bool isBinary() const { return !fBinary.empty(); }
};
```

**成员说明：**

#### fText

- **类型**：`std::string`
- **用途**：存储文本形式的着色器代码
- **适用后端**：Metal、GLSL、HLSL 等文本着色器语言
- **特点**：人类可读，便于调试和日志记录

#### fBinary

- **类型**：`std::vector<uint32_t>`
- **用途**：存储二进制形式的着色器字节码
- **适用后端**：SPIR-V（当前唯一的二进制格式后端）
- **特点**：紧凑高效，直接由驱动程序消费

#### isBinary() 方法

```cpp
bool isBinary() const { return !fBinary.empty(); }
```

- **功能**：判断着色器是否以二进制形式存储
- **返回值**：如果 `fBinary` 非空返回 `true`，否则返回 `false`
- **使用场景**：调用者根据返回值决定读取 `fText` 还是 `fBinary`

## 公共 API 函数

`NativeShader` 是一个纯数据结构（POD-like），只有一个公共方法：

### isBinary()

```cpp
bool isBinary() const {
    return !fBinary.empty();
}
```

**用途：** 判断着色器格式类型

**使用示例：**

```cpp
SkSL::NativeShader shader;
// ... 通过某个代码生成器填充 shader ...

if (shader.isBinary()) {
    // 处理二进制格式（SPIR-V）
    uploadToDriver(shader.fBinary.data(), shader.fBinary.size());
} else {
    // 处理文本格式（Metal/GLSL/HLSL）
    compileAndUpload(shader.fText.c_str());
}
```

## 内部实现细节

### 设计理念

`NativeShader` 采用了极简设计哲学：

1. **零成本抽象**：没有虚函数，没有额外开销
2. **内存安全**：使用标准库容器（`std::string` 和 `std::vector`）自动管理内存
3. **类型安全**：通过类型系统区分文本和二进制数据

### 互斥性约定

虽然结构体允许同时填充 `fText` 和 `fBinary`，但按照约定，代码生成器应该只填充其中一个：

- **文本后端**：只填充 `fText`，保持 `fBinary` 为空
- **二进制后端**：只填充 `fBinary`，保持 `fText` 为空

这种互斥性通过使用约定而非语言机制强制执行，提供了灵活性但也要求开发者遵守约定。

### SPIR-V 的特殊性

SPIR-V 是当前唯一使用二进制格式的后端：

```cpp
// SPIR-V 代码生成器
bool ToSPIRV(Program& program, const ShaderCaps* caps, NativeShader* out) {
    std::vector<uint32_t> spirv;
    if (!ToSPIRV(program, caps, &spirv, nullptr)) {
        return false;
    }
    out->fBinary = std::move(spirv);  // 使用移动语义避免拷贝
    return true;
}
```

SPIR-V 使用 `uint32_t` 作为基本单位，因为 SPIR-V 规范要求所有指令和数据都是 32 位对齐的。

### 文本格式示例

Metal/GLSL/HLSL 后端将生成的代码存储在 `fText` 中：

```cpp
// Metal 代码生成器
bool ToMetal(Program& program, const ShaderCaps* caps, NativeShader* out) {
    StringStream stream;
    if (!ToMetal(program, caps, &stream)) {
        return false;
    }
    out->fText = stream.str();
    return true;
}
```

## 依赖关系

### 头文件依赖

`SkSLNativeShader.h` 只依赖标准库头文件：

```cpp
#include <cstdint>      // uint32_t 类型定义
#include <string>       // std::string
#include <vector>       // std::vector
```

这使得 `NativeShader` 成为一个非常轻量的接口，可以在 Skia 的各个层级使用，而不引入复杂的依赖关系。

### 使用者

**代码生成器（生产者）：**
- `SkSLMetalCodeGenerator`：生成 Metal 代码，填充 `fText`
- `SkSLGLSLCodeGenerator`：生成 GLSL 代码，填充 `fText`
- `SkSLHLSLCodeGenerator`：生成 HLSL 代码，填充 `fText`
- `SkSLSPIRVCodeGenerator`：生成 SPIR-V 字节码，填充 `fBinary`

**着色器消费者（消费者）：**
- GPU 驱动程序包装器
- 着色器缓存系统
- 着色器编译管道
- 调试和分析工具

### 相关类型

- `SkSL::Program`：SkSL 程序的输入表示
- `ShaderCaps`：着色器能力查询接口
- `OutputStream`：流式输出接口（某些代码生成器使用）

## 设计模式与设计决策

### 联合体的替代方案

`NativeShader` 本质上是一个"类型安全的联合体"（tagged union）的变体。在 C++ 中，可以用 `std::variant<std::string, std::vector<uint32_t>>` 实现类似功能，但 `NativeShader` 的设计更简单直观：

**选择两个成员而非 variant 的理由：**

1. **简单性**：无需引入 C++17 特性或 Boost
2. **向后兼容**：与旧代码兼容
3. **访问便利**：无需 `std::get` 或 `std::visit`
4. **清晰性**：`fText` 和 `fBinary` 名称直观

### 值语义

`NativeShader` 使用值语义而非引用语义：

```cpp
// 值语义，支持拷贝和移动
NativeShader shader1 = generateShader();
NativeShader shader2 = shader1;  // 拷贝
NativeShader shader3 = std::move(shader1);  // 移动
```

这简化了内存管理，但对于大型着色器代码，拷贝可能有性能开销。实践中，通常使用移动语义或智能指针传递。

### 开放式扩展

如果将来需要支持新的二进制格式（如 DXIL、WGSL 字节码），可以扩展结构体：

```cpp
struct NativeShader {
    std::string fText;
    std::vector<uint32_t> fBinary;
    // 未来可以添加：
    // std::vector<uint8_t> fDXIL;
    // std::vector<uint32_t> fWGSL;
};
```

但当前设计假设只有两种格式（文本/二进制），因此保持简洁。

### 零初始化

标准库容器的默认构造函数会创建空容器，因此 `NativeShader` 的默认实例处于明确的"空"状态：

```cpp
NativeShader shader;
// shader.fText 是空字符串
// shader.fBinary 是空向量
// shader.isBinary() 返回 false
```

## 性能考量

### 内存分配

`std::string` 和 `std::vector` 会动态分配内存：

- **小字符串优化（SSO）**：短字符串可能不分配堆内存
- **向量预留**：可以通过 `reserve()` 预分配内存减少重新分配

对于大型着色器代码，内存分配可能占用可观的时间。

### 移动语义

C++11 的移动语义允许高效传递 `NativeShader`：

```cpp
NativeShader generateShader() {
    NativeShader shader;
    shader.fText = "...";  // 大字符串
    return shader;  // 移动，不拷贝
}
```

现代编译器会自动优化，避免不必要的拷贝。

### 二进制格式的优势

SPIR-V 使用二进制格式的优势：

1. **更快的解析**：二进制比文本解析更快
2. **更小的体积**：二进制通常比文本紧凑
3. **无歧义**：避免文本解析的边界情况

但文本格式便于调试和人工检查。

### 缓存友好性

`std::vector<uint32_t>` 提供连续内存布局，对缓存友好。着色器驱动程序通常期望连续的字节流，这使得 `fBinary` 可以直接传递给驱动程序 API。

## 相关文件

### 代码生成器头文件

- `SkSLMetalCodeGenerator.h`：定义 `ToMetal(..., NativeShader*)` 重载
- `SkSLGLSLCodeGenerator.h`：定义 `ToGLSL(..., NativeShader*)` 重载
- `SkSLHLSLCodeGenerator.h`：定义 `ToHLSL(..., NativeShader*)` 重载
- `SkSLSPIRVCodeGenerator.h`：定义 `ToSPIRV(..., NativeShader*)` 重载

### 实现文件

- `SkSLMetalCodeGenerator.cpp`：实现 Metal 代码生成逻辑
- `SkSLGLSLCodeGenerator.cpp`：实现 GLSL 代码生成逻辑
- `SkSLHLSLCodeGenerator.cpp`：实现 HLSL 代码生成逻辑
- `SkSLSPIRVCodeGenerator.cpp`：实现 SPIR-V 生成逻辑

### 使用者

- `SkSLCompiler.h/cpp`：SkSL 编译器主接口
- `GrShaderCaps.h`：GPU 着色器能力查询
- 各种 GPU 后端实现（Ganesh、Graphite）

### 相关工具

- `SkSLToBackend.h`：提供统一的后端转换接口
- 着色器缓存系统：使用 `NativeShader` 存储编译结果

### 测试

- `tests/SkSLTest.cpp`：SkSL 编译器测试
- `tests/sksl/`：各种 SkSL 测试用例，间接测试 `NativeShader`
