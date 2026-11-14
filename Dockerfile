FROM public.ecr.aws/lambda/python:3.14

COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /uvx /bin/

WORKDIR ${LAMBDA_TASK_ROOT}

COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project --no-hashes \
    --format requirements.txt > /tmp/requirements.txt \
    && uv pip install --system --requirement /tmp/requirements.txt

RUN dnf install -y \
    alsa-lib \
    atk \
    at-spi2-atk \
    cairo \
    cups-libs \
    dbus-libs \
    expat \
    fontconfig \
    freetype \
    glib2 \
    gtk3 \
    libdrm \
    libX11 \
    libxcb \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXfixes \
    libXi \
    libxkbcommon \
    libXrandr \
    libXScrnSaver \
    libXtst \
    mesa-libgbm \
    nspr \
    nss \
    pango \
    && dnf clean all

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}" \
    && python -m playwright install --only-shell chromium \
    && chmod -R a+rX "${PLAYWRIGHT_BROWSERS_PATH}"

COPY get_data.py lambda_function.py ./

CMD ["lambda_function.lambda_handler"]
