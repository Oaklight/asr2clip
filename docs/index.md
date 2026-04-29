---
title: 首页
author: Oaklight
hide:
  - navigation
---

<div style="display: flex; align-items: center; gap: 1.5em; margin-bottom: 0.5em;">
  <div>
    <h1 style="margin: 0 0 0.2em 0;">asr2clip</h1>
    <p style="margin: 0; font-size: 1.1em; opacity: 0.85;">实时语音转文字剪贴板工具。</p>
    <p style="margin: 0.4em 0 0 0;">
      <a href="https://pypi.org/project/asr2clip/"><img src="https://img.shields.io/pypi/v/asr2clip?color=green" alt="PyPI"></a>
      <a href="https://github.com/Oaklight/asr2clip/releases/latest"><img src="https://img.shields.io/github/v/release/Oaklight/asr2clip?color=green" alt="Release"></a>
      <a href="https://github.com/Oaklight/asr2clip/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue.svg" alt="AGPL-3.0"></a>
    </p>
  </div>
</div>

asr2clip 可以实时识别语音，将其转换为文字，并自动复制到系统剪贴板。它利用 ASR API 服务进行语音识别，提供灵活的录音模式以适应不同使用场景。

---

## 快速开始

```bash
pip install asr2clip       # 安装
asr2clip --edit            # 创建/编辑配置文件
asr2clip --test            # 测试配置
asr2clip                   # 开始录音和转录
```

---

## 核心特性

| | |
|---|---|
| **实时转录** | 一条命令即可录音并转录 |
| **剪贴板集成** | 自动复制到剪贴板（无需外部工具） |
| **语音活动检测** | 多特征 VAD 自适应阈值，自动转录 |
| **持续录音模式** | 适用于会议和讲座的长时间录音 |
| **多后端支持** | OpenAI Whisper、硅基流动、Xinference 等 |
| **本地 ASR 服务器** | 可选的离线转录（基于 sherpa-onnx） |
| **文件转录** | 转录已有的音频文件 |
| **最小依赖** | 核心功能使用内置 YAML 和 HTTP 模块 |
| **跨平台** | 支持 Linux、macOS 和 Windows |

---

## 使用场景

**会议转录** — 使用持续录音模式和 VAD 录制会议，自动将语音片段转录到带时间戳的文件中。

**快速语音记录** — 按键说话，文字即刻出现在剪贴板，随处粘贴。

**课堂笔记** — 捕获课堂音频，自动分段转录。

**音频文件处理** — 从命令行转录已有的音频文件。

---

## 文档目录

- **[安装](getting-started/installation.md)** — 系统依赖和安装方式
- **[快速开始](getting-started/quickstart.md)** — 几分钟内上手使用
- **[配置](getting-started/configuration.md)** — 配置文件格式和选项
- **[使用指南](usage/)** — 录音模式、VAD 和高级功能
- **[API 参考](api/)** — 模块文档
- **[更新日志](changelog.md)** — 版本历史

## 许可证

GNU Affero 通用公共许可证 v3.0
