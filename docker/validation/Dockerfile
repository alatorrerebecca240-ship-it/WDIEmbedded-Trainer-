# Official GCC 14 / Debian bookworm; pin the base image, not a moving tag.
FROM gcc:14-bookworm@sha256:5e927c284bf55a7dc796262e311a0703344f62f41f5621eb56843111b1d37e15

# Headers + date-time library required by the Exercism Gigasecond exercise.
# Keep dependency license/copyright files under /usr/share/doc.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libboost-dev=1.74.0.3 libboost-date-time-dev=1.74.0.3 \
    && rm -rf /var/lib/apt/lists/*

COPY smoke.c smoke.cpp smoke.sh /opt/trainer/
RUN sh /opt/trainer/smoke.sh && rm -f /tmp/trainer-smoke-c /tmp/trainer-smoke-cpp
USER 65534:65534
WORKDIR /tmp
CMD ["sh"]
