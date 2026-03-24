Unicode 比较工具
============================

本目录包含以下内容

cpp/*
-----
此文件夹包含 SkUnicode 和 golang 之间的桥接代码

go/*
----
此文件夹包含一组 golang 工具，用于下载、预处理数据，然后生成比较表格

download_wiki.go
----------------
make download_wiki
./download_wiki
你可能需要更新 go-wiki 包：go get -u github.com/trietmn/go-wiki
Wiki 语言列表：https://meta.wikimedia.org/wiki/List_of_Wikipedias

extract_info.go
---------------

generate_table.go
-----------------

