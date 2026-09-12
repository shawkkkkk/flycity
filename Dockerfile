FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY flycity ./flycity
COPY site ./site
RUN pip install --no-cache-dir .
ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE 8000
CMD ["python", "-m", "flycity"]
