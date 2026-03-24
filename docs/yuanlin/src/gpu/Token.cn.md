# Token

> 源文件: src/gpu/Token.h

## 概述

`Token` 是 Skia GPU 模块中用于对 Recorder 内的操作进行排序的通用令牌类。它提供了一个轻量级的序列号机制，用于跟踪和管理 GPU 命令的执行顺序，特别是在延迟执行（deferred execution）和资源生命周期管理场景中。

该模块包含两个核心类：
1. **Token**: 不透明的序列号令牌，支持比较和递增操作
2. **TokenTracker**: 管理令牌的发放和当前状态，维护绘制令牌（draw token）和刷新令牌（flush token）两个序列

`Token` 被 Ganesh 和 Graphite 两个 GPU 后端共同使用，是跨后端的基础设施组件。

## 架构位置

```
skia/
├── src/gpu/
│   └── Token.h                    # 本模块（头文件实现）
├── src/gpu/ganesh/
│   └── ops/GrOpFlushState.h       # Ganesh 后端使用
└── src/gpu/graphite/
    └── RecorderPriv.h             # Graphite 后端使用
```

`Token` 位于 `skgpu` 命名空间，作为 GPU 模块的通用工具，不依赖于特定后端。它在命令提交、资源上传、以及延迟代理解析等场景中扮演重要角色。

## 主要类与结构体

### 1. Token 类

**继承关系**: 无继承，值语义类型

**关键成员变量**:

| 类型 | 名称 | 说明 |
|------|------|------|
| `uint64_t` | `fSequenceNumber` | 64 位无符号整数序列号 |

**不变量**:
- 序列号 0 为保留的无效令牌（`InvalidToken()`）
- 序列号单调递增
- 比较操作等价于整数比较

### 2. TokenTracker 类

**继承关系**: 无继承

**关键成员变量**:

| 类型 | 名称 | 说明 |
|------|------|------|
| `Token` | `fCurrentDrawToken` | 当前绘制令牌 |
| `Token` | `fCurrentFlushToken` | 当前刷新令牌 |

**友元类**:
- `GrOpFlushState` (Ganesh)
- `TestingUploadTarget` (测试)
- `skgpu::graphite::RecorderPriv` (Graphite)

仅这些类可以调用 `issueDrawToken()` 和 `issueFlushToken()` 来递增令牌。

## 公共 API 函数

### Token 类

#### 1. 构造与静态工厂

```cpp
static Token InvalidToken()  // 返回序列号为 0 的无效令牌
Token(const Token&) = default  // 拷贝构造
Token& operator=(const Token&) = default  // 拷贝赋值
```

**用途**: 无效令牌常用作哨兵值，表示"未初始化"或"无令牌"状态。

#### 2. 比较操作符

```cpp
bool operator==(const Token& that) const
bool operator!=(const Token& that) const
bool operator<(const Token that) const
bool operator<=(const Token that) const
bool operator>(const Token that) const
bool operator>=(const Token that) const
```

**功能**: 支持全序比较，等价于比较内部序列号
**用途**: 判断令牌的先后顺序，检查资源是否可用等

#### 3. 递增操作符

```cpp
Token& operator++()      // 前置递增，返回递增后的值
Token operator++(int)    // 后置递增，返回递增前的值
```

**功能**: 生成下一个令牌
**注意**: 通常不应直接在用户代码中递增令牌，而是通过 `TokenTracker` 管理

#### 4. next() 方法

```cpp
Token next() const
```

**功能**: 返回下一个令牌，不修改当前对象
**示例**:
```cpp
Token t = currentToken.next();  // t = currentToken + 1
```

#### 5. value() 方法

```cpp
uint64_t value() const
```

**功能**: 获取原始序列号，用于调试和比较
**用途**: 日志输出、序列化等

#### 6. inInterval() 方法

```cpp
bool inInterval(const Token& start, const Token& end)
```

**功能**: 判断令牌是否在闭区间 `[start, end]` 内
**返回**: `*this >= start && *this <= end`
**用途**: 判断资源是否在特定命令批次范围内被使用

### TokenTracker 类

#### 1. nextFlushToken()

```cpp
Token nextFlushToken() const
```

**功能**: 获取下一个刷新令牌
**含义**: 表示**当前**正在记录的命令批次的 ID
**用途**: 延迟上传器（deferred uploader）使用此令牌标记上传时机

#### 2. currentFlushToken()

```cpp
Token currentFlushToken() const
```

**功能**: 获取最近已发放的刷新令牌
**含义**: 表示**最近完成**的刷新批次的 ID
**用途**: 判断某个刷新批次是否已完成

#### 3. nextDrawToken()

```cpp
Token nextDrawToken() const
```

**功能**: 获取下一个绘制令牌
**含义**: 表示即将分配的绘制操作的 ID
**用途**: 为新创建的绘制操作分配唯一标识

#### 4. issueDrawToken() (私有)

```cpp
Token issueDrawToken()
```

**功能**: 递增并返回新的绘制令牌
**访问限制**: 仅友元类可调用

#### 5. issueFlushToken() (私有)

```cpp
Token issueFlushToken()
```

**功能**: 递增并返回新的刷新令牌
**访问限制**: 仅友元类可调用

## 内部实现细节

### 令牌的两种类型

**Draw Token (绘制令牌)**:
- 为每个绘制操作（`GrOp` 或 `DrawPass`）分配
- 用于资源依赖跟踪
- 确保资源在被使用前已准备好

**Flush Token (刷新令牌)**:
- 为每个刷新批次（flush batch）分配
- 用于延迟上传和代理解析
- 确保上传在正确的刷新时机执行

### 序列号设计

使用 `uint64_t` 的原因：
- 足够大，即使每秒 10^9 次递增也需 584 年才溢出
- 64 位对齐，高效比较和拷贝
- 避免整数溢出的复杂处理

### 初始化状态

两个令牌都初始化为 `InvalidToken()` (0)：
```cpp
Token fCurrentDrawToken = Token::InvalidToken();
Token fCurrentFlushToken = Token::InvalidToken();
```

首次调用 `issue*Token()` 后，令牌变为 1。

### 友元访问模式

限制令牌发放权限的原因：
1. **防止误用**: 随意递增令牌会破坏顺序性
2. **集中管理**: 所有令牌由刷新状态或记录器统一管理
3. **清晰职责**: 明确哪些组件负责命令提交

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `<cstdint>` | `uint64_t` 类型定义 |

**说明**: `Token` 完全自包含，无其他 Skia 依赖。

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `GrOpFlushState` | Ganesh 后端管理绘制操作的令牌 |
| `GrDeferredProxyUploader` | 延迟纹理上传的时机控制 |
| `GrTextureProxy` | 纹理代理的延迟解析 |
| `skgpu::graphite::RecorderPriv` | Graphite 后端的命令记录 |
| 资源生命周期管理 | 判断资源何时可安全释放 |

## 设计模式与设计决策

### 设计模式

1. **值对象模式**: `Token` 是不可变的值类型，拷贝语义简单
2. **友元访问模式**: 限制令牌发放权限，保证顺序性
3. **单调递增序列模式**: 类似逻辑时钟（Lamport clock）概念

### 设计决策

**为什么不使用 int32_t？**
- 32 位容易溢出（约 43 亿次递增）
- 长时间运行的应用可能触发溢出
- 64 位提供实际无限的序列空间

**为什么分离 Draw 和 Flush 令牌？**
- **粒度不同**: Draw 令牌细粒度（每个绘制操作），Flush 令牌粗粒度（每批命令）
- **用途不同**: Draw 令牌用于资源依赖，Flush 令牌用于上传时机
- **独立递增**: 两者生命周期不同，需要独立计数

**为什么不使用原子操作？**
- 令牌的发放和使用都在单线程（记录线程）内
- 令牌本身可在线程间传递（只读访问）
- 避免不必要的原子操作开销

**为什么不支持减量操作？**
- 令牌必须单调递增，保证时间顺序
- 减量会破坏"发生在之前"的语义
- 如需撤销，应使用其他机制（如回滚栈）

### nextDrawToken vs nextFlushToken

**语义差异**:
- `nextDrawToken()`: "下一个将要创建的绘制操作的 ID"
- `nextFlushToken()`: "当前正在记录的批次的 ID"

**使用示例** (Ganesh):
```cpp
// 记录绘制操作
GrOp* op = createOp();
op->setDrawToken(tracker.nextDrawToken());
tracker.issueDrawToken();  // 分配给该 op

// 延迟上传
uploader->setFlushToken(tracker.nextFlushToken());
// 在刷新时检查
if (uploader->flushToken() <= tracker.currentFlushToken()) {
    // 执行上传
}
```

## 性能考量

### 内存占用

- 单个 `Token` 对象：8 字节（`uint64_t`）
- `TokenTracker` 对象：16 字节（两个 `Token`）
- 极其轻量，可按值传递

### 运算性能

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 构造 | O(1) | 简单整数赋值 |
| 比较 | O(1) | 单次整数比较 |
| 递增 | O(1) | 整数加法 |
| inInterval | O(1) | 两次比较 |

### 缓存友好性

- 8 字节对齐，通常与指针大小相同
- 可打包进其他结构体无额外对齐浪费
- 比较操作无分支预测失败（简单整数比较）

### 典型用例的性能

**资源依赖检查**:
```cpp
if (resource->lastUseToken() < currentDrawToken) {
    // 资源可复用
}
```
成本：单次整数比较，约 1 个 CPU 周期。

**延迟上传排序**:
```cpp
std::sort(uploaders.begin(), uploaders.end(),
    [](auto& a, auto& b) { return a->token() < b->token(); });
```
Token 比较不涉及指针追踪，排序效率高。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/Token.h` | 定义 | 本模块头文件（头文件实现） |
| `src/gpu/ganesh/GrOpFlushState.h` | 使用 | Ganesh 刷新状态，管理令牌发放 |
| `src/gpu/ganesh/GrDeferredProxyUploader.h` | 使用 | 延迟上传器使用 flush token |
| `src/gpu/graphite/RecorderPriv.h` | 使用 | Graphite 记录器私有接口 |
| `src/gpu/ganesh/ops/GrOp.h` | 使用 | 绘制操作关联 draw token |
| `src/gpu/ganesh/GrTextureProxy.h` | 使用 | 纹理代理使用令牌管理生命周期 |

## 使用示例

### 示例 1: 资源生命周期管理

```cpp
class DeferredResource {
public:
    void markUsedInDraw(Token drawToken) {
        fLastUseToken = std::max(fLastUseToken, drawToken);
    }

    bool canBeReused(Token currentToken) const {
        return fLastUseToken < currentToken;
    }

private:
    Token fLastUseToken = Token::InvalidToken();
};
```

### 示例 2: 延迟上传排队

```cpp
class DeferredUploader {
public:
    void scheduleUpload(TokenTracker& tracker, UploadFunc func) {
        fFlushToken = tracker.nextFlushToken();
        fUploadFunc = std::move(func);
    }

    bool shouldExecute(Token currentFlush) const {
        return fFlushToken <= currentFlush;
    }

private:
    Token fFlushToken;
    UploadFunc fUploadFunc;
};
```

### 示例 3: 调试信息输出

```cpp
void logToken(const Token& t) {
    if (t == Token::InvalidToken()) {
        SkDebugf("Token: INVALID\n");
    } else {
        SkDebugf("Token: %llu\n", t.value());
    }
}
```
