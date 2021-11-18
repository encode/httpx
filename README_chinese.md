<p align="center">
  <a href="https://www.python-httpx.org/"><img width="350" height="208" src="https://raw.githubusercontent.com/encode/httpx/master/docs/img/butterfly.png" alt='HTTPX'></a>
</p>

<p align="center"><strong>HTTPX</strong> <em>- 适用于Python的次世代HTTP客户端 </em></p>

<p align="center">
<a href="https://github.com/encode/httpx/actions">
    <img src="https://github.com/encode/httpx/workflows/Test%20Suite/badge.svg" alt="Test Suite">
</a>
<a href="https://pypi.org/project/httpx/">
    <img src="https://badge.fury.io/py/httpx.svg" alt="Package version">
</a>
</p>

HTTPX是一个功能齐全的HTTP客户端python3库. 它集成了 **一个命令行客户端**, 支持 **HTTP/1.1 和 HTTP/2**, 而且提供了 **同步和异步API**.

**注意！**: *0.21版本包括对集成命令行的一些改进。最新版本与重新设计的 `http核心`. 都应该自动更新到所需的版本，如果您遇到任何问题，那么您应该确保您安装的版本为 `httpx0.21.*` 且 `httpcore0.14.*` . 请参考 [the CHANGELOG](https://github.com/encode/httpx/blob/master/CHANGELOG.md) 来获得更多细节.*

---

通过pip安装httpx:

```shell
$ pip install httpx
```

使用httpx:

```pycon
>>> import httpx
>>> r = httpx.get('https://www.example.org/')
>>> r
<Response [200 OK]>
>>> r.status_code
200
>>> r.headers['content-type']
'text/html; charset=UTF-8'
>>> r.text
'<!doctype html>\n<html>\n<head>\n<title>Example Domain</title>...'
```

或者使用命令行客户端.

```shell
$ pip install 'httpx[cli]'  # 只安装集成的命令行功能
```

它现在允许我们直接从命令行使用HTTPX

<p align="center">
  <img width="700" src="docs/img/httpx-help.png" alt='httpx --help'>
</p>

发送一个请求...

<p align="center">
  <img width="700" src="docs/img/httpx-request.png" alt='httpx http://httpbin.org/json'>
</p>

## 特性

HTTPX将并为您提供以下功能:

* 广泛的 [requests-compatible API](https://www.python-httpx.org/compatibility/).
* 内置的命令行客户端功能.
* HTTP/1.1 [和 HTTP/2 支持](https://www.python-httpx.org/http2/).
* 标准同步接口，也支持 [异步](https://www.python-httpx.org/async/).
* 能够直接向 [WSGI 应用发送请求](https://www.python-httpx.org/advanced/#calling-into-python-web-apps) 或向 [ASGI 应用发送请求](https://www.python-httpx.org/async/#calling-into-python-web-apps).
* 在任何地方设置详细的timeout.
* 全类型注释.
* 全部代码均通过测试.

加上这些应该具备的标准功能

* 域名与URL
* 保持活动状态
* 具有Cookie持久性的会话
* 浏览器风格的SSL验证
* 身份验证
* Elegant Key/Value Cookies
* 自动解压缩
* 内容自动解码
* Unicode Response Bodies
* 分段文件上传
* 支持HTTP(S) 代理
* 支持设定timeout
* 流式下载
* 支持 .netrc 
* 接收Chunked编码

## 安装

使用pip安装:

```shell
$ pip install httpx
```

安装HTTP/2支持:

```shell
$ pip install httpx[http2]
```

HTTPX 要求 Python 3.6版本或更高.

## 文档

项目文档现已就绪，请访问 [https://www.python-httpx.org/](https://www.python-httpx.org/) 来阅读！

想学习基础知识？请访问 [快速开始](https://www.python-httpx.org/quickstart/).

想获得进阶帮助？ 请访问 [Advanced Usage](https://www.python-httpx.org/advanced/) 来获得答案, 不妨来看看 [异步支持](https://www.python-httpx.org/async/) 或者 [HTTP/2](https://www.python-httpx.org/http2/) 

[Developer Interface](https://www.python-httpx.org/api/) 提供了全面的API参考。

要了解与HTTPX集成的工具, 请访问 [第三方包](https://www.python-httpx.org/third_party_packages/).

## 贡献

如果您想对本项目做出贡献，请访问 [贡献者指南](https://www.python-httpx.org/contributing/) 来了解注意事项

## 依赖

HTTPX项目依赖于这些优秀的库:

* `httpcore` - The underlying transport implementation for `httpx`.
  * `h11` - HTTP/1.1 support.
  * `h2` - HTTP/2 support. *(Optional, with `httpx[http2]`)*
* `certifi` - SSL certificates.
* `charset_normalizer` - Charset auto-detection.
* `rfc3986` - URL parsing & normalization.
  * `idna` - Internationalized domain name support.
* `sniffio` - Async library autodetection.
* `rich` - Rich terminal support. *(Optional, with `httpx[cli]`)*
* `click` - Command line client support. *(Optional, with `httpx[cli]`)*
* `brotli` or `brotlicffi` - Decoding for "brotli" compressed responses. *(Optional, with `httpx[brotli]`)*
* `async_generator` - Backport support for `contextlib.asynccontextmanager`. *(Only required for Python 3.6)*

A huge amount of credit is due to `requests` for the API layout that
much of this work follows, as well as to `urllib3` for plenty of design
inspiration around the lower-level networking details.

<p align="center">&mdash; ⭐️ &mdash;</p>
<p align="center"><i>HTTPX 代码使用 <a href="https://github.com/encode/httpx/blob/master/LICENSE.md">BSD 开源协议</a>. 在英国布莱顿设计和构建。</i></p>
