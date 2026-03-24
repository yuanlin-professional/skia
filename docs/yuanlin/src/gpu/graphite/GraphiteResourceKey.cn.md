# GraphiteResourceKey

> 源文件
> - src/gpu/graphite/GraphiteResourceKey.h
> - src/gpu/graphite/GraphiteResourceKey.cpp

## 概述

`GraphiteResourceKey` 是用于标识和查找 GPU 资源的键类型。它支持可擦除的资源缓存，允许不同类型的资源（纹理、缓冲区、管线等）使用统一的缓存机制。该类基于 Skia 传统 GPU 后端的资源键设计，但针对 Graphite 进行了简化。

## 主要类与结构体

### GraphiteResourceKey 类

```cpp
class GraphiteResourceKey {
public:
    GraphiteResourceKey();
    GraphiteResourceKey(const GraphiteResourceKey& that);
    ~GraphiteResourceKey();

    GraphiteResourceKey& operator=(const GraphiteResourceKey& that);

    bool operator==(const GraphiteResourceKey& that) const;
    bool operator!=(const GraphiteResourceKey& that) const;

    // 获取哈希值（用于哈希表）
    uint32_t hash() const;

    // 构建器模式
    class Builder;

private:
    // 变长数据（域 + 自定义数据）
    uint32_t* fKey = nullptr;
};
```

### Builder 类

```cpp
class Builder {
public:
    Builder(GraphiteResourceKey* key,
           uint32_t domain,
           int dataLength);

    ~Builder();

    // 写入自定义数据
    uint32_t& operator[](int index);

private:
    GraphiteResourceKey* fKey;
    int fDataLength;
};
```

## 使用模式

### 创建资源键

```cpp
GraphiteResourceKey key;
{
    GraphiteResourceKey::Builder builder(&key, kTextureDomain, 3);
    builder[0] = width;
    builder[1] = height;
    builder[2] = format;
}
// key 现在可用于缓存查找
```

### 域（Domain）

域用于区分不同类型的资源：
- 相同域：相同类型的资源
- 不同域：不同类型的资源（即使数据相同也不会冲突）

## 内部实现

### 内存布局

键数据存储在堆分配的数组中：
```
[header: size + domain][data0][data1][...][dataN]
```

### 哈希计算

使用 MurmurHash 或类似算法计算键的哈希值，用于快速查找。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/ResourceCache.h` | 使用资源键的缓存 |
| `src/gpu/graphite/Resource.h` | 资源基类 |
| `src/gpu/graphite/GlobalCache.h` | 全局资源缓存 |
