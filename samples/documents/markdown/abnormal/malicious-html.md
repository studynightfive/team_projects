# 正常内容部分

这是一段正常的文本内容，用于测试安全清洗功能。

## XSS 攻击测试

以下内容包含各种 XSS 攻击向量，应该在清洗后被移除：

<script>alert('XSS攻击 - 脚本标签')</script>

<img src="x" onerror="alert('XSS攻击 - onerror事件')">

<a href="javascript:alert('XSS攻击 - javascript协议')">点击这里</a>

<div onclick="alert('XSS攻击 - onclick事件')">点击触发</div>

<iframe src="http://malicious.example.com"></iframe>

<svg onload="alert('XSS攻击 - SVG onload')"></svg>

<body onload="alert('XSS攻击 - body onload')">

## 正常内容继续

这段内容在攻击向量之后，应该正常保留。

### 含外部跟踪链接的图片

![正常图片](https://example.com/logo.png)

![带跟踪参数的图片](https://example.com/track.png?utm_source=test&session_id=12345)

### 正常文本结束

这是文档的最后一段，用于验证清洗后的内容完整性。