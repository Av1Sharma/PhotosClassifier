import unittest,tempfile,threading
from pathlib import Path
import numpy as np
from PIL import Image
from photoclassifier.engine import scan,connect,match,export_approved,Recognizer
class FakeRecognizer:
    def __init__(self):self.calls=0
    def faces(self,path):
        self.calls+=1
        if path.name=='broken.jpg':raise ValueError('Corrupt image')
        if path.name=='empty.jpg':return []
        return [(np.array([1.,0.,0.]),[1,1,5,5],(20,20))]
class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.source=self.root/'library';self.refs=self.root/'references';self.source.mkdir();(self.refs/'Person').mkdir(parents=True);self.db=self.root/'catalog.sqlite3';self.engine=FakeRecognizer()
        for p in [self.refs/'Person'/'portrait.jpg',self.source/'one'/'same.jpg',self.source/'two'/'same.jpg',self.source/'empty.jpg']:
            p.parent.mkdir(exist_ok=True);Image.new('RGB',(20,20),'white').save(p)
    def tearDown(self):self.temp.cleanup()
    def test_match_threshold_and_ambiguity(self):
        a=np.array([1.,0.]);b=np.array([.999,.01])
        self.assertTrue(match(a,{'A':[a],'B':[b]})[2]);self.assertIsNone(match(np.array([0.,1.]),{'A':[a]}));self.assertEqual(match(a,{'A':[a]})[0],'A')
    def test_resume_and_export_preserve_nested_names(self):
        key=scan(self.source,self.refs,self.db,recognizer=self.engine);calls=self.engine.calls
        scan(self.source,self.refs,self.db,recognizer=self.engine);self.assertEqual(self.engine.calls,calls+1)
        with connect(self.db) as db:db.execute("UPDATE matches SET status='approved'")
        out=self.root/'export';self.assertEqual(export_approved(self.db,key,out),(2,0));self.assertEqual(export_approved(self.db,key,out),(0,2));self.assertEqual(len(list(out.rglob('same.jpg'))),2);self.assertEqual(len(list(self.source.rglob('same.jpg'))),2)
        with self.assertRaises(ValueError):export_approved(self.db,key,self.source/'output')
        p=self.source/'one'/'same.jpg';p.write_bytes(b'changed')
        with self.assertRaises(ValueError):export_approved(self.db,key,out)
    def test_changed_and_removed_files_invalidate_review(self):
        key=scan(self.source,self.refs,self.db,recognizer=self.engine)
        with connect(self.db) as db:db.execute("UPDATE matches SET status='approved'")
        (self.source/'one'/'same.jpg').write_bytes(b'changed');(self.source/'two'/'same.jpg').unlink()
        scan(self.source,self.refs,self.db,recognizer=self.engine)
        with connect(self.db) as db:
            rows=db.execute('SELECT * FROM matches').fetchall();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['status'],'pending')
    def test_corruption_and_pause(self):
        (self.source/'broken.jpg').write_bytes(b'not an image');key=scan(self.source,self.refs,self.db,recognizer=self.engine)
        with connect(self.db) as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM files WHERE error!=''").fetchone()[0],1)
        stop=threading.Event();stop.set();self.assertIsNone(scan(self.source,self.refs,self.db,stop=stop,recognizer=self.engine))
    def test_no_usable_references(self):
        (self.refs/'Person'/'portrait.jpg').rename(self.refs/'Person'/'empty.jpg')
        with self.assertRaises(ValueError):scan(self.source,self.refs,self.db,recognizer=self.engine)
    def test_export_does_not_overwrite(self):
        key=scan(self.source,self.refs,self.db,recognizer=self.engine)
        with connect(self.db) as db:db.execute("UPDATE matches SET status='approved'")
        out=self.root/'export';export_approved(self.db,key,out);existing=next(out.rglob('same.jpg'));existing.write_bytes(b'keep me')
        with self.assertRaises(FileExistsError):export_approved(self.db,key,out)
        self.assertEqual(existing.read_bytes(),b'keep me')
if __name__=='__main__':unittest.main()
