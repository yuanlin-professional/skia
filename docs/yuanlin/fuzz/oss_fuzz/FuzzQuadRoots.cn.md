# FuzzQuadRoots (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzQuadRoots.cpp

## 概述

`FuzzQuadRoots.cpp` 是用于 Google OSS-Fuzz 平台的模糊测试入口,专门测试二次方程求根算法。该文件作为 LibFuzzer 的适配器,将 OSS-Fuzz 提供的随机数据转换为 Skia 内部 fuzzer 可识别的格式。二次方程求根是图形几何运算的基础,用于曲线求交、碰撞检测等场景。

## 架构位置

```
skia/fuzz/
  ├── oss_fuzz/
  │   └── FuzzQuadRoots.cpp (本文件 - OSS-Fuzz适配器)
  └── FuzzCommon.cpp (实际测试逻辑)
```

**工作流**: OSS-Fuzz → LLVMFuzzerTestOneInput → fuzz_QuadRoots → 二次求根算法

## 主要类与结构体

### LLVMFuzzerTestOneInput

```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size)
```

LibFuzzer 标准入口点,执行以下逻辑:

1. **输入验证**: 限制数据大小不超过 `4 * sizeof(double)` (32字节)
2. **Fuzz 对象创建**: 将原始数据包装为 `Fuzz` 对象
3. **测试调用**: 调用 `fuzz_QuadRoots` 执行实际测试
4. **返回**: 总是返回 0(继续fuzzing)

## 公共 API 函数

**fuzz_QuadRoots** (在其他文件中定义):
- 解析 fuzz 数据为二次方程系数(a, b, c)
- 调用 Skia 的求根算法
- 验证结果的正确性

## 内部实现细节

### 输入大小限制

```cpp
if (size > 4 * sizeof(double)) {
    return 0;
}
```

**原因**: 二次方程 ax² + bx + c = 0 最多需要 4 个 double 参数(包括可能的额外上下文)。超出此大小的输入无效,直接跳过可提高 fuzzing 效率。

### LibFuzzer 集成

通过 `#if defined(SK_BUILD_FOR_LIBFUZZER)` 条件编译,确保只在 LibFuzzer 构建时包含此代码。

## 依赖关系

- `fuzz/Fuzz.h`: Skia fuzzing 框架
- `fuzz_QuadRoots`: 实际测试函数(链接时提供)
- LibFuzzer: Google 的覆盖率引导模糊测试引擎

## 设计模式与设计决策

### 适配器模式

该文件作为适配器,连接 LibFuzzer 和 Skia 内部 fuzzing 基础设施:
- **LibFuzzer 接口**: `LLVMFuzzerTestOneInput`
- **Skia 接口**: `fuzz_QuadRoots(Fuzz*)`

### 输入过滤

通过预先检查输入大小,避免处理无效数据,提高 fuzzing 吞吐量。

## 性能考量

- **轻量级封装**: 最小开销的数据转换
- **早期退出**: 无效输入立即返回
- **覆盖率引导**: LibFuzzer 自动关注高覆盖率的输入变异

## 相关文件

- `fuzz/FuzzQuadRoots.cpp`: 独立 fuzzer 版本
- `fuzz/FuzzCommon.cpp`: `fuzz_QuadRoots` 实现
- `src/pathops/SkPathOpsQuad.cpp`: 二次方程求根实现

**OSS-Fuzz 构建**:
```bash
# 由 OSS-Fuzz 基础设施自动编译和运行
export CC=clang
export CXX=clang++
export CFLAGS="-fsanitize=fuzzer-no-link"
export CXXFLAGS="-fsanitize=fuzzer-no-link"
./build_fuzzers.sh
```

该文件是 Skia 与 Google OSS-Fuzz 持续模糊测试基础设施集成的关键部分,每天在数千台服务器上运行,自动发现潜在的安全漏洞和稳定性问题。
