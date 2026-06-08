FROM postgres:17-bookworm

ARG POSTGRES_VERSION=17
ARG TIMESCALEDB_VERSION=2.18.0
ARG PGVECTOR_VERSION=0.8.0
ARG AGE_VERSION=1.7.0

# Установка всех необходимых зависимостей, включая git
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cmake \
    curl \
    wget \
    gnupg \
    lsb-release \
    flex \
    bison \
    libkrb5-dev \
    libssl-dev \
    libreadline-dev \
    zlib1g-dev \
    libcurl4-openssl-dev \
    liblz4-dev \
    libzstd-dev \
    libsnappy-dev \
    libpam0g-dev \
    libxml2-dev \
    libxslt1-dev \
    libperl-dev \
    python3-dev \
    tcl-dev \
    libsystemd-dev \
    libselinux1-dev \
    postgresql-server-dev-${POSTGRES_VERSION} \
    && rm -rf /var/lib/apt/lists/*

# Установка TimescaleDB через официальный репозиторий
RUN wget https://github.com/timescale/timescaledb/archive/refs/tags/${TIMESCALEDB_VERSION}.tar.gz \
        -O /tmp/timescaledb.tar.gz \
    && mkdir -p /tmp/timescaledb-src \
    && tar -xzf /tmp/timescaledb.tar.gz -C /tmp/timescaledb-src --strip-components=1 \
    && cd /tmp/timescaledb-src \
    && ./bootstrap \
        -DREGRESS_CHECKS=OFF \
        -DWARNINGS_AS_ERRORS=OFF \
        -DASSERTIONS=OFF \
    && cd build \
    && make -j$(nproc) \
    && make install \
    && rm -rf /tmp/timescaledb-src /tmp/timescaledb.tar.gz

# Сборка pgvector из исходников
RUN wget https://github.com/pgvector/pgvector/archive/refs/tags/v${PGVECTOR_VERSION}.tar.gz -O /tmp/pgvector.tar.gz \
    && mkdir -p /tmp/pgvector \
    && tar -xzf /tmp/pgvector.tar.gz -C /tmp/pgvector --strip-components=1 \
    && cd /tmp/pgvector \
    && make \
    && make install \
    && rm -rf /tmp/pgvector /tmp/pgvector.tar.gz

# Сборка Apache AGE из исходников
RUN wget https://github.com/apache/age/archive/refs/tags/PG17/v1.7.0-rc0.tar.gz -O /tmp/age.tar.gz \
    && mkdir -p /tmp/age \
    && tar -xzf /tmp/age.tar.gz -C /tmp/age --strip-components=1 \
    && cd /tmp/age \
    && make PG_CONFIG=/usr/lib/postgresql/${POSTGRES_VERSION}/bin/pg_config USE_PGXS=1 \
    && make PG_CONFIG=/usr/lib/postgresql/${POSTGRES_VERSION}/bin/pg_config USE_PGXS=1 install \
    && rm -rf /tmp/age /tmp/age.tar.gz

# Очистка сборочных зависимостей для уменьшения размера образа
RUN apt-get remove -y \
    build-essential \
    cmake \
    flex \
    bison \
    postgresql-server-dev-${POSTGRES_VERSION} \
    libreadline-dev \
    zlib1g-dev \
    libssl-dev \
    libcurl4-openssl-dev \
    libkrb5-dev \
    liblz4-dev \
    libzstd-dev \
    libsnappy-dev \
    libpam0g-dev \
    libxml2-dev \
    libxslt1-dev \
    libperl-dev \
    python3-dev \
    tcl-dev \
    libsystemd-dev \
    libselinux1-dev \
    wget \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Настройка TimescaleDB в postgresql.conf
RUN echo "shared_preload_libraries = 'timescaledb'" >> /usr/share/postgresql/postgresql.conf.sample

# Копирование скрипта инициализации
COPY init.sql /docker-entrypoint-initdb.d/

# Healthcheck для мониторинга состояния PostgreSQL
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD pg_isready -U postgres -d postgres || exit 1

EXPOSE 5432

CMD ["postgres"]