# StrikeForGPU - GPU 文本 Strike 接口

> 源文件: `src/text/StrikeForGPU.h`, `src/text/StrikeForGPU.cpp`

## 概述

StrikeForGPU 模块定义了 GPU 文本渲染所需的 Strike（字形缓存）抽象接口。核心组件包括 SkStrikePromise（延迟获取 Strike 的承诺对象）、StrikeForGPU（GPU 端 Strike 操作的纯虚接口）、以及相关的辅助类型（IDOrPath、IDOrDrawable、StrikeMutationMonitor）。

该模块解决了 GPU 文本渲染中多线程与序列化的核心问题：在多线程环境中创建文本数据，但延迟到 GPU 单线程环境中才实际获取 Strike。

## 架构位置

```
sktext 命名空间
  ├── SkStrikePromise — Strike 的延迟获取承诺
  ├── StrikeForGPU — GPU Strike 操作接口（纯虚）
  ├── StrikeForGPUCacheInterface — GPU Strike 缓存接口
  └── StrikeMutationMonitor — RAII 锁管理
```

- **上层使用**: SubRunContainer、GlyphVector、SlugImpl
- **下层依赖**: SkStrike、SkStrikeCache、SkStrikeSpec、SkDescriptor

## 主要类与结构体

### SkStrikePromise
延迟获取 SkStrike 的承诺对象。支持两种状态：
- 持有 `sk_sp<SkStrike>` — 直接引用已有 Strike
- 持有 `unique_ptr<SkStrikeSpec>` — 延迟查找，调用 `strike()` 时从全局缓存获取

**设计意义**: 在远程字形缓存场景中，SkStrikePromise 序列化为 SkDescriptor，反序列化时用描述符从缓存中查找 Strike。

### StrikeForGPU
纯虚接口类（继承 SkRefCnt），定义 GPU 端 Strike 操作：
- `lock()` / `unlock()` — 加锁/解锁（防止并发修改）
- `digestFor()` — 为指定字形生成摘要
- `prepareForImage/Path/Drawable()` — 准备字形渲染数据
- `strikePromise()` — 返回 Strike 承诺

### StrikeMutationMonitor
RAII 风格的锁管理器，构造时调用 `strike->lock()`，析构时调用 `unlock()`。

### IDOrPath / IDOrDrawable
联合体类型，用于延迟将字形 ID 转换为 SkPath 或 SkDrawable：
- 初始存储 SkGlyphID
- 渲染时原地替换为 SkPath 或 SkDrawable 指针

### StrikeForGPUCacheInterface
GPU Strike 缓存的工厂接口，提供 `findOrCreateScopedStrike` 方法。

## 公共 API 函数

```cpp
// SkStrikePromise
explicit SkStrikePromise(sk_sp<SkStrike>&& strike);
explicit SkStrikePromise(const SkStrikeSpec& spec);
static std::optional<SkStrikePromise> MakeFromBuffer(SkReadBuffer&, const SkStrikeClient*, SkStrikeCache*);
void flatten(SkWriteBuffer&) const;
SkStrike* strike();       // 获取或延迟创建 Strike
void resetStrike();       // 释放 Strike 引用
const SkDescriptor& descriptor() const;
```

## 内部实现细节

### SkStrikePromise::strike()
使用 `std::variant` 的两阶段模式：
1. 若持有 SkStrikeSpec，则从全局 StrikeCache 查找/创建 Strike，然后替换 variant 内容
2. 若已持有 Strike，直接返回

### 序列化/反序列化
- `flatten()`: 序列化底层描述符
- `MakeFromBuffer()`: 反序列化描述符，可选地通过 SkStrikeClient 转换 TypfaceID，然后从缓存查找 Strike

## 依赖关系

- `SkStrike` / `SkStrikeCache` — Strike 缓存系统
- `SkStrikeSpec` — Strike 查找规范
- `SkDescriptor` — Strike 描述符
- `SkGlyph` / `SkGlyphDigest` — 字形数据
- `SkPath` / `SkDrawable` — 字形渲染形式

## 设计模式与设计决策

1. **Promise 模式**: SkStrikePromise 实现了延迟获取模式，适配多线程创建+单线程消费的场景
2. **Variant 状态机**: 使用 `std::variant<sk_sp<SkStrike>, unique_ptr<SkStrikeSpec>>` 表达两种状态
3. **RAII 锁**: StrikeMutationMonitor 确保 Strike 访问期间的线程安全
4. **Union 优化**: IDOrPath/IDOrDrawable 通过联合体实现零开销的延迟转换

## 性能考量

- SkStrikePromise 的延迟获取避免了不必要的 Strike 创建
- IDOrPath 联合体避免了额外的内存分配
- StrikeMutationMonitor 的 RAII 模式确保锁的正确释放

## 相关文件

- `src/core/SkStrike.h` — Strike 实现
- `src/core/SkStrikeCache.h` — 全局 Strike 缓存
- `src/core/SkStrikeSpec.h` — Strike 查找规范
- `src/text/gpu/GlyphVector.h` — 使用 SkStrikePromise 的字形向量
