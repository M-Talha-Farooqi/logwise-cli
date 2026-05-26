# ---- build stage ----
FROM python:3.12-slim AS build
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir build && python -m build --wheel

# ---- runtime stage ----
FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.title="logwise" \
      org.opencontainers.image.description="Resilient server-log analyzer CLI"
# non-root user — good container hygiene
RUN useradd --create-home --uid 10001 app
WORKDIR /home/app
COPY --from=build /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl
USER app
ENTRYPOINT ["logwise"]
CMD ["--help"]
