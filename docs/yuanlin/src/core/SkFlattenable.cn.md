# SkFlattenable

> 源文件
> - include/core/SkFlattenable.h
> - src/core/SkFlattenable.cpp

## 概述

`SkFlattenable` 是 Skia 中所有可序列化对象的抽象基类,提供了对象扁平化(序列化)和反扁平化(反序列化)的基础框架。它支持将复杂的图形效果对象(如着色器、颜色滤镜、图像滤镜等)转换为字节流,以便在进程间传输或持久化存储,并能通过工厂函数重建原始对象。

该类通过全局注册表机制管理类名到工厂函数的映射,支持动态类型识别和对象创建。`SkFlattenable` 是 Skia 实现跨平台对象序列化、字体缓存键生成、以及远程渲染等高级功能的核心基础设施。

## 架构位置

`SkFlattenable` 在 Skia 架构中处于序列化层,为各种图形效果类提供统一的序列化接口:

```
应用层对象(SkPaint, SkCanvas等)
    ↓
效果对象(继承自 SkFlattenable)
    - SkColorFilter
    - SkShader
    - SkImageFilter
    - SkMaskFilter
    - SkPathEffect
    - SkBlender
    ↓
SkFlattenable (序列化基类)
    ↓
SkReadBuffer / SkWriteBuffer (序列化工具)
    ↓
二进制数据流 / 字体缓存键
```

**关键交互模块**:
- **SkWriteBuffer**: 负责将对象写入字节流
- **SkReadBuffer**: 负责从字节流读取并重建对象
- **全局注册表**: 管理类名与工厂函数的映射关系

## 主要类与结构体

### SkFlattenable

**继承关系**
```
SkRefCnt (引用计数基类)
    ↓
SkFlattenable (序列化基类)
    ↓
具体效果类:
    ├── SkColorFilter
    ├── SkShader
    ├── SkImageFilter
    ├── SkMaskFilter
    ├── SkPathEffect
    ├── SkBlender
    └── SkDrawable
```

**关键成员类型**

| 类型定义 | 说明 |
|---------|------|
| `Factory` | 类型别名,指向工厂函数的指针:`sk_sp<SkFlattenable> (*)(SkReadBuffer&)` |

**枚举类型: Type**

| 枚举值 | 说明 |
|-------|------|
| `kSkColorFilter_Type` | 颜色滤镜类型 |
| `kSkBlender_Type` | 混合器类型 |
| `kSkDrawable_Type` | 可绘制对象类型 |
| `kSkDrawLooper_Type` | 绘制循环器类型(已弃用) |
| `kSkImageFilter_Type` | 图像滤镜类型 |
| `kSkMaskFilter_Type` | 遮罩滤镜类型 |
| `kSkPathEffect_Type` | 路径效果类型 |
| `kSkShader_Type` | 着色器类型 |

### 辅助类

#### SkNamedFactorySet

管理工厂函数的集合,用于序列化时记录引用的工厂。

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFactorySet` | `SkFactorySet` | 存储工厂函数的集合 |
| `fNames` | `SkTDArray<const char*>` | 存储工厂名称的数组 |
| `fNextAddedFactory` | `uint32_t` | 下一个要返回的工厂索引 |

#### SkRefCntSet

管理引用计数对象的集合,基于 `SkPtrRecorder` 实现。

**关键方法**

| 方法 | 说明 |
|-----|------|
| `incPtr(void* ptr)` | 增加对象的引用计数 |
| `decPtr(void* ptr)` | 减少对象的引用计数 |

## 公共 API 函数

### 纯虚函数(派生类必须实现)

```cpp
virtual Factory getFactory() const = 0;
```
- **功能**: 返回用于重建对象的工厂函数
- **实现**: 通常通过 `SK_FLATTENABLE_HOOKS` 宏自动生成

```cpp
virtual const char* getTypeName() const = 0;
```
- **功能**: 返回对象的类名字符串
- **用途**: 序列化时标识对象类型

```cpp
virtual Type getFlattenableType() const = 0;
```
- **功能**: 返回对象所属的类型类别
- **用途**: 反序列化时验证类型匹配

```cpp
virtual void flatten(SkWriteBuffer&) const {}
```
- **功能**: 将对象数据写入缓冲区
- **默认实现**: 空函数(无需序列化额外数据的子类可不实现)
- **注意**: 标记为 DEPRECATED public,将来会移至 protected

### 序列化接口

```cpp
sk_sp<SkData> serialize(const SkSerialProcs* procs = nullptr) const;
```
- **功能**: 将对象序列化为 `SkData` 对象
- **参数**: `procs` - 可选的序列化配置
- **返回值**: 包含序列化数据的 `SkData` 智能指针
- **使用场景**: 需要动态分配内存存储序列化数据

```cpp
size_t serialize(void* memory, size_t memory_size,
                 const SkSerialProcs* procs = nullptr) const;
```
- **功能**: 将对象序列化到预分配的内存缓冲区
- **参数**:
  - `memory`: 目标内存缓冲区
  - `memory_size`: 缓冲区大小
  - `procs`: 可选的序列化配置
- **返回值**:
  - 成功时返回写入的字节数
  - 缓冲区不足时返回 0
- **使用场景**: 栈内存或预分配缓冲区,避免堆分配

### 反序列化接口

```cpp
static sk_sp<SkFlattenable> Deserialize(Type type, const void* data,
                                        size_t size,
                                        const SkDeserialProcs* procs = nullptr);
```
- **功能**: 从字节流反序列化对象
- **参数**:
  - `type`: 期望的对象类型
  - `data`: 序列化数据指针
  - `size`: 数据大小
  - `procs`: 可选的反序列化配置
- **返回值**: 重建的对象智能指针,失败时返回 nullptr
- **安全性**: 会验证读取的类型与期望类型是否匹配

### 全局注册表管理

```cpp
static void Register(const char name[], Factory factory);
```
- **功能**: 注册类名与工厂函数的映射
- **调用时机**: 程序初始化阶段,通过 `SK_REGISTER_FLATTENABLE` 宏自动调用
- **线程安全**: 非线程安全,必须在单线程环境下完成注册

```cpp
static Factory NameToFactory(const char name[]);
```
- **功能**: 根据类名查找对应的工厂函数
- **返回值**: 找到时返回工厂函数指针,否则返回 nullptr
- **实现**: 使用二分查找,时间复杂度 O(log n)

```cpp
static const char* FactoryToName(Factory fact);
```
- **功能**: 根据工厂函数指针查找对应的类名
- **返回值**: 找到时返回类名字符串,否则返回 nullptr
- **实现**: 线性搜索,时间复杂度 O(n)

## 内部实现细节

### 全局注册表实现

```cpp
namespace {
    struct Entry {
        const char*             fName;
        SkFlattenable::Factory  fFactory;
    };

    int gCount = 0;
    Entry gEntries[128];  // 固定大小数组,最多 128 个类型
}
```

**注册流程**:
1. 程序启动时,每个可序列化类通过 `SK_REGISTER_FLATTENABLE` 宏注册
2. 注册信息存储在全局数组 `gEntries` 中
3. 调用 `SkFlattenable::Finalize()` 对数组按类名排序

**查找优化**:
```cpp
void SkFlattenable::Finalize() {
    std::sort(gEntries, gEntries + gCount, EntryComparator());
}

Factory SkFlattenable::NameToFactory(const char name[]) {
    RegisterFlattenablesIfNeeded();  // 延迟初始化
    auto pair = std::equal_range(gEntries, gEntries + gCount,
                                 name, EntryComparator());
    return (pair.first == pair.second) ? nullptr : pair.first->fFactory;
}
```
- 使用 `std::equal_range` 进行二分查找
- 查找前确保数组已排序

### 序列化实现

**基本流程**:
```cpp
sk_sp<SkData> SkFlattenable::serialize(const SkSerialProcs* procs) const {
    SkBinaryWriteBuffer writer(procs ? *procs : SkSerialProcs());
    writer.writeFlattenable(this);
    size_t size = writer.bytesWritten();
    auto data = SkData::MakeUninitialized(size);
    writer.writeToMemory(data->writable_data());
    return data;
}
```

**两阶段写入**:
1. 第一阶段: 计算所需的缓冲区大小
2. 第二阶段: 将数据写入分配的内存

**固定缓冲区版本**:
```cpp
size_t SkFlattenable::serialize(void* memory, size_t memory_size,
                                const SkSerialProcs* procs) const {
    SkBinaryWriteBuffer writer(memory, memory_size, procs ? *procs : SkSerialProcs());
    writer.writeFlattenable(this);
    return writer.usingInitialStorage() ? writer.bytesWritten() : 0u;
}
```
- 如果缓冲区足够,返回写入的字节数
- 如果缓冲区不足,返回 0(写入失败)

### 反序列化实现

```cpp
sk_sp<SkFlattenable> SkFlattenable::Deserialize(Type type, const void* data,
                                                size_t size,
                                                const SkDeserialProcs* procs) {
    SkReadBuffer buffer(data, size);
    if (procs) {
        buffer.setDeserialProcs(*procs);
    }
    return sk_sp<SkFlattenable>(buffer.readFlattenable(type));
}
```

**读取流程** (在 `SkReadBuffer::readFlattenable` 中):
1. 读取类名字符串
2. 使用 `NameToFactory` 查找工厂函数
3. 调用工厂函数创建对象
4. 对象从缓冲区读取自身数据
5. 验证类型匹配

### 宏辅助系统

**SK_FLATTENABLE_HOOKS 宏**:
```cpp
#define SK_FLATTENABLE_HOOKS(type)                                   \
    static sk_sp<SkFlattenable> CreateProc(SkReadBuffer&);           \
    friend class SkFlattenable::PrivateInitializer;                  \
    Factory getFactory() const override { return type::CreateProc; } \
    const char* getTypeName() const override { return #type; }
```

**使用示例**:
```cpp
class MyEffect : public SkFlattenable {
public:
    SK_FLATTENABLE_HOOKS(MyEffect)

    void flatten(SkWriteBuffer& buffer) const override {
        // 写入自定义数据
    }

    static sk_sp<SkFlattenable> CreateProc(SkReadBuffer& buffer) {
        // 读取数据并创建对象
        return sk_sp<SkFlattenable>(new MyEffect(...));
    }
};

// 在初始化代码中
SK_REGISTER_FLATTENABLE(MyEffect);
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRefCnt` | 提供引用计数基类 |
| `SkData` | 存储序列化后的字节数据 |
| `SkReadBuffer` | 从字节流读取数据 |
| `SkWriteBuffer` | 向字节流写入数据 |
| `SkSerialProcs` | 序列化配置结构 |
| `SkDeserialProcs` | 反序列化配置结构 |
| `SkPtrRecorder` | 管理指针集合 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| `SkColorFilter` | 继承 `SkFlattenable`,实现颜色滤镜序列化 |
| `SkShader` | 继承 `SkFlattenable`,实现着色器序列化 |
| `SkImageFilter` | 继承 `SkFlattenable`,实现图像滤镜序列化 |
| `SkMaskFilter` | 继承 `SkFlattenable`,实现遮罩滤镜序列化 |
| `SkPathEffect` | 继承 `SkFlattenable`,实现路径效果序列化 |
| `SkPaint` | 使用 `SkFlattenable` 对象作为效果 |
| 字体缓存 | 使用序列化数据生成缓存键 |

## 设计模式与设计决策

### 抽象工厂模式

通过全局注册表实现抽象工厂模式:
```cpp
// 注册阶段
SkFlattenable::Register("MyEffect", MyEffect::CreateProc);

// 创建阶段
Factory factory = SkFlattenable::NameToFactory("MyEffect");
sk_sp<SkFlattenable> obj = factory(buffer);
```

**优势**:
- 支持动态类型创建
- 解耦类名与具体类型
- 支持跨进程/跨平台对象重建

### 序列化器模式

使用 `SkReadBuffer` 和 `SkWriteBuffer` 实现序列化器模式:
```cpp
// 写入
void MyEffect::flatten(SkWriteBuffer& buffer) const {
    buffer.writeScalar(fValue);
    buffer.writeColor(fColor);
}

// 读取
MyEffect::MyEffect(SkReadBuffer& buffer) {
    fValue = buffer.readScalar();
    fColor = buffer.readColor();
}
```

### 设计决策

1. **全局注册表**: 使用固定大小数组(128)而非动态容器
   - **原因**: 效果类型数量有限,避免动态分配
   - **权衡**: 限制了可注册类型数量,但简化了实现

2. **二分查找优化**: 注册后对数组排序
   - **原因**: 查找操作远多于注册操作
   - **性能**: O(log n) 查找 vs O(n) 线性搜索

3. **类型枚举**: 使用 `Type` 枚举限制可序列化类型
   - **原因**: 类型安全,防止误用
   - **用途**: 反序列化时验证类型匹配

4. **延迟初始化**: 通过 `RegisterFlattenablesIfNeeded()` 延迟注册
   - **原因**: 确保所有静态对象都已初始化
   - **实现**: 使用静态局部变量保证单次初始化

5. **禁用序列化支持**: `SK_DISABLE_EFFECT_DESERIALIZATION` 宏
   - **用途**: 减少二进制大小(移动平台)
   - **影响**: 无法反序列化效果对象

## 性能考量

### 查找性能

1. **名称到工厂**: O(log n) 二分查找
2. **工厂到名称**: O(n) 线性搜索
   - 原因: 反向查找使用较少,不值得维护额外索引

### 内存优化

1. **栈内存序列化**:
   ```cpp
   char buffer[512];
   size_t size = obj->serialize(buffer, sizeof(buffer));
   ```
   - 小对象避免堆分配
   - 提高缓存局部性

2. **引用计数**: 继承自 `SkRefCnt`,避免拷贝开销

3. **智能指针**: 使用 `sk_sp<T>` 自动管理生命周期

### 序列化开销

1. **两阶段写入**: 需要两次遍历对象
   - 第一次: 计算大小
   - 第二次: 写入数据
   - **优化**: 可使用预分配缓冲区避免第一阶段

2. **类型信息**: 每个对象都需写入类名
   - **开销**: 类名字符串长度 + 长度字段
   - **优化**: 可考虑使用类型 ID 代替字符串

### 线程安全

**非线程安全部分**:
- 全局注册表的修改(`Register`, `Finalize`)
- **要求**: 在单线程环境下完成初始化

**线程安全部分**:
- 注册表的查找(`NameToFactory`, `FactoryToName`)
- 对象序列化和反序列化(每个对象独立)

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkReadBuffer.h` | 依赖 | 反序列化缓冲区 |
| `src/core/SkWriteBuffer.h` | 依赖 | 序列化缓冲区 |
| `include/core/SkData.h` | 依赖 | 字节数据容器 |
| `include/core/SkSerialProcs.h` | 依赖 | 序列化配置 |
| `src/core/SkPtrRecorder.h` | 依赖 | 指针记录器 |
| `include/effects/SkColorFilter.h` | 派生类 | 颜色滤镜 |
| `include/core/SkShader.h` | 派生类 | 着色器 |
| `include/core/SkImageFilter.h` | 派生类 | 图像滤镜 |
| `include/core/SkMaskFilter.h` | 派生类 | 遮罩滤镜 |
| `include/core/SkPathEffect.h` | 派生类 | 路径效果 |
