# FuzzNullCanvas

> 源文件: fuzz/oss_fuzz/FuzzNullCanvas.cpp

## 概述

`FuzzNullCanvas.cpp` 是 Skia 中用于模糊测试 Null Canvas 的工具。Null Canvas 是一种特殊的画布实现,它接收所有绘制命令但不产生任何实际输出,主要用于测试绘制 API 的调用稳定性而无需实际渲染开销。该模块通过 OSS-Fuzz 框架对 Null Canvas 的接口进行自动化安全测试,验证在接收任意绘制命令序列时的稳定性,专注于 API 层面的错误检测。

## 架构位置

- **路径**: `fuzz/oss_fuzz/FuzzNullCanvas.cpp`
- **模块层次**: 测试工具层 > 模糊测试子系统 > OSS-Fuzz 集成
- **测试目标**: Null Canvas 绘制接口

## 主要类与结构体

### 核心函数

#### `fuzz_NullCanvas`
```cpp
void fuzz_NullCanvas(Fuzz* f);
```
**功能**: 执行 Null Canvas 的模糊测试(外部定义),生成随机绘制命令并应用于 Null Canvas

#### `LLVMFuzzerTestOneInput`
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
```
**功能**: LibFuzzer 入口点,输入限制 4000 字节,设置可移植字体管理器

## 公共 API 函数

使用的 Skia API:
- `SkNullCanvas` 或类似的 Null Canvas 实现
- 标准 `SkCanvas` 绘制方法
- `ToolUtils::UsePortableFontMgr()`: 可移植字体管理

## 内部实现细节

### 测试流程
```
输入数据 → Fuzz 对象 → 设置字体管理器
  → fuzz_NullCanvas
  → 生成随机绘制命令
  → 应用于 Null Canvas
  → 验证 API 调用稳定性
```

### Null Canvas 的优势

**性能优势**:
- 无实际渲染开销
- 无内存分配(像素缓冲区)
- 快速测试吞吐量

**测试焦点**:
- API 调用序列的合法性
- 参数验证逻辑
- 状态管理正确性

### 可移植字体管理

```cpp
ToolUtils::UsePortableFontMgr();
```
确保文本相关的绘制命令在不同平台上行为一致。

## 依赖关系

- `fuzz/Fuzz.h`: 模糊测试框架
- `tools/fonts/FontToolUtils.h`: 字体管理工具
- Null Canvas 实现(可能在 `tools/` 或 `src/utils/`)

## 设计模式与设计决策

### 1. 空对象模式(Null Object Pattern)

Null Canvas 是空对象模式的典型应用:
- 实现完整的 `SkCanvas` 接口
- 所有操作都是空操作(no-op)
- 避免 if-null 检查

### 2. 专注于 API 层

**设计理念**: 将测试重点放在 API 调用逻辑,而非渲染正确性
**优点**:
- 更高的测试吞吐量
- 发现 API 层面的缺陷
- 补充实际渲染测试

## 性能考量

### 1. 零渲染开销

**最大优势**: Null Canvas 无任何渲染成本
**效果**: 可以在相同时间内测试更多的命令组合

### 2. 输入大小限制

4000 字节足以生成复杂的绘制命令序列

## 相关文件

1. **`fuzz/fuzz_canvas.cpp`**: 包含 `fuzz_NullCanvas` 实现
2. **`tools/debugger/DebugCanvas.h`**: 另一种特殊 Canvas 实现
3. **`fuzz/oss_fuzz/FuzzCanvas.cpp`**: 通用 Canvas 测试
4. **`fuzz/oss_fuzz/FuzzAPISVGCanvas.cpp`**: SVG Canvas 测试

该模糊测试器通过零开销的测试策略,为 Skia 的 Canvas API 提供了高效的安全性测试,专注于接口层面的稳定性验证。
