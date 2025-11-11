# HolisticaQuant 部署指南

本指南将帮助您将 HolisticaQuant 部署到公网，让其他人也能使用您的网站。

## 部署方案

我们推荐使用 **Railway（后端）+ Vercel（前端）** 的组合，这是最简单且免费的部署方案。

### 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| Railway + Vercel | 免费额度充足，自动部署，无需Dockerfile | 需要分别部署前后端 | ⭐⭐⭐⭐⭐ |
| Render | 全栈部署，免费额度 | 免费版有休眠限制 | ⭐⭐⭐ |
| ngrok | 零配置，立即分享 | 仅适合临时测试 | ⭐⭐ |

## 方案1：Railway + Vercel（推荐）

### 前置准备

1. 确保代码已推送到 GitHub
2. 准备 API 密钥（至少一个 LLM 提供商的密钥）

### 步骤1：部署后端（Railway）

1. **访问 Railway**
   - 打开 https://railway.app
   - 使用 GitHub 账号登录

2. **创建新项目**
   - 点击 "New Project"
   - 选择 "Deploy from GitHub repo"
   - 选择您的 HolisticaQuant 仓库

3. **配置环境变量**
   - 点击项目进入详情页
   - 点击 "Variables" 标签页
   - 添加以下环境变量：

   ```
   # 内置API密钥（用于默认共享，类似Streamlit）
   BUILTIN_DOUBAO_API_KEY=your_doubao_key_here
   BUILTIN_OPENAI_API_KEY=your_openai_key_here  # 可选
   BUILTIN_ANTHROPIC_API_KEY=your_anthropic_key_here  # 可选
   BUILTIN_DEEPSEEK_API_KEY=your_deepseek_key_here  # 可选
   
   # 部署模式
   DEPLOYMENT_MODE=production
   
   # 其他可选配置
   LLM_TEMPERATURE=0.7
   LLM_MAX_TOKENS=4000
   ```

4. **部署**
   - Railway 会自动检测 Python 项目并开始部署
   - 等待部署完成（约 2-5 分钟）
   - 部署完成后，点击 "Settings" -> "Generate Domain" 生成公网域名
   - 记录后端 URL（例如：`https://your-app.railway.app`）

### 步骤2：部署前端（Vercel）

1. **访问 Vercel**
   - 打开 https://vercel.com
   - 使用 GitHub 账号登录

2. **创建新项目**
   - 点击 "Add New Project"
   - 选择您的 HolisticaQuant 仓库
   - 点击 "Import"

3. **配置项目**
   - **Root Directory**: `website`
   - **Framework Preset**: Vite
   - **Build Command**: `npm install && npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

4. **配置环境变量**
   - 在 "Environment Variables" 部分添加：
   ```
   VITE_API_BASE_URL=https://your-app.railway.app
   ```
   （将 `your-app.railway.app` 替换为您的 Railway 后端 URL）

5. **部署**
   - 点击 "Deploy"
   - 等待部署完成（约 2-3 分钟）
   - 部署完成后，Vercel 会自动生成前端 URL（例如：`https://your-app.vercel.app`）

### 完成

- 访问前端 URL 即可使用
- 分享链接给其他人
- 用户可以使用内置密钥，也可以配置自己的密钥

## 方案2：Render（全栈部署）

### 部署后端

1. 访问 https://render.com，使用 GitHub 登录
2. 点击 "New +" -> "Web Service"
3. 选择您的仓库
4. 配置：
   - **Name**: holisticaquant-backend
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn holisticaquant.api.server:app --host 0.0.0.0 --port $PORT`
5. 添加环境变量（同 Railway）
6. 点击 "Create Web Service"

### 部署前端

1. 点击 "New +" -> "Static Site"
2. 选择您的仓库
3. 配置：
   - **Root Directory**: `website`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
4. 添加环境变量：`VITE_API_BASE_URL` = 后端URL
5. 点击 "Create Static Site"

## 方案3：ngrok（临时分享）

适合快速测试和演示：

```bash
# 1. 安装 ngrok
# macOS: brew install ngrok
# 或访问 https://ngrok.com/download

# 2. 启动后端（本地）
python scripts/dev.py

# 3. 在另一个终端运行 ngrok
ngrok http 8000

# 4. ngrok 会显示公网 URL，例如：
# Forwarding  https://xxxx.ngrok.io -> http://localhost:8000
```

**注意**：ngrok 免费版有连接数限制，仅适合临时测试。

## 环境变量说明

### 必需环境变量

- `BUILTIN_DOUBAO_API_KEY` - 豆包内置密钥（至少配置一个）
- `DEPLOYMENT_MODE` - 部署模式：`development` 或 `production`

### 可选环境变量

#### LLM 配置
- `BUILTIN_OPENAI_API_KEY` - OpenAI 内置密钥
- `BUILTIN_ANTHROPIC_API_KEY` - Anthropic 内置密钥
- `BUILTIN_DEEPSEEK_API_KEY` - DeepSeek 内置密钥
- `LLM_TEMPERATURE` - LLM 温度（默认：0.7）
- `LLM_MAX_TOKENS` - 最大 token 数（默认：4000）

#### 部署配置
- `ALLOWED_ORIGINS` - 生产环境允许的 CORS 域名（逗号分隔）
- `PORT` - 服务端口（Railway/Render 自动设置）

## 故障排查

### 后端无法启动

1. **检查 Python 版本**
   - Railway/Render 需要 Python 3.11+
   - 确保 `runtime.txt` 文件存在

2. **检查依赖**
   - 确保 `requirements.txt` 包含所有依赖
   - 检查构建日志中的错误信息

3. **检查环境变量**
   - 确保至少配置了一个内置 API 密钥
   - 检查环境变量名称是否正确

### 前端无法连接后端

1. **检查 API URL**
   - 确保 `VITE_API_BASE_URL` 正确
   - 确保后端 URL 包含 `https://` 前缀

2. **检查 CORS**
   - 如果部署模式是 `production`，确保前端域名在 `ALLOWED_ORIGINS` 中
   - 或设置 `ALLOWED_ORIGINS=*`（不推荐，但可以快速测试）

3. **检查网络**
   - 确保后端服务正在运行
   - 检查后端健康检查端点：`https://your-backend-url/api/health`

### API 密钥相关问题

1. **用户无法使用内置密钥**
   - 检查后端环境变量是否正确配置
   - 检查后端日志中的错误信息

2. **用户自定义密钥不生效**
   - 检查前端是否正确发送 `X-Session-Id` 请求头
   - 检查后端日志中的会话信息

## 安全建议

1. **生产环境 CORS**
   - 设置 `ALLOWED_ORIGINS` 限制允许的域名
   - 不要使用 `ALLOWED_ORIGINS=*`

2. **API 密钥安全**
   - 内置密钥仅用于默认共享，不要暴露给前端
   - 用户密钥存储在浏览器 localStorage，不会上传到服务器（除非用户主动配置）

3. **HTTPS**
   - Railway 和 Vercel 默认提供 HTTPS
   - 确保所有 API 调用都使用 HTTPS

## 更新部署

### 更新后端

1. 推送代码到 GitHub
2. Railway/Render 会自动重新部署

### 更新前端

1. 推送代码到 GitHub
2. Vercel 会自动重新部署

## 监控和日志

- **Railway**: 在项目详情页查看日志和指标
- **Vercel**: 在项目详情页查看部署日志和性能指标
- **Render**: 在服务详情页查看日志

## 成本估算

### Railway
- 免费额度：$5/月
- 适合中小型项目

### Vercel
- 免费额度：100GB 带宽/月
- 适合大多数项目

### Render
- 免费额度：有限（有休眠限制）
- 适合测试和小型项目

## 支持

如有问题，请查看：
- 项目 README.md
- GitHub Issues
- Railway/Vercel 官方文档

