# GrBackendDrawableInfo - 后端可绘制对象信息封装

> 源文件: `include/gpu/ganesh/vk/GrBackendDrawableInfo.h`

## 概述

GrBackendDrawableInfo 是一个轻量级封装类，用于在 SkDrawable 的 `drawBackendGpu()` 调用中传递后端特定的绘制信息。当前实现专注于 Vulkan 后端，为自定义 GPU 绘制提供类型安全的接口。

## 架构位置

- **所属子系统**: GPU/Ganesh 渲染后端
- **层级**: 公共 API 接口层
- **作用域**: 多后端抽象（当前仅支持 Vulkan）

该类位于 Ganesh 的后端抽象层，虽然当前只支持 Vulkan，但设计上预留了扩展到其他后端的可能性。

## 主要类与结构体

### GrBackendDrawableInfo

封装后端特定的可绘制对象信息，提供类型安全的访问接口。

**继承关系**: 无继承（独立类）

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fIsValid | bool | 标识该对象是否已正确初始化 |
| fBackend | GrBackendApi | 标识后端类型（当前仅支持 kVulkan） |
| fVkInfo | GrVkDrawableInfo | Vulkan 特定的绘制信息 |

## 公共 API 函数

### 默认构造函数
```cpp
GrBackendDrawableInfo()
```
- **功能**: 创建无效的 drawable 信息对象
- **后置条件**: `fIsValid` 被设置为 false

### Vulkan 构造函数
```cpp
explicit GrBackendDrawableInfo(const GrVkDrawableInfo& info)
```
- **功能**: 从 Vulkan drawable 信息创建封装对象
- **参数**:
  - `info` - Vulkan 特定的 drawable 信息（包含命令缓冲区、渲染通道等）
- **后置条件**:
  - `fIsValid` 被设置为 true
  - `fBackend` 被设置为 `GrBackendApi::kVulkan`
  - `fVkInfo` 存储传入的信息

### `isValid`
```cpp
bool isValid() const
```
- **功能**: 检查对象是否已正确初始化
- **返回值**: 如果对象有效返回 true，否则返回 false
- **用途**: 在使用前验证对象状态

### `backend`
```cpp
GrBackendApi backend() const
```
- **功能**: 获取封装的后端类型
- **返回值**: 后端 API 枚举值（当前仅 `kVulkan`）
- **用途**: 在多后端环境中识别信息类型

### `getVkDrawableInfo`
```cpp
bool getVkDrawableInfo(GrVkDrawableInfo* outInfo) const
```
- **功能**: 提取 Vulkan drawable 信息
- **参数**:
  - `outInfo` - 输出参数，用于接收 Vulkan 信息的指针（不可为空）
- **返回值**:
  - 如果是有效的 Vulkan drawable 信息返回 true，并填充 outInfo
  - 否则返回 false，outInfo 内容未定义
- **使用模式**: 先检查返回值再使用 outInfo

## 内部实现细节

### 类型安全设计
该类通过以下机制确保类型安全：
1. **显式构造**: 通过 `explicit` 关键字防止隐式转换
2. **状态验证**: `isValid()` 提供运行时检查
3. **后端检查**: `getVkDrawableInfo` 内部验证后端类型

### 数据存储策略
采用值语义存储 `GrVkDrawableInfo`：
- 避免指针管理和生命周期问题
- 简化对象复制和传递
- 适合轻量级信息传递场景

### 可扩展性预留
虽然当前只支持 Vulkan，但代码结构预留了扩展空间：
```cpp
// 未来可添加：
GrGLDrawableInfo fGLInfo;
GrMtlDrawableInfo fMtlInfo;
```
通过 `fBackend` 枚举和类型安全的 getter，可以在不破坏 API 的情况下添加新后端。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/gpu/ganesh/GrTypes.h | GrBackendApi 枚举定义 |
| include/gpu/ganesh/vk/GrVkTypes.h | GrVkDrawableInfo 结构体定义 |

### 被依赖的模块

- **SkDrawable**: 使用该类在 `drawBackendGpu()` 中接收后端信息
- **GrRecordingContext**: 在调用 drawable 时创建和传递该对象
- **用户自定义 SkDrawable 子类**: 通过该接口注入自定义 GPU 命令

## 设计模式与设计决策

### 1. 类型安全封装模式
通过封装类隐藏底层联合体或变体类型的复杂性：
- **优点**:
  - 防止错误的类型访问
  - 提供清晰的 API 语义
- **代价**:
  - 增加一层间接访问
  - 需要额外的有效性检查

### 2. 未来可扩展设计
通过 `GrBackendApi` 枚举支持多后端：
- 当前仅实现 Vulkan
- 注释明确指出："如有必要，可扩展为通用接口"
- 设计保持简单直到需求明确

### 3. 值语义传递
采用复制而非引用/指针传递信息：
- 简化生命周期管理
- 避免悬空指针问题
- 适合 drawable 信息的短暂性质（仅在单次绘制调用中使用）

## 性能考量

### 内存占用
对象大小取决于 `GrVkDrawableInfo` 的大小：
- 包含指针类型（VkCommandBuffer, VkRenderPass 等）
- 总大小约 32-48 字节（取决于平台）
- 适合按值传递

### 复制开销
- `GrVkDrawableInfo` 包含基本类型和指针，复制成本低
- 无需深度复制，因为所有 Vulkan 句柄都是不透明指针
- 在绘制路径中的开销可忽略不计

### 分支预测优化
`getVkDrawableInfo` 中的双重检查：
```cpp
if (this->isValid() && GrBackendApi::kVulkan == fBackend)
```
在 Vulkan 后端环境中，两个条件都高度可预测，分支预测成功率高。

## 使用示例场景

### 自定义 Vulkan 绘制
用户可创建 SkDrawable 子类，在 `drawBackendGpu()` 中接收 `GrBackendDrawableInfo`：
1. 检查 `isValid()` 和后端类型
2. 提取 `GrVkDrawableInfo`
3. 使用次级命令缓冲区记录自定义 Vulkan 命令
4. Skia 在其渲染通道中执行这些命令

### 跨引擎集成
当 Skia 嵌入到游戏引擎或应用中时：
- 引擎可通过 drawable 注入自定义渲染
- 保持与 Skia 渲染管线的同步
- 利用 Skia 的状态管理和优化

## 相关文件

| 文件 | 关系 |
|------|------|
| include/gpu/ganesh/vk/GrVkTypes.h | 定义 GrVkDrawableInfo 结构体 |
| include/core/SkDrawable.h | SkDrawable 的 drawBackendGpu 方法使用此类 |
| include/gpu/ganesh/GrTypes.h | 定义 GrBackendApi 枚举 |
| src/gpu/ganesh/vk/GrVkGpu.cpp | 创建和填充 drawable 信息 |
| include/gpu/ganesh/gl/GrGLTypes.h | OpenGL 后端的类似类型定义（供未来扩展参考） |
