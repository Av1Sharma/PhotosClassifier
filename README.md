# PhotosClassifier

PhotosClassifier is a local desktop tool for reviewing face-similarity candidates and copying approved photos into person folders. It uses Python, OpenCV, SQLite, Pillow, and Tkinter. Original library files are never moved or modified.

Project page and Mac download: https://av1sharma.github.io/projects/photos-classifier.html

## Mac app

Download and unzip the Apple-silicon app. It includes the recognition models and Python runtime, so a separate Python install is not required. Requires macOS 14 or newer. The app is ad-hoc signed, not Apple-notarized; if macOS blocks the first launch, approve it in System Settings → Privacy & Security. Intel Mac users can run from source.

## Run from source

Use Python 3.12 or 3.13 with Tk. On Linux, install the distribution's Tk package first. On Windows, replace `.venv/bin/python` with `.venv\Scripts\python`.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m photoclassifier.models
.venv/bin/python -m photoclassifier
```

The model setup downloads pinned OpenCV Zoo models and verifies their Git LFS SHA-256 hashes. Recognition runs locally and makes no network requests.

## Use

1. Create a reference folder with one subfolder per person, such as `references/Avi/portrait1.jpg`. Each reference image should contain one face. Folder names define identities; names are not inferred from filenames.
2. Select a separate photo library. The app scans JPEG, PNG, WebP, BMP, and TIFF files recursively. HEIC and RAW are not supported.
3. Scan using the default cosine-similarity threshold of 0.45. A higher threshold returns fewer candidates. Scores are not calibrated probabilities.
4. Pause and resume scans. Unchanged files are cached in SQLite; changed files invalidate earlier reviews. Failed files can be retried. Changing reference portraits or the threshold starts a distinct scan.
5. Review every candidate manually. You can inspect the face box, approve, reject, or reset a decision. A `?` marks competing profiles within a 0.05 similarity margin.
6. Export approved photos to a destination outside the source library and reference folders. Source subdirectories are preserved within person folders. Identical existing exports are skipped; different files are not overwritten.

The local catalog is stored at `~/.photosclassifier/catalog.sqlite3` and contains file paths, scores, face boxes, and review decisions. Face embeddings are held in memory during scans and are not persisted. The catalog is not encrypted, and no photos or metadata are uploaded.

## Models and limitations

YuNet detects faces and SFace computes embeddings. Model files are pinned to OpenCV Zoo revision `47534e27c9851bb1128ccc0102f1145e27f23f98`; the corresponding upstream license files are included. Images are EXIF-oriented and downscaled to at most 1600 pixels for inference.

Small faces, motion blur, helmets, unusual lighting, and profile views can cause misses or incorrect matches. Similarity is not identity verification. This is a personal photo-organization tool; use reference photos with the subjects' permission and review every candidate. The packaged Mac runtime has been smoke-tested with a real face-detection sample, but the workflow has not been benchmarked on the original 50 GB collection.

## Tests and Mac packaging

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The tests cover similarity thresholds, ambiguity, cached resume, changed and deleted files, corrupt images, missing references, duplicate filenames, and export collision protection.

`build-mac.sh` packages the application for Apple silicon. Packaging requires macOS and the dependencies documented in the script and project files; it does not produce Apple notarization. The `dist/` directory contains release artifacts and checksums.
