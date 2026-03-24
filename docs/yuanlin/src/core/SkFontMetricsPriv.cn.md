# SkFontMetricsPriv

> 源文件：src/core/SkFontMetricsPriv.h, src/core/SkFontMetricsPriv.cpp

## 概述

SkFontMetricsPriv 是 Skia 字体度量系统的私有序列化工具类,提供将 SkFontMetrics 结构体序列化和反序列化的功能。该类用于在不同上下文之间传输字体度量数据,例如在进程间通信或持久化存储场景中。

## 架构位置

```
Skia 图形库
└── src/core (核心模块)
    ├── SkFontMetricsPriv (字体度量序列化工具)
    ├── SkReadBuffer (读取缓冲区)
    ├── SkWriteBuffer (写入缓冲区)
    └── include/core
        └── SkFontMetrics (公共字体度量结构)
```

该类位于 Skia 核心层的私有实现部分,为字体系统提供内部序列化支持。

## 主要类与结构体

### SkFontMetricsPriv

**继承关系**
- 无继承,纯静态工具类

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| 无 | - | 该类只包含静态方法,无实例成员 |

**核心字段布局**

SkFontMetrics 包含以下字段(按序列化顺序):

| 字段 | 类型 | 说明 |
|------|------|------|
| fFlags | uint32_t | 标志位 |
| fTop | SkScalar | 最大上升值(推荐边界) |
| fAscent | SkScalar | 基线上升值 |
| fDescent | SkScalar | 基线下降值 |
| fBottom | SkScalar | 最大下降值(推荐边界) |
| fLeading | SkScalar | 行间距 |
| fAvgCharWidth | SkScalar | 平均字符宽度 |
| fMaxCharWidth | SkScalar | 最大字符宽度 |
| fXMin | SkScalar | 最小 X 边界 |
| fXMax | SkScalar | 最大 X 边界 |
| fXHeight | SkScalar | 小写字母 x 的高度 |
| fCapHeight | SkScalar | 大写字母高度 |
| fUnderlineThickness | SkScalar | 下划线粗细 |
| fUnderlinePosition | SkScalar | 下划线位置 |
| fStrikeoutThickness | SkScalar | 删除线粗细 |
| fStrikeoutPosition | SkScalar | 删除线位置 |

## 公共 API 函数

### Flatten

```cpp
static void Flatten(SkWriteBuffer& buffer, const SkFontMetrics& metrics)
```

将 SkFontMetrics 结构序列化到缓冲区。

**参数**
- buffer: 写入目标缓冲区
- metrics: 待序列化的字体度量数据

**功能**
- 按固定顺序写入所有 16 个字段
- 使用 SkWriteBuffer 的类型安全写入方法
- 保证数据格式的向后兼容性

### MakeFromBuffer

```cpp
static std::optional<SkFontMetrics> MakeFromBuffer(SkReadBuffer& buffer)
```

从缓冲区反序列化 SkFontMetrics 结构。

**返回值**
- 成功时返回 SkFontMetrics 对象
- 失败时返回 std::nullopt

**功能**
- 按 Flatten 相同顺序读取字段
- 验证缓冲区状态确保数据完整性
- 使用现代 C++ optional 类型处理错误

## 内部实现细节

### 序列化策略

1. **固定字段顺序**: 所有字段按预定义顺序序列化,确保版本兼容性
2. **类型一致性**: 使用 SkWriteBuffer/SkReadBuffer 的类型化方法
3. **完整性校验**: 反序列化时检查 buffer.isValid() 确保所有读取成功

### 错误处理

```cpp
// 反序列化失败检测
if (buffer.isValid()) {
    return metrics;  // 成功返回数据
}
return std::nullopt;  // 失败返回空值
```

使用 SkReadBuffer 的内部状态跟踪确保数据完整性。如果任何读取操作失败,buffer 会标记为无效状态。

### 内存布局

序列化后的二进制布局:
```
[fFlags:4字节] [fTop:4字节] [fAscent:4字节] ... [fStrikeoutPosition:4字节]
总计: 1个uint + 15个scalar = 64字节 (32位系统)
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkFontMetrics | 字体度量数据结构定义 |
| SkWriteBuffer | 序列化写入接口 |
| SkReadBuffer | 反序列化读取接口 |
| SkAssert | 调试断言支持 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| SkFont 序列化系统 | 字体对象持久化 |
| SkTypeface 序列化 | 字体面数据传输 |
| 进程间通信模块 | 跨进程字体度量传递 |

## 设计模式与设计决策

### 设计模式

1. **静态工具类模式**: 提供纯函数式接口,无状态管理
2. **访问者模式**: SkWriteBuffer/SkReadBuffer 作为访问者遍历数据结构

### 设计决策

1. **为何使用 std::optional**
   - 提供类型安全的错误处理
   - 避免使用指针或异常
   - 符合现代 C++ 最佳实践

2. **固定字段顺序的原因**
   - 保证二进制兼容性
   - 简化版本管理
   - 避免字段标记开销

3. **分离序列化逻辑**
   - 保持 SkFontMetrics 结构简单
   - 集中管理序列化代码
   - 便于未来扩展

## 性能考量

### 性能优化

1. **直接写入**: 无中间缓冲,直接写入目标缓冲区
2. **固定大小**: 所有字段已知大小,无需动态分配
3. **顺序访问**: 按内存布局顺序访问,缓存友好

### 性能特征

- **时间复杂度**: O(1) - 固定 16 个字段读写
- **空间复杂度**: O(1) - 栈上临时对象,无堆分配
- **序列化开销**: ~16 次方法调用 + 64 字节数据拷贝

### 优化建议

当前实现已足够高效,无明显优化空间。可能的极端优化:
- 使用 memcpy 批量复制(但会损失类型安全)
- 位打包减少数据大小(但会增加计算开销)

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/core/SkFontMetrics.h | 字体度量公共结构定义 |
| src/core/SkReadBuffer.h | 反序列化读取缓冲区 |
| src/core/SkWriteBuffer.h | 序列化写入缓冲区 |
| src/core/SkFont_serial.cpp | 字体对象序列化实现 |
| src/core/SkTypeface.cpp | 字体面实现(使用字体度量) |
