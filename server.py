import os,sqlite3,secrets,hashlib,hmac,json,tempfile,subprocess,base64,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from http import cookies
BASE=Path(__file__).parent; DB=BASE/"data.db"; WEB=BASE/"index.html"; SESS={}; SESSION_SECRET=os.getenv("SESSION_SECRET","codinglab-demo-secret-change-in-render")
TEST_CASES={
1:[["PUBLIC","5 10","15"],["PUBLIC","0 0","0"],["PUBLIC","-5 12","7"],["PUBLIC","123 456","579"],["PUBLIC","-10 -20","-30"],["HIDDEN","1 999","1000"],["HIDDEN","10000 25000","35000"],["HIDDEN","7 -3","4"],["HIDDEN","-100 250","150"],["HIDDEN","999999 1","1000000"]],
2:[["PUBLIC","0","EVEN"],["PUBLIC","1","ODD"],["PUBLIC","2","EVEN"],["PUBLIC","-1","ODD"],["PUBLIC","-2","EVEN"],["HIDDEN","100","EVEN"],["HIDDEN","101","ODD"],["HIDDEN","999","ODD"],["HIDDEN","1000","EVEN"],["HIDDEN","12345","ODD"]],
3:[["PUBLIC","4 12 7","12"],["PUBLIC","1 2 3","3"],["PUBLIC","-5 -2 -9","-2"],["PUBLIC","5 5 2","5"],["PUBLIC","0 -1 -2","0"],["HIDDEN","100 99 101","101"],["HIDDEN","-100 0 50","50"],["HIDDEN","999 999 999","999"],["HIDDEN","-8 -3 -5","-3"],["HIDDEN","42 7 19","42"]],
4:[["PUBLIC","80 90 75 85 70","80.00"],["PUBLIC","0 0 0 0 0","0.00"],["PUBLIC","100 100 100 100 100","100.00"],["PUBLIC","1 2 3 4 5","3.00"],["PUBLIC","10 20 30 40 50","30.00"],["HIDDEN","55 65 75 85 95","75.00"],["HIDDEN","99 88 77 66 55","77.00"],["HIDDEN","12 15 18 21 24","18.00"],["HIDDEN","1 1 1 2 2","1.40"],["HIDDEN","73 82 91 64 70","76.00"]],
5:[["PUBLIC","5\n-1 3 7 0 -2","2"],["PUBLIC","4\n1 2 3 4","4"],["PUBLIC","5\n-5 -4 -3 -2 -1","0"],["PUBLIC","3\n0 0 1","1"],["PUBLIC","6\n-1 0 2 -3 4 5","3"],["HIDDEN","7\n1 -2 3 -4 5 -6 7","4"],["HIDDEN","4\n10 20 -1 -2","2"],["HIDDEN","8\n-8 -7 0 6 5 4 -3 2","4"],["HIDDEN","1\n99","1"],["HIDDEN","5\n0 -1 0 -2 0","0"]],
6:[["PUBLIC","hello","olleh"],["PUBLIC","a","a"],["PUBLIC","coding","gnidoc"],["PUBLIC","program","margorp"],["PUBLIC","12345","54321"],["HIDDEN","level","level"],["HIDDEN","abcde","edcba"],["HIDDEN","a1b2","2b1a"],["HIDDEN","OpenAI","IAnepO"],["HIDDEN","computer","retupmoc"]],
7:[["PUBLIC","0","1"],["PUBLIC","1","1"],["PUBLIC","2","2"],["PUBLIC","3","6"],["PUBLIC","5","120"],["HIDDEN","6","720"],["HIDDEN","7","5040"],["HIDDEN","8","40320"],["HIDDEN","9","362880"],["HIDDEN","10","3628800"]],
8:[["PUBLIC","4\n1 2 3 4","10"],["PUBLIC","3\n10 20 30","60"],["PUBLIC","5\n1 -2 3 -4 5","3"],["PUBLIC","1\n99","99"],["PUBLIC","6\n0 0 0 0 0 0","0"],["HIDDEN","7\n1 2 3 4 5 6 7","28"],["HIDDEN","5\n10 -10 20 -20 30","30"],["HIDDEN","4\n100 200 300 400","1000"],["HIDDEN","8\n-1 -2 -3 -4 -5 -6 -7 -8","-36"],["HIDDEN","2\n999 1","1000"]],
9:[["PUBLIC","1","NO"],["PUBLIC","2","YES"],["PUBLIC","3","YES"],["PUBLIC","4","NO"],["PUBLIC","17","YES"],["HIDDEN","18","NO"],["HIDDEN","97","YES"],["HIDDEN","100","NO"],["HIDDEN","101","YES"],["HIDDEN","1000","NO"]],
10:[["PUBLIC","5\n4 1 3 2 5","1 2 3 4 5"],["PUBLIC","3\n3 2 1","1 2 3"],["PUBLIC","4\n10 5 8 1","1 5 8 10"],["PUBLIC","1\n99","99"],["PUBLIC","5\n5 5 3 3 1","1 3 3 5 5"],["HIDDEN","6\n0 -1 4 -3 2 1","-3 -1 0 1 2 4"],["HIDDEN","4\n100 20 50 10","10 20 50 100"],["HIDDEN","7\n7 6 5 4 3 2 1","1 2 3 4 5 6 7"],["HIDDEN","5\n-5 -2 -9 -1 -7","-9 -7 -5 -2 -1"],["HIDDEN","8\n1 9 2 8 3 7 4 6","1 2 3 4 6 7 8 9"]]
}

def ensure_test_data(c):
 cols={row["name"] for row in c.execute("PRAGMA table_info(sub)")}
 if "details" not in cols:
  c.execute("ALTER TABLE sub ADD COLUMN details TEXT")
 for qid,cases in TEST_CASES.items():
  if not c.execute("SELECT 1 FROM q WHERE id=?",(qid,)).fetchone():
   continue
  count=c.execute("SELECT COUNT(*) FROM tc WHERE qid=?",(qid,)).fetchone()[0]
  if count!=10:
   c.execute("DELETE FROM tc WHERE qid=?",(qid,))
   c.executemany("INSERT INTO tc(qid,kind,input,expected,weight) VALUES(?,?,?,?,1)",[(qid,k,i,e) for k,i,e in cases])
 c.commit()

def db():
 DB.parent.mkdir(exist_ok=True); c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
 c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password TEXT,role TEXT)")
 c.execute("CREATE TABLE IF NOT EXISTS q(id INTEGER PRIMARY KEY,title TEXT,body TEXT,input TEXT,output TEXT,sample_in TEXT,sample_out TEXT,score INTEGER)")
 c.execute("CREATE TABLE IF NOT EXISTS tc(id INTEGER PRIMARY KEY,qid INTEGER,kind TEXT,input TEXT,expected TEXT,weight REAL)")
 c.execute("CREATE TABLE IF NOT EXISTS sub(id INTEGER PRIMARY KEY,user_id INTEGER,qid INTEGER,code TEXT,status TEXT,score REAL,passed INTEGER,total INTEGER,error TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)")
 c.execute("CREATE TABLE IF NOT EXISTS exam(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,mode TEXT,duration_minutes INTEGER,started_at INTEGER,expires_at INTEGER,finished_at INTEGER,status TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)")
 cols_sub={row["name"] for row in c.execute("PRAGMA table_info(sub)")}
 if "exam_id" not in cols_sub:
  c.execute("ALTER TABLE sub ADD COLUMN exam_id INTEGER")
 if not c.execute("SELECT 1 FROM users").fetchone():
  def pw(x): return hashlib.sha256(x.encode()).hexdigest()
  c.executemany("INSERT INTO users(username,password,role) VALUES(?,?,?)",[("student",pw("student123"),"student"),("admin",pw("admin123"),"admin")])
  qs=[("ผลรวมสองจำนวน","รับ A และ B แล้วแสดงผลรวม","A B","ผลรวม","5 10","15"),("คู่หรือคี่","รับ N แล้วพิมพ์ EVEN หรือ ODD","N","EVEN/ODD","8","EVEN"),("ค่าสูงสุด","รับ A B C แล้วแสดงค่ามากที่สุด","A B C","ค่ามากที่สุด","4 12 7","12"),("ค่าเฉลี่ย","รับคะแนน 5 ค่า แสดงค่าเฉลี่ย 2 ตำแหน่ง","5 คะแนน","ค่าเฉลี่ย","80 90 75 85 70","80.00"),("นับเลขบวก","รับ N และสมาชิก N ค่า นับค่าที่มากกว่า 0","N และ array","จำนวน","5\n-1 3 7 0 -2","2"),("กลับสตริง","รับคำหนึ่งคำแล้วแสดงย้อนกลับ","string","reverse","hello","olleh"),("แฟกทอเรียล","รับ N แล้วหาค่า N!","N","N!","5","120"),("ผลรวมอาร์เรย์","รับ N และ array แล้วหาผลรวม","N และ array","sum","4\n1 2 3 4","10"),("จำนวนเฉพาะ","ตรวจว่า N เป็นจำนวนเฉพาะหรือไม่","N","YES/NO","17","YES"),("เรียงลำดับ","รับ N และตัวเลข แล้วเรียงจากน้อยไปมาก","N และ array","sorted","5\n4 1 3 2 5","1 2 3 4 5")]
  for i,x in enumerate(qs,1):
   c.execute("INSERT INTO q VALUES(?,?,?,?,?,?,?,?)",(i,*x,10))
   c.execute("INSERT INTO tc(qid,kind,input,expected,weight) VALUES(?,?,?,?,1)",(i,"PUBLIC",x[4],x[5]))
   c.execute("INSERT INTO tc(qid,kind,input,expected,weight) VALUES(?,?,?,?,1)",(i,"HIDDEN",x[4]+"\n",x[5]+"\n"))
  c.commit()
 ensure_test_data(c)
 return c
def send(h,obj,code=200):
 b=json.dumps(obj,ensure_ascii=False).encode(); h.send_response(code); h.send_header("Content-Type","application/json; charset=utf-8"); h.send_header("Content-Length",str(len(b))); h.end_headers(); h.wfile.write(b)
class H(BaseHTTPRequestHandler):
 def read(self):
  n=int(self.headers.get("Content-Length",0)); return json.loads(self.rfile.read(n) or b"{}")
 def user(self):
  auth=self.headers.get("Authorization","")
  token=auth[7:].strip() if auth.startswith("Bearer ") else ""
  if not token:
   s=self.headers.get("Cookie",""); cc=cookies.SimpleCookie(s); t=cc.get("sid"); token=t.value if t else ""
  u=SESS.get(token)
  if u:return u
  try:
   raw,sig=token.rsplit(".",1); expected=hmac.new(SESSION_SECRET.encode(),raw.encode(),hashlib.sha256).hexdigest()
   if not hmac.compare_digest(sig,expected): return None
   payload=json.loads(base64.urlsafe_b64decode(raw+"==="))
   if int(payload.get("e",0)) < int(time.time()): return None
   c=db(); row=c.execute("SELECT * FROM users WHERE username=?",(str(payload.get("u","")),)).fetchone()
   return dict(row) if row else None
  except Exception:
   return None
 def make_token(self,username):
  payload=base64.urlsafe_b64encode(json.dumps({"u":username,"e":int(time.time())+86400},separators=(",",":")).encode()).decode().rstrip("=")
  sig=hmac.new(SESSION_SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()
  return payload+"."+sig
 def current_exam(self,c,u):
  row=c.execute("SELECT * FROM exam WHERE user_id=? AND status='ACTIVE' ORDER BY id DESC LIMIT 1",(u["id"],)).fetchone()
  if not row:return None
  if row["expires_at"] and row["expires_at"] <= int(time.time()):
   c.execute("UPDATE exam SET status='TIMEOUT',finished_at=? WHERE id=? AND status='ACTIVE'",(int(time.time()),row["id"])); c.commit(); return None
  return row

 def exam_payload(self,row):
  if not row:return {"active":False}
  now=int(time.time()); remaining=max(0,(row["expires_at"] or now)-now) if row["mode"]=="timed" else 0
  return {"active":True,"exam":dict(row),"remaining_seconds":remaining}

 def do_GET(self):
  if self.path=="/" or self.path=="/index.html":
   b=WEB.read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b); return
  u=self.user(); c=db()
  if self.path=="/api/me": return send(self,{"user":u})
  if self.path=="/api/exam/state":
   return send(self,self.exam_payload(self.current_exam(c,u)))
  if self.path.startswith("/api/summary/"):
   eid=int(self.path.rsplit("/",1)[1]); ex=c.execute("SELECT * FROM exam WHERE id=? AND user_id=?",(eid,u["id"])).fetchone()
   if not ex:return send(self,{"error":"exam not found"},404)
   qs=c.execute("SELECT id,title,score FROM q ORDER BY id").fetchall()
   rows=c.execute("SELECT s.qid,s.score,s.passed,s.total,s.status FROM sub s WHERE s.user_id=? AND s.exam_id=? AND s.id=(SELECT MAX(s2.id) FROM sub s2 WHERE s2.user_id=s.user_id AND s2.exam_id=s.exam_id AND s2.qid=s.qid)",(u["id"],eid)).fetchall()
   by={r["qid"]:dict(r) for r in rows}
   items=[]; total=0; max_total=0; solved=0
   for q in qs:
    x=by.get(q["id"]); val=float(x["score"]) if x else 0
    total+=val; max_total+=float(q["score"] or 10)
    if x: solved+=1
    items.append({"qid":q["id"],"title":q["title"],"max_score":q["score"],"score":val,"passed":x["passed"] if x else 0,"test_total":x["total"] if x else 10,"status":x["status"] if x else "NOT_SUBMITTED"})
   return send(self,{"exam":dict(ex),"total_score":round(total,2),"max_score":round(max_total,2),"solved":solved,"questions":items})
  if not u: return send(self,{"error":"login"},401)
  if self.path=="/api/questions":
   return send(self,[dict(x) for x in c.execute("SELECT id,title,body,input,output,sample_in,sample_out,score FROM q ORDER BY id")])
  if self.path.startswith("/api/questions/"):
   qid=int(self.path.rsplit("/",1)[1]); q=c.execute("SELECT * FROM q WHERE id=?",(qid,)).fetchone()
   if not q:return send(self,{"error":"not found"},404)
   return send(self,dict(q))
  if self.path.startswith("/api/history/"):
   qid=int(self.path.rsplit("/",1)[1]); rows=c.execute("SELECT id,status,score,passed,total,error,created,details FROM sub WHERE user_id=? AND qid=? ORDER BY id DESC",(u["id"],qid)).fetchall()
   out=[]
   for row in rows:
    item=dict(row)
    try:item["details"]=json.loads(item.get("details") or "[]")
    except Exception:item["details"]=[]
    out.append(item)
   return send(self,out)
  if self.path=="/api/submissions":
   rows=c.execute("SELECT sub.id,sub.qid,q.title,sub.status,sub.score,sub.passed,sub.total,sub.created,sub.exam_id,exam.mode,exam.duration_minutes FROM sub JOIN q ON q.id=sub.qid LEFT JOIN exam ON exam.id=sub.exam_id WHERE sub.user_id=? ORDER BY sub.id DESC LIMIT 200",(u["id"],)).fetchall()
   return send(self,[dict(r) for r in rows])
  if self.path=="/api/admin/submissions" and u["role"]=="admin":
   return send(self,[dict(x) for x in c.execute("SELECT sub.*,users.username FROM sub JOIN users ON users.id=sub.user_id ORDER BY sub.id DESC LIMIT 100")])
  return send(self,{"error":"not found"},404)
 def do_POST(self):
  p=self.path; x=self.read(); c=db()
  if p=="/api/login":
   username=str(x.get("username","")).strip().lower(); password=str(x.get("password",""))
   u=c.execute("SELECT * FROM users WHERE lower(username)=?",(username,)).fetchone(); ph=hashlib.sha256(password.encode()).hexdigest()
   if not u or not hmac.compare_digest(u["password"],ph): return send(self,{"error":"ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"},401)
   sid=self.make_token(u["username"]); SESS[sid]=dict(u); b=json.dumps({"user":dict(u),"token":sid},ensure_ascii=False).encode(); self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.send_header("Set-Cookie",f"sid={sid}; HttpOnly; SameSite=Lax; Path=/"); self.end_headers(); self.wfile.write(b); return
  if p=="/api/logout":
   u=self.user(); s=self.headers.get("Cookie",""); cc=cookies.SimpleCookie(s); t=cc.get("sid"); SESS.pop(t.value,None) if t else None; return send(self,{"ok":1})
  u=self.user()
  if not u:return send(self,{"error":"login"},401)
  if p=="/api/exam/start":
   mode=str(x.get("mode","practice"))
   duration=int(x.get("duration_minutes",60) or 60)
   if mode not in ("practice","timed"): return send(self,{"error":"invalid mode"},400)
   if mode=="timed" and duration not in (30,60,90): return send(self,{"error":"เลือกเวลา 30, 60 หรือ 90 นาที"},400)
   now=int(time.time())
   c.execute("UPDATE exam SET status='ABANDONED',finished_at=? WHERE user_id=? AND status='ACTIVE'",(now,u["id"]))
   expires=now+duration*60 if mode=="timed" else 0
   c.execute("INSERT INTO exam(user_id,mode,duration_minutes,started_at,expires_at,status) VALUES(?,?,?,?,?,'ACTIVE')",(u["id"],mode,duration if mode=="timed" else None,now,expires))
   c.commit()
   row=c.execute("SELECT * FROM exam WHERE id=last_insert_rowid()").fetchone()
   return send(self,self.exam_payload(row))
  if p=="/api/exam/finish":
   row=self.current_exam(c,u)
   if not row:return send(self,{"active":False})
   c.execute("UPDATE exam SET status='FINISHED',finished_at=? WHERE id=?",(int(time.time()),row["id"])); c.commit()
   return send(self,{"ok":1,"exam_id":row["id"]})
  if p=="/api/submit":
   exam=self.current_exam(c,u)
   if not exam:return send(self,{"error":"ยังไม่มีรอบสอบที่กำลังทำอยู่ กรุณาเลือกโหมดสอบก่อน"},409)
   qid=int(x["qid"]); code=str(x["code"]); q=c.execute("SELECT * FROM q WHERE id=?",(qid,)).fetchone(); tests=c.execute("SELECT * FROM tc WHERE qid=? ORDER BY id",(qid,)).fetchall()
   if not q:return send(self,{"error":"question not found"},404)
   total=len(tests); passed=0; score=0; err=""; status="RUNTIME_ERROR"; details=[]
   for idx,t in enumerate(tests,1):
    details.append({"no":idx,"kind":t["kind"],"input":t["input"],"expected":t["expected"],"actual":"","status":"NOT_RUN","error":""})
   with tempfile.TemporaryDirectory() as d:
    src=Path(d)/"main.c"; exe=Path(d)/"main"; src.write_text(code,encoding="utf-8")
    cp=None
    try:
     cp=subprocess.run(["gcc",str(src),"-O2","-std=c11","-o",str(exe)],capture_output=True,text=True,timeout=5)
    except subprocess.TimeoutExpired:
     status="COMPILE_TIMEOUT"; err="Compiler timeout (5 seconds)"
    except Exception as e:
     status="COMPILE_ERROR"; err=str(e)
    if cp is not None and cp.returncode != 0:
     status="COMPILE_ERROR"; err=cp.stderr or "Compilation failed"
    elif cp is not None:
     for idx,t in enumerate(tests):
      dcase=details[idx]
      try:
       r=subprocess.run([str(exe)],input=t["input"],capture_output=True,text=True,timeout=2)
       dcase["actual"]=r.stdout
       if r.returncode!=0:
        dcase["status"]="FAILED"; dcase["error"]=r.stderr or ("Program exited with code "+str(r.returncode))
        if not err:err=dcase["error"]
       elif " ".join(r.stdout.split())==" ".join(t["expected"].split()):
        passed += 1; dcase["status"]="PASSED"
       else:
        dcase["status"]="FAILED"
      except subprocess.TimeoutExpired:
       dcase["status"]="FAILED"; dcase["error"]="เกินเวลา 2 วินาที"
       if not err:err=dcase["error"]
      except Exception as e:
       dcase["status"]="FAILED"; dcase["error"]=str(e)
       if not err:err=dcase["error"]
     score=round(q["score"]*passed/total,2) if total else 0
     status="ACCEPTED" if passed==total else "WRONG_ANSWER"
   c.execute("INSERT INTO sub(user_id,qid,code,status,score,passed,total,error,details,exam_id) VALUES(?,?,?,?,?,?,?,?,?,?)",(u["id"],qid,code,status,score,passed,total,err,json.dumps(details,ensure_ascii=False),exam["id"])); c.commit()
   return send(self,{"status":status,"score":score,"passed":passed,"total":total,"error":err,"details":details})
  if p=="/api/admin/question" and u["role"]=="admin":
   qid=c.execute("SELECT COALESCE(MAX(id),0)+1 FROM q").fetchone()[0]; c.execute("INSERT INTO q VALUES(?,?,?,?,?,?,?,?)",(qid,x["title"],x["body"],x.get("input",""),x.get("output",""),x.get("sample_in",""),x.get("sample_out",""),int(x.get("score",10)))); c.commit(); return send(self,{"id":qid})
  return send(self,{"error":"not found"},404)
def main():
    host = os.getenv("HOST", "0.0.0.0")
    try:
        port = int(os.getenv("PORT", "10000"))
    except ValueError:
        port = 10000
    db().close()
    server = ThreadingHTTPServer((host, port), H)
    print(f"CProgrammingTest listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()

