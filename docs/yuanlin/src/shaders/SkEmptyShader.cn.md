# SkEmptyShader

> 源文件
> - src/shaders/SkEmptyShader.h
> - src/shaders/SkEmptyShader.cpp

## 概述

`SkEmptyShader` 是 Skia 着色器系统中最简单的着色器实现,它代表一个"空"着色器,即永远不绘制任何内容的着色器。该着色器的 `createContext()` 方法始终返回 `nullptr`,并且其 `appendStages()` 方法返回 `false`,表示无法添加到光栅管线中。

这个着色器主要用于表示"无着色器"的状态,在某些需要着色器对象但实际上不希望进行着色的场景中使用。它比使用空指针更安全,提供了一个明确的语义表达。

## 架构位置

`SkEmptyShader` 位于 Skia 的着色器模块中:

- **模块路径**: `src/shaders/`
- **基类**: `SkShaderBase` (位于 `src/shaders/SkShaderBase.h`)
- **公共接口**: 通过 `SkShaders::Empty()` 工厂函数创建
- **角色**: 空对象模式实现,表示"无操作"着色器

该类在着色器类型层次结构中是一个特殊的叶子节点,主要用于边界情况处理和安全默认值。

## 主要类与结构体

### SkEmptyShader

表示空着色器的实现类。

**关键特性**:
```cpp
class SkEmptyShader : public SkShaderBase {
public:
    SkEmptyShader() {}  // 空构造函数

    ShaderType type() const override { return ShaderType::kEmpty; }
};
```

**核心方法**:
- `SkEmptyShader()`: 默认构造函数,无需初始化任何状态
- `ShaderType type() const`: 返回 `ShaderType::kEmpty`
- `bool appendStages()`: 始终返回 `false`
- `void flatten()`: 空实现,不序列化任何数据

### 工厂函数

```cpp
namespace SkShaders {
    sk_sp<SkShader> Empty();
}
```

创建并返回空着色器实例的工厂函数。

## 公共 API 函数

### SkShaders::Empty()

```cpp
sk_sp<SkShader> Empty()
```

创建一个空着色器实例。

**返回值**: 智能指针 `sk_sp<SkShader>`,指向 `SkEmptyShader` 实例

**实现**:
```cpp
sk_sp<SkShader> SkShaders::Empty() {
    return sk_make_sp<SkEmptyShader>();
}
```

**使用场景**:
- 作为安全的默认值替代空指针
- 表示"不使用着色器"的明确语义
- 在着色器组合中表示禁用的组件
- 测试和调试场景

### appendStages()

```cpp
bool appendStages(const SkStageRec&, const SkShaders::MatrixRec&) const override
```

**返回值**: 始终返回 `false`

**语义**: 表示该着色器无法添加到光栅管线中,导致整个绘制操作被跳过。

这是空着色器的核心特性:通过返回 `false`,它告诉渲染系统"没有东西可绘制",从而避免执行任何实际的绘制操作。

### flatten()

```cpp
void flatten(SkWriteBuffer& buffer) const override {
    // Do nothing.
    // We just don't want to fall through to SkShader::flatten(),
    // which will write data we don't care to serialize or decode.
}
```

**语义**: 空实现,不写入任何数据到序列化缓冲区。

注释说明了为什么需要显式覆盖这个方法:防止意外调用基类的 `SkShader::flatten()`,后者可能会写入不必要的数据。

### CreateProc()

```cpp
sk_sp<SkFlattenable> SkEmptyShader::CreateProc(SkReadBuffer&)
```

反序列化工厂函数。

**参数**: `SkReadBuffer&` - 读取缓冲区(未使用)

**返回值**: 通过 `SkShaders::Empty()` 创建的新实例

**实现**: 直接调用工厂函数,不读取任何数据:
```cpp
sk_sp<SkFlattenable> SkEmptyShader::CreateProc(SkReadBuffer&) {
    return SkShaders::Empty();
}
```

## 内部实现细节

### 最小化实现

`SkEmptyShader` 是一个几乎完全空的类:
- **无成员变量**: 不需要存储任何状态
- **无构造逻辑**: 默认构造函数为空
- **最小方法实现**: 所有方法都是最简单的实现

### 序列化策略

**写入** (`flatten`):
- 不写入任何数据
- 显式覆盖以避免基类行为
- 保持序列化流的简洁

**读取** (`CreateProc`):
- 不读取任何数据
- 直接创建新实例
- 所有空着色器都是等价的

这种设计意味着序列化的空着色器只占用类型标识符的空间,没有额外的数据开销。

### 失败语义

`appendStages()` 返回 `false` 的效果:
1. 渲染系统检测到管线构建失败
2. 整个绘制操作被跳过
3. 不会生成任何像素输出
4. 相当于"什么都不绘制"

这是一种优雅的方式来表达"无效绘制",比抛出异常或使用空指针更安全。

### 类型识别

```cpp
ShaderType type() const override { return ShaderType::kEmpty; }
```

返回专门的枚举值,允许在运行时快速识别空着色器,可能用于优化或特殊处理。

## 依赖关系

### 直接依赖

- **SkShaderBase**: 基类,提供着色器接口
- **SkFlattenable**: 序列化框架
- **SkShader**: 公共着色器接口
- **SkRefCnt**: 引用计数(通过 `sk_sp`)

### 最小依赖设计

`SkEmptyShader` 刻意保持最小的依赖:
- 不依赖颜色、矩阵、图像等复杂类型
- 不依赖光栅管线组件
- 不依赖任何效果或变换系统

这使得它成为最轻量级的着色器实现。

### 被依赖关系

可能的使用场景:
- **SkPaint**: 作为默认着色器或表示"无着色器"
- **着色器组合**: 在混合或变换链中表示禁用的组件
- **测试代码**: 作为占位符或边界情况测试
- **优化路径**: 快速检测并跳过无效绘制

## 设计模式与设计决策

### 空对象模式 (Null Object Pattern)

`SkEmptyShader` 是空对象模式的标准实现:
- **目的**: 提供一个"什么都不做"的对象,替代空指针
- **优势**: 避免空指针检查,统一接口处理
- **实现**: 所有方法都有安全的默认行为

### 单例模式的潜力

虽然当前实现每次调用 `Empty()` 都创建新实例,但理论上可以优化为单例:
```cpp
// 潜在优化
sk_sp<SkShader> SkShaders::Empty() {
    static sk_sp<SkShader> instance = sk_make_sp<SkEmptyShader>();
    return instance;
}
```

这将减少内存分配,因为所有空着色器都是功能等价的。

### 快速失败设计

`appendStages()` 返回 `false` 而不是添加"无操作"管线阶段:
- **优点**: 避免管线开销,完全跳过绘制
- **优点**: 清晰表达"无效"语义
- **权衡**: 调用者必须处理 `false` 返回值

### 显式覆盖 flatten()

虽然空实现看似可以省略,但显式覆盖有重要意义:
- 文档化意图:明确表示"我们不想序列化任何东西"
- 防御性编程:避免基类未来变更导致意外行为
- 性能优化:跳过基类的序列化逻辑

### 最小完备性

只实现绝对必要的方法:
- 不覆盖 `isOpaque()` - 使用基类默认值
- 不覆盖 `isConstant()` - 使用基类默认值
- 不实现上下文创建 - 基类已返回 `nullptr`

这体现了"最小惊讶原则"和YAGNI (You Aren't Gonna Need It) 原则。

## 性能考量

### 零开销抽象

`SkEmptyShader` 接近零开销:
- **无成员变量**: 对象大小仅为虚函数表指针(通常 8 字节)
- **无初始化成本**: 构造函数为空
- **快速失败**: `appendStages()` 立即返回 `false`
- **无管线开销**: 完全跳过管线构建和执行

### 序列化效率

- **写入**: 不写入任何数据,仅类型 ID
- **读取**: 不读取任何数据,直接创建实例
- **大小**: 序列化后占用最小空间

### 潜在优化

如果实现为单例:
- 消除重复分配
- 减少内存占用
- 改善缓存局部性

但当前实现的多实例方式也有优点:
- 更简单的生命周期管理
- 避免静态初始化问题
- 与其他着色器一致的语义

### 跳过绘制的效率

当使用空着色器时:
- 整个绘制操作被跳过
- 不需要设置图形状态
- 不需要发出绘制命令
- 节省了所有下游处理

这使得使用 `SkEmptyShader` 比绘制透明像素更高效。

## 相关文件

### 核心依赖
- `src/shaders/SkShaderBase.h` - 着色器基类定义
- `src/shaders/SkShaderBase.cpp` - 着色器基类实现
- `include/core/SkShader.h` - 公共着色器接口
- `include/effects/SkShaders.h` - 着色器工厂函数声明

### 序列化
- `include/core/SkFlattenable.h` - 可序列化对象基类
- `src/core/SkReadBuffer.h` - 反序列化工具
- `src/core/SkWriteBuffer.h` - 序列化工具

### 引用计数
- `include/core/SkRefCnt.h` - 智能指针和引用计数

### 相关着色器
- `src/shaders/SkColorShader.h` - 最简单的"有用"着色器(对比)
- `src/shaders/SkShaderBase.h` - 包含 `ShaderType` 枚举定义

### 管线相关
- `src/core/SkRasterPipeline.h` - 光栅管线(虽然空着色器不使用它)
- `src/shaders/SkShaderBase.h` - 定义 `SkStageRec` 结构

### 使用示例位置
- `src/core/SkPaint.cpp` - 可能使用空着色器作为默认值
- 各种着色器组合类 - 可能在组件禁用时使用
