# SDFMaskFilter - 有符号距离场遮罩滤镜

> 源文件: `src/text/gpu/SDFMaskFilter.h`, `src/text/gpu/SDFMaskFilter.cpp`

## 概述

SDFMaskFilter 将 alpha 遮罩转换为有符号距离场（Signed Distance Field, SDF）表示。SDF 文本渲染技术允许在较低分辨率的纹理中存储字形轮廓信息，然后在片段着色器中以任意缩放级别高质量地重建字形边缘，广泛用于 GPU 加速的文本渲染。

该模块通过 `SK_DISABLE_SDF_TEXT` 宏控制编译，可在不需要 SDF 文本时完全禁用。

## 架构位置

```
SkMaskFilter (公共接口)
  └── SkMaskFilterBase (内部基类)
        └── SDFMaskFilterImpl (SDF 遮罩滤镜实现)

SDFMaskFilter (公共工厂类)
```

- **使用者**: SubRunContainer 中的 SDFTSubRun
- **类型标识**: `SkMaskFilterBase::Type::kSDF`

## 主要类与结构体

### SDFMaskFilter
公共工厂类，仅提供一个静态方法 `Make()`。

### SDFMaskFilterImpl
实际实现类（文件内部定义），继承自 SkMaskFilterBase。

## 公共 API 函数

```cpp
static sk_sp<SkMaskFilter> SDFMaskFilter::Make();
```
创建 SDF 遮罩滤镜实例。

## 内部实现细节

### 格式
- 输入格式: A8、BW 或 LCD16
- 输出格式: `SkMask::kSDF_Format`

### filterMask
1. 使用 `SkMaskBuilder::PrepareDestination` 创建目标遮罩，添加 `SK_DistanceFieldPad` 的边距
2. 根据输入格式选择对应的距离场生成函数：
   - A8: `SkGenerateDistanceFieldFromA8Image`
   - LCD16: `SkGenerateDistanceFieldFromLCD16Mask`
   - BW: `SkGenerateDistanceFieldFromBWImage`

### computeFastBounds
在源边界四周各扩展 `SK_DistanceFieldPad` 像素。

### 序列化
CreateProc 直接调用 `SDFMaskFilter::Make()` 创建新实例（无参数需要序列化）。

## 依赖关系

- `SkMaskFilterBase` — 遮罩滤镜基类
- `SkDistanceFieldGen` — 距离场生成函数
- `SkMask` / `SkMaskBuilder` — 遮罩数据结构
- `SK_DistanceFieldPad` — 距离场边距常量

## 设计模式与设计决策

1. **编译时可选**: 通过 `SK_DISABLE_SDF_TEXT` 宏完全禁用，减小二进制体积
2. **无状态设计**: 滤镜无参数，所有实例等价
3. **Pimpl 模式**: 公共接口 SDFMaskFilter 与实现 SDFMaskFilterImpl 分离

## 性能考量

- 距离场生成是 CPU 密集型操作，但只在字形首次缓存时执行一次
- 生成后的 SDF 纹理可在任意缩放下复用，大幅减少纹理 atlas 的内存需求

## 相关文件

- `src/core/SkDistanceFieldGen.h` — 距离场生成实现
- `src/text/gpu/SubRunContainer.cpp` — SDFTSubRun 使用此滤镜
- `src/text/gpu/DistanceFieldAdjustTable.h` — SDF 的 gamma 调整
