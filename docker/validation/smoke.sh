#!/bin/sh
set -eu
gcc -std=c11 -Wall -Wextra -Wpedantic -Werror /opt/trainer/smoke.c -o /tmp/trainer-smoke-c
/tmp/trainer-smoke-c
g++ -std=c++17 -Wall -Wextra -Wpedantic -Werror /opt/trainer/smoke.cpp -lboost_date_time -o /tmp/trainer-smoke-cpp
/tmp/trainer-smoke-cpp
