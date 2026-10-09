import json, queue, threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageOps, ImageTk, ImageDraw
from .engine import connect, scan, export_approved
from .models import install

class App:
    def __init__(self,root):
        self.root=root;root.title('PhotosClassifier');root.geometry('1180x800');root.minsize(980,760);root.columnconfigure(0,weight=1);root.rowconfigure(1,weight=1)
        self.events=queue.Queue();self.stop=threading.Event();self.busy=False;self.scan_id=None;self.source=tk.StringVar();self.refs=tk.StringVar();self.threshold=tk.DoubleVar(value=.45);self.filter=tk.StringVar(value='pending');self.status=tk.StringVar(value='Choose two folders to begin.');self.rows={}
        state=Path.home()/'.photosclassifier';state.mkdir(exist_ok=True);self.db_path=state/'catalog.sqlite3'
        root.configure(bg='#fafbf8');style=ttk.Style();style.theme_use('clam');style.configure('.',font=('Helvetica',12),background='#fafbf8',foreground='#273c34');style.configure('TButton',padding=(10,6));style.configure('Accent.TButton',background='#315f4d',foreground='white');style.map('Accent.TButton',background=[('active','#234837')]);style.configure('Treeview',rowheight=32,background='#fffef9',fieldbackground='#fffef9');style.configure('Treeview.Heading',font=('Helvetica',11,'bold'),padding=8);style.configure('Title.TLabel',font=('Helvetica',22));style.configure('Muted.TLabel',foreground='#63746a',font=('Helvetica',11));style.configure('TEntry',padding=7)
        head=ttk.Frame(root,padding=(32,28));head.grid(row=0,column=0,sticky='ew');ttk.Label(head,text='PhotosClassifier',style='Title.TLabel').pack(side='left');ttk.Button(head,text='Help',command=self.help).pack(side='right')
        body=ttk.Panedwindow(root,orient='horizontal');body.grid(row=1,column=0,sticky='nsew',padx=32)
        left=ttk.Frame(body,padding=(0,12,32,16));body.add(left,weight=1)
        ttk.Label(left,text='Folders',font=('Helvetica',14)).pack(anchor='w',pady=(0,24))
        for title,var,button in [('People',self.refs,'Browse…'),('Photos',self.source,'Browse…')]:
            ttk.Label(left,text=title,font=('Helvetica',12)).pack(anchor='w',pady=(8,5));ttk.Entry(left,textvariable=var,width=31).pack(fill='x');ttk.Button(left,text=button,command=lambda v=var:self.choose(v)).pack(fill='x',pady=(8,24))
        ttk.Label(left,text='One folder per person.',style='Muted.TLabel',wraplength=245,justify='left').pack(anchor='w',pady=(0,10))
        ttk.Label(left,text='Match threshold',font=('Helvetica',12)).pack(anchor='w');ttk.Spinbox(left,from_=.10,to=.99,increment=.01,textvariable=self.threshold,width=9).pack(anchor='w',pady=8)
        ttk.Frame(left,height=20).pack()
        self.scan_button=ttk.Button(left,text='Scan',style='Accent.TButton',command=self.start_scan);self.scan_button.pack(fill='x',pady=5)
        self.pause_button=ttk.Button(left,text='Pause',command=self.pause,state='disabled');self.pause_button.pack(fill='x',pady=5)
        
        ttk.Button(left,text='Previous scans',command=self.previous).pack(fill='x',pady=5)
        ttk.Separator(left).pack(fill='x',pady=9)
        ttk.Label(left,text='Local processing. Originals kept.',style='Muted.TLabel',wraplength=245,justify='left').pack(anchor='w')
        right=ttk.Frame(body,padding=(8,8,0,8));body.add(right,weight=4)
        toolbar=ttk.Frame(right);toolbar.pack(fill='x');ttk.Label(toolbar,text='Matches',style='Muted.TLabel').pack(side='left');box=ttk.Combobox(toolbar,textvariable=self.filter,values=['pending','approved','rejected','all'],state='readonly',width=11);box.pack(side='right');box.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        self.summary=ttk.Label(right,text='No scan selected.',style='Muted.TLabel');self.summary.pack(anchor='w',pady=10)
        self.tree=ttk.Treeview(right,columns=('person','photo','score','status'),show='headings',height=5,selectmode='browse');self.tree.pack(fill='both',expand=True)
        for col,label,width in [('person','Person',115),('photo','Photo',220),('score','Similarity',90),('status','Review',100)]:self.tree.heading(col,text=label);self.tree.column(col,width=width,minwidth=70)
        self.tree.bind('<<TreeviewSelect>>',self.preview)
        self.preview_label=tk.Label(right,text='Select a photo',bg='#e3e8df',fg='#566e5c',height=9,font=('Helvetica',12));self.preview_label.pack(fill='both',expand=True,pady=12)
        self.detail=ttk.Label(right,text='',style='Muted.TLabel',wraplength=690);self.detail.pack(anchor='w')
        actions=ttk.Frame(right);actions.pack(fill='x',pady=(10,0))
        ttk.Button(actions,text='Approve',style='Accent.TButton',command=lambda:self.review('approved')).pack(side='left',padx=(0,6));ttk.Button(actions,text='Reject',command=lambda:self.review('rejected')).pack(side='left',padx=6);ttk.Button(actions,text='Reset',command=lambda:self.review('pending')).pack(side='left',padx=6);ttk.Button(actions,text='Export…',command=self.export).pack(side='right')
        bottom=ttk.Frame(root,padding=(24,14));bottom.grid(row=2,column=0,sticky='ew');self.progress=ttk.Progressbar(bottom,mode='determinate');self.progress.pack(fill='x',pady=(0,8));ttk.Label(bottom,textvariable=self.status,style='Muted.TLabel',wraplength=1100).pack(anchor='w')
        self.log=tk.Text(root,height=3,bg='#edf0e8',fg='#4a6050',font=('Menlo',10),relief='flat',state='disabled');self.log.grid(row=3,column=0,sticky='ew',padx=32,pady=(0,16));self.log.grid_remove()
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(100,self.poll)
    def help(self):
        window=tk.Toplevel(self.root);window.title('Help');window.geometry('440x420')
        frame=ttk.Frame(window,padding=28);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Before you scan',font=('Helvetica',18)).pack(anchor='w',pady=(0,20))
        ttk.Label(frame,text='People: one folder per person, with clear single-face portraits.\n\nPhotos: a separate library of JPEG, PNG, WebP, TIFF, BMP, or HEIC/HEIF files.\n\nA higher threshold gives fewer matches. Scores are similarities, not probabilities. Review each match before exporting.\n\nExport copies approved photos to a separate folder. Originals stay where they are.',wraplength=380,justify='left').pack(anchor='w')
        ttk.Button(frame,text='Install / verify models',command=self.models).pack(anchor='w',pady=(24,8))
        ttk.Button(frame,text='Show log',command=lambda:(self.log.grid(),window.destroy())).pack(anchor='w')
    def choose(self,var):
        if self.busy:return
        path=filedialog.askdirectory()
        if path:var.set(path)
    def launch(self,fn):
        if self.busy:return
        self.busy=True;self.scan_button.configure(state='disabled')
        def work():
            try:fn()
            except Exception as exc:self.events.put(('error',str(exc)))
            finally:self.events.put(('done',None))
        threading.Thread(target=work,daemon=True).start()
    def models(self):
        if self.busy:return
        self.status.set('Verifying model downloads…')
        self.launch(lambda:install(lambda s:self.events.put(('log',s))))
    def start_scan(self):
        if self.busy:return
        try:threshold=self.threshold.get()
        except tk.TclError:messagebox.showerror('Invalid threshold','Enter a number from 0.10 to 0.99.');return
        source,refs=self.source.get(),self.refs.get()
        if not source or not refs:messagebox.showerror('Choose folders','Select your library and reference portraits first.');return
        self.stop.clear();self.pause_button.configure(state='normal');self.status.set('Learning reference portraits…')
        def work():
            key=scan(source,refs,self.db_path,threshold,self.stop,lambda *args:self.events.put(args))
            self.events.put(('scan_complete',key))
        self.launch(work)
    def pause(self):self.stop.set();self.status.set('Pausing after the current image…')
    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='log':self.log.configure(state='normal');self.log.insert('end',str(value)+'\n');self.log.see('end');self.log.configure(state='disabled')
                elif kind=='start':self.scan_id=value[0];self.progress.configure(maximum=max(1,value[1]),value=0);self.status.set(f'{value[1]} photos · {value[2]} people learned')
                elif kind=='progress':self.progress.configure(value=value[0]);self.status.set(f'{value[0]} / {value[1]} · {value[2]}')
                elif kind=='scan_complete':
                    if value:self.scan_id=value
                    self.refresh();self.status.set('Paused. Resume anytime.' if self.stop.is_set() else 'Scan complete.')
                elif kind=='exported':self.status.set(f'Export complete: {value[0]} copied, {value[1]} already present. Originals unchanged.')
                elif kind=='error':self.status.set(value);messagebox.showerror('PhotosClassifier',value)
                elif kind=='done':self.busy=False;self.scan_button.configure(state='normal');self.pause_button.configure(state='disabled')
        except queue.Empty:pass
        self.root.after(100,self.poll)
    def refresh(self):
        self.tree.delete(*self.tree.get_children());self.rows={};self.preview_label.configure(image='',text='Select a photo');self.detail.configure(text='')
        if not self.scan_id:return
        db=connect(self.db_path)
        try:
            args=[self.scan_id];query='SELECT * FROM matches WHERE scan=?'
            if self.filter.get()!='all':query+=' AND status=?';args.append(self.filter.get())
            query+=' ORDER BY person,score DESC'
            for row in db.execute(query,args):
                key=str(row['id']);self.rows[key]=dict(row);self.tree.insert('', 'end',iid=key,values=(row['person'],row['path'],f'{row["score"]:.3f}'+(' ?' if row['ambiguous'] else ''),row['status']))
            total=db.execute('SELECT COUNT(*) FROM files WHERE scan=?',(self.scan_id,)).fetchone()[0];errors=db.execute("SELECT COUNT(*) FROM files WHERE scan=? AND error!=''",(self.scan_id,)).fetchone()[0];approved=db.execute("SELECT COUNT(*) FROM matches WHERE scan=? AND status='approved'",(self.scan_id,)).fetchone()[0]
            self.summary.configure(text=f'{total} scanned · {len(self.rows)} {self.filter.get()} candidates · {approved} approved · {errors} file errors')
        finally:db.close()
    def preview(self,event=None):
        selected=self.tree.selection()
        if not selected:return
        row=self.rows[selected[0]];db=connect(self.db_path)
        try:record=db.execute('SELECT source FROM scans WHERE id=?',(self.scan_id,)).fetchone()
        finally:db.close()
        try:
            with Image.open(Path(record['source'])/row['path']) as im:image=ImageOps.exif_transpose(im).convert('RGB')
            box=json.loads(row['box']);h,w=box['shape'];x,y,bw,bh=box['rect'];draw=ImageDraw.Draw(image);sx,sy=image.width/w,image.height/h
            draw.rectangle((x*sx,y*sy,(x+bw)*sx,(y+bh)*sy),outline='#9bef8b',width=max(3,image.width//180))
            image.thumbnail((max(300,self.preview_label.winfo_width()-20),265));self.preview_image=ImageTk.PhotoImage(image);self.preview_label.configure(image=self.preview_image,text='',height=275)
            self.detail.configure(text=f'{row["person"]} · cosine similarity {row["score"]:.3f}'+(' · Similar match to another person.' if row['ambiguous'] else '')+'\n'+row['path'])
        except Exception as exc:self.preview_label.configure(image='',text=f'Cannot preview: {exc}')
    def review(self,status):
        if self.busy:return
        selected=self.tree.selection()
        if not selected:return
        keys=list(self.rows);index=keys.index(selected[0]);db=connect(self.db_path)
        try:
            with db:db.execute('UPDATE matches SET status=? WHERE id=?',(status,int(selected[0])))
        finally:db.close()
        self.refresh();children=self.tree.get_children()
        if children:self.tree.selection_set(children[min(index,len(children)-1)]);self.tree.see(children[min(index,len(children)-1)])
    def previous(self):
        if self.busy:return
        db=connect(self.db_path)
        try:rows=db.execute('SELECT * FROM scans ORDER BY rowid DESC').fetchall()
        finally:db.close()
        if not rows:messagebox.showinfo('Previous scans','No saved scans yet.');return
        window=tk.Toplevel(self.root);window.title('Choose a saved scan');window.geometry('740x320');listing=tk.Listbox(window,font=('Helvetica',12));listing.pack(fill='both',expand=True,padx=16,pady=16)
        for row in rows:listing.insert('end',f'{row["source"]} · threshold {row["threshold"]}')
        def choose():
            if not listing.curselection():return
            row=rows[listing.curselection()[0]];self.scan_id=row['id'];self.source.set(row['source']);self.refs.set(row['refs']);self.threshold.set(row['threshold']);window.destroy();self.refresh()
        ttk.Button(window,text='Open scan',command=choose).pack(pady=10)
    def export(self):
        if self.busy or not self.scan_id:return
        folder=filedialog.askdirectory(title='Export approved photos to a separate folder')
        if folder:
            key=self.scan_id;self.status.set('Copying approved photos…');self.launch(lambda:self.events.put(('exported',export_approved(self.db_path,key,folder))))
    def close(self):
        if self.busy:self.stop.set();self.status.set('Please wait for the current operation to finish before closing.');return
        self.root.destroy()
def main():
    root=tk.Tk();App(root);root.mainloop()
