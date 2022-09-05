<p align="center">
  <a href="https://www.python-httpx.org/"><img width="350" height="208" src="https://raw.githubusercontent.com/encode/httpx/master/docs/img/butterfly.png" alt='HTTPX'></a>
</p>

<p align="center"><strong>HTTPX</strong> <em>- 适用于 Python 的下一代 HTTP 客户端</em></p>

<p align="center">
<a href="https://github.com/encode/httpx/actions">
    <img src="https://github.com/encode/httpx/workflows/Test%20Suite/badge.svg" alt="Test Suite">
</a>
<a href="https://pypi.org/project/httpx/">
    <img src="https://badge.fury.io/py/httpx.svg" alt="Package version">
</a>
</p>

HTTPX 是适用于 Python3 的功能齐全的 HTTP 客户端。 它集成了 **一个命令行客户端**，同时支持 **HTTP/1.1 和 HTTP/2**，并提供了 **同步和异步 API**。

---

通过 pip 安装 HTTPX：

```shell
$ pip install httpx
```

使用 httpx：

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

或者使用命令行客户端。

```shell
$ pip install 'httpx[cli]'  # 命令行功能是可选的。
```

它允许我们直接通过命令行来使用 HTTPX...

<p align="center">
  <img width="700" src="docs/img/httpx-help.png" alt='httpx --help'>
</p>

发送一个请求...

<p align="center">
  <img width="700" src="docs/img/httpx-request.png" alt='httpx http://httpbin.org/json'>
</p>

## 特性

HTTPX 建立在成熟的 requests 可用性基础上，为您提供以下功能：

* 广泛的 [requests 兼容 API](https://www.python-httpx.org/compatibility/)。
* 内置的命令行客户端功能。
* HTTP/1.1 [和 HTTP/2 支持](https://www.python-httpx.org/http2/)。
* 标准同步接口，也支持 [异步](https://www.python-httpx.org/async/)。
* 能够直接向 [WSGI 应用发送请求](https://www.python-httpx.org/advanced/#calling-into-python-web-apps) 或向 [ASGI 应用发送请求](https://www.python-httpx.org/async/#calling-into-python-web-apps)。
* 每一处严格的超时控制。
* 完整的类型注解。
* 100% 测试。

加上这些应该具备的标准功能...

* 国际化域名与 URL
* Keep-Alive & 连接池
* Cookie 持久性会话
* 浏览器风格的 SSL 验证
* 基础或摘要身份验证
* 优雅的键值 Cookies
* 自动解压缩
* 内容自动解码
* Unicode 响应正文
* 分段文件上传
* HTTP(S)代理支持
* 可配置的连接超时
* 流式下载
* .netrc 支持
* 分块请求

## 安装

使用 pip 安装：

```shell
$ pip install httpx
```

或者，安装可选的 HTTP/2 支持：

```shell
$ pip install httpx[http2]
```

HTTPX 要求 Python 3.7+ 版本。

## 文档

项目文档现已就绪，请访问 [https://www.python-httpx.org/](https://www.python-httpx.org/) 来阅读。

要浏览所有基础知识，请访问 [快速开始](https://www.python-httpx.org/quickstart/)。

更高级的主题，可参阅 [高级用法](https://www.python-httpx.org/advanced/) 章节, [异步支持](https://www.python-httpx.org/async/) 或者 [HTTP/2](https://www.python-httpx.org/http2/) 章节。

[Developer Interface](https://www.python-httpx.org/api/) 提供了全面的 API 参考。

要了解与 HTTPX 集成的工具, 请访问 [第三方包](https://www.python-httpx.org/third_party_packages/)。

## 贡献

如果您想对本项目做出贡献，请访问 [贡献者指南](https://www.python-httpx.org/contributing/) 来了解如何开始。

## 依赖

HTTPX 项目依赖于这些优秀的库：

* `httpcore` - `httpx` 基础传输接口实现。
  * `h11` - HTTP/1.1 支持。
* `certifi` - SSL 证书。
* `rfc3986` - URL 解析与规范化。
  * `idna` - 国际化域名支持。
* `sniffio` - 异步库自动检测。

以及这些可选的安装：

* `h2` - HTTP/2 支持。 *(可选的，通过 `httpx[http2]`)*
* `socksio` - SOCKS 代理支持。 *(可选的， 通过 `httpx[socks]`)*
* `rich` - 丰富的终端支持。 *(可选的，通过 `httpx[cli]`)*
* `click` - 命令行客户端支持。 *(可选的，通过 `httpx[cli]`)*
* `brotli` 或者 `brotlicffi` - 对 “brotli” 压缩响应的解码。*(可选的，通过 `httpx[brotli]`)*

这项工作的大量功劳都归功于参考了 `requests` 所遵循的 API 结构，以及 `urllib3` 中众多围绕底层网络细节的设计灵感。

---

<p align="center"><i>HTTPX 使用 <a href="https://github.com/encode/httpx/blob/master/LICENSE.md">BSD 开源协议</a> code。<br/>精心设计和制作。</i><br/>&mdash; 🦋 &mdash;</p>
