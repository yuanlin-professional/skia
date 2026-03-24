# SkSpan

> 源文件: `include/core/SkSpan.h`

## 概述
SkSpan 是 Skia 对连续内存区域的轻量级视图封装，类似于 C++20 的 `std::span`。它提供了一个非拥有型的数组引用，用于安全地传递和访问连续内存块，避免了指针和长度分离传递的不安全性。

## 架构位置
位于 Skia 核心模块 (`include/core`) 的公共 API 层，作为基础工具类被广泛使用。实际实现位于 `include/private/base/SkSpan_impl.h`，通过公共头文件重新导出，避免了核心文件与基础文件之间的循环依赖。

## 设计决策

### 公私分离架构
SkSpan 采用了独特的两层架构设计：

```
include/core/SkSpan.h (公共API)
    └── include/private/base/SkSpan_impl.h (实际实现)
```

**设计原因**:
1. **依赖解耦**: SkSpan 是许多内部类型的基础，如果放在 core 中会导致 base 文件依赖 core 文件，形成循环依赖
2. **API 稳定性**: 公共头文件保持不变，实现细节可在 private 目录中演进
3. **清晰的层次结构**: private/base 层提供基础工具，core 层提供高层 API

### IWYU 导出策略
使用 `// IWYU pragma: export` 标记，确保包含 SkSpan.h 的代码能够看到完整的实现，无需手动包含私有头文件。

## 核心概念

### Span 语义
Span 代表一个非拥有型的连续内存视图，具有以下特点：
- **非拥有**: 不管理对象生命周期，只提供访问视图
- **连续内存**: 指向的元素在内存中连续存储
- **边界检查**: 提供大小信息，支持安全的范围检查
- **轻量复制**: 仅包含指针和长度，复制开销极小

### 适用场景
Span 在以下场景中特别有用：
- 函数参数传递数组而不转移所有权
- 访问容器的子区间
- 统一处理数组、vector、静态数组等不同容器
- 避免指针+长度的分离传递模式

## 使用示例

### 基本用法（推测）
```cpp
// 从数组创建 span
int data[10] = {0};
SkSpan<int> span(data, 10);

// 从 vector 创建 span
std::vector<float> vec = {1.0f, 2.0f, 3.0f};
SkSpan<float> vecSpan(vec.data(), vec.size());

// 作为函数参数
void processPixels(SkSpan<const uint8_t> pixels) {
    for (size_t i = 0; i < pixels.size(); ++i) {
        // 安全访问
    }
}

// 调用
uint8_t buffer[256];
processPixels(SkSpan<const uint8_t>(buffer, 256));
```

### 与原生指针的对比
```cpp
// 旧方式：不安全，容易出错
void oldStyle(const int* data, size_t length);

// 新方式：类型安全，包含大小信息
void newStyle(SkSpan<const int> data);
```

## 实现细节

### 内存布局
Span 通常只包含两个成员：
- 指向数据的指针（8 字节，64位系统）
- 元素数量（8 字节，size_t）

总大小约 16 字节，复制开销极小，适合值传递。

### 模板特化
实现文件 `SkSpan_impl.h` 可能包含：
- 不同 const 修饰的特化版本
- 从不同容器类型构造的辅助函数
- 子视图提取操作（subspan）
- 迭代器支持

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `include/private/base/SkSpan_impl.h` | 实际实现代码 |
| 标准库类型 | size_t, iterator traits 等 |

### 被依赖的模块
SkSpan 作为基础类型，被 Skia 中大量模块使用：
- 图像处理函数（传递像素缓冲区）
- 路径操作（传递点数组）
- 文本渲染（传递字形索引）
- 着色器系统（传递颜色数组）
- OpenType SVG 解码器（传递调色板，如 `SkOpenTypeSVGDecoder::render` 的 palette 参数）

## 与 C++ 标准库的关系

### std::span 对比
C++20 引入了 `std::span`，SkSpan 与其功能类似：
- **相同点**: 非拥有型视图、轻量级、提供边界信息
- **差异**: SkSpan 可能针对 Skia 特定需求进行了定制
- **历史原因**: SkSpan 可能早于 std::span 出现（支持 C++17 及更早版本）

### 未来演进
随着 Skia 迁移到更新的 C++ 标准，SkSpan 可能：
1. 逐步被 std::span 替代
2. 作为 std::span 的类型别名
3. 保持独立实现以支持旧版编译器

## 性能考量

### 零开销抽象
SkSpan 遵循 C++ 的零开销抽象原则：
- 编译器可内联所有访问操作
- 无虚函数，无动态分派
- 与原生指针+长度的性能相当
- 调试模式可添加边界检查，发布模式可移除

### 缓存友好性
Span 保证了内存的连续性，有利于：
- CPU 缓存预取
- SIMD 向量化操作
- 减少内存访问延迟

## 最佳实践

### 何时使用 SkSpan
- 函数需要访问数组但不需要所有权
- 需要传递数组的子区间
- 统一处理不同类型的容器
- 替代 `const T*` + `size_t` 参数对

### 何时不使用 SkSpan
- 需要管理对象生命周期（使用智能指针）
- 非连续内存（使用迭代器或容器引用）
- 需要修改容器大小（使用容器本身）

### 所有权语义
```cpp
// SkSpan 不延长对象生命周期
SkSpan<int> dangling() {
    std::vector<int> temp = {1, 2, 3};
    return SkSpan<int>(temp.data(), temp.size()); // 危险！悬空引用
}

// 正确做法：确保数据生命周期足够长
class DataHolder {
    std::vector<int> data_;
public:
    SkSpan<int> getSpan() { return SkSpan<int>(data_.data(), data_.size()); }
};
```

## 相关文件
| 文件 | 关系 |
|------|------|
| `include/private/base/SkSpan_impl.h` | 实际实现 |
| `include/core/SkOpenTypeSVGDecoder.h` | 使用 SkSpan 作为参数类型 |
| `include/core/SkTypes.h` | 可能包含相关的类型定义 |

## 技术细节补充

### 类型安全
SkSpan 通过模板参数提供强类型检查：
```cpp
SkSpan<int> intSpan;
SkSpan<const int> constIntSpan = intSpan;  // OK: 可以转换为 const
// SkSpan<int> intSpan2 = constIntSpan;    // 错误: 不能去除 const
```

### 与迭代器的关系
SkSpan 可能提供标准迭代器接口，使其可用于范围 for 循环：
```cpp
SkSpan<int> span = ...;
for (int value : span) {
    // 遍历元素
}
```
