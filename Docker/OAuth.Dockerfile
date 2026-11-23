FROM postgres:18.6

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential postgresql-server-dev-18 libpq-dev libcurl4-openssl-dev libssl-dev \
    cmake git pkg-config curl ca-certificates

RUN git clone https://github.com/akheron/jansson.git /tmp/jansson && \
    git -C /tmp/jansson checkout dbb5fb3636e155fccfce4cd215de752779bd6971 && \
    cmake -S /tmp/jansson -B /tmp/jansson/build -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
    -DBUILD_SHARED_LIBS=OFF -DJANSSON_BUILD_SHARED_LIBS=OFF -DJANSSON_BUILD_DOCS=OFF \
    -DJANSSON_EXAMPLES=OFF -DJANSSON_WITHOUT_TESTS=ON && \
    cmake --build /tmp/jansson/build --parallel 2 && cmake --install /tmp/jansson/build

RUN git clone https://github.com/benmcollins/libjwt.git /tmp/libjwt && \
    git -C /tmp/libjwt checkout 602118d99d46ca5df71bda60d3df642135417f29 && \
    cmake -S /tmp/libjwt -B /tmp/libjwt/build -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
    -DBUILD_SHARED_LIBS=OFF -DCMAKE_INSTALL_LIBDIR=lib -DEXCLUDE_DEPRECATED=ON \
    -DWITH_GNUTLS=OFF -DWITH_JSON_C=OFF -DWITH_LIBCURL=OFF -DWITH_MBEDTLS=OFF -DWITH_TESTS=OFF && \
    cmake --build /tmp/libjwt/build --parallel 2 && cmake --install /tmp/libjwt/build

RUN git clone https://github.com/proddata/pg_oauth_validator.git /tmp/validator && \
    git -C /tmp/validator checkout b58ce3208a691b1282e3f6e9cd5bbec877cc4b09 && \
    make -C /tmp/validator -o check-static-link-dependencies \
        PG_CONFIG=/usr/lib/postgresql/18/bin/pg_config all && \
    make -C /tmp/validator -o check-static-link-dependencies \
        PG_CONFIG=/usr/lib/postgresql/18/bin/pg_config install
