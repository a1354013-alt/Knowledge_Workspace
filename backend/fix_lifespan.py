with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 改進 #4：統一 lifespan() 使用 logger 而非 print
old_code = """@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    print("✅ 企業 AI 助理 API 啟動")
    print(f"📝 允許的來源: {ALLOWED_ORIGINS}")
    print(f"🔐 Allow Credentials: {ALLOW_CREDENTIALS}")
    print(f"🔑 OpenAI API Key: {'已配置' if os.getenv('OPENAI_API_KEY') else '未配置（使用 sentence-transformers）'}")
    print(f"🔐 JWT 驗證: 已啟用")
    print(f"👤 Admin 管理: 已啟用")
    yield
    print("✅ 應用關閉")"""

new_code = """@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 【改進】統一使用 logger，便於日誌聚合和監控
    logger.info("✅ 企業 AI 助理 API 啟動")
    logger.info(f"📝 允許的來源: {ALLOWED_ORIGINS}")
    logger.info(f"🔐 Allow Credentials: {ALLOW_CREDENTIALS}")
    logger.info(f"🔑 OpenAI API Key: {'已配置' if os.getenv('OPENAI_API_KEY') else '未配置（使用 sentence-transformers）'}")
    logger.info(f"🔐 JWT 驗證: 已啟用")
    logger.info(f"👤 Admin 管理: 已啟用")
    yield
    logger.info("✅ 應用關閉")"""

content = content.replace(old_code, new_code)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 改進 #4 完成")
