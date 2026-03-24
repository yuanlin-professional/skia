# SerializationUtils (管线序列化工具)

> 源文件：[src/gpu/graphite/SerializationUtils.h](../../../../src/gpu/graphite/SerializationUtils.h)、[src/gpu/graphite/SerializationUtils.cpp](../../../../src/gpu/graphite/SerializationUtils.cpp)

## 概述

`SerializationUtils` 提供了 Graphite 图形管线描述（`GraphicsPipelineDesc` 和 `RenderPassDesc`）的序列化与反序列化工具函数。这些工具服务于 Android 风格的管线预编译 API，允许将管线描述转换为二进制数据（`SkData`）进行持久化存储或传输，并在需要时恢复原始的管线描述对象。

序列化格式包含魔术字节、版本号、图形管线描述、渲染通道描述和结束标记，形成一个完整的自描述二进制 blob。

## 架构位置

`SerializationUtils` 位于管线预编译与缓存系统中：

- **上游**：预编译系统在收集到管线组合后调用 `PipelineDescToData` 序列化。
- **下游**：应用启动时调用 `DataToPipelineDesc` 反序列化，恢复管线描述后提交给管线编译系统。
- **协作者**：依赖 `ShaderCodeDictionary` 查找和创建 `PaintParamsKey`，依赖 `Caps` 恢复运行时信息。

## 主要类与结构体

本文件没有定义类，仅提供顶层自由函数。

## 公共 API 函数

### `PipelineDescToData`
```cpp
sk_sp<SkData> PipelineDescToData(const Caps*, ShaderCodeDictionary*,
                                  const GraphicsPipelineDesc&, const RenderPassDesc&);
```
将管线描述序列化为二进制数据。返回 `nullptr` 表示失败（如着色器键不可序列化）。

### `DataToPipelineDesc`
```cpp
bool DataToPipelineDesc(const Caps*, ShaderCodeDictionary*, const SkData*,
                        GraphicsPipelineDesc*, RenderPassDesc*);
```
从二进制数据反序列化管线描述。返回 `false` 表示数据无效或格式不匹配。

### 测试工具（GPU_TEST_UTILS）
- `DumpPipelineDesc`：打印管线描述的可读表示。
- `ComparePipelineDescs`：比较两组管线描述是否相等。

## 内部实现细节

### 二进制格式
序列化数据结构如下：
```
[magic: 8B "skiapipe"] [version: 4B]
[renderStepID: 4B] [keySize: 4B] [keyData: keySize*4B]
[colorAttachment: 4B] [resolveAttachment: 4B] [dsAttachment: 4B]
[writeSwizzle: 2B] [sampleCount: 1B]
[endTag: 4B "end "]
```

### GraphicsPipelineDesc 序列化
- 写入 `renderStepID`（uint32）。
- 从 `ShaderCodeDictionary` 查找 `PaintParamsKey`，验证可序列化后写入键数据。
- 如果 `paintParamsID` 无效（深度裁剪管线等），写入键大小为 0。

### AttachmentDesc 序列化
每个附件描述压缩为一个 32 位标记：`[format:8][loadOp:8][storeOp:8][sampleCount:8]`。未使用的附件（`TextureFormat::kUnsupported`）使用特殊标记。

### RenderPassDesc 序列化
序列化三个附件描述、写入 swizzle 和采样数。**不序列化**清除值和 `DstReadStrategy`——清除值不影响管线结构，DstReadStrategy 在反序列化时从 `Caps` 重新获取。

### 反序列化验证
反序列化过程包含严格的边界检查：
- 魔术字节和版本号验证。
- `renderStepID` 范围检查（< `kNumRenderSteps`）。
- 采样数必须为 2 的幂且在 [1,16] 范围内。
- 格式、加载/存储操作的枚举范围检查。
- 键的可序列化性验证。
- 结束标记验证。

## 依赖关系

### 上游依赖
- `GraphicsPipelineDesc`：图形管线描述。
- `RenderPassDesc` / `AttachmentDesc`：渲染通道描述。
- `ShaderCodeDictionary`：着色器代码字典（查找/创建 PaintParamsKey）。
- `PaintParamsKey`：着色器参数键。
- `Caps`：能力查询（反序列化时获取 DstReadStrategy）。
- `SkStream` / `SkWStream`：流式 I/O。

### 下游使用者
- 管线预编译 API（Android Precompilation）。
- 管线缓存系统。

## 设计模式与设计决策

1. **版本化格式**：通过 `kCurrent_Version` 控制序列化版本，支持未来格式演进。当前版本为 1。

2. **自描述二进制格式**：魔术字节 + 版本号 + 结束标记提供完整的数据完整性验证。

3. **选择性序列化**：不序列化不影响管线结构的字段（清除值、DstReadStrategy），减少数据大小并避免反序列化时的兼容性问题。

4. **紧凑编码**：附件描述压缩为单个 32 位整数，最大化空间效率。

5. **防御性反序列化**：每个字段都有严格的范围和有效性检查，防止无效数据导致崩溃。

## 性能考量

- 序列化/反序列化操作基于流式 I/O，内存分配最小化。
- 序列化数据非常紧凑（约 30-50 字节/管线），适合批量持久化。
- 可选的往返测试（`#if 0` 块）可在开发时启用，验证序列化正确性。

## 相关文件

- `src/gpu/graphite/GraphicsPipelineDesc.h`：图形管线描述。
- `src/gpu/graphite/RenderPassDesc.h`：渲染通道描述。
- `src/gpu/graphite/ShaderCodeDictionary.h/.cpp`：着色器代码字典。
- `src/gpu/graphite/PaintParamsKey.h`：着色器参数键。
- `src/gpu/graphite/Caps.h`：能力查询。
