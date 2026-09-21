FROM python:3.12-slim

WORKDIR /work
COPY verify.py .

# 仅使用标准库；一次性运行，验收结束即退出并以退出码报告结果
CMD ["python", "verify.py"]
