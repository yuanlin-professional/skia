# FuzzSKSL2Pipeline

> 源文件: fuzz/oss_fuzz/FuzzSKSL2Pipeline.cpp

## 概述

`FuzzSKSL2Pipeline.cpp` 是 Skia 中用于模糊测试 SkSL 到 Pipeline Stage 代码生成器的工具。该模块通过 OSS-Fuzz 框架对 SkSL 编译器的 Pipeline Stage 后端进行自动化安全测试,验证将 SkSL 代码转换为 Pipeline Stage 格式的稳定性。模糊测试器将字节流作为 SkSL 运行时着色器代码输入,测试编译和代码生成过程,以发现编译器崩溃、断言失败和代码生成错误。

## 架构位置

- **路径**: `fuzz/oss_fuzz/FuzzSKSL2Pipeline.cpp`
- **模块层次**: 测试工具层 > 模糊测试子系统 > OSS-Fuzz 集成
- **测试目标**: SkSL 编译器的 Pipeline Stage 代码生成器
- **依赖关系**: 依赖 SkSL 编译器基础设施

## 主要类与结构体

### 核心函数

#### `FuzzSKSL2Pipeline`
```cpp
bool FuzzSKSL2Pipeline(const uint8_t *data, size_t size)
```

**功能**: 执行 SkSL 到 Pipeline Stage 的转换测试
- **参数**: 输入字节流作为 SkSL 源代码
- **返回值**: 编译和转换是否成功
- **核心逻辑**:
  1. 将字节流转换为 SkSL 源代码字符串
  2. 使用 `SkSL::Compiler` 编译为 `Program`
  3. 创建 `Callbacks` 实现处理代码生成回调
  4. 调用 `PipelineStage::ConvertProgram` 生成 Pipeline Stage 代码

### Callbacks 内部类

```cpp
class Callbacks : public SkSL::PipelineStage::Callbacks
```

**功能**: 实现 Pipeline Stage 代码生成的回调接口
**主要方法**:
- `declareUniform()`: 声明 uniform 变量
- `defineFunction()`: 定义函数
- `declareFunction()`: 声明函数
- `defineStruct()`: 定义结构体
- `declareGlobal()`: 声明全局变量
- `sampleShader()`: 生成着色器采样代码
- `sampleColorFilter()`: 生成颜色滤镜采样代码
- `sampleBlender()`: 生成混合器采样代码
- `toLinearSrgb()` / `fromLinearSrgb()`: 颜色空间转换

## 公共 API 函数

使用的 SkSL API:
- `SkSL::Compiler`: SkSL 编译器
- `SkSL::ProgramKind::kRuntimeShader`: 运行时着色器程序类型
- `SkSL::PipelineStage::ConvertProgram()`: 转换为 Pipeline Stage 格式
- `SkSL::VarDeclaration` / `Variable`: 变量声明和引用

## 内部实现细节

### 测试流程

```
输入字节流
    ↓
转换为 SkSL 源代码字符串
    ↓
SkSL::Compiler::convertProgram
    ↓
编译为 Program 对象
    ↓
创建 Callbacks 实现
    ↓
PipelineStage::ConvertProgram
    ↓
生成 Pipeline Stage 代码(通过回调)
```

### 编译配置

```cpp
SkSL::ProgramSettings settings;
std::unique_ptr<SkSL::Program> program =
        compiler.convertProgram(SkSL::ProgramKind::kRuntimeShader,
                                std::string(reinterpret_cast<const char*>(data), size),
                                settings);
```

**关键点**:
- 使用 `kRuntimeShader` 程序类型
- 默认的 `ProgramSettings`(无特殊配置)

### Callbacks 实现细节

#### Uniform 声明
```cpp
std::string declareUniform(const SkSL::VarDeclaration* decl) override {
    return std::string(decl->var()->name());
}
```
**策略**: 返回变量名作为 uniform 声明

#### 子对象采样
```cpp
std::string sampleShader(int index, std::string coords) override {
    return "child_" + std::to_string(index) + ".eval(" + coords + ")";
}
```
**策略**: 生成标准的子着色器调用代码

#### 空操作实现
```cpp
void defineFunction(const char*, const char*, bool) override {}
void declareFunction(const char*) override {}
void defineStruct(const char*) override {}
void declareGlobal(const char*) override {}
```
**设计理念**: 不实际生成代码,仅验证编译器不崩溃

### Pipeline Stage 转换

```cpp
SkSL::PipelineStage::ConvertProgram(*program, "coords", "inColor", "half4(1)", &callbacks);
```

**参数说明**:
- `*program`: 编译后的 SkSL 程序
- `"coords"`: 坐标变量名
- `"inColor"`: 输入颜色变量名
- `"half4(1)"`: 默认颜色值
- `&callbacks`: 代码生成回调实现

### 输入大小限制

```cpp
if (size > 3000) {
    return 0;
}
```

限制为 3000 字节,控制编译时间。

## 依赖关系

**SkSL 编译器模块**:
- `src/sksl/SkSLCompiler.h`: 编译器主类
- `src/sksl/SkSLProgramKind.h`: 程序类型枚举
- `src/sksl/SkSLProgramSettings.h`: 编译配置
- `src/sksl/codegen/SkSLPipelineStageCodeGenerator.h`: Pipeline Stage 代码生成器
- `src/sksl/ir/SkSLProgram.h`: 程序 IR
- `src/sksl/ir/SkSLVarDeclarations.h`: 变量声明 IR
- `src/sksl/ir/SkSLVariable.h`: 变量 IR

**模糊测试框架**:
- `fuzz/Fuzz.h`: 模糊测试基础设施(头文件引入)

## 设计模式与设计决策

### 1. 回调模式(Callback Pattern)

**设计决策**: 使用回调接口处理代码生成
**优点**:
- 解耦编译器和代码生成
- 灵活支持不同的后端
- 便于测试和模拟

### 2. 最小化验证策略

**设计决策**: Callbacks 不实际生成完整代码,仅返回占位符
**理由**:
- 专注于测试编译器稳定性
- 避免复杂的代码生成逻辑干扰测试
- 提高测试效率

### 3. 标准化接口

**子对象采样**:
```cpp
"child_" + std::to_string(index) + ".eval(...)"
```
**优点**: 生成一致格式的代码,便于验证

### 4. 早期退出

```cpp
if (!program) {
    return false;
}
```
编译失败时提前退出,避免后续无效操作。

## 性能考量

### 1. 编译时间控制

**输入大小限制**: 3000 字节
**影响因素**:
- 代码复杂度(嵌套、循环)
- 函数数量
- 符号表大小

### 2. 最小化代码生成开销

**策略**: Callbacks 实现极简,避免实际字符串拼接和复杂逻辑
**效果**: 将测试重点放在编译器,而非后端代码生成

### 3. 内存管理

**智能指针**: 使用 `std::unique_ptr<SkSL::Program>` 自动管理程序对象
**优点**: 避免内存泄漏,简化资源管理

## 相关文件

### SkSL 编译器核心

1. **`src/sksl/SkSLCompiler.cpp`**
   - 编译器实现

2. **`src/sksl/codegen/SkSLPipelineStageCodeGenerator.cpp`**
   - Pipeline Stage 代码生成器实现

3. **`src/sksl/ir/SkSLProgram.h`**
   - 程序 IR 定义

### 同类型测试器

4. **`fuzz/oss_fuzz/FuzzSKSL2GLSL.cpp`** (如果存在)
   - 测试 GLSL 后端

5. **`fuzz/oss_fuzz/FuzzSKSL2Metal.cpp`** (如果存在)
   - 测试 Metal 后端

6. **`fuzz/oss_fuzz/FuzzSkRuntimeBlender.cpp`**
   - 测试运行时混合器(使用 SkSL)

### 测试文件

7. **`tests/SkSLTest.cpp`**
   - SkSL 编译器的单元测试

8. **`resources/sksl/` 目录**
   - SkSL 测试用例

### 构建配置

9. **`BUILD.gn`** (相关部分)
   - 定义 `fuzz_sksl2pipeline` 目标

该模糊测试器为 Skia 的 SkSL 编译器 Pipeline Stage 后端提供了全面的安全性测试,确保在处理任意 SkSL 代码时的稳定性,是着色器编译基础设施的重要质量保障。
