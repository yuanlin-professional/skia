# PaintParamsKey

> 源文件
> - src/gpu/graphite/PaintParamsKey.h
> - src/gpu/graphite/PaintParamsKey.cpp

## 概述

`PaintParamsKey` 是 Skia Graphite 渲染引擎中表示着色器配置的紧凑数据结构。它将复杂的绘制参数（如着色器、颜色滤镜、混合模式等）编码为一个 uint32_t 数组，作为着色器查找和编译的唯一键。

该类采用树形结构编码：每个节点包含代码片段ID（4字节）和可选的嵌入数据，子节点以深度优先顺序排列。键支持多个根节点，分别表示颜色计算、最终混合和可选的裁剪。

`PaintParamsKeyBuilder` 与 `PaintParamsKey` 共享底层内存，通过锁定/解锁机制实现高效的键生成和重用，避免频繁的内存分配。

## 架构位置

```
PaintParams (绘制参数)
  └── PaintParamsKeyBuilder (键构建器)
      └── PaintParamsKey (着色器键)
          └── UniquePaintParamsID (字典查找)
              └── 着色器代码生成
```

`PaintParamsKey` 位于绘制参数和着色器代码之间，是着色器缓存和编译系统的核心数据结构。

## 主要类与结构体

### PaintParamsKey

**核心职责**：
- 存储着色器配置的紧凑表示
- 支持相等性比较和哈希计算
- 解码为 `ShaderNode` 树用于代码生成
- 支持序列化验证

**关键成员**：

```cpp
SkSpan<const uint32_t> fData;  // 数据始终由外部拥有（Builder或Arena）
```

### 键编码格式

#### 普通节点

```
[4字节: code-snippet ID]
[N个子节点，深度优先遍历]
```

#### 带数据节点

```
[4字节: code-snippet ID]
[4字节: data length]
[0-M字节: variable length data]
[N个子节点]
```

#### 键结构示例

```
键根节点布局（2或3个根）：
1. 颜色根节点 - 产生"src"颜色
2. 最终混合节点 - 定义src与dst的混合
3. 裁剪节点（可选）- 产生解析覆盖率
```

**隐式结构**：
```
逻辑上等价于：
[ BlendCompose [ [ color-root ] surface-color [ final-blend ] ] ]

但为节省空间，BlendCompose和surface-color节点是隐式的
```

### PaintParamsKeyBuilder

**核心职责**：
- 增量构建 `PaintParamsKey`
- 维护调试时的栈帧验证
- 支持锁定/解锁机制以共享内存

**关键成员**：

```cpp
skia_private::TArray<uint32_t> fData;  // 底层数据存储
bool fHasError = false;                 // 错误标志
int fDataHighWaterMark = 0;             // 高水位标记，用于容量管理

#ifdef SK_DEBUG
    const ShaderCodeDictionary* fDict;
    skia_private::TArray<StackFrame> fStack;  // 验证栈
    bool fLocked = false;                     // 锁定状态
#endif
```

### StackFrame（调试专用）

```cpp
struct StackFrame {
    int fCodeSnippetID;
    int fNumExpectedChildren;  // 预期子节点数
    int fNumActualChildren = 0; // 实际子节点数
    int fDataSize = -1;         // 数据大小（-1表示无数据）
};
```

**用途**：验证键构建的正确性
- 检查子节点数量匹配
- 验证数据添加的合法性
- 确保 `beginBlock`/`endBlock` 配对

### AutoLockBuilderAsKey

```cpp
class AutoLockBuilderAsKey {
public:
    AutoLockBuilderAsKey(PaintParamsKeyBuilder* builder);
    ~AutoLockBuilderAsKey();

    const PaintParamsKey& operator*() const;
    const PaintParamsKey* operator->() const;
};
```

**用途**：RAII 管理 Builder 的锁定/解锁

**使用模式**：
```cpp
{
    AutoLockBuilderAsKey key(&builder);
    // 使用 *key 或 key-> 访问
    dictionary->findOrCreate(*key);
}  // 自动解锁 builder
```

## 公共 API 函数

### PaintParamsKey 方法

#### clone

```cpp
PaintParamsKey clone(SkArenaAlloc* arena) const;
```

**功能**：在 arena 中复制键数据，返回独立的 `PaintParamsKey`

**用途**：将 Builder-owned 键转换为持久键

#### getRootNodes

```cpp
SkSpan<const ShaderNode*> getRootNodes(
    const Caps* caps,
    const ShaderCodeDictionary* dict,
    SkArenaAlloc* arena,
    int availableVaryings) const;
```

**功能**：将键解码为 `ShaderNode` 树森林

**返回值**：
- 2-3个根节点（颜色、混合、可选裁剪）
- 空 span 表示包含未知代码片段ID

**优化逻辑**：
1. 根据 `availableVaryings` 决定哪些表达式提升到顶点着色器
2. 坐标修改表达式优先提升（`lift_coord_expressions`）
3. 如果支持存储缓冲区，提升常量颜色表达式（`lift_color_expressions`）

#### toString

```cpp
SkString toString(const Caps* caps, const ShaderCodeDictionary* dict) const;
```

**功能**：转换为人类可读的字符串

**格式**：
- 单行格式：`SnippetName [child1 child2] SnippetName2 ...`
- 多行格式（通过 `dump`）：缩进显示树结构

**数据显示**：
- 不可变采样器：尝试解码为人类可读形式
- 其他数据：Base64编码显示

#### isSerializable

```cpp
[[nodiscard]] bool isSerializable(const ShaderCodeDictionary* dict) const;
```

**功能**：验证键是否适合序列化

**检查项**：
- 所有代码片段ID有效
- 仅包含 Skia 内部代码片段（非用户自定义 RuntimeEffect）
- 数据大小和结构正确

### PaintParamsKeyBuilder 方法

#### beginBlock / endBlock

```cpp
void beginBlock(BuiltInCodeSnippetID id);
void beginBlock(int32_t codeSnippetID);
void endBlock();
```

**用途**：标记代码片段块的开始和结束

**调试验证**：
- 检查子节点数量
- 验证数据添加的正确性
- 确保栈平衡

#### addBlock

```cpp
void addBlock(BuiltInCodeSnippetID id);
```

**便利方法**：等价于 `beginBlock(id); endBlock();`

**用途**：添加无子节点的块（如 `SolidColorShader`）

#### addData

```cpp
void addData(SkSpan<const uint32_t> data);
```

**功能**：为当前块添加嵌入数据

**格式**：先写入数据大小，再写入实际数据

**限制**：
- 仅支持声明 `storesSamplerDescData()` 的代码片段
- 每个块最多调用一次

#### addErrorBlock

```cpp
void addErrorBlock();
```

**功能**：标记错误状态

**效果**：
- 设置 `fHasError = true`
- 添加 `kError` 代码片段保持结构
- `lockAsKey()` 将返回无效键

#### tryShrinkCapacity

```cpp
void tryShrinkCapacity();
```

**功能**：尝试缩减内部数组容量

**逻辑**：如果高水位标记低于容量的一半，将容量减半

**用途**：避免长期持有过大的内存

#### lockAsKey / unlock

```cpp
PaintParamsKey lockAsKey();  // private，通过 AutoLockBuilderAsKey 使用
void unlock();               // private
```

**功能**：锁定/解锁 Builder

**锁定时**：
- 更新高水位标记
- 检查栈平衡
- 返回 `PaintParamsKey` 视图

**解锁时**：
- 清空 `fData`（保留容量）
- 重置错误标志
- 清空调试栈

## 内部实现细节

### 树形结构编码

深度优先遍历编码：

```
示例：BlendShader(ColorShader(red), ColorShader(blue), kSrcOver)

编码为：
[BlendShader ID]
  [ColorShader ID] [red数据]
  [ColorShader ID] [blue数据]
  [SrcOverBlend ID]
```

**解码逻辑**（`createNode`）：
```cpp
ShaderNode* createNode(dict, currentIndex, arena) {
    int id = fData[(*currentIndex)++];
    const ShaderSnippet* entry = dict->getEntry(id);

    // 读取嵌入数据（如果有）
    if (entry->storesSamplerDescData()) {
        int dataLen = fData[(*currentIndex)++];
        dataSpan = fData.subspan((*currentIndex), dataLen);
        *currentIndex += dataLen;
    }

    // 递归创建子节点
    for (int i = 0; i < entry->fNumChildren; ++i) {
        childArray[i] = createNode(dict, currentIndex, arena);
    }

    return new ShaderNode(entry, childArray, ...);
}
```

### 表达式提升优化

#### 坐标表达式提升

```cpp
bool lift_coord_expressions(SkSpan<ShaderNode*> nodes, int* availableVaryings) {
    for (ShaderNode* node : nodes) {
        if (可提升 && varyings > 0 && needsLocalCoords) {
            --varyings;
            node->setLiftExpressionFlag();
            // 递归检查子节点
            if (!lift_coord_expressions(node->children(), &varyings)) {
                node->setOmitExpressionFlag();  // 子节点不需要，省略片段着色器中的计算
            }
            node->unsetLocalCoordsFlag();
        }
    }
}
```

**效果**：
- 坐标变换移至顶点着色器
- 通过 varying 传递到片段着色器
- 如果子节点也不需要，完全省略片段计算

#### 颜色表达式提升

```cpp
void lift_color_expressions(SkSpan<ShaderNode*> nodes, int* availableVaryings) {
    for (ShaderNode* node : nodes) {
        if (可提升 && varyings > 0 && 是常量颜色) {
            --varyings;
            node->setLiftExpressionFlag();
        }
    }
}
```

**条件**：仅在支持存储缓冲区时启用

**原因**：避免存储缓冲区访问的开销大于 varying 传递

### 内存管理策略

#### 共享内存模型

```cpp
PaintParamsKeyBuilder builder;
{
    AutoLockBuilderAsKey key(&builder);
    // key.fData 指向 builder.fData
}  // unlock() 调用 fData.clear()，但保留容量
```

**优点**：
- 避免键数据的拷贝
- 重用内存，减少分配
- 高水位标记避免容量震荡

#### 容量管理

```cpp
void tryShrinkCapacity() {
    int halfCapacity = fData.capacity() / 2;
    if (fDataHighWaterMark < halfCapacity) {
        fDataHighWaterMark = 0;
        fData.reserve_exact(halfCapacity);
    }
}
```

**时机**：周期性调用（如每帧结束）

**策略**：保守缩减，避免频繁调整

### 序列化验证

```cpp
bool is_block_valid(dict, keyData, currentIndex) {
    uint32_t id = keyData[(*currentIndex)++];

    // 仅允许内置和已知运行时效果
    if (id >= kBuiltInCodeSnippetIDCount &&
        !SkKnownRuntimeEffects::IsSkiaKnownRuntimeEffect(id) &&
        !dict->isUserDefinedKnownRuntimeEffect(id)) {
        return false;
    }

    // 递归验证子节点
    for (int i = 0; i < entry->fNumChildren; ++i) {
        if (!is_block_valid(dict, keyData, currentIndex)) {
            return false;
        }
    }
    return true;
}
```

## 依赖关系

### 核心依赖

| 依赖项 | 作用 |
|--------|------|
| `ShaderCodeDictionary` | 查询代码片段定义 |
| `ShaderNode` | 着色器节点树表示 |
| `SkArenaAlloc` | 内存分配 |
| `Caps` | 设备能力查询 |

### 工具类

| 类型 | 用途 |
|------|------|
| `SkChecksum::Hash32` | 计算键的哈希值 |
| `SkBase64` | 数据的 Base64 编码 |
| `BuiltInCodeSnippetID` | 内置代码片段枚举 |

## 设计模式与设计决策

### 1. 享元模式（Flyweight）

键数据通过字典共享，多个 `PaintParamsKey` 可以指向同一份数据：

```cpp
UniquePaintParamsID id = dict->findOrCreate(key);
// 字典内部存储键数据，所有相同键共享
```

### 2. 建造者模式（Builder）

`PaintParamsKeyBuilder` 增量构建 `PaintParamsKey`：

```cpp
builder.beginBlock(kImageShader);
    builder.addData(...);
    builder.beginBlock(kColorFilter);
        // ...
    builder.endBlock();
builder.endBlock();
```

### 3. RAII 管理锁定

`AutoLockBuilderAsKey` 确保 Builder 的正确锁定/解锁：

```cpp
{
    AutoLockBuilderAsKey key(&builder);
    use(key);
}  // 自动解锁
```

### 4. 不可变键（Immutable Key）

一旦锁定，`PaintParamsKey` 的数据不可修改，确保线程安全和哈希稳定性。

### 5. 调试时栈验证

Debug 模式下维护栈帧，验证键结构的正确性：

```cpp
#ifdef SK_DEBUG
    void pushStack(int32_t codeSnippetID);
    void popStack();
#endif
```

### 6. 延迟优化

表达式提升在 `getRootNodes` 时执行，而非构建时，避免不必要的计算。

## 性能考量

### 键构建效率

1. **内存重用**：`clear()` 保留容量，避免重新分配
2. **高水位标记**：记录最大使用量，智能缩减容量
3. **单次遍历**：构建键时只遍历一次绘制参数树

### 键比较和哈希

1. **快速相等性检查**：
   ```cpp
   bool operator==(const PaintParamsKey& that) const {
       return fData.size() == that.fData.size() &&
              !memcmp(fData.data(), that.fData.data(), fData.size());
   }
   ```

2. **高效哈希**：
   ```cpp
   uint32_t operator()(const PaintParamsKey& k) const {
       return SkChecksum::Hash32(k.fData.data(), k.fData.size_bytes());
   }
   ```

### 表达式提升优化

1. **减少片段着色器工作**：坐标变换移至顶点着色器
2. **减少 uniform 访问**：常量颜色通过 varying 传递
3. **自适应策略**：根据 `availableVaryings` 和设备能力动态选择

### 调试开销隔离

所有调试验证代码都在 `#ifdef SK_DEBUG` 中，发布版本零开销：

```cpp
SkDEBUGCODE(this->pushStack(codeSnippetID);)
```

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/ShaderCodeDictionary.h` | 代码片段字典 |
| `src/gpu/graphite/KeyHelpers.h` | 键构建辅助函数 |
| `src/gpu/graphite/PipelineData.h` | 管线数据（uniform、纹理） |
| `src/gpu/graphite/KeyContext.h` | 键生成上下文 |
| `src/gpu/graphite/BuiltInCodeSnippetID.h` | 内置代码片段枚举 |
| `src/gpu/graphite/Caps.h` | 设备能力 |
| `src/base/SkArenaAlloc.h` | Arena分配器 |
| `src/core/SkChecksum.h` | 哈希计算 |
| `src/base/SkBase64.h` | Base64编码 |
