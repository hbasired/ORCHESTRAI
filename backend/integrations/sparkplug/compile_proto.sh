#!/usr/bin/env bash
# Regenerate sparkplug_b_pb2.py from the canonical Eclipse Sparkplug B v3.0 proto.
# Build-time only (grpcio-tools bundles protoc); runtime needs just `protobuf`.
# Pinned grpcio-tools==1.62.3 emits protobuf-4.x-compatible code (TF-2.15-safe; research §25.4).
set -euo pipefail
cd "$(dirname "$0")"
python -m grpc_tools.protoc -I. --python_out=. sparkplug_b.proto
echo "Generated sparkplug_b_pb2.py from sparkplug_b.proto"
