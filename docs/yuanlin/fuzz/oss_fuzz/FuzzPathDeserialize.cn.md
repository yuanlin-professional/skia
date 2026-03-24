# FuzzPathDeserialize (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzPathDeserialize.cpp

## 概述

测试 SkPath 的反序列化功能,专注于版本 4 格式(Chrome 使用的版本)。路径序列化用于跨进程传输路径数据,反序列化的安全性至关重要。

## 架构位置

测试 `src/core/SkReadBuffer.h` 中的路径反序列化逻辑。

## 主要类与结构体

### FuzzPathDeserialize 函数

```cpp
void FuzzPathDeserialize(const uint8_t *data, size_t size)
```

流程:
1. 创建 SkReadBuffer: `SkReadBuffer buf(data, size)`
2. 读取路径: `buf.readPath()`
3. 验证缓冲区有效性
4. 渲染路径到 surface 以触发代码执行

### LLVMFuzzerTestOneInput

版本过滤:
```cpp
unsigned version = packed & 0xFF;
if (version != 4) {
    return 0;  // 只测试版本 4
}
```

输入大小: 4-2000 字节

## 内部实现细节

### 版本控制

- Skia 路径序列化有版本号
- Chrome 只生成版本 4
- Fuzzer 聚焦于实际使用的版本

### 安全考虑

反序列化是安全边界:
- 验证数据完整性
- 防止缓冲区溢出
- 处理损坏的数据

## 依赖关系

- `src/core/SkReadBuffer.cpp`: 反序列化实现
- `src/core/SkPath.cpp`: 路径表示

## 设计模式与设计决策

**引导 Fuzzing**: 通过版本过滤,引导 fuzzer 关注实际使用的代码路径。

## 性能考量

路径反序列化需要解析和验证,但相对快速。

## 相关文件

- `src/core/SkWriteBuffer.cpp`: 序列化实现
- `tests/SerializationTest.cpp`: 序列化测试

该 fuzzer 是发现路径反序列化安全问题的关键工具,对 Chrome 的安全性很重要。
