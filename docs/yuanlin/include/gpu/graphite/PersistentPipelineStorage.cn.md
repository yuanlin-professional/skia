# PersistentPipelineStorage

> 源文件: `include/gpu/graphite/PersistentPipelineStorage.h`

## 概述

PersistentPipelineStorage 是一个抽象接口类,允许 Graphite 在 Context 生命周期之间持久化管线(Pipeline)数据。通过实现该接口,客户端可以将编译好的着色器管线缓存到磁盘,从而在应用重启后跳过耗时的着色器编译过程。

## 架构位置

该文件位于 Skia Graphite GPU 后端的公共接口层,属于 `skgpu::graphite` 命名空间。它是 Graphite 着色器管线缓存系统的核心抽象,为跨会话的着色器缓存提供了接口支持。该类通常通过 `ContextOptions` 传递给 Context。

## 主要类与结构体

### PersistentPipelineStorage

```cpp
class SK_API PersistentPipelineStorage
```

**职责**: 定义管线数据持久化的抽象接口,客户端需实现具体的存储机制(如文件系统、数据库等)。

**继承关系**: 独立类,不继承其他类

**设计特点**:
- 抽象基类,包含纯虚函数
- 禁用拷贝构造和拷贝赋值
- 虚析构函数支持多态销毁

**生命周期**:
- 由客户端管理生命周期
- 必须在关联的 Context 生命周期内保持有效

## 公共 API 函数

### `load` (纯虚函数)

```cpp
virtual sk_sp<SkData> load() = 0;
```

- **功能**: 加载之前存储的管线数据
- **参数**: 无
- **返回值**:
  - 成功: 包含管线数据的 `sk_sp<SkData>`
  - 失败或无数据: `nullptr`
- **调用时机**: Context 初始化时调用,用于恢复之前的管线缓存
- **实现要求**:
  - 如果没有先前的数据,应返回 nullptr
  - 返回的数据应该是之前通过 `store` 保存的完整数据
  - 需要处理文件损坏、版本不匹配等异常情况

### `store` (纯虚函数)

```cpp
virtual void store(const SkData& data) = 0;
```

- **功能**: 持久化提供的管线数据
- **参数**:
  - `data` - 要保存的管线数据,由 Graphite 生成
- **返回值**: void
- **调用时机**:
  - 管线编译完成后
  - Context 销毁前
  - 可能在应用运行期间多次调用
- **实现要求**:
  - 应该原子性地保存数据(避免部分写入)
  - 可以异步执行以避免阻塞渲染
  - 需要处理磁盘空间不足等错误情况

### 构造与析构

```cpp
virtual ~PersistentPipelineStorage() = default;

protected:
    PersistentPipelineStorage() = default;
    PersistentPipelineStorage(const PersistentPipelineStorage&) = delete;
    PersistentPipelineStorage& operator=(const PersistentPipelineStorage&) = delete;
```

- **析构函数**: 虚析构,支持通过基类指针删除派生类对象
- **构造函数**: protected,只能通过派生类构造
- **拷贝语义**: 显式删除,防止意外拷贝

## 内部实现细节

### 数据格式

管线数据的格式由 Graphite 内部定义,客户端不需要解析:
- 二进制格式,包含编译后的着色器代码和元数据
- 可能包含版本信息、平台信息等
- 格式可能在不同 Skia 版本间变化

### 版本兼容性

Graphite 会验证加载的数据版本:
- 版本不匹配时会忽略旧数据
- 客户端不需要处理版本检查
- 但应该容忍 `load` 返回的数据被 Graphite 拒绝

### 线程安全

文档未明确说明,但推荐:
- `load` 在 Context 创建线程调用
- `store` 可能在任意线程调用
- 客户端实现应该是线程安全的

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkRefCnt.h` | 引用计数类型(间接通过 SkData) |
| `include/private/base/SkAPI.h` | SK_API 宏定义 |
| `SkData` (前向声明) | 数据容器 |

### 被依赖的模块

- `ContextOptions`: 通过 `fPersistentPipelineStorage` 字段引用
- `Context`: 在初始化和销毁时调用 load/store
- `PipelineCache`: 内部管线缓存实现使用该接口

## 设计模式与设计决策

### 策略模式

PersistentPipelineStorage 是策略模式的典型应用:
- 定义了存储操作的接口
- 具体存储策略由客户端决定
- Graphite 核心代码与存储细节解耦

### 为什么使用抽象接口

1. **平台无关**: 不同平台有不同的存储机制(iOS vs Android vs Desktop)
2. **灵活性**: 客户端可选择文件、数据库、内存等存储方式
3. **安全性**: 客户端可以控制敏感数据的存储位置
4. **测试性**: 便于单元测试(可提供 mock 实现)

### 禁用拷贝的原因

- 持久化对象通常是单例或全局对象
- 拷贝可能导致数据不一致
- 通过指针传递更明确所有权

## 性能考量

### 启动性能提升

启用持久化缓存后:
- **冷启动**: 首次运行仍需编译着色器
- **热启动**: 后续启动可跳过编译,提速显著(通常 5-10倍)
- **效果**: 对于复杂应用,可减少数秒的启动时间

### 存储开销

- **大小**: 管线数据通常几 KB 到几 MB
- **频率**: 不频繁写入,主要在初始化和关闭时
- **建议**: 使用压缩可进一步减小磁盘占用

### 异步存储

推荐实现异步 `store`:
```cpp
void MyStorage::store(const SkData& data) {
    auto dataCopy = sk_sp<SkData>(SkData::MakeWithCopy(data.data(), data.size()));
    std::thread([this, dataCopy]() {
        writeToFile(dataCopy);
    }).detach();
}
```

## 实现示例

### 基于文件的实现

```cpp
class FilePipelineStorage : public PersistentPipelineStorage {
public:
    explicit FilePipelineStorage(const std::string& cachePath)
        : fCachePath(cachePath) {}

    sk_sp<SkData> load() override {
        FILE* file = fopen(fCachePath.c_str(), "rb");
        if (!file) return nullptr;

        fseek(file, 0, SEEK_END);
        size_t size = ftell(file);
        fseek(file, 0, SEEK_SET);

        auto data = SkData::MakeUninitialized(size);
        fread(data->writable_data(), 1, size, file);
        fclose(file);

        return data;
    }

    void store(const SkData& data) override {
        FILE* file = fopen(fCachePath.c_str(), "wb");
        if (!file) return;

        fwrite(data.data(), 1, data.size(), file);
        fclose(file);
    }

private:
    std::string fCachePath;
};
```

### 使用方式

```cpp
// 创建存储对象
auto storage = std::make_unique<FilePipelineStorage>("/path/to/cache.bin");

// 通过 ContextOptions 传递
ContextOptions options;
options.fPersistentPipelineStorage = storage.get();
auto context = ContextFactory::MakeMetal(backendContext, options);

// 确保 storage 在 context 生命周期内有效
// ...

// context 销毁时会自动调用 store
```

## 平台相关说明

### iOS/macOS

- 使用 NSCachesDirectory 或 NSApplicationSupportDirectory
- 注意 App Store 审核关于缓存的要求

### Android

- 使用 getCacheDir() 或 getFilesDir()
- 考虑清除缓存的用户选项

### Desktop

- Windows: %LOCALAPPDATA%\AppName\Cache
- Linux: ~/.cache/AppName
- macOS: ~/Library/Caches/AppName

## 注意事项

### 数据验证

客户端不应该修改或依赖管线数据的内容:
- 格式是内部实现细节
- 可能在版本间变化
- Graphite 会自动验证加载的数据

### 错误处理

`load` 失败时:
- 返回 nullptr
- Graphite 会重新编译管线
- 不影响功能,只影响性能

`store` 失败时:
- 应该静默失败
- 不影响当前渲染
- 只影响下次启动性能

### 线程安全建议

```cpp
class ThreadSafeStorage : public PersistentPipelineStorage {
    std::mutex fMutex;
    // ...实现中对共享数据的访问都加锁
};
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/graphite/ContextOptions.h` | 通过 fPersistentPipelineStorage 字段引用 |
| `include/core/SkData.h` | 数据容器定义 |
| `src/gpu/graphite/PipelineCache.cpp` | 内部管线缓存实现 |
| `src/gpu/graphite/Context.cpp` | 调用 load/store 的位置 |

## 未来改进方向

1. **增量更新**: 当前可能保存全部管线数据,未来可能支持增量更新
2. **压缩支持**: 接口可能扩展压缩选项
3. **多 Context 共享**: 可能支持多个 Context 共享同一缓存
4. **云同步**: 对于跨设备应用,可能支持云端同步管线缓存
