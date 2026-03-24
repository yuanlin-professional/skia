# 模糊测试 (Fuzzing)
在此文件夹中，我们保存了我们的_模糊测试器_ (Fuzzer)（接受随机输入并随机执行代码的代码片段，专注于特定的 API）。例如，我们有一个编解码器模糊测试器 (Codec Fuzzer)，它接受一个变异的 png/jpeg 或类似文件并尝试将其转换为 `SkImage`。我们还有一个画布模糊测试器 (Canvas Fuzzer)，它接受一组随机字节并将其转换为对 `SkCanvas` 的调用。

## 可执行文件
这些模糊测试器以两种不同的方式打包（参见 //BUILD.gn）。有一个 `fuzz` 可执行文件包含所有模糊测试器，是重现模糊测试器报告的 bug 的便捷方式。还有单独的模糊测试器可执行文件，每个只包含一个模糊测试器，方便使用 [libfuzzer](https://llvm.org/docs/LibFuzzer.html) 进行构建。

参见 [../site/dev/testing/fuzz.md] 获取有关使用 `fuzz` 可执行文件构建和运行模糊测试器的更多信息。

## 持续运行
我们使用 [OSS-Fuzz](https://github.com/google/oss-fuzz) 对 Skia 进行模糊测试，OSS-Fuzz 反过来使用 libfuzzer、afl-fuzz、hong-fuzz 等模糊测试引擎来对 Skia 进行模糊测试。OSS-Fuzz 会在发现问题时自动[提交和关闭 bug](https://bugs.chromium.org/p/oss-fuzz/issues/list?q=label:Proj-skia)。

OSS-Fuzz 仓库中有一个 [Skia 文件夹](https://github.com/google/oss-fuzz/tree/master/projects/skia)，当我们想要添加/删除/更改自动运行的模糊测试器时，我们会在其中进行修改。[此文档](https://google.github.io/oss-fuzz/getting-started/new-project-guide/#testing-locally)描述了如何使用 Docker 在本地测试 OSS-Fuzz 构建和模糊测试器。

在 OSS-Fuzz 中启用模糊测试器时，我们通常需要遵循以下步骤：
  1. *将种子语料库 (Seed Corpus) 添加到 `gs://skia-cdn/oss-fuzz/`（在 [Skia Buildbots 项目](https://console.cloud.google.com/storage/browser/skia-cdn?project=google.com:skia-buildbots)中）。需要获取 "breakglass" 权限才能上传到此存储桶。
  2. *更新 [Dockerfile](https://github.com/google/oss-fuzz/blob/master/projects/skia/Dockerfile) 以将种子语料库下载到构建镜像。
  3. 更新 [build.sh](https://github.com/google/oss-fuzz/blob/628264df27f53cc60fcb27406a2da05d2197c025/projects/skia/build.sh#L99) 以构建所需的模糊测试器目标并将其移动到 $OUT。如果有种子语料库，将其移动到 $OUT 并确保其名称与模糊测试器可执行文件相同，后缀为 `_seed_corpus.zip`。

*适用于强烈依赖随机数据格式的模糊测试器，例如图像解码、SkSL 解析。这些被称为_二进制模糊测试器_ (Binary Fuzzer)，与_API 模糊测试器_ (API Fuzzer) 相对。

添加模糊测试器的示例 PR：[二进制](https://github.com/google/oss-fuzz/pull/4108)、[API](https://github.com/google/oss-fuzz/pull/5657)

还有一个为 [skcms 仓库](https://skia.googlesource.com/skcms/) 设置的 [OSS-Fuzz 文件夹](https://github.com/google/oss-fuzz/tree/master/projects/skcms)。构建过程类似，但 build.sh 脚本不是使用 GN 目标编译，而是直接编译模糊测试器可执行文件。

### OSS-Fuzz 仪表板
<https://oss-fuzz.com/fuzzer-stats> 对于查看我们的模糊测试器运行指标很有用。它显示诸如每秒执行次数（越高越好）、每个模糊测试器的边覆盖率百分比、模糊测试运行中以 OOM/超时/崩溃结束的百分比、整个模糊测试输入语料库 (corpus_backup) 等信息。如需查看此仪表板的权限，请联系 aarya@。以下是一些示例仪表板：

 - [由 libFuzzer 驱动的所有 Skia 模糊测试器的逐模糊测试器摘要](https://oss-fuzz.com/fuzzer-stats?group_by=by-fuzzer&date_start=2021-08-16&date_end=2021-08-22&fuzzer=libFuzzer&job=libfuzzer_asan_skia&project=skia)
 - [由 afl-fuzz 驱动的 sksl2glsl 的五天摘要](https://oss-fuzz.com/fuzzer-stats?group_by=by-day&date_start=2021-08-16&date_end=2021-08-22&fuzzer=afl_skia_sksl2glsl&job=afl_asan_skia&project=skia)

OSS-Fuzz 还提供[所有 Skia 模糊测试器的合并覆盖率报告](https://oss-fuzz.com/coverage-report/job/libfuzzer_asan_skia/latest)。[2021 年 8 月 22 日的覆盖率报告示例](https://storage.googleapis.com/oss-fuzz-coverage/skia/reports/20210822/linux/report.html)

## 另请参阅
  - [创建二进制模糊测试器](https://docs.google.com/document/d/1QDX0o8yDdmhbjoudNsXc66iuRXRF5XNNqGnzDzX7c2I/edit)
  - [创建 API 模糊测试器](https://docs.google.com/document/d/1e3ikXO7SwoBsbsi1MF06vydXRlXvYalVORaiUuOXk2Y/edit)
