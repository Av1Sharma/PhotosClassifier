#!/bin/sh
set -eu
cd "$(dirname "$0")"
.venv/bin/python -m photoclassifier.models
PYINSTALLER_CONFIG_DIR="${TMPDIR:-/tmp}/photosclassifier-build-cache" .venv/bin/pyinstaller \
 --noconfirm --windowed --name PhotosClassifier --add-data 'models:models' --collect-all cv2 launch.py
codesign --verify --deep --strict dist/PhotosClassifier.app
ditto -c -k --sequesterRsrc --keepParent dist/PhotosClassifier.app dist/PhotosClassifier-2.1.0-mac-arm64.zip
