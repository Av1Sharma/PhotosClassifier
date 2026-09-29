"""Pinned OpenCV model downloads; photo processing never uses the network."""
from pathlib import Path
import hashlib
import urllib.request
REVISION = '47534e27c9851bb1128ccc0102f1145e27f23f98'
FILES = {
 'yunet.onnx': 'face_detection_yunet/face_detection_yunet_2023mar.onnx',
 'sface.onnx': 'face_recognition_sface/face_recognition_sface_2021dec.onnx',
}
ROOT = Path(__file__).resolve().parents[1] / 'models'
def install(report=print):
    ROOT.mkdir(exist_ok=True)
    for name, source in FILES.items():
        pointer_url=f'https://raw.githubusercontent.com/opencv/opencv_zoo/{REVISION}/models/{source}'
        with urllib.request.urlopen(pointer_url,timeout=60) as r: pointer=r.read().decode()
        expected=next(line.split(':',1)[1] for line in pointer.splitlines() if line.startswith('oid sha256:'))
        target=ROOT/name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==expected:
            report(f'{name}: verified');continue
        report(f'Downloading {name}…')
        url=f'https://media.githubusercontent.com/media/opencv/opencv_zoo/{REVISION}/models/{source}'
        temporary=target.with_suffix('.part')
        try:
            with urllib.request.urlopen(url,timeout=120) as r,temporary.open('wb') as out:
                while chunk:=r.read(1024*1024):out.write(chunk)
            if hashlib.sha256(temporary.read_bytes()).hexdigest()!=expected:raise ValueError(f'Checksum mismatch for {name}')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        license_url=f'https://raw.githubusercontent.com/opencv/opencv_zoo/{REVISION}/models/{source.split("/")[0]}/LICENSE'
        with urllib.request.urlopen(license_url,timeout=60) as r:(ROOT/f'{name}.LICENSE').write_bytes(r.read())
        report(f'{name}: ready')
if __name__=='__main__':install()
