# JsonWriteBuffer

> 源文件: `tools/debugger/JsonWriteBuffer.h`, `tools/debugger/JsonWriteBuffer.cpp`

## 概述

JsonWriteBuffer 是 Skia 调试器中用于将 SkFlattenable 对象序列化为 JSON 格式的适配器类。它实现了 `SkWriteBuffer` 接口，将原本写入二进制格式的序列化调用重定向到 `SkJSONWriter`，使调试器能够以人类可读的 JSON 格式展示 Shader、ColorFilter、ImageFilter 等 flattenable 对象的内部结构。

## 架构位置

```
SkWriteBuffer (抽象基类)
  +-- SkBinaryWriteBuffer  (二进制序列化)
  +-- JsonWriteBuffer      (JSON 序列化) <-- 本文件

DrawCommand::flatten() --> JsonWriteBuffer --> SkJSONWriter
```

## 主要类与结构体

### `JsonWriteBuffer`
- **继承**: `SkWriteBuffer`（final 类）
- **成员**:
  - `fWriter`: SkJSONWriter 指针
  - `fUrlDataManager`: URL 数据管理器
  - `fCount`: 字段计数器（用于生成有序键名）

## 公共 API 函数

所有方法均为 `SkWriteBuffer` 接口的 override 实现：

| 函数 | 说明 |
|------|------|
| `writePad32(buffer, bytes)` | 写入原始字节为十六进制数组 |
| `writeByteArray(data, size)` | 写入字节数组为十六进制 |
| `writeBool(value)` | 写入布尔值 |
| `writeScalar(value)` | 写入浮点数 |
| `writeScalarArray(values)` | 写入浮点数组 |
| `writeInt(value)` / `writeUInt(value)` | 写入整数 |
| `writeIntArray(values)` | 写入整数数组 |
| `writeString(value)` | 写入字符串 |
| `writeFlattenable(flattenable)` | 递归序列化 flattenable 对象 |
| `writeColor(color)` / `writeColor4f(color)` | 写入颜色值 |
| `writePoint(point)` / `writePoint3(point)` | 写入点 |
| `writeMatrix(matrix)` / `write(SkM44)` | 写入矩阵 |
| `writeRect(rect)` / `writeIRect(rect)` | 写入矩形 |
| `writeRegion(region)` / `writePath(path)` | 写入区域/路径 |
| `writeImage(image)` | 写入图像（PNG 编码） |
| `writeTypeface(typeface)` | 写入字体（指针地址） |
| `writePaint(paint)` | 写入 Paint |

## 内部实现细节

### 有序键名生成
`append(type)` 方法生成格式为 `"00_type"`, `"01_type"`, ... 的键名，其中前缀数字确保 JSON 属性按序列化顺序排列，type 描述数据类型。

### Flattenable 递归序列化
`writeFlattenable` 创建新的 JsonWriteBuffer 实例，递归调用 `flattenable->flatten()`，使嵌套的 flattenable 对象（如 ComposeShader 中的子 Shader）也能被正确序列化。

### 委托到 DrawCommand 辅助方法
大量写入方法委托给 `DrawCommand::MakeJsonColor`, `MakeJsonPoint`, `MakeJsonMatrix` 等静态方法，确保 JSON 格式与其他序列化路径一致。

### 不完全支持的类型
- `writeStream`: 仅记录长度，不序列化内容
- `writeTypeface`: 仅记录指针地址（不支持完整序列化）

## 依赖关系

- **Skia 核心**: `SkWriteBuffer`, `SkFlattenable`, `SkString`
- **调试器**: `DrawCommand`（JSON 辅助方法）
- **序列化**: `SkJSONWriter`

## 设计模式与设计决策

1. **适配器模式**: 将 SkWriteBuffer 的二进制写入接口适配为 JSON 输出
2. **有序编号**: 通过数字前缀保持属性顺序，因为 JSON 对象的属性顺序在规范中不保证
3. **递归序列化**: 通过创建新 JsonWriteBuffer 实例实现 flattenable 对象图的完整遍历
4. **降级处理**: 对不完全支持的类型（stream、typeface）提供最小化输出而非失败

## 性能考量

- 每个 flattenable 对象的递归序列化会创建新的 JsonWriteBuffer，但这仅用于调试场景
- 原始字节数据转为十六进制字符串会显著增加输出大小

## 相关文件

- `tools/debugger/DrawCommand.h/.cpp` - 使用 JsonWriteBuffer 的命令系统
- `src/utils/SkJSONWriter.h` - JSON 写入器
- `src/core/SkWriteBuffer.h` - 序列化缓冲基类
- `tools/UrlDataManager.h` - 二进制数据 URL 管理
