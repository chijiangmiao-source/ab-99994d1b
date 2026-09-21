# The acceptance runner needs only the Python standard library; keep it tiny.
FROM python:3.11-alpine
WORKDIR /verify
COPY verify.py ./
CMD ["python", "-u", "verify.py"]
