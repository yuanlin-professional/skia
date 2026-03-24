# GrTracing

> 源文件: src/gpu/ganesh/GrTracing.h

## 概述

`GrTracing` 是 Skia Ganesh GPU 后端的追踪宏定义头文件,提供统一的性能分析和调试追踪接口。它整合了 Skia 的审计追踪(Audit Trail)系统和通用的事件追踪机制,用于记录 GPU 操作的执行路径、性能指标和调试信息。

该模块通过宏封装,在编译时可选择性地启用或禁用追踪功能,确保 Release 版本零性能开销。主要用于开发、调试和性能分析场景。

## 架构位置

`GrTracing` 在 Ganesh 系统中的位置:

- **层级**: 基础设施层,横跨整个 Ganesh 后端
- **依赖**: 依赖 Skia 核心的追踪系统和审计追踪系统
- **被依赖**: 几乎所有 Ganesh 的渲染操作和管理类

该模块是开发和诊断工具,不参与实际渲染逻辑。

## 主要类与结构体

该头文件不定义类,仅提供宏定义。

### 追踪宏

#### GR_CREATE_TRACE_MARKER_CONTEXT

```cpp
#define GR_CREATE_TRACE_MARKER_CONTEXT(classname, op, context) \
    GR_AUDIT_TRAIL_AUTO_FRAME(context->priv().auditTrail(), classname "::" op); \
    TRACE_EVENT0("skia.gpu", classname "::" op)
```

**功能**: 创建一个追踪标记,用于记录上下文级别的操作。

**参数**:
- `classname`: 类名(const char*)
- `op`: 操作名(const char*)
- `context`: `GrContext` 指针

**展开为两部分**:
1. **审计追踪帧**: `GR_AUDIT_TRAIL_AUTO_FRAME` 在审计日志中记录操作
2. **事件追踪**: `TRACE_EVENT0` 发送到系统的性能分析工具

**使用示例**:
```cpp
void GrRenderTargetContext::clear(...) {
    GR_CREATE_TRACE_MARKER_CONTEXT("GrRenderTargetContext", "clear", fContext);
    // ... 清空逻辑
}
```

**作用域**: 宏展开的对象在作用域结束时自动记录结束时间。

## 内部实现细节

### 双重追踪机制

宏同时启用两个追踪系统:

#### 1. GR_AUDIT_TRAIL_AUTO_FRAME

**来源**: `src/gpu/ganesh/GrAuditTrail.h`

**功能**:
- 记录 GPU 操作的层级调用栈
- 捕获操作名称和时间戳
- 构建操作树,用于调试和分析

**实现**: 利用 RAII,构造时记录开始,析构时记录结束。

**用途**:
- GPU 调试工具(如 Skia Debugger)
- 分析渲染管线的操作序列
- 查找性能瓶颈

#### 2. TRACE_EVENT0

**来源**: `src/core/SkTraceEvent.h`

**功能**:
- 发送事件到系统级追踪工具
- 支持 Chrome Tracing、Android Systrace 等

**参数**:
- `"skia.gpu"`: 事件类别
- `classname "::" op`: 事件名称

**用途**:
- 集成到系统性能分析流程
- 可视化 GPU 操作时间线
- 跨模块性能分析

### 字符串拼接

宏使用 `::` 拼接类名和操作名:

```cpp
classname "::" op
// 例如: "GrRenderTargetContext::clear"
```

**优点**: 提供明确的操作标识,易于过滤和分组。

### 零开销原则

在不启用追踪的构建中:
- `GR_AUDIT_TRAIL_AUTO_FRAME` 展开为空语句
- `TRACE_EVENT0` 展开为空语句

**效果**: Release 版本无任何追踪开销。

### 上下文访问

通过 `context->priv().auditTrail()` 访问审计追踪:

**设计**: 使用 `priv()` 访问器,表明这是内部实现细节。

### 自动帧管理

`AUTO_FRAME` 后缀表示自动作用域管理:
- 构造时记录进入
- 析构时记录退出

**好处**: 无需手动配对调用,避免遗漏。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkTraceEvent.h` | 系统事件追踪接口 |
| `GrAuditTrail.h` | GPU 操作审计日志 |
| `GrContext` | 提供审计追踪实例 |

### 被依赖的模块

该宏被以下场景使用:
- 所有 `GrContext` 级别的操作
- 渲染目标上下文的绘制操作
- 纹理创建和更新
- 着色器编译
- 命令提交

**覆盖范围**: 几乎所有重要的 GPU 操作入口点。

## 设计模式与设计决策

### 宏而非函数

选择宏而非内联函数:

**原因**:
1. 可在编译时完全消除(条件编译)
2. 避免函数调用开销(即使内联)
3. 支持可变参数和复杂展开

### 统一的命名约定

`classname "::" op` 格式:

**好处**:
- 易于解析和过滤
- 提供完整的调用上下文
- 一致的日志格式

### RAII 模式

利用 C++ 的作用域和析构:

**优势**:
- 自动配对开始/结束
- 异常安全(即使抛出异常也会记录结束)
- 代码简洁

### 分层追踪

区分上下文级别和操作级别:

**当前**: 只有 `CONTEXT` 级别宏

**可扩展**: 未来可添加 `OP` 级别、`TASK` 级别等宏。

### 依赖注入

通过参数传入 `context`:

**灵活性**: 支持多上下文环境,不依赖全局状态。

## 性能考量

### 条件编译

追踪代码通过宏控制:

```cpp
#if SK_ENABLE_TRACING
    // 追踪代码
#else
    // 空
#endif
```

**效果**: Release 版本二进制中不包含追踪代码。

### 字符串字面量

类名和操作名使用字符串字面量:

**优点**:
- 编译时常量,存储在只读数据段
- 无运行时内存分配
- 指针比较快速

### 栈分配

追踪对象在栈上分配:

**好处**:
- 无堆分配开销
- 缓存友好
- 自动清理

### 短路评估

如果追踪未启用,宏展开为空:

**编译器行为**:
```cpp
GR_CREATE_TRACE_MARKER_CONTEXT("Foo", "bar", ctx);
// 展开为空,编译器完全消除
```

### 最小侵入性

宏调用通常是函数第一行:

**好处**:
- 不影响核心逻辑
- 易于添加/删除
- 代码审查友好

## 使用场景

### 性能分析

**流程**:
1. 启用追踪构建
2. 运行应用,记录追踪数据
3. 使用 Chrome Tracing 可视化
4. 识别耗时操作

### 调试

**用途**:
- 理解操作执行顺序
- 追踪参数传递
- 定位崩溃点

### 测试

**场景**:
- 验证操作是否被调用
- 检查调用频率
- 确保操作顺序正确

### 审计

**功能**:
- 记录所有 GPU 操作
- 生成操作日志
- 符合性检查

## 扩展性

### 添加新宏

可以定义其他级别的追踪宏:

```cpp
#define GR_CREATE_TRACE_MARKER_OP(opname, op) \
    TRACE_EVENT0("skia.gpu.op", opname "::" op)
```

### 添加参数

可以使用 `TRACE_EVENT1/2` 添加参数:

```cpp
#define GR_TRACE_WITH_SIZE(name, size) \
    TRACE_EVENT1("skia.gpu", name, "size", size)
```

### 平台特定追踪

可以添加平台特定的追踪后端。

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/core/SkTraceEvent.h` | 事件追踪基础设施 |
| `src/gpu/ganesh/GrAuditTrail.h` | GPU 审计追踪实现 |
| `src/gpu/ganesh/GrContext.h` | 提供上下文访问 |
| `src/gpu/ganesh/GrRenderTargetContext.h` | 使用追踪的典型类 |
| `src/gpu/ganesh/GrOpsTask.h` | 操作任务追踪 |
