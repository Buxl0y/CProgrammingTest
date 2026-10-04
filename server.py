import os,sqlite3,secrets,hashlib,hmac,json,tempfile,subprocess
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from http import cookies
BASE=Path(__file__).parent; DB=BASE/"data.db"; WEB=BASE/"index.html"; SESS={}
def db():
 DB.parent.mkdir(exist_ok=True); c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
 c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password TEXT,role TEXT)")
 c.execute("CREATE TABLE IF NOT EXISTS q(id INTEGER PRIMARY KEY,title TEXT,body TEXT,input TEXT,output TEXT,sample_in TEXT,sample_out TEXT,score INTEGER)")
 c.execute("CREATE TABLE IF NOT EXISTS tc(id INTEGER PRIMARY KEY,qid INTEGER,kind TEXT,input TEXT,expected TEXT,weight REAL)")
 c.execute("CREATE TABLE IF NOT EXISTS sub(id INTEGER PRIMARY KEY,user_id INTEGER,qid INTEGER,code TEXT,status TEXT,score REAL,passed INTEGER,total INTEGER,error TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)")
 if not c.execute("SELECT 1 FROM users").fetchone():
  def pw(x): return hashlib.sha256(x.encode()).hexdigest()
  c.executemany("INSERT INTO users(username,password,role) VALUES(?,?,?)",[("student",pw("student123"),"student"),("admin",pw("admin123"),"admin")])
  qs=[("ผลรวมสองจำนวน","รับ A และ B แล้วแสดงผลรวม","A B","ผลรวม","5 10","15"),("คู่หรือคี่","รับ N แล้วพิมพ์ EVEN หรือ ODD","N","EVEN/ODD","8","EVEN"),("ค่าสูงสุด","รับ A B C แล้วแสดงค่ามากที่สุด","A B C","ค่ามากที่สุด","4 12 7","12"),("ค่าเฉลี่ย","รับคะแนน 5 ค่า แสดงค่าเฉลี่ย 2 ตำแหน่ง","5 คะแนน","ค่าเฉลี่ย","80 90 75 85 70","80.00"),("นับเลขบวก","รับ N และสมาชิก N ค่า นับค่าที่มากกว่า 0","N และ array","จำนวน","5\n-1 3 7 0 -2","2"),("กลับสตริง","รับคำหนึ่งคำแล้วแสดงย้อนกลับ","string","reverse","hello","olleh"),("แฟกทอเรียล","รับ N แล้วหาค่า N!","N","N!","5","120"),("ผลรวมอาร์เรย์","รับ N และ array แล้วหาผลรวม","N และ array","sum","4\n1 2 3 4","10"),("จำนวนเฉพาะ","ตรวจว่า N เป็นจำนวนเฉพาะหรือไม่","N","YES/NO","17","YES"),("เรียงลำดับ","รับ N และตัวเลข แล้วเรียงจากน้อยไปมาก","N และ array","sorted","5\n4 1 3 2 5","1 2 3 4 5")]
  for i,x in enumerate(qs,1):
   c.execute("INSERT INTO q VALUES(?,?,?,?,?,?,?,?)",(i,*x,10))
   c.execute("INSERT INTO tc(qid,kind,input,expected,weight) VALUES(?,?,?,?,1)",(i,"PUBLIC",x[4],x[5]))
   c.execute("INSERT INTO tc(qid,kind,input,expected,weight) VALUES(?,?,?,?,1)",(i,"HIDDEN",x[4]+"\n",x[5]+"\n"))
  c.commit()
 return c
def send(h,obj,code=200):
 b=json.dumps(obj,ensure_ascii=False).encode(); h.send_response(code); h.send_header("Content-Type","application/json; charset=utf-8"); h.send_header("Content-Length",str(len(b))); h.end_headers(); h.wfile.write(b)
class H(BaseHTTPRequestHandler):
 def read(self):
  n=int(self.headers.get("Content-Length",0)); return json.loads(self.rfile.read(n) or b"{}")
 def user(self):
  s=self.headers.get("Cookie",""); c=cookies.SimpleCookie(s); t=c.get("sid"); return SESS.get(t.value) if t else None
 def do_GET(self):
  if self.path=="/" or self.path=="/index.html":
   b=WEB.read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b); return
  u=self.user(); c=db()
  if self.path=="/api/me": return send(self,{"user":u})
  if not u: return send(self,{"error":"login"},401)
  if self.path=="/api/questions":
   return send(self,[dict(x) for x in c.execute("SELECT id,title,body,input,output,sample_in,sample_out,score FROM q ORDER BY id")])
  if self.path.startswith("/api/questions/"):
   qid=int(self.path.rsplit("/",1)[1]); q=c.execute("SELECT * FROM q WHERE id=?",(qid,)).fetchone()
   if not q:return send(self,{"error":"not found"},404)
   return send(self,dict(q))
  if self.path.startswith("/api/history/"):
   qid=int(self.path.rsplit("/",1)[1]); return send(self,[dict(x) for x in c.execute("SELECT id,status,score,passed,total,created FROM sub WHERE user_id=? AND qid=? ORDER BY id DESC",(u["id"],qid))])
  if self.path=="/api/admin/submissions" and u["role"]=="admin":
   return send(self,[dict(x) for x in c.execute("SELECT sub.*,users.username FROM sub JOIN users ON users.id=sub.user_id ORDER BY sub.id DESC LIMIT 100")])
  return send(self,{"error":"not found"},404)
 def do_POST(self):
  p=self.path; x=self.read(); c=db()
  if p=="/api/login":
   u=c.execute("SELECT * FROM users WHERE username=?",(x.get("username"),)).fetchone(); ph=hashlib.sha256(x.get("password","").encode()).hexdigest()
   if not u or not hmac.compare_digest(u["password"],ph): return send(self,{"error":"ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"},401)
   sid=secrets.token_urlsafe(32); SESS[sid]=dict(u); self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Set-Cookie",f"sid={sid}; HttpOnly; SameSite=Lax; Path=/"); self.end_headers(); self.wfile.write(json.dumps({"user":dict(u)}).encode()); return
  if p=="/api/logout":
   u=self.user(); s=self.headers.get("Cookie",""); cc=cookies.SimpleCookie(s); t=cc.get("sid"); SESS.pop(t.value,None) if t else None; return send(self,{"ok":1})
  u=self.user()
  if not u:return send(self,{"error":"login"},401)
  if p=="/api/submit":
   qid=int(x["qid"]); code=x["code"]; q=c.execute("SELECT * FROM q WHERE id=?",(qid,)).fetchone(); tests=c.execute("SELECT * FROM tc WHERE qid=? ORDER BY id",(qid,)).fetchall()
   with tempfile.TemporaryDirectory() as d:
    src=Path(d)/"main.c"; exe=Path(d)/"main"; src.write_text(code)
    try:
     cp=subprocess.run(["gcc",str(src),"-O2","-std=c11","-o",str(exe)],capture_output=True,text=True,timeout=5)
     if cp.returncode: status="COMPILE_ERROR"; score=0; passed=0; err=cp.stderr
     else:
      passed=0; err=""; total=len(tests)
      for t in tests:
       try:
        r=subprocess.run([str(exe)],input=t["input"],capture_output=True,text=True,timeout=2)
        if r.returncode==0 and " ".join(r.stdout.split())==" ".join(t["expected"].split()): passed+=1
       except Exception: pass
      score=round(q["score"]*passed/total,2) if total else 0; status="ACCEPTED" if passed==total else "WRONG_ANSWER"
   c.execute("INSERT INTO sub(user_id,qid,code,status,score,passed,total,error) VALUES(?,?,?,?,?,?,?,?)",(u["id"],qid,code,status,score,passed,len(tests),err)); c.commit()
   return send(self,{"status":status,"score":score,"passed":passed,"total":len(tests),"error":err})
  if p=="/api/admin/question" and u["role"]=="admin":
   qid=c.execute("SELECT COALESCE(MAX(id),0)+1 FROM q").fetchone()[0]; c.execute("INSERT INTO q VALUES(?,?,?,?,?,?,?,?)",(qid,x["title"],x["body"],x.get("input",""),x.get("output",""),x.get("sample_in",""),x.get("sample_out",""),int(x.get("score",10)))); c.commit(); return send(self,{"id":qid})
  return send(self,{"error":"not found"},404)
db().close()
ThreadingHTTPServer((os.getenv("HOST","0.0.0.0"),int(os.getenv("PORT","8000"))),H).serve_forever()
