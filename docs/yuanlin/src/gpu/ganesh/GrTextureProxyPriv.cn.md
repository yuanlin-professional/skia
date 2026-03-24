# GrTextureProxyPriv

> 源文件: src/gpu/ganesh/GrTextureProxyPriv.h

## 概述

`GrTextureProxyPriv` 是 `GrTextureProxy` 的特权访问辅助类，用于封装对纹理代理的高级特性访问接口。该类采用"友元访问器"（Friend Accessor）设计模式，提供了对 `GrTextureProxy` 内部功能的受控访问，主要用于管理延迟上传（deferred upload）操作。

该类的主要职责是管理在工作线程中准备的纹理数据的延迟上传，使得纹理数据可以在录制阶段准备好，在实际 flush 阶段才上传到 GPU，从而支持多线程渲染和 DDL（Deferred Display List）工作流。

## 架构位置

`GrTextureProxyPriv` 位于 Skia GPU 代理访问控制层：

```
Skia GPU 代理系统
├── GrTextureProxy                    # 纹理代理主类
│   ├── 公共接口                       # 一般操作
│   └── 私有成员                       # 内部状态
│       └── fDeferredUploader          # 延迟上传器
└── GrTextureProxyPriv (本类)          # 特权访问接口
    └── setDeferredUploader()          # 管理延迟上传
    └── scheduleUpload()               # 调度上传
    └── resetDeferredUploader()        # 清理上传器
```

访问模式：
```
外部代码 → textureProxy->texPriv().setDeferredUploader(...)
         (通过 texPriv() 访问特权接口)
```

## 主要类与结构体

### 继承关系

该类不使用继承，而是作为 `GrTextureProxy` 的嵌套友元类。

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fTextureProxy | GrTextureProxy* | 指向关联的纹理代理 |

### 关联类型

**GrDeferredProxyUploader**：
- 存储待上传的纹理数据
- 在 flush 时执行实际上传
- 上传完成后可释放 CPU 内存

## 公共 API 函数

### 设置延迟上传器

```cpp
void setDeferredUploader(std::unique_ptr<GrDeferredProxyUploader> uploader)
```

**功能**：为纹理代理附加延迟上传器对象。

**使用场景**：
- 在工作线程准备纹理数据
- 数据保存在 uploader 中
- 代理保持未实例化状态

**前置条件**：
- 纹理代理尚未设置上传器（通过断言检查）

### 检查是否有延迟上传

```cpp
bool isDeferred() const
```

**功能**：检查纹理代理是否附加了延迟上传器。

**返回值**：
- `true`: 有延迟上传器
- `false`: 无延迟上传器

### 调度上传

```cpp
void scheduleUpload(GrOpFlushState* flushState)
```

**功能**：为延迟代理调度 ASAP（尽快）上传操作。

**执行条件**：
- 纹理代理有延迟上传器
- 纹理代理已实例化（有实际 GPU 纹理）

**使用时机**：
- 在 flush 阶段
- 纹理即将被使用之前

### 重置延迟上传器

```cpp
void resetDeferredUploader()
```

**功能**：清除纹理代理的延迟上传器对象。

**使用场景**：
- 上传完成后释放 CPU 内存
- 清理不再需要的上传器

**前置条件**：
- 纹理代理必须有上传器（通过断言检查）

## 内部实现细节

### 构造函数

```cpp
explicit GrTextureProxyPriv(GrTextureProxy* textureProxy)
    : fTextureProxy(textureProxy) {}
```

- 私有构造函数，只能通过 `GrTextureProxy::texPriv()` 创建
- 简单地存储指向纹理代理的指针

### setDeferredUploader 实现

```cpp
void GrTextureProxyPriv::setDeferredUploader(
    std::unique_ptr<GrDeferredProxyUploader> uploader) {
    SkASSERT(!fTextureProxy->fDeferredUploader);
    fTextureProxy->fDeferredUploader = std::move(uploader);
}
```

**实现逻辑**：
1. 断言当前没有上传器（避免覆盖）
2. 移动语义转移所有权到纹理代理

### scheduleUpload 实现

```cpp
void GrTextureProxyPriv::scheduleUpload(GrOpFlushState* flushState) {
    if (fTextureProxy->fDeferredUploader &&
        fTextureProxy->isInstantiated()) {
        fTextureProxy->fDeferredUploader->scheduleUpload(
            flushState, fTextureProxy);
    }
}
```

**实现逻辑**：
1. 检查是否有上传器
2. 检查是否已实例化
3. 调用上传器的 `scheduleUpload()` 方法
4. 如果实例化失败或内容已上传，静默跳过

### resetDeferredUploader 实现

```cpp
void GrTextureProxyPriv::resetDeferredUploader() {
    SkASSERT(fTextureProxy->fDeferredUploader);
    fTextureProxy->fDeferredUploader.reset();
}
```

**实现逻辑**：
1. 断言有上传器（确保正确使用）
2. 重置 unique_ptr，释放上传器对象

### 访问控制

该类使用多层访问控制：

1. **私有构造函数**：防止外部直接创建
2. **友元声明**：只有 `GrTextureProxy` 可以创建实例
3. **禁止取地址**：
   ```cpp
   const GrTextureProxyPriv* operator&() const;
   GrTextureProxyPriv* operator&();
   ```
   声明但不定义，防止持久化指针

### 创建方法

```cpp
// 在 GrTextureProxy 中定义
inline GrTextureProxyPriv GrTextureProxy::texPriv() {
    return GrTextureProxyPriv(this);
}

inline const GrTextureProxyPriv GrTextureProxy::texPriv() const {
    return GrTextureProxyPriv(const_cast<GrTextureProxy*>(this));
}
```

返回值语义，不持有持久引用。

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|-----|---------|------|
| GrTextureProxy | 友元访问 | 被访问的主类 |
| GrDeferredProxyUploader | 使用 | 延迟上传器接口 |
| GrOpFlushState | 参数类型 | 刷新状态上下文 |
| SkToBool | 工具函数 | 类型转换辅助 |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|-----|---------|------|
| GrProxyProvider | 使用 | 在创建代理时设置上传器 |
| GrOpFlushState | 使用 | 在 flush 时调度上传 |
| DDL 录制代码 | 使用 | 多线程纹理准备 |

## 设计模式与设计决策

### 友元访问器模式（Friend Accessor Pattern）

**设计理念**：
```cpp
class GrTextureProxy {
private:
    friend class GrTextureProxyPriv;
    std::unique_ptr<GrDeferredProxyUploader> fDeferredUploader;
public:
    GrTextureProxyPriv texPriv();
};

class GrTextureProxyPriv {
    void setDeferredUploader(...);
};
```

**优势**：
1. **封装性**：私有成员对外不可见
2. **控制访问**：只有特权代码可以访问
3. **清晰意图**：`.texPriv()` 明确表示特权操作
4. **类型安全**：编译时检查访问权限

### 禁止持久化

**防止滥用**：
```cpp
// 正确使用（临时对象）
proxy->texPriv().setDeferredUploader(...);

// 错误使用（被禁止）
auto* priv = &proxy->texPriv();  // 编译错误
```

通过禁止取地址，强制使用短期临时对象模式。

### 返回值语义

返回 `GrTextureProxyPriv` 对象而非指针：
- 自动生命周期管理
- 栈分配，无堆开销
- 编译器可以优化掉临时对象

### const 正确性

提供 const 和非 const 版本：
```cpp
GrTextureProxyPriv texPriv();
const GrTextureProxyPriv texPriv() const;
```

const 版本允许在 const 纹理代理上查询状态（如 `isDeferred()`）。

### 移动语义

`setDeferredUploader()` 使用移动语义：
```cpp
void setDeferredUploader(std::unique_ptr<GrDeferredProxyUploader> uploader)
```

明确转移所有权，避免复制开销。

## 性能考量

### 零开销抽象

- `GrTextureProxyPriv` 只是薄包装层
- 编译器可以内联所有方法调用
- 运行时无额外开销

### 延迟上传优势

1. **多线程准备**：
   - 工作线程在 CPU 准备数据
   - 主线程不阻塞
   - 提高并行度

2. **内存管理**：
   - 上传前：CPU 内存
   - 上传后：GPU 内存
   - 上传完成释放 CPU 内存

3. **批处理**：
   - 多个上传可批量处理
   - 减少 GPU 同步点
   - 提高吞吐量

### ASAP 上传策略

`scheduleUpload()` 安排尽快上传：
- 减少后续绘制操作的等待时间
- 允许 GPU 尽早开始处理数据
- 优化流水线效率

### 条件检查优化

```cpp
if (fTextureProxy->fDeferredUploader &&
    fTextureProxy->isInstantiated())
```

短路求值：
- 大多数情况下第一个条件为 false
- 避免不必要的 `isInstantiated()` 调用

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrTextureProxy.h | 主类 | 被访问的纹理代理类 |
| src/gpu/ganesh/GrTextureProxy.cpp | 实现 | texPriv 方法的实现 |
| src/gpu/ganesh/GrDeferredProxyUploader.h | 使用 | 延迟上传器接口 |
| src/gpu/ganesh/GrOpFlushState.h | 使用 | 刷新状态类 |
| src/gpu/ganesh/GrProxyProvider.h | 使用者 | 设置延迟上传器 |
| include/private/base/SkTo.h | 工具 | SkToBool 辅助函数 |
