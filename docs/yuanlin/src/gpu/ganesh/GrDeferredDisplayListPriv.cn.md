# GrDeferredDisplayListPriv

> 源文件
> - src/gpu/ganesh/GrDeferredDisplayListPriv.h

## 概述

`GrDeferredDisplayListPriv` 是 `GrDeferredDisplayList`（延迟显示列表，DDL）的特权访问类，为 Skia 内部代码提供对 DDL 私有成员的访问接口。该类遵循"特权窗口"（Privileged Window）设计模式，不包含任何自有数据成员或虚函数，仅作为访问 `GrDeferredDisplayList` 内部实现的桥梁。

DDL 是 Skia 的一种预录制渲染命令机制，允许在一个线程或上下文中录制渲染操作，然后在另一个线程或上下文中回放。`GrDeferredDisplayListPriv` 提供了访问DDL内部渲染任务列表、目标代理、延迟代理数据和程序数据的内部接口。

## 架构位置

`GrDeferredDisplayListPriv` 位于 Skia DDL 架构的核心层：

```
Skia Deferred Display List Architecture
├── Public API Layer (公共API层)
│   └── GrDeferredDisplayList (DDL容器)
├── Privileged Access Layer (特权访问层)
│   └── GrDeferredDisplayListPriv ← 当前模块
├── Recording Layer (录制层)
│   └── GrDeferredDisplayListRecorder (DDL录制器)
├── Execution Layer (执行层)
│   └── GrDDLTask (DDL任务)
└── Internal Data (内部数据)
    ├── fRenderTasks (渲染任务列表)
    ├── fTargetProxy (目标代理)
    ├── fLazyProxyData (延迟代理数据)
    └── fProgramData (程序数据)
```

该模块在架构中的职责：
- 为内部模块提供受控的DDL数据访问
- 隔离公共API与内部实现细节
- 支持DDL的回放和调试
- 访问渲染任务列表和代理信息

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|-----|---------|------|
| `GrDeferredDisplayListPriv` | 无 | DDL特权访问类 |

### 访问的DDL内部成员

| 成员 | 类型 | 说明 |
|-----|------|------|
| `fRenderTasks` | `skia_private::TArray<sk_sp<GrRenderTask>>` | 录制的渲染任务列表 |
| `fTargetProxy` | `sk_sp<GrRenderTargetProxy>` | DDL的目标渲染表面代理 |
| `fLazyProxyData` | `sk_sp<LazyProxyData>` | 延迟代理数据 |
| `fProgramData` | `TArray<GrRecordingContext::ProgramData>` | 着色器程序数据 |

## 公共 API 函数

### numRenderTasks
```cpp
int numRenderTasks() const;
```
获取DDL中渲染任务的数量。

**返回值：** 渲染任务数量

### targetProxy
```cpp
GrRenderTargetProxy* targetProxy() const;
```
获取DDL的目标渲染表面代理。

**返回值：** 目标代理指针，如果没有则为 `nullptr`

### lazyProxyData
```cpp
const GrDeferredDisplayList::LazyProxyData* lazyProxyData() const;
```
获取延迟代理数据。

**返回值：** 延迟代理数据指针

**用途：** 包含回放时用于实例化延迟代理的信息

### programData
```cpp
const skia_private::TArray<GrRecordingContext::ProgramData>& programData() const;
```
获取着色器程序数据数组。

**返回值：** 程序数据的常量引用

**用途：** 包含DDL中使用的所有着色器程序的描述和信息，用于预编译

### renderTasks
```cpp
const skia_private::TArray<sk_sp<GrRenderTask>>& renderTasks() const;
```
获取渲染任务列表。

**返回值：** 渲染任务数组的常量引用

**用途：** 访问DDL中录制的所有渲染任务，用于回放和调试

## 内部实现细节

### 特权访问器实现

`GrDeferredDisplayListPriv` 的实现非常简洁，仅包含一个指向 `GrDeferredDisplayList` 的指针：

```cpp
class GrDeferredDisplayListPriv {
public:
    int numRenderTasks() const {
        return fDDL->fRenderTasks.size();
    }

    GrRenderTargetProxy* targetProxy() const {
        return fDDL->fTargetProxy.get();
    }

    const GrDeferredDisplayList::LazyProxyData* lazyProxyData() const {
        return fDDL->fLazyProxyData.get();
    }

    const skia_private::TArray<GrRecordingContext::ProgramData>& programData() const {
        return fDDL->programData();
    }

    const skia_private::TArray<sk_sp<GrRenderTask>>& renderTasks() const {
        return fDDL->fRenderTasks;
    }

private:
    explicit GrDeferredDisplayListPriv(GrDeferredDisplayList* ddl) : fDDL(ddl) {}
    GrDeferredDisplayListPriv& operator=(const GrDeferredDisplayListPriv&) = delete;

    const GrDeferredDisplayListPriv* operator&() const;  // 禁止取地址
    GrDeferredDisplayListPriv* operator&();

    GrDeferredDisplayList* fDDL;

    friend class GrDeferredDisplayList;
};
```

### 访问方法

在 `GrDeferredDisplayList` 类中提供访问方法：

```cpp
class GrDeferredDisplayList {
public:
    GrDeferredDisplayListPriv priv() {
        return GrDeferredDisplayListPriv(this);
    }

    const GrDeferredDisplayListPriv priv() const {
        return GrDeferredDisplayListPriv(const_cast<GrDeferredDisplayList*>(this));
    }

private:
    friend class GrDeferredDisplayListPriv;
    // ... 私有成员 ...
};
```

### 使用示例

```cpp
// 在 GrDDLTask 中访问DDL内部任务
void GrDDLTask::onExecute(GrOpFlushState* flushState) {
    for (auto& task : fDDL->priv().renderTasks()) {
        task->execute(flushState);
    }
}

// 访问任务数量
int numTasks = ddl->priv().numRenderTasks();

// 访问目标代理
GrRenderTargetProxy* target = ddl->priv().targetProxy();
```

### LazyProxyData

延迟代理数据包含回放时需要的信息：

```cpp
struct LazyProxyData {
    sk_sp<GrRenderTargetProxy> fReplayDest;  // 回放目标
};
```

当DDL回放时，`fReplayDest` 指向实际的渲染目标，延迟代理通过它实例化。

### ProgramData

程序数据包含着色器程序的描述：

```cpp
struct ProgramData {
    GrProgramDesc desc;    // 程序描述符
    GrProgramInfo info;    // 程序信息
};
```

用于支持DDL的程序预编译功能。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrDeferredDisplayList` | 被访问的DDL对象 |
| `GrRenderTask` | 渲染任务 |
| `GrRenderTargetProxy` | 渲染目标代理 |
| `GrRecordingContext::ProgramData` | 程序数据 |
| `skia_private::TArray` | 动态数组 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `GrDDLTask` | 访问DDL内部渲染任务 |
| `GrDrawingManager` | 处理DDL任务 |
| DDL调试工具 | 检查DDL内容 |
| 着色器预编译系统 | 访问程序数据 |

## 设计模式与设计决策

### 特权访问器模式（Privileged Window Pattern）

这是该类的核心设计模式：

```cpp
class GrDeferredDisplayListPriv {
private:
    explicit GrDeferredDisplayListPriv(GrDeferredDisplayList* ddl);
    GrDeferredDisplayListPriv& operator=(const GrDeferredDisplayListPriv&) = delete;
    const GrDeferredDisplayListPriv* operator&() const;
    GrDeferredDisplayListPriv* operator&();
    friend class GrDeferredDisplayList;
};
```

**优点：**
- 清晰分离公共API和内部接口
- 避免友元类污染
- 零运行时开销
- 类型安全
- 防止误用（禁止取地址）

### 不可变访问（Immutable Access）

所有访问方法都返回常量引用或常量指针：
```cpp
const skia_private::TArray<sk_sp<GrRenderTask>>& renderTasks() const;
```

保证外部代码不能修改DDL的内部状态，维护DDL的不可变性。

### 友元访问控制

使用友元机制限制访问权限：
```cpp
friend class GrDeferredDisplayList;
```

只有 `GrDeferredDisplayList` 可以创建 `GrDeferredDisplayListPriv` 实例。

### const正确性

提供const和非const版本的 `priv()` 方法：
```cpp
GrDeferredDisplayListPriv priv();
const GrDeferredDisplayListPriv priv() const;
```

但所有访问方法都返回const数据，确保DDL内容不被修改。

### 设计决策

1. **不包含数据成员**：确保特权访问器没有额外的内存开销
2. **禁止取地址**：防止误用和生命周期问题
3. **返回值拷贝**：`priv()` 返回值对象而非引用，利用RVO优化
4. **内联访问**：所有方法都很简单，可以内联优化
5. **禁止赋值**：防止创建多个访问器实例

## 性能考量

### 零开销抽象

`GrDeferredDisplayListPriv` 设计为零开销抽象：
- 无虚函数
- 仅一个指针成员
- 所有方法可内联
- 编译器可完全优化掉包装

### 直接访问

内部方法直接访问DDL的私有成员，无间接调用：
```cpp
return fDDL->fRenderTasks.size();  // 直接访问
```

### 返回值优化（RVO）

`priv()` 方法返回值对象，编译器应用RVO优化，避免拷贝：
```cpp
GrDeferredDisplayListPriv priv() { return GrDeferredDisplayListPriv(this); }
```

实际上等价于传递 `this` 指针。

### 避免虚函数调用

使用内联方法而非虚函数，避免虚函数表查找开销。

### 常量引用返回

返回常量引用避免拷贝大型数组：
```cpp
const skia_private::TArray<sk_sp<GrRenderTask>>& renderTasks() const;
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/private/chromium/GrDeferredDisplayList.h` | 被访问 | DDL公共接口 |
| `src/gpu/ganesh/GrDDLTask.h` | 使用 | DDL任务 |
| `src/gpu/ganesh/GrRenderTask.h` | 访问 | 渲染任务 |
| `src/gpu/ganesh/GrRenderTargetProxy.h` | 访问 | 渲染目标代理 |
| `include/private/chromium/GrDeferredDisplayListRecorder.h` | 关联 | DDL录制器 |
| `src/gpu/ganesh/GrDrawingManager.h` | 使用 | 绘制管理器 |
| `src/gpu/ganesh/GrRecordingContext.h` | 访问 | 录制上下文（ProgramData定义） |
| `include/private/base/SkTArray.h` | 依赖 | 动态数组 |
