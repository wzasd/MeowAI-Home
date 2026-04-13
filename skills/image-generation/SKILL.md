---
name: image-generation
description: >
  通过浏览器自动化，在 Gemini / ChatGPT 上生成图片并下载。
  Use when: 需要生成概念图、UI 参考图、猫猫头像。
  Not for: Pencil 内部设计。
  Output: 生成的图片文件保存到项目 assets/ 目录。
triggers:
  - "生成图片"
  - "画一张"
  - "generate image"
  - "AI 画图"
  - "画个"
next: []
---

# Image Generation — AI 图片生成

> 参考: MeowAI Home image-generation skill

## 流程

1. **理解需求**: 明确要生成什么类型的图片
2. **生成提示词**: 构造精确的图片生成 prompt
3. **调用生成**: 通过 Gemini/ChatGPT 生成
4. **保存结果**: 下载到 `assets/` 目录

## 适用场景

- 概念图
- UI 参考图
- 素材图片
- 猫猫头像

## 注意

- 不适合精确设计稿（用 pencil-design）
- 需要浏览器自动化支持
