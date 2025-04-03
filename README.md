# 渐变图像生成器 (Gradient Image Generator)

一个功能强大的渐变图像生成工具，可以创建高质量的线性和径向渐变图像，支持自定义颜色、尺寸和方向。

![渐变图像示例](output/c5022f-8ef9e0_lg_1024x1024.png)

## 功能特点

- 支持线性渐变和径向渐变
- 自定义主色和次色
- 多种渐变方向选项
- 自定义图像尺寸和纵横比
- 实时预览功能
- 支持导出PNG和JPG格式
- 异步图像生成，不阻塞UI
- 生成CSS代码，方便在网页中使用

## 安装要求

- Python 3.6+
- 依赖库：
  - Pillow (PIL) 10.0.0+
  - NumPy 1.26.0+
  - SciPy 1.11.3+

## 安装步骤

1. 克隆或下载此仓库

```bash
git clone https://github.com/yourusername/GradientImgGenerator.git
cd GradientImgGenerator
```

2. 创建并激活虚拟环境（可选但推荐）

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

运行主程序：

```bash
python gradient_generator.py
```

### 基本操作

1. 选择渐变类型（线性或径向）
2. 设置主色和次色（可以使用颜色选择器或输入十六进制颜色代码）
3. 选择渐变方向或位置
4. 设置图像尺寸和纵横比
5. 点击"Update Preview"查看预览
6. 点击"Save PNG"或"Save JPG"保存图像

### 高级功能

- **随机颜色**：点击"Random"按钮生成随机颜色
- **交换尺寸**：点击"Swap"按钮快速交换宽度和高度
- **预览缩放**：使用缩放滑块调整预览大小
- **纵横比预设**：选择常用的纵横比，如1:1、16:9、4:3等
- **CSS代码生成**：自动生成对应的CSS渐变代码

## 技术细节

### 架构

- 使用Tkinter构建用户界面
- 使用PIL (Pillow)库处理图像生成
- 使用NumPy和SciPy进行高效的数学计算
- 多线程处理，确保UI响应性

### 渐变算法

- **线性渐变**：支持8个方向的线性渐变
- **径向渐变**：支持9个不同位置的径向渐变

### 性能优化

- 异步图像生成，不阻塞UI
- 先生成低分辨率预览，再生成高分辨率图像
- 使用高质量的LANCZOS重采样算法

## 示例输出

程序可以生成各种尺寸和颜色的渐变图像，输出示例保存在`output`目录中：

- 线性渐变：从左上到右下的红色到青色渐变
- 径向渐变：从中心向外扩散的渐变
- 支持大尺寸图像生成（如10240×10240像素）

## 贡献指南

欢迎贡献代码、报告问题或提出新功能建议！

1. Fork此仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启一个Pull Request

## 许可证

此项目采用MIT许可证 - 详情请参阅[LICENSE](LICENSE)文件

## 联系方式

如有任何问题或建议，请通过以下方式联系：

- 项目GitHub页面：[https://github.com/yourusername/GradientImgGenerator](https://github.com/yourusername/GradientImgGenerator)
- 电子邮件：your.email@example.com

---

*此项目由[Your Name]创建和维护*