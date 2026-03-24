# TextureInfoPriv

> 源文件: src/gpu/graphite/TextureInfoPriv.h

## 概述

`TextureInfoPriv` 是 Skia Graphite 架构中 `TextureInfo` 的内部辅助头文件，提供纹理信息的私有访问接口和实用函数。该文件定义了纹理信息的内部表示、后端特定数据的访问方法以及格式验证函数，仅供 Graphite 内部使用。

## 架构位置

```
Graphite 纹理信息系统：
  ├── TextureInfo（公共 API）
  ├── TextureInfoPriv（内部辅助）★
  └── 后端特定实现：
      ├── MtlTextureInfo
      ├── VulkanTextureInfo
      └── DawnTextureInfo
```

## 主要函数和接口

### 后端数据访问

```cpp
namespace TextureInfoPriv {
    const void* GetBackendData(const TextureInfo& info);
    bool IsValid(const TextureInfo& info);
}
```

**功能**: 访问纹理信息的后端特定数据，验证纹理信息的有效性。

### 格式查询

提供内部格式查询函数，避免在公共 API 中暴露后端细节。

### 纹理用途检查

验证纹理信息的用途标志是否与后端能力匹配。

## 内部实现细节

### 后端数据封装

`TextureInfo` 使用不透明的后端数据存储：
```cpp
struct TextureInfo {
    // 公共成员...
private:
    BackendTextureData fBackendData;  // 后端特定数据
};
```

`TextureInfoPriv` 提供访问接口：
```cpp
const void* GetBackendData(const TextureInfo& info) {
    return &info.fBackendData;
}
```

### 有效性验证

```cpp
bool IsValid(const TextureInfo& info) {
    // 检查尺寸、格式、用途等
    return info.isValid();
}
```

## 依赖关系

### 内部依赖

| 依赖 | 用途 |
|------|------|
| `TextureInfo` | 公共纹理信息类 |
| 后端头文件 | Metal/Vulkan/Dawn 特定类型 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `Caps` | 格式支持查询 |
| `Texture` | 纹理创建 |
| `ResourceProvider` | 资源分配 |

## 设计模式与设计决策

### 友元访问

通过命名空间函数访问 `TextureInfo` 的私有成员，避免破坏封装。

### 内部头文件

分离公共 API 和内部实现，客户端代码无法访问 `TextureInfoPriv`。

### 关键设计决策

1. **不透明数据**: 后端数据对公共 API 不可见
2. **验证集中化**: 统一的有效性检查逻辑
3. **最小 API 表面**: 仅暴露必要的内部接口

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `include/gpu/graphite/TextureInfo.h` | 公共纹理信息 API |
| `src/gpu/graphite/TextureFormat.h` | 纹理格式枚举 |
| `src/gpu/graphite/Caps.h` | 后端能力查询 |
