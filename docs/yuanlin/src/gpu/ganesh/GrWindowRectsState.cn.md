# GrWindowRectsState

> 源文件: src/gpu/ganesh/GrWindowRectsState.h

## 概述

`GrWindowRectsState` 是 Skia Ganesh GPU 后端中封装窗口矩形裁剪状态的轻量级类。它将 `GrWindowRectangles` 矩形集合与裁剪模式(排除或包含)结合,形成完整的窗口矩形裁剪配置,用于 GPU 渲染管线中的高级裁剪功能。

该类作为 `GrWindowRectangles` 的薄包装层,添加了模式语义和状态查询接口,是裁剪系统与渲染管线之间的桥梁。

## 架构位置

`GrWindowRectsState` 在 Ganesh 渲染系统中的位置:

- **上层**: 被渲染管线状态和绘制操作使用
- **同层**: 与 `GrClip` 和裁剪栈协作
- **下层**: 依赖 `GrWindowRectangles` 存储矩形数据

该类是裁剪状态管理的高层抽象,连接裁剪逻辑和 GPU 硬件能力。

## 主要类与结构体

### GrWindowRectsState 类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMode` | `Mode` | 裁剪模式(排除或包含) |
| `fWindows` | `GrWindowRectangles` | 窗口矩形集合 |

### Mode 枚举

```cpp
enum class Mode : bool {
    kExclusive,  // 排除模式:矩形外的区域通过测试
    kInclusive   // 包含模式:矩形内的区域通过测试
};
```

**语义**:
- **kExclusive**: 类似"擦除"矩形区域,渲染矩形外的部分
- **kInclusive**: 类似"保留"矩形区域,只渲染矩形内的部分

**存储**: 使用 `bool` 作为底层类型,节省空间。

## 公共 API 函数

### 构造函数

```cpp
GrWindowRectsState()  // 默认构造:排除模式,空集合
```

**默认状态**: 排除模式 + 空矩形集合 = 无裁剪效果。

```cpp
GrWindowRectsState(const GrWindowRectangles& windows, Mode mode)
```

**功能**: 使用指定矩形和模式构造状态。

### 查询函数

```cpp
bool enabled() const
```

**功能**: 判断窗口矩形裁剪是否启用。

**逻辑**:
```cpp
return Mode::kInclusive == fMode || !fWindows.empty();
```

**语义**:
- 包含模式: 即使空集合也有效(排除所有像素)
- 排除模式: 只有非空集合才有效

```cpp
Mode mode() const                          // 获取模式
const GrWindowRectangles& windows() const  // 获取矩形集合
int numWindows() const                     // 获取矩形数量
```

### 修改函数

```cpp
void setDisabled()
```

**功能**: 禁用窗口矩形裁剪。

**实现**:
```cpp
fMode = Mode::kExclusive;
fWindows.reset();
```

**效果**: 排除模式 + 空集合 = 无裁剪。

```cpp
void set(const GrWindowRectangles& windows, Mode mode)
```

**功能**: 设置新的矩形集合和模式。

### 比较运算符

```cpp
bool operator==(const GrWindowRectsState& that) const
bool operator!=(const GrWindowRectsState& that) const
```

**相等条件**: 模式和矩形集合都相同。

## 内部实现细节

### enabled 方法的设计

```cpp
bool enabled() const {
    return Mode::kInclusive == fMode || !fWindows.empty();
}
```

**为什么包含模式的空集合有效?**

- **排除模式 + 空集合**: 没有矩形需要排除 → 全部通过 → 无效果
- **包含模式 + 空集合**: 只有空矩形内通过 → 全部失败 → 有效果(完全裁剪)

**用途**: 包含模式的空集合可实现"全裁剪",排除所有像素。

### operator== 实现

```cpp
bool operator==(const GrWindowRectsState& that) const {
    if (fMode != that.fMode) {
        return false;
    }
    return fWindows == that.fWindows;
}
```

**短路优化**: 先比较模式(单个 bool),再比较矩形集合。

### setDisabled 的选择

选择排除模式而非包含模式:

**原因**: 排除模式 + 空集合是最自然的"无裁剪"状态,匹配默认构造函数的行为。

### 最小化接口

类不提供直接修改 `fWindows` 的方法:

**设计**: 强制通过 `set()` 设置,确保模式和矩形的一致性。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrWindowRectangles` | 存储窗口矩形集合 |

**依赖极少**: 该类是纯数据容器,几乎无外部依赖。

### 被依赖的模块

该类被以下模块使用:
- `GrPipeline`: 渲染管线状态
- `GrOpsTask`: 操作任务的裁剪状态
- `GrClip`: 裁剪栈的窗口矩形部分
- GPU 后端实现(Vulkan/Metal/D3D)

## 设计模式与设计决策

### 值语义

类使用值语义而非引用语义:

**好处**:
- 拷贝安全
- 无生命周期管理问题
- 简化使用

**代价**: 拷贝开销(但 `GrWindowRectangles` 已优化拷贝)。

### 聚合(Aggregation)

组合 `GrWindowRectangles` 而非继承:

**优点**:
- 关注点分离(数据存储 vs 状态管理)
- 避免继承的复杂性
- 灵活性更高

### 枚举类型安全

使用 `enum class Mode`:

**好处**:
- 类型安全,防止隐式转换
- 明确作用域
- 自文档化

### 语义明确的禁用

提供 `setDisabled()` 而非 `set(empty, kExclusive)`:

**优势**:
- API 意图清晰
- 防止误用(如 `set(empty, kInclusive)` 实际有效果)

### 简洁的实现

整个类只有约 50 行代码:

**哲学**: 做好一件简单的事,不添加不必要的复杂性。

## 性能考量

### 内联友好

所有方法都很简单,适合内联:

**效果**: 编译器可完全内联,零调用开销。

### 拷贝效率

依赖 `GrWindowRectangles` 的优化拷贝:
- 单矩形: 栈拷贝
- 多矩形: 引用计数

**结果**: 拷贝 `GrWindowRectsState` 非常快。

### 比较效率

`operator==` 短路优化:
```cpp
if (fMode != that.fMode) {
    return false;  // 单个 bool 比较
}
```

避免不必要的矩形比较。

### 内存占用

```cpp
sizeof(GrWindowRectsState) ≈ sizeof(Mode) + sizeof(GrWindowRectangles)
                           ≈ 1 byte + 20 bytes
                           ≈ 24 bytes (考虑对齐)
```

**紧凑**: 适合嵌入到其他结构体中。

### enabled 的快速路径

```cpp
Mode::kInclusive == fMode  // 单次比较
```

包含模式直接返回 `true`,无需检查矩形集合。

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/gpu/ganesh/GrWindowRectangles.h` | 依赖的矩形集合类 |
| `src/gpu/ganesh/GrPipeline.h` | 使用该状态的渲染管线 |
| `src/gpu/ganesh/GrClip.h` | 裁剪系统接口 |
| `src/gpu/ganesh/GrOpsTask.h` | 操作任务中的裁剪状态 |
