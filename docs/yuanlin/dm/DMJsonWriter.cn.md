# DMJsonWriter - DM 测试结果 JSON 写入器

> 源文件:
> - `dm/DMJsonWriter.h`
> - `dm/DMJsonWriter.cpp`

## 概述

DMJsonWriter 是 Skia 的 DM（Drawing Manager）测试工具的结果收集与 JSON 序列化组件。它提供线程安全的接口来收集测试运行的位图结果（BitmapResult），并将所有结果写入 `dm.json` 文件，或从已有的 JSON 文件中读取结果。该组件是 DM 测试基础设施中的核心输出模块，负责生成可供 CI/CD 系统消费的结构化测试报告。

## 架构位置

```
DM 测试框架
├── 测试执行器 (各种 Source/Sink)
├── JsonWriter (结果收集与输出)   <── 本模块
└── 命令行参数解析
```

`JsonWriter` 位于 DM 命名空间下，作为测试结果的终端汇总点，接收来自各个测试执行线程的结果数据。

## 主要类与结构体

### `JsonWriter` (类)

仅包含静态方法的工具类，所有方法均为线程安全。

### `JsonWriter::BitmapResult` (结构体)

描述单次测试运行的结果，包含以下字段：

| 字段 | 类型 | 描述 |
|------|------|------|
| `name` | `SkString` | 测试名称，如 "ninepatch-stretch" |
| `config` | `SkString` | 配置类型，如 "gpu", "8888" |
| `sourceType` | `SkString` | 源类型，如 "gm", "skp", "image" |
| `sourceOptions` | `SkString` | 源选项，如 "codec", "subset" |
| `md5` | `SkString` | 结果的 MD5 哈希值（ASCII，32 字节） |
| `ext` | `SkString` | 输出文件扩展名，如 "png", "pdf" |
| `gamut` | `SkString` | 色域信息 |
| `transferFn` | `SkString` | 传输函数 |
| `colorType` | `SkString` | 颜色类型 |
| `alphaType` | `SkString` | Alpha 类型 |
| `colorDepth` | `SkString` | 颜色深度 |

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `AddBitmapResult(const BitmapResult&)` | 线程安全地将一个结果添加到全局结果列表末尾 |
| `DumpJson(dir, key, properties)` | 将所有收集的结果写入 `dir/dm.json` |
| `ReadJson(path, callback)` | 读取 JSON 文件并对每条记录调用回调函数 |

## 内部实现细节

### 线程安全机制

使用全局互斥锁 `bitmap_result_mutex()` 保护共享数据：

```cpp
static SkMutex& bitmap_result_mutex() {
    static SkMutex& mutex = *(new SkMutex);
    return mutex;
}
```

该互斥锁通过堆分配避免了静态析构顺序问题（Meyer's singleton 变体）。

### JSON 输出格式

`DumpJson` 生成的 JSON 结构：

```json
{
  "properties": { ... },
  "key": { ... },
  "max_rss_MB": 1234,
  "results": [
    {
      "key": { "name": "...", "config": "...", "source_type": "...", "source_options": "..." },
      "options": { "ext": "...", "gamut": "...", ... },
      "md5": "..."
    }
  ]
}
```

- `properties` 和 `key` 来自命令行参数
- `max_rss_MB` 为进程最大常驻内存集大小
- `source_options` 仅在非空时输出，减少 JSON 体积

### JSON 读取

`ReadJson` 使用 `skjson::DOM` 解析器读取 JSON 文件，遍历 `results` 数组并通过回调函数逐条返回 `BitmapResult`。

## 依赖关系

- **Skia 核心**: `SkData`、`SkStream`、`SkString`、`SkMutex`
- **JSON 处理**: `SkJSONWriter`（写入）、`SkJSONReader`（读取，来自 `modules/jsonreader`）
- **文件系统**: `SkOSFile`、`SkOSPath`
- **工具**: `ProcStats`（获取内存使用信息）、`CommandLineFlags`（命令行参数）
- **容器**: `skia_private::TArray`

## 设计模式与设计决策

- **全静态接口**: `JsonWriter` 不需要实例化，所有方法为静态，简化了跨模块使用
- **全局状态 + 互斥锁**: 使用全局 `TArray<BitmapResult>` 收集结果，配合互斥锁实现线程安全
- **回调模式**: `ReadJson` 使用函数指针回调逐条处理结果，避免一次性加载所有结果到内存
- **Pretty Print**: JSON 输出使用 `SkJSONWriter::Mode::kPretty` 格式化，便于人工检查
- **容错设计**: `DumpJson` 在 `dir` 为空字符串时直接返回，不报错

## 性能考量

- 互斥锁的粒度覆盖整个 `AddBitmapResult` 和 `DumpJson` 中的序列化操作，在高并发场景下可能成为瓶颈
- 使用 `SkFILEWStream` 进行文件写入，配合 `SkJSONWriter` 的流式写入，避免在内存中构建完整 JSON 字符串
- `max_rss_MB` 的获取通过 `sk_tools::getMaxResidentSetSizeMB()`，仅在值有效时写入

## 相关文件

- `dm/DM.cpp` - DM 测试主程序，调用 `JsonWriter` 输出结果
- `tools/ProcStats.h` - 进程统计信息获取
- `tools/flags/CommandLineFlags.h` - 命令行标志定义
- `src/utils/SkJSONWriter.h` - JSON 写入工具
- `modules/jsonreader/SkJSONReader.h` - JSON 读取工具
