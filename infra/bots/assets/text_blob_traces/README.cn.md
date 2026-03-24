文本块追踪 (Text Blob Traces)
================

创建
------

按照常规方式下载并构建 Chromium，但需要在
`third_party/skia/src/core/SkRemoteGlyphCache.h` 文件顶部添加以下行

    #define SK_CAPTURE_DRAW_TEXT_BLOB

运行 `chrome --no-sandbox URL`，追踪文件将被写入当前工作目录。使用 `blob_cache_sim` 检查追踪内容。

上传
------

要上传资产的新版本，首先将新版本放入
`text_blob_traces` 目录，然后执行：

    infra/bots/assets/assets.py upload -t text_blob_traces text_blob_traces

然后提交文件 `infra/bots/assets/text_blob_traces/VERSION`

下载
--------

执行：

    infra/bots/assets/assets.py download -t text_blob_traces text_blob_traces

运行基准测试和模拟器
-----------------------

    tools/git-sync-deps
    bin/gn gen out/release --args='is_debug=false'
    ninja -C out/release nanobench blob_cache_sim

    out/release/nanobench -m SkDiffBench --texttraces text_blob_traces -q

    out/release/blob_cache_sim text_blob_traces/*
