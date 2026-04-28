# 本地 ASR 服务器

asr2clip 包含一个可选的本地 ASR 服务器，基于 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) 实现完全离线的语音识别。

## 安装

使用 `local_asr` 可选依赖安装：

```bash
pip install "asr2clip[local_asr]"
```

## 启动服务器

```bash
asr2clip-serve
```

服务器默认在 `http://localhost:8000` 启动，提供 OpenAI 兼容的 `/v1/audio/transcriptions` 端点。

## 配置

将 asr2clip 指向本地服务器：

```yaml
api_base_url: "http://localhost:8000/v1/"
api_key: "not-used"
model_name: "sherpa-onnx"
```

## 使用方式

```bash
# 在一个终端启动服务器
asr2clip-serve

# 在另一个终端使用本地服务器
asr2clip -c local_config.yaml
```

## 特性

- **完全离线** — 无需互联网连接
- **OpenAI 兼容 API** — 可作为直接替代
- **自动下载模型** — 首次使用时自动下载模型
- **多模型支持** — 通过 sherpa-onnx 配置 ASR 模型
