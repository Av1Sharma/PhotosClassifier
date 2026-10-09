from pathlib import Path
import hashlib, json, sqlite3, shutil, re
from PIL import Image, ImageOps
from .models import ROOT
EXTENSIONS={'.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff','.heic','.heif'}
def fingerprint(path):
    s=path.stat();return f'{s.st_size}:{s.st_mtime_ns}'
def images(folder):
    return sorted(p for p in folder.rglob('*') if p.is_file() and not p.is_symlink() and p.suffix.lower() in EXTENSIONS)
def read_image(path,max_size=1600):
    import cv2, numpy as np
    if path.suffix.lower() in {'.heic','.heif'}:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    with Image.open(path) as image:
        image=ImageOps.exif_transpose(image).convert('RGB');image.thumbnail((max_size,max_size))
        return cv2.cvtColor(np.array(image),cv2.COLOR_RGB2BGR)
class Recognizer:
    def __init__(self):
        import cv2
        if not all((ROOT/n).exists() for n in ('yunet.onnx','sface.onnx')):raise RuntimeError('Install models first: python -m photoclassifier.models')
        self.detector=cv2.FaceDetectorYN.create(str(ROOT/'yunet.onnx'),'',(320,320),0.85,0.3,5000)
        self.recognizer=cv2.FaceRecognizerSF.create(str(ROOT/'sface.onnx'),'')
    def faces(self,path):
        image=read_image(path);self.detector.setInputSize((image.shape[1],image.shape[0]));_,faces=self.detector.detect(image)
        if faces is None:return []
        return [(self.recognizer.feature(self.recognizer.alignCrop(image,f)).flatten(),[float(v) for v in f[:4]],image.shape[:2]) for f in faces]

def match(feature,profiles,threshold=.45,margin=.05):
    """Return best sufficiently separated identity, with similarity (not probability)."""
    import numpy as np
    norm=np.linalg.norm(feature)
    if not norm:return None
    scores=sorted(((max(float(np.dot(feature,v)/(norm*np.linalg.norm(v))) for v in vectors),name) for name,vectors in profiles.items()),reverse=True)
    if not scores or scores[0][0]<threshold:return None
    ambiguous=len(scores)>1 and scores[0][0]-scores[1][0]<margin
    return scores[0][1],scores[0][0],ambiguous

def connect(path):
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row
    db.executescript('''CREATE TABLE IF NOT EXISTS scans (id TEXT PRIMARY KEY,source TEXT,refs TEXT,threshold REAL);
    CREATE TABLE IF NOT EXISTS files (scan TEXT,path TEXT,fingerprint TEXT,faces INTEGER,error TEXT,PRIMARY KEY(scan,path));
    CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY,scan TEXT,path TEXT,person TEXT,score REAL,ambiguous INTEGER,box TEXT,status TEXT DEFAULT 'pending');
    CREATE INDEX IF NOT EXISTS match_scan ON matches(scan);
    ''');return db

def scan(source,refs,db_path,threshold=.45,stop=None,report=lambda *x:None,recognizer=None):
    source,refs=Path(source).resolve(),Path(refs).resolve()
    if not source.is_dir() or not refs.is_dir():raise ValueError('Choose existing library and reference folders.')
    if source==refs or source in refs.parents or refs in source.parents:raise ValueError('Keep references and library in separate, non-nested folders.')
    if not .1<=threshold<=.99:raise ValueError('Similarity threshold must be 0.10–0.99.')
    engine=recognizer or Recognizer();profiles={};signature=[]
    for person in sorted(refs.iterdir()):
        if not person.is_dir() or person.is_symlink() or person.name.startswith('.'):continue
        vectors=[]
        for path in images(person):
            if stop and stop.is_set():return None
            signature.append((str(path),fingerprint(path)))
            try:
                faces=engine.faces(path)
                if len(faces)!=1:report('log',f'Skipped reference {person.name}/{path.name}: expected exactly one face, found {len(faces)}.');continue
                vectors.append(faces[0][0])
            except Exception as exc:report('log',f'Skipped reference {path.name}: {exc}')
        if vectors:profiles[person.name]=vectors
    if not profiles:raise ValueError('No usable references. Use one folder per person, with clear, single-face portraits.')
    key=hashlib.sha256(json.dumps([str(source),signature,threshold,'yunet-sface-v2-1600-margin05']).encode()).hexdigest()
    db=connect(db_path)
    try:
        db.execute('INSERT OR IGNORE INTO scans VALUES (?,?,?,?)',(key,str(source),str(refs),threshold));db.commit()
        paths=images(source);report('start',(key,len(paths),len(profiles)))
        seen=set()
        for index,path in enumerate(paths):
            if stop and stop.is_set():report('log','Scan paused. Run again to resume unchanged files.');break
            rel=str(path.relative_to(source));seen.add(rel);stamp=fingerprint(path)
            old=db.execute('SELECT fingerprint,error FROM files WHERE scan=? AND path=?',(key,rel)).fetchone()
            if old and old['fingerprint']==stamp and not old['error']:
                report('progress',(index+1,len(paths),rel+' · cached'));continue
            found=[];error='';face_count=0
            try:
                faces=engine.faces(path);face_count=len(faces)
                for feature,box,shape in faces:
                    m=match(feature,profiles,threshold)
                    if m:found.append((*m,json.dumps({'rect':box,'shape':shape})))
                if fingerprint(path)!=stamp:raise ValueError('File changed while scanning; retry.')
            except Exception as exc:error=str(exc);found=[];report('log',f'{rel}: {error}')
            with db:
                db.execute('DELETE FROM matches WHERE scan=? AND path=?',(key,rel))
                for name,score,ambiguous,box in found:
                    db.execute('INSERT INTO matches(scan,path,person,score,ambiguous,box) VALUES(?,?,?,?,?,?)',(key,rel,name,score,int(ambiguous),box))
                db.execute('INSERT OR REPLACE INTO files VALUES(?,?,?,?,?)',(key,rel,stamp,face_count,error))
            report('progress',(index+1,len(paths),rel))
        else:
            # Remove stale candidates only after a complete scan, never after pause.
            for row in db.execute('SELECT path FROM files WHERE scan=?',(key,)).fetchall():
                if row['path'] not in seen:
                    db.execute('DELETE FROM matches WHERE scan=? AND path=?',(key,row['path']));db.execute('DELETE FROM files WHERE scan=? AND path=?',(key,row['path']))
            db.commit()
        return key
    finally:db.close()

def export_approved(db_path,scan_id,destination):
    dest=Path(destination).resolve();db=connect(db_path)
    try:
        record=db.execute('SELECT * FROM scans WHERE id=?',(scan_id,)).fetchone()
        if not record:raise ValueError('No scan selected.')
        source=Path(record['source']).resolve();refs=Path(record['refs']).resolve()
        if any(dest==p or dest in p.parents or p in dest.parents for p in (source,refs)):raise ValueError('Export to a separate folder outside the source library and references.')
        rows=db.execute("SELECT DISTINCT m.path,m.person,f.fingerprint FROM matches m JOIN files f ON m.scan=f.scan AND m.path=f.path WHERE m.scan=? AND m.status='approved'",(scan_id,)).fetchall()
        copied=0;skipped=0
        for row in rows:
            path=(source/row['path']).resolve()
            if source not in path.parents or not path.is_file() or fingerprint(path)!=row['fingerprint']:raise ValueError(f'Source changed or missing: {row["path"]}. Rescan before exporting.')
            name=re.sub(r'[^\w .-]','_',row['person']).strip('. ') or 'Person'
            # Stable suffix avoids two names sanitizing into one output directory.
            person=name+'-'+hashlib.sha256(row['person'].encode()).hexdigest()[:6]
            target=(dest/person/row['path']).resolve()
            if dest not in target.parents:raise ValueError('Unsafe export path.')
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():
                if hashlib.sha256(target.read_bytes()).digest()==hashlib.sha256(path.read_bytes()).digest():skipped+=1;continue
                raise FileExistsError(f'Existing file differs: {target}. Choose another export folder.')
            # Exclusive creation ensures a file is never silently overwritten.
            with target.open('xb') as out,path.open('rb') as inp:shutil.copyfileobj(inp,out)
            shutil.copystat(path,target);copied+=1
        return copied,skipped
    finally:db.close()
