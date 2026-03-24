SVG 工具
=========

本目录包含以下内容——


svgs.txt
--------
此文本文件每行包含一个 SVG URL。
这是用于测试渲染正确性的 SVG 文件列表。

svg_images.txt
--------------
此文本文件每行包含一个图像 URL。
这是 svgs.txt 中 SVG 使用的图像列表。

svgs_parse_only.txt
-------------------
此文本文件每行包含一个 SVG URL。
这是用于测试 SVG 解析代码的 SVG 文件列表。

svg_downloader.py
-----------------
此 Python 脚本解析 txt 文件，并将 SVG 和图像下载到指定目录中。

该脚本可以手动运行：
$ python svg_downloader.py --output_dir /tmp/svgs/
或
$ python svg_downloader.py --output_dir /tmp/svgs/ --input_file svgs_parse_only.txt --prefix svgparse_

如果指定了 --keep_common_prefix 参数，则 URL 中公共前缀之后的部分将保留在目标目录层次结构中。例如，如果输入文件包含 URL https://example.com/images/a.png 和 https://example.com/images/subdir/b.png，则下载的文件将分别位于 output_dir/a.png 和 output_dir/subdir/b.png。
