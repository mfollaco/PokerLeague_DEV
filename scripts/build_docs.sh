#!/usr/bin/env bash
set -euo pipefail
rm -rf docs
cp -R frontend docs
echo "✅ docs/ rebuilt from frontend/"
