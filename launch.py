"""Desktop entry point; --smoke-test validates a packaged runtime without opening a window."""
import argparse,json
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoke-test',type=Path,metavar='IMAGE')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    if args.smoke_test:
        from photoclassifier.engine import Recognizer
        faces=Recognizer().faces(args.smoke_test)
        if not faces:raise RuntimeError('No face detected in the smoke-test fixture')
        report={'faces':len(faces),'embedding_dimensions':len(faces[0][0]),'status':'passed'}
        if args.report:args.report.write_text(json.dumps(report))
        return
    from photoclassifier.ui import main as ui_main
    ui_main()
if __name__=='__main__':main()
