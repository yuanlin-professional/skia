# PrecompileContextPriv

> 源文件: src/gpu/graphite/PrecompileContextPriv.h

## 概述

`PrecompileContextPriv` 是 Skia Graphite GPU 后端中 `PrecompileContext` 的私有访问器类。该类采用"Priv"模式（Privilege Pattern），为 Skia 内部代码提供访问 `PrecompileContext` 私有成员的特权接口，而不暴露给外部客户端。这是 Skia 中常用的设计模式，用于维护清晰的公共/私有 API 边界。

该类纯粹是一个访问窗口，不包含任何额外的数据成员或虚函数，确保零开销抽象。

## 架构位置

在 Skia Graphite 预编译系统中的位置：

```
skia/
├── include/
│   └── gpu/graphite/
│       └── PrecompileContext.h           # 公共 API
├── src/
    └── gpu/
        └── graphite/
            ├── PrecompileContextPriv.h   # 本文件（私有访问器）
            ├── SharedContext.h           # 共享上下文
            └── PublicPrecompile.cpp      # 使用 Priv 接口
```

## 主要类与结构体

### PrecompileContextPriv

```cpp
class PrecompileContextPriv {
public:
    // 访问器方法
    const Caps* caps() const;
    const ShaderCodeDictionary* shaderCodeDictionary() const;
    ShaderCodeDictionary* shaderCodeDictionary();
    const RendererProvider* rendererProvider() const;
    SharedContext* sharedContext();
    ResourceProvider* resourceProvider();

#if defined(GPU_TEST_UTILS)
    GlobalCache* globalCache();
#endif

private:
    friend class PrecompileContext;

    explicit PrecompileContextPriv(PrecompileContext* precompileContext);
    PrecompileContextPriv& operator=(const PrecompileContextPriv&) = delete;

    // 防止取地址
    const PrecompileContextPriv* operator&() const;
    PrecompileContextPriv* operator&();

    PrecompileContext* fPrecompileContext;
};
```

**设计特点：**
- 仅 `PrecompileContext` 可创建实例（友元）
- 不可复制赋值
- 不可取地址
- 零数据成员开销（仅存储指针）

## 公共 API 函数

### caps

```cpp
const Caps* caps() const {
    return fPrecompileContext->fSharedContext->caps();
}
```

**功能：** 获取 GPU 能力信息

**返回值：** `Caps` 对象，描述 GPU 功能和限制

**使用场景：**
- 查询支持的纹理格式
- 检查功能支持情况
- 决定管线配置

### shaderCodeDictionary

```cpp
const ShaderCodeDictionary* shaderCodeDictionary() const;
ShaderCodeDictionary* shaderCodeDictionary();
```

**功能：** 获取着色器代码字典

**返回值：** 着色器代码字典，管理着色器代码片段

**使用场景：**
- 生成管线键
- 查找预定义的着色器片段
- 注册自定义着色器

### rendererProvider

```cpp
const RendererProvider* rendererProvider() const {
    return fPrecompileContext->fSharedContext->rendererProvider();
}
```

**功能：** 获取渲染器提供者

**返回值：** 所有可用渲染器的集合

**使用场景：**
- 枚举渲染器
- 预编译时遍历所有渲染器

### sharedContext

```cpp
SharedContext* sharedContext() {
    return fPrecompileContext->fSharedContext.get();
}
```

**功能：** 获取共享上下文

**返回值：** 跨 Recorder 共享的上下文对象

### resourceProvider

```cpp
ResourceProvider* resourceProvider() {
    return fPrecompileContext->fResourceProvider.get();
}
```

**功能：** 获取资源提供者

**返回值：** 管理 GPU 资源创建和缓存的对象

**使用场景：**
- 创建图形管线
- 分配 GPU 资源
- 查询缓存

### globalCache（测试专用）

```cpp
#if defined(GPU_TEST_UTILS)
GlobalCache* globalCache() {
    return fPrecompileContext->fSharedContext->globalCache();
}
#endif
```

**功能：** 获取全局缓存（仅测试构建）

**使用场景：**
- 测试缓存行为
- 验证资源重用
- 调试缓存问题

## PrecompileContext 集成

### priv() 方法

```cpp
// 在 PrecompileContext 中定义
inline PrecompileContextPriv PrecompileContext::priv() {
    return PrecompileContextPriv(this);
}

inline const PrecompileContextPriv PrecompileContext::priv() const {
    return PrecompileContextPriv(const_cast<PrecompileContext*>(this));
}
```

**使用方式：**
```cpp
PrecompileContext* context = ...;
const Caps* caps = context->priv().caps();
auto* dict = context->priv().shaderCodeDictionary();
```

## 内部实现细节

### 防止取地址

```cpp
const PrecompileContextPriv* operator&() const;
PrecompileContextPriv* operator&();
```

**原因：**
- 防止创建悬空指针
- 确保临时对象不被持久化
- 强制直接使用模式

**错误用法：**
```cpp
auto* privPtr = &context->priv();  // 编译错误
```

**正确用法：**
```cpp
context->priv().caps();  // 临时对象，立即使用
```

### const 正确性

```cpp
inline const PrecompileContextPriv PrecompileContext::priv() const {
    return PrecompileContextPriv(const_cast<PrecompileContext*>(this));
}
```

**注意：** 使用 `const_cast`，但返回的 `PrecompileContextPriv` 标记为 `const`

**NOLINTNEXTLINE 注释：**
- 抑制 linter 警告（`readability-const-return-type`）
- const 返回类型在此模式中是刻意的设计

### 友元声明

```cpp
friend class PrecompileContext;
```

**作用：** 仅 `PrecompileContext` 可创建 `PrecompileContextPriv` 实例

## 依赖关系

### 直接依赖

1. **PrecompileContext** (include/gpu/graphite/PrecompileContext.h)
   - 被访问的主类

2. **SharedContext** (src/gpu/graphite/SharedContext.h)
   - 提供共享资源和能力信息

3. **Caps** (前向声明)
   - GPU 能力信息

4. **ShaderCodeDictionary** (前向声明)
   - 着色器代码字典

5. **RendererProvider** (前向声明)
   - 渲染器提供者

6. **ResourceProvider** (前向声明)
   - 资源提供者

7. **GlobalCache** (前向声明，测试构建)
   - 全局资源缓存

### 被依赖模块

1. **PublicPrecompile.cpp**
   - 使用 `priv()` 访问内部成员
   - 实现预编译逻辑

2. **测试代码**
   - 使用 `priv()` 进行单元测试
   - 验证内部状态

## 设计模式与设计决策

### 1. Priv 模式（Privilege Pattern）

**实现：**
```cpp
class PrecompileContext {
public:
    PrecompileContextPriv priv();  // 公共接口
private:
    friend class PrecompileContextPriv;
    // 私有成员
};
```

**优势：**
- 清晰的 API 边界
- 内部代码可访问私有成员
- 外部代码无法访问

### 2. 零开销抽象

```cpp
class PrecompileContextPriv {
    PrecompileContext* fPrecompileContext;  // 仅一个指针
};
```

**性能：**
- `sizeof(PrecompileContextPriv) == sizeof(void*)`
- 方法调用可内联
- 零运行时开销

### 3. 临时对象模式

```cpp
context->priv().caps();  // PrecompileContextPriv 是临时对象
```

**优势：**
- 不需要存储 Priv 对象
- 语法简洁
- 防止意外持久化

### 4. const 正确性

提供 const 和非 const 版本：

```cpp
PrecompileContextPriv priv();
const PrecompileContextPriv priv() const;
```

**保证：** 从 const Context 无法修改内部状态

### 5. 条件编译

```cpp
#if defined(GPU_TEST_UTILS)
    GlobalCache* globalCache();
#endif
```

**原因：**
- 测试工具仅在测试构建可用
- 减少生产构建的 API 表面
- 避免测试代码污染生产代码

## 性能考量

### 1. 内联优化

所有方法都在头文件中定义：

**优势：**
- 编译器可完全内联
- 零函数调用开销
- 等同于直接访问

**实际开销：**
```cpp
context->priv().caps();
// 编译后等价于：
context->fSharedContext->caps();
```

### 2. 指针传递

```cpp
PrecompileContextPriv(PrecompileContext* precompileContext)
    : fPrecompileContext(precompileContext) {}
```

**开销：** 单个指针赋值（~1 CPU 周期）

### 3. 临时对象

```cpp
context->priv().caps();  // 创建临时 PrecompileContextPriv
```

**优化：**
- 编译器优化掉临时对象
- RVO/NRVO 消除拷贝
- 零额外开销

## 相关文件

### 核心依赖
- `include/gpu/graphite/PrecompileContext.h` - 主类
- `src/gpu/graphite/SharedContext.h` - 共享上下文

### 类似 Priv 类
- `src/gpu/graphite/ContextPriv.h` - Context 的 Priv 类
- `src/gpu/graphite/RecorderPriv.h` - Recorder 的 Priv 类
- `src/core/SkImagePriv.h` - SkImage 的 Priv 类
- `src/core/SkPathPriv.h` - SkPath 的 Priv 类

### 使用者
- `src/gpu/graphite/PublicPrecompile.cpp` - 预编译实现
- `tests/graphite/PrecompileTest.cpp` - 预编译测试

### 设计文档
- Skia Priv 模式指南
- API 设计最佳实践
