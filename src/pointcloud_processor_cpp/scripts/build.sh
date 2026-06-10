#!/usr/bin/env bash
set -euo pipefail
BUILD_TYPE="${BUILD_TYPE:-RelWithDebInfo}"
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS_DIR="${CATKIN_WS:-$(cd "${PKG_DIR}/../.." && pwd)}"
mkdir -p "${WS_DIR}/src"
ln -sfn "${PKG_DIR}" "${WS_DIR}/src/pointcloud_processor"
cd "${WS_DIR}"
catkin_make -DCMAKE_BUILD_TYPE="${BUILD_TYPE}"
