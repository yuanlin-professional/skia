# SkFontConfigInterface

> 源文件: include/ports/SkFontConfigInterface.h, src/ports/SkFontConfigInterface.cpp

## 概述

`SkFontConfigInterface` 是 Skia 图形库提供的一个简单的远程字体管理接口。它定义了一个抽象的字体配置接口，允许客户端通过轻量级的协议查询和访问字体资源。该接口设计用于支持远程字体服务场景，例如在沙盒化的渲染进程中，通过 IPC 向主进程请求字体信息。

该模块提供全局单例管理机制，支持自定义实现的注入，并包含默认的直接访问 libfontconfig 的实现。

## 架构位置

```
skia/
├── include/
│   └── ports/
│       └── SkFontConfigInterface.h    # 公共接口定义
└── src/
    └── ports/
        └── SkFontConfigInterface.cpp   # 全局单例和默认实现
```

该模块位于 `ports` 层，为 Linux/Unix 系统提供字体配置抽象，是跨平台字体系统的一部分。

## 主要类与结构体

### SkFontConfigInterface

字体配置接口的抽象基类。

**继承关系:**
- 继承自 `SkRefCnt`

**关键成员变量:**
无直接成员变量（抽象基类）

### FontIdentity

字体标识符结构体，用于唯一标识一个字体。

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fID` | uint32_t | 字体的唯一标识符 |
| `fTTCIndex` | int32_t | TrueType Collection 中的索引 |
| `fString` | SkString | 字体文件路径或其他字符串标识 |
| `fStyle` | SkFontStyle | 字体样式（粗细、宽度、倾斜） |

**公共方法:**

| 方法名 | 说明 |
|--------|------|
| `operator==` | 比较两个 FontIdentity 是否相等 |
| `operator!=` | 比较两个 FontIdentity 是否不等 |
| `writeToMemory` | 序列化到内存（对齐到 4 字节） |
| `readFromMemory` | 从内存反序列化 |

## 公共 API 函数

### RefGlobal

```cpp
static sk_sp<SkFontConfigInterface> RefGlobal();
```

获取全局 `SkFontConfigInterface` 实例。如果全局实例不为空，则对其调用 `ref()`，调用者需要平衡 `unref()`。如果全局实例为空，则返回 `GetSingletonDirectInterface` 的结果。

**返回值:**
- 全局字体配置接口的智能指针

### SetGlobal

```cpp
static void SetGlobal(sk_sp<SkFontConfigInterface> fc);
```

替换当前的全局实例。

**参数:**
- `fc`: 新的全局字体配置接口实例

**注意事项:**
- 会释放之前的全局实例
- 线程安全（使用互斥锁保护）

### matchFamilyName

```cpp
virtual bool matchFamilyName(
    const char familyName[],
    SkFontStyle requested,
    FontIdentity* outFontIdentifier,
    SkString* outFamilyName,
    SkFontStyle* outStyle
) = 0;
```

根据字体族名称和样式查找最佳匹配的字体。

**参数:**
- `familyName`: 请求的字体族名称
- `requested`: 请求的字体样式
- `outFontIdentifier`: [输出] 匹配的字体标识符
- `outFamilyName`: [输出] 实际找到的字体族名称（可能与请求不同）
- `outStyle`: [输出] 实际找到的字体样式（可能与请求不同）

**返回值:**
- 找到匹配返回 `true`，否则返回 `false`

### openStream

```cpp
virtual SkStreamAsset* openStream(const FontIdentity&) = 0;
```

根据字体标识符打开字体数据流。

**参数:**
- `FontIdentity`: 字体标识符

**返回值:**
- 字体数据流，如果无法访问则返回 `nullptr`
- 调用者负责删除返回的流

### makeTypeface

```cpp
virtual sk_sp<SkTypeface> makeTypeface(
    const FontIdentity& identity,
    sk_sp<SkFontMgr> mgr
);
```

根据字体标识符创建 `SkTypeface` 实例。

**参数:**
- `identity`: 字体标识符
- `mgr`: 字体管理器，用于构建字体实例

**返回值:**
- `SkTypeface` 智能指针

**默认实现:**
使用 `openStream()` 获取字体数据流，然后通过 `mgr->makeFromStream()` 创建字体实例。派生类可以实现更复杂的缓存方案。

### GetSingletonDirectInterface

```cpp
static SkFontConfigInterface* GetSingletonDirectInterface();
```

返回直接访问 libfontconfig 的单例实例。该方法不影响返回实例的引用计数。

**返回值:**
- 直接访问 libfontconfig 的接口实例

## 内部实现细节

### 全局单例管理

使用静态互斥锁 `font_config_interface_mutex()` 保护全局实例 `gFontConfigInterface`：

```cpp
static SkMutex& font_config_interface_mutex() {
    static SkMutex& mutex = *(new SkMutex);
    return mutex;
}
static SkFontConfigInterface* gFontConfigInterface;
```

这种实现确保：
- 线程安全的单例访问
- 避免静态析构顺序问题（使用堆分配的互斥锁）

### RefGlobal 实现逻辑

```cpp
sk_sp<SkFontConfigInterface> SkFontConfigInterface::RefGlobal() {
    SkAutoMutexExclusive ac(font_config_interface_mutex());

    if (gFontConfigInterface) {
        return sk_ref_sp(gFontConfigInterface);
    }
    return sk_ref_sp(SkFontConfigInterface::GetSingletonDirectInterface());
}
```

1. 获取互斥锁
2. 如果全局实例存在，返回其智能指针
3. 否则，返回直接接口的单例

### SetGlobal 实现逻辑

```cpp
void SkFontConfigInterface::SetGlobal(sk_sp<SkFontConfigInterface> fc) {
    SkAutoMutexExclusive ac(font_config_interface_mutex());

    SkSafeUnref(gFontConfigInterface);
    gFontConfigInterface = fc.release();
}
```

1. 获取互斥锁
2. 安全释放旧的全局实例
3. 将新实例的所有权转移到全局变量

### makeTypeface 默认实现

```cpp
sk_sp<SkTypeface> SkFontConfigInterface::makeTypeface(
    const FontIdentity& identity,
    sk_sp<SkFontMgr> mgr
) {
    return mgr->makeFromStream(
        std::unique_ptr<SkStreamAsset>(this->openStream(identity)),
        identity.fTTCIndex
    );
}
```

默认实现简单地：
1. 调用 `openStream` 获取字体数据流
2. 将流传递给字体管理器的 `makeFromStream` 方法
3. 使用 `fTTCIndex` 指定 TTC 集合中的字体索引

派生类可以重写此方法以实现更复杂的缓存策略。

### FontIdentity 序列化

`writeToMemory` 和 `readFromMemory` 方法提供二进制序列化支持，用于跨进程传输字体标识符（例如通过共享内存或 IPC）。序列化格式对齐到 4 字节边界。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRefCnt` | 引用计数基类 |
| `SkMutex` | 互斥锁，保护全局单例 |
| `SkFontMgr` | 字体管理器，用于创建字体实例 |
| `SkStream` | 字体数据流接口 |
| `SkTypeface` | 字体类型接口 |
| `SkFontStyle` | 字体样式描述 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFontMgr_FontConfigInterface` | 使用该接口实现字体管理器 |
| 沙盒化渲染进程 | 通过该接口访问主进程的字体资源 |
| libfontconfig 封装 | 直接接口实现 |

## 设计模式与设计决策

### 抽象工厂模式

`SkFontConfigInterface` 定义抽象接口，具体实现可以是：
- 直接访问 libfontconfig（通过 `GetSingletonDirectInterface`）
- 通过 IPC 与远程服务通信
- 自定义的字体配置逻辑

### 单例模式

全局单例设计允许：
- 系统范围内共享同一个字体配置接口
- 支持自定义实现的注入（通过 `SetGlobal`）
- 提供默认实现（通过 `GetSingletonDirectInterface`）

### 序列化支持

`FontIdentity` 提供序列化方法，支持：
- 跨进程传输字体标识符
- 缓存字体查询结果
- IPC 消息编码

### 延迟加载

`RefGlobal` 在全局实例不存在时才创建默认实例，支持延迟初始化。

### 扩展点设计

`makeTypeface` 提供默认实现，但允许派生类重写以实现：
- 字体实例缓存
- 自定义字体加载策略
- 性能优化

## 性能考量

### 线程安全开销

全局单例访问需要获取互斥锁，可能成为多线程场景的瓶颈。优化策略：
- 使用 `RefGlobal` 缓存本地副本，避免重复获取
- 考虑使用原子操作或读写锁优化

### IPC 延迟

如果接口实现基于 IPC：
- 每次 `matchFamilyName` 和 `openStream` 调用都涉及进程间通信
- 建议在客户端实现缓存层

### 默认实现性能

`makeTypeface` 默认实现每次都打开新的流，可能导致：
- 重复的文件 I/O
- 重复的字体解析

派生类应该实现缓存机制。

### 内存使用

`FontIdentity` 包含 `SkString`，可能产生堆分配。对于高频使用场景，考虑：
- 使用对象池
- 实现更紧凑的序列化格式

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/ports/SkFontConfigInterface.h` | 接口定义头文件 |
| `src/ports/SkFontConfigInterface.cpp` | 全局单例实现 |
| `include/ports/SkFontMgr_FontConfigInterface.h` | 基于该接口的字体管理器 |
| `src/ports/SkFontMgr_FontConfigInterface.cpp` | 字体管理器实现 |
| `src/ports/SkFontConfigInterface_direct.h` | 直接访问 libfontconfig 的实现 |
| `src/ports/SkFontConfigInterface_direct.cpp` | 直接接口实现 |
| `include/core/SkFontMgr.h` | 字体管理器基类 |
| `include/core/SkTypeface.h` | 字体类型基类 |
