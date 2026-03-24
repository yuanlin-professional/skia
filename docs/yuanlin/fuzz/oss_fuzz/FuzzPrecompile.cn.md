# FuzzPrecompile

> 源文件: fuzz/oss_fuzz/FuzzPrecompile.cpp

## 概述

`FuzzPrecompile.cpp` 是 Skia 中用于模糊测试着色器预编译功能的工具。该模块通过 OSS-Fuzz 框架对 Skia 的着色器预编译管线进行自动化安全测试,验证在处理各种着色器配置和组合时的稳定性。预编译功能是 Skia Graphite 渲染管线的重要组成部分,用于提前编译着色器以减少运行时开销。

## 架构位置

- **路径**: `fuzz/oss_fuzz/FuzzPrecompile.cpp`
- **模块层次**: 测试工具层 > 模糊测试子系统 > OSS-Fuzz 集成
- **测试目标**: 着色器预编译功能

## 主要类与结构体

### 核心函数

#### `fuzz_Precompile`
```cpp
void fuzz_Precompile(Fuzz* f);
```
**功能**: 执行着色器预编译的模糊测试(外部定义)

#### `LLVMFuzzerTestOneInput`
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
```
**功能**: LibFuzzer 入口点,输入限制 4000 字节

#### `__lsan_default_options`
```cpp
const char *__lsan_default_options()
```
**功能**: 配置 LeakSanitizer 选项
**配置**: 设置 `print_suppressions=0` 以减少输出噪音

## 公共 API 函数

使用的 Skia API(通过 `fuzz_Precompile`):
- Graphite 预编译接口
- 着色器组合生成
- 字体管理相关功能

## 内部实现细节

### LSAN 配置

```cpp
const char *__lsan_default_options() {
    // Don't print the list of LSAN suppressions on every execution.
    return "print_suppressions=0";
}
```

**设计理念**:
- LeakSanitizer(LSAN)用于检测内存泄漏
- 禁用 suppression 列表打印,减少日志噪音
- 提高模糊测试的可读性

### 可移植字体管理

```cpp
ToolUtils::UsePortableFontMgr();
```
确保字体相关的着色器生成在不同平台上一致。

### extern "C" 块

```cpp
extern "C" {
    // 函数定义
}
```
**目的**: 确保 C 链接约定,与 LibFuzzer 和 LSAN 运行时兼容。

## 依赖关系

- `fuzz/Fuzz.h`: 模糊测试框架
- `tools/fonts/FontToolUtils.h`: 字体管理工具
- Graphite 预编译模块(可能在 `src/gpu/graphite/`)

## 设计模式与设计决策

### 1. Sanitizer 集成

**设计决策**: 显式配置 LSAN 选项
**优点**:
- 优化测试输出
- 保留泄漏检测功能
- 提高开发者体验

### 2. 环境标准化

使用可移植字体管理器确保测试可重现性。

## 性能考量

### 1. 预编译的性能特性

**操作**:
- 着色器组合枚举
- 编译器调用
- 缓存管理

**输入限制**: 4000 字节控制组合复杂度

### 2. LSAN 开销

LeakSanitizer 会增加内存跟踪开销,但对于检测内存泄漏至关重要。

## 相关文件

1. **`fuzz/fuzz_precompile.cpp`**: `fuzz_Precompile` 实现
2. **`src/gpu/graphite/Precompile.h`**: 预编译接口
3. **`tests/PrecompileTest.cpp`**: 预编译单元测试

该模糊测试器为 Skia 的着色器预编译功能提供了安全性测试,确保在处理各种着色器组合时的稳定性,并通过 LSAN 集成检测潜在的内存泄漏问题。
