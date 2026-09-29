# PhotosClassifier 2

A local desktop photo workspace built with Python, OpenCV, SQLite, Pillow, and Tkinter. Match reference portraits against a library, review candidates, then copy approved photos into person folders. Original files are never moved.

Project and Mac download: https://av1sharma.github.io/projects/photos-classifier.html

## Mac app

Download and unzip the Apple-silicon application. It includes the recognition models and Python runtime; no Python installation is needed. Requires macOS 14 or newer. It is ad-hoc signed, not Apple-notarized. If macOS blocks first launch, use Privacy & Security → Open Anyway for this app. Intel Mac users can run the source instead.

## Run from source

Python 3.12 or 3.13 with Tk is required by the pinned dependencies. On Linux, install your distribution's Tk package first. Commands below use macOS/Linux venv paths; Windows uses `.venv\Scripts\python`.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m photoclassifier.models
.venv/bin/python -m photoclassifier
```

On Mac, `Launch.command` runs the prepared environment. The model installer downloads pinned OpenCV Zoo models and verifies their Git LFS SHA-256 hashes. Recognition itself makes no network requests.

## Use

1. Create a reference folder with one subfolder per person: `references/Avi/portrait1.jpg`, `references/Avi/portrait2.jpg`. Each image must contain exactly one face. Folder names define identities; names are not guessed from filenames.
2. Choose a separate photo library. The app recursively scans JPEG, PNG, WebP, BMP, and TIFF images. HEIC and RAW are not supported.
3. Scan at the default cosine-similarity threshold of 0.45. Higher thresholds return fewer candidates. Scores are not calibrated probabilities.
4. Pause at any time. Run again to resume. Unchanged files are cached in a SQLite catalog; changed files invalidate prior review. Failed files are retried. Changed reference portraits or thresholds create a distinct scan.
5. Select a candidate to view its face box. Approve, reject, or reset it. A `?` indicates competing profiles within a 0.05 similarity margin. All candidates require manual review, including apparently strong matches.
6. Export approved photos to a separate destination outside both library and reference folders. Relative source paths are retained under each person folder, so repeated filenames do not collide. Existing identical exports are skipped; different files are never overwritten.

The catalog lives at `~/.photosclassifier/catalog.sqlite3` and contains local file paths, scores, boxes, and review decisions. Face embeddings are held in memory during scans, not persisted. This catalog is not encrypted; use an OS account you trust. No photos or metadata are uploaded.

## Models and limitations

[YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) detects faces; [SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface) computes embeddings. Model files are pinned to OpenCV Zoo revision `47534e27c9851bb1128ccc0102f1145e27f23f98`; upstream license files accompany downloads.

Images are EXIF-oriented and downscaled to a maximum of 1600 px for inference. Small faces, motion blur, helmets, unusual lighting, and profile views can cause misses or incorrect matches. Reference portraits should be representative and used with the subjects' permission. The app is a personal photo-organization tool, not identity verification. The packaged Mac runtime also passes a real face-detection smoke test. The rebuilt workflow has not been benchmarked on the original 50 GB collection.

## Tests and packaging

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/pip install pyinstaller
PYINSTALLER_CONFIG_DIR=/tmp/photosclassifier-build-cache .venv/bin/pyinstaller \
  --noconfirm --windowed --name PhotosClassifier \
  --add-data 'models:models' --collect-all cv2 launch.py
```

Tests cover similarity thresholds, ambiguity, cached resume, changed/deleted files, corrupt images, missing references, duplicate filenames, and export collision protection. A separate real-model smoke test used the public NASA astronaut sample distributed by scikit-image, matched a brightness-adjusted copy, and exported it successfully. This confirms the inference pipeline, not accuracy on an event-photo dataset.

## Demo video (60–90 seconds)

1. Prepare two or three consenting friends' reference folders and a small event-photo folder.
2. Scan and show progress; pause and resume to demonstrate caching.
3. Select a candidate, show the face box and similarity, and approve it. Reject a questionable candidate.
4. Export approved photos and show person folders with preserved subdirectories.
5. Explain that originals stay untouched and everything runs locally.

The original `script.py`, `scriptreworked.py`, and notes are retained as development history. Use the `photoclassifier` package for the supported app.
