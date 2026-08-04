FROM eclipse-temurin:21-jre-alpine

ARG JENA_VERSION=6.2.0
ARG JENA_ARCHIVE=apache-jena-fuseki-${JENA_VERSION}.tar.gz
ARG JENA_URL=https://archive.apache.org/dist/jena/binaries/${JENA_ARCHIVE}

RUN wget -q "${JENA_URL}" -O "/tmp/${JENA_ARCHIVE}" \
    && wget -q "${JENA_URL}.sha512" -O "/tmp/${JENA_ARCHIVE}.sha512" \
    && cd /tmp \
    && sha512sum -c "${JENA_ARCHIVE}.sha512" \
    && tar -xzf "${JENA_ARCHIVE}" \
    && mv "apache-jena-fuseki-${JENA_VERSION}" /fuseki \
    && rm "/tmp/${JENA_ARCHIVE}" "/tmp/${JENA_ARCHIVE}.sha512" \
    && addgroup -S fuseki \
    && adduser -S -G fuseki fuseki \
    && mkdir -p /fuseki/databases/dpp \
    && chown -R fuseki:fuseki /fuseki

USER fuseki
WORKDIR /fuseki
EXPOSE 3030
ENTRYPOINT ["./fuseki-server"]
CMD ["--update", "--loc=/fuseki/databases/dpp", "/dpp"]
