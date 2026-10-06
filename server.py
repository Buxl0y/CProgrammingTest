import os,sqlite3,secrets,hashlib,hmac,json,tempfile,subprocess,base64,time,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from http import cookies
BASE=Path(__file__).parent; DB=BASE/"data.db"; WEB=BASE/"index.html"; ADMIN_WEB=BASE/"admin.html"; SESS={}; SESSION_SECRET=os.getenv("SESSION_SECRET","codinglab-demo-secret-change-in-render"); DB_INIT_LOCK=threading.Lock(); DB_READY=False
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

SOLUTIONS={
 11: "#include <stdio.h>\n\nint main(void) {\n    double r;\n    scanf(\"%lf\", &r);\n    double area = 3.142 * r * r;\n    printf(\"%.3f\\n\", area);\n    return 0;\n}",
 12: "#include <stdio.h>\n\nint main(void) {\n    int score;\n    scanf(\"%d\", &score);\n    if (score >= 90 && score <= 100) printf(\"A\");\n    else if (score >= 85) printf(\"B+\");\n    else if (score >= 75) printf(\"B\");\n    else if (score >= 70) printf(\"C+\");\n    else if (score >= 60) printf(\"C\");\n    else printf(\"See you next semester\");\n    printf(\"\\n\");\n    return 0;\n}",
 13: "#include <stdio.h>\n\nint main(void) {\n    long long n, sum = 0;\n    scanf(\"%lld\", &n);\n    for (long long i = 1; i <= n; ++i) sum += i;\n    printf(\"%lld\\n\", sum);\n    return 0;\n}",
 14: "#include <stdio.h>\n\nint main(void) {\n    long long w, l, h;\n    scanf(\"%lld %lld %lld\", &w, &l, &h);\n    printf(\"%lld\\n\", w * l * h);\n    return 0;\n}",
 15: "#include <stdio.h>\n\nint main(void) {\n    double liters; int source;\n    scanf(\"%lf%d\", &liters, &source);\n    double factor;\n    if (source == 1) factor = 0.0003;\n    else if (source == 2) factor = 0.0001;\n    else if (source == 3) factor = 0.0004;\n    else { printf(\"Invalid Input\\n\"); return 0; }\n    printf(\"%.4f\\n\", liters * factor);\n    return 0;\n}",
 16: "#include <stdio.h>\n\nint main(void) {\n    int a[3], b[3], A = 0, B = 0;\n    for (int i=0;i<3;i++) scanf(\"%d\",&a[i]);\n    for (int i=0;i<3;i++) scanf(\"%d\",&b[i]);\n    for (int i=0;i<3;i++) { if(a[i]>b[i]) A++; else if(a[i]<b[i]) B++; }\n    printf(\"%d %d\\n\", A, B);\n    return 0;\n}",
 17: "#include <stdio.h>\n\nint main(void) {\n    double f; scanf(\"%lf\",&f);\n    printf(\"%.2f\\n\",(f-32.0)*5.0/9.0);\n    return 0;\n}",
 18: "#include <stdio.h>\n\nint main(void) {\n    int h; scanf(\"%d\",&h);\n    printf(\"%d\\n\",h/168);\n    printf(\"%d\\n\",(h%168)/24);\n    printf(\"%d\\n\",h%24);\n    return 0;\n}",
 19: "#include <stdio.h>\n\nint main(void) {\n    char c; scanf(\" %c\",&c);\n    switch(c){case 'I':printf(\"1\\n\");break;case 'V':printf(\"5\\n\");break;case 'X':printf(\"10\\n\");break;case 'L':printf(\"50\\n\");break;case 'C':printf(\"100\\n\");break;case 'D':printf(\"500\\n\");break;case 'M':printf(\"1000\\n\");break;default:printf(\"Invalid\\n\");}\n    return 0;\n}",
 20: "#include <stdio.h>\n\nint main(void) {\n    int n, even=0, odd=0; long long x;\n    scanf(\"%d\",&n);\n    for(int i=0;i<n;i++){scanf(\"%lld\",&x); if(x%2==0) even++; else odd++;}\n    printf(\"%d\\n\",even*6+odd*5);\n    return 0;\n}",
 21: "#include <stdio.h>\n\nint main(void) {\n    char n[105]; long long k; scanf(\"%104s %lld\",n,&k);\n    int sum=0; for(int i=0;n[i];i++) sum+=n[i]-'0';\n    if(sum==0 || k==0){printf(\"0\\n\"); return 0;}\n    long long v=(sum%9)*(k%9);\n    int ans=(v==0)?9:(int)((v-1)%9+1);\n    printf(\"%d\\n\",ans);\n    return 0;\n}",
 22: "#include <stdio.h>\n\nint main(void) {\n    int n; scanf(\"%d\",&n);\n    const int seq[5]={1,2,3,4,0};\n    for(int i=1;i<=n;i++){\n        for(int j=0;j<i;j++){int v=(i-1-j)%5; printf(\"%d\",seq[v]); if(j+1<i) printf(\" \");}\n        printf(\"\\n\");\n    }\n    return 0;\n}",
 23: "#include <stdio.h>\n\nint main(void) {\n    long long a,b; scanf(\"%lld %lld\",&a,&b); printf(\"%lld\\n\",a+b); return 0;\n}",
 24: "#include <stdio.h>\n\nint main(void) {\n    int a,b,c; scanf(\"%d %d %d\",&a,&b,&c);\n    if(a<=0||b<=0||c<=0||a+b<=c||a+c<=b||b+c<=a) printf(\"0\\n\");\n    else if(a==b&&b==c) printf(\"1\\n\");\n    else if(a==b||b==c||a==c) printf(\"2\\n\");\n    else printf(\"3\\n\");\n    return 0;\n}"
}

def ensure_test_data(c):
 cols={row["name"] for row in c.execute("PRAGMA table_info(sub)")}
 if "details" not in cols:
  c.execute("ALTER TABLE sub ADD COLUMN details TEXT")
 for qid,cases in TEST_CASES.items():
  if not c.execute("SELECT 1 FROM q WHERE id=?",(qid,)).fetchone():
   continue
  c.execute("DELETE FROM tc WHERE qid=?",(qid,))
  c.executemany("INSERT INTO tc(qid,kind,input,expected,weight) VALUES(?,?,?,?,1)",[(qid,k,i,e) for k,i,e in cases])
 c.commit()

def _init_db(c):
 c.execute("PRAGMA journal_mode=WAL")
 c.execute("PRAGMA synchronous=NORMAL")
 c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password TEXT,role TEXT)")
 c.execute("CREATE TABLE IF NOT EXISTS q(id INTEGER PRIMARY KEY,title TEXT,body TEXT,input TEXT,output TEXT,sample_in TEXT,sample_out TEXT,score INTEGER)")
 c.execute("CREATE TABLE IF NOT EXISTS tc(id INTEGER PRIMARY KEY,qid INTEGER,kind TEXT,input TEXT,expected TEXT,weight REAL)")
 c.execute("CREATE TABLE IF NOT EXISTS sub(id INTEGER PRIMARY KEY,user_id INTEGER,qid INTEGER,code TEXT,status TEXT,score REAL,passed INTEGER,total INTEGER,error TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)")
 c.execute("CREATE TABLE IF NOT EXISTS exam(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,mode TEXT,duration_minutes INTEGER,started_at INTEGER,expires_at INTEGER,finished_at INTEGER,status TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)")
 cols_exam={row["name"] for row in c.execute("PRAGMA table_info(exam)")}
 if "participant_name" not in cols_exam:
  c.execute("ALTER TABLE exam ADD COLUMN participant_name TEXT")
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
  extra=[
   (11,"คำนวณพื้นที่วงกลม (CalCirArea)","รับค่ารัศมีของวงกลม แล้วคำนวณพื้นที่ด้วยสูตร A = 3.142 × r² และแสดงผลทศนิยม 3 ตำแหน่ง","จำนวนจริง 1 ค่า คือรัศมี","พื้นที่วงกลม แสดงทศนิยม 3 ตำแหน่ง","2","12.568",[
    ("PUBLIC","2","12.568"),("PUBLIC","10","314.200"),("PUBLIC","24","1809.792"),("PUBLIC","1","3.142"),("PUBLIC","5.5","95.045"),("HIDDEN","0","0.000"),("HIDDEN","3","28.278"),("HIDDEN","7.25","165.151"),("HIDDEN","12.5","490.938"),("HIDDEN","100","31420.000")]),
   (12,"คำนวณเกรด (CalGrade)","รับคะแนนจำนวนเต็มแล้วแสดงเกรดตามช่วงคะแนน: 90-100 A, 85-89 B+, 75-84 B, 70-74 C+, 60-69 C และ 0-59 แสดง See you next semester","จำนวนเต็ม 1 ค่า","เกรดหรือข้อความตามเงื่อนไข","90","A",[
    ("PUBLIC","90","A"),("PUBLIC","59","See you next semester"),("PUBLIC","69","C"),("PUBLIC","85","B+"),("PUBLIC","75","B"),("HIDDEN","100","A"),("HIDDEN","89","B+"),("HIDDEN","84","B"),("HIDDEN","74","C+"),("HIDDEN","60","C")]),
   (13,"คำนวณผลรวมตัวเลข (CalSum)","รับจำนวนเต็ม N แล้วคำนวณผลรวม 1 ถึง N","จำนวนเต็ม 1 ค่า","ผลรวมเป็นจำนวนเต็ม","8","36",[
    ("PUBLIC","8","36"),("PUBLIC","10","55"),("PUBLIC","99","4950"),("PUBLIC","1","1"),("PUBLIC","100","5050"),("HIDDEN","2","3"),("HIDDEN","50","1275"),("HIDDEN","500","125250"),("HIDDEN","1000","500500"),("HIDDEN","7","28")]),
   (14,"คำนวณปริมาตรกล่อง (CalVolume)","รับความกว้าง ความยาว และความสูงของกล่องเป็นจำนวนเต็มบวก 3 ค่า แล้วแสดงปริมาตรของกล่อง","จำนวนเต็ม 3 ค่า คั่นด้วยช่องว่าง","ปริมาตรเป็นจำนวนเต็ม","3 4 2","24",[
    ("PUBLIC","3 4 2","24"),("PUBLIC","1 2 3","6"),("PUBLIC","2 5 10","100"),("PUBLIC","10 10 10","1000"),("PUBLIC","1 1 1","1"),("HIDDEN","4 5 6","120"),("HIDDEN","7 8 9","504"),("HIDDEN","2 3 4","24"),("HIDDEN","10 20 30","6000"),("HIDDEN","5 6 7","210")]),
   (15,"คำนวณคาร์บอนฟุตพริ้นท์ (CarbonFootprint)","รับปริมาณการใช้น้ำเป็นลิตรและแหล่งน้ำ 1-3 โดยตัวคูณคือ 1=0.0003, 2=0.0001, 3=0.0004 กิโลกรัม CO2 ต่อลิตร หากแหล่งน้ำไม่ใช่ 1-3 ให้แสดง Invalid Input","2 บรรทัด: ปริมาณน้ำและรหัสแหล่งน้ำ","ค่าคาร์บอนฟุตพริ้นท์ทศนิยม 4 ตำแหน่ง หรือ Invalid Input","3000\n2","0.3000",[
    ("PUBLIC","3000\n2","0.3000"),("PUBLIC","1250\n1","0.3750"),("PUBLIC","111\n4","Invalid Input"),("PUBLIC","1000\n3","0.4000"),("PUBLIC","500\n2","0.0500"),("HIDDEN","0\n1","0.0000"),("HIDDEN","2500\n1","0.7500"),("HIDDEN","999\n2","0.0999"),("HIDDEN","100\n3","0.0400"),("HIDDEN","100\n9","Invalid Input")]),
   (16,"เรตติ้งข้อสอบ (ExamRating)","รับคะแนนประเมินข้อสอบ 2 ข้อ ข้อละ 3 ด้าน เปรียบเทียบทีละด้าน ถ้าข้อใดได้คะแนนมากกว่าให้เรตติ้งเพิ่ม 1 คะแนน ถ้าเท่ากันไม่มีใครได้เพิ่ม","2 บรรทัด บรรทัดละจำนวนเต็ม 3 ค่า","เรตติ้งของข้อสอบข้อที่ 1 และ 2 คั่นด้วยช่องว่าง","17 28 30\n80 16 15","2 1",[
    ("PUBLIC","17 28 30\n80 16 15","2 1"),("PUBLIC","56 25 37\n56 39 35","1 1"),("PUBLIC","1 2 3\n3 2 1","1 1"),("PUBLIC","100 100 100\n1 1 1","3 0"),("PUBLIC","1 1 1\n100 100 100","0 3"),("HIDDEN","50 50 50\n50 50 50","0 0"),("HIDDEN","90 10 70\n80 20 60","2 1"),("HIDDEN","10 90 30\n20 80 40","1 2"),("HIDDEN","7 8 9\n7 9 8","1 1"),("HIDDEN","99 1 50\n1 99 50","1 1")]),
   (17,"แปลงอุณหภูมิ (FtoC)","รับอุณหภูมิองศาฟาเรนไฮต์ แล้วแปลงเป็นองศาเซลเซียสด้วยสูตร (F - 32) × 5/9 และแสดงทศนิยม 2 ตำแหน่ง","จำนวนจริง 1 ค่า","อุณหภูมิองศาเซลเซียสทศนิยม 2 ตำแหน่ง","32","0.00",[
    ("PUBLIC","32","0.00"),("PUBLIC","101.3","38.50"),("PUBLIC","212","100.00"),("PUBLIC","0","-17.78"),("PUBLIC","-40","-40.00"),("HIDDEN","100","37.78"),("HIDDEN","98.6","37.00"),("HIDDEN","50","10.00"),("HIDDEN","451.4","233.00"),("HIDDEN","77","25.00")]),
   (18,"ชั่วโมงเป็นสัปดาห์ วัน ชั่วโมง (HourDayWeek)","รับจำนวนชั่วโมง 0-9999 แล้วแปลงเป็นจำนวนสัปดาห์ วัน และชั่วโมง โดย 1 วัน=24 ชั่วโมง และ 1 สัปดาห์=7 วัน","จำนวนเต็ม 1 ค่า","แสดง 3 บรรทัด: สัปดาห์ วัน ชั่วโมง","74","0\n3\n2",[
    ("PUBLIC","74","0\n3\n2"),("PUBLIC","400","2\n2\n16"),("PUBLIC","23","0\n0\n23"),("PUBLIC","168","1\n0\n0"),("PUBLIC","24","0\n1\n0"),("HIDDEN","0","0\n0\n0"),("HIDDEN","167","0\n6\n23"),("HIDDEN","169","1\n0\n1"),("HIDDEN","9999","59\n3\n15"),("HIDDEN","48","0\n2\n0")]),
   (19,"แปลงเลขโรมัน (RomanToNum)","รับอักษรโรมัน 1 ตัว ได้แก่ I, V, X, L, C, D หรือ M แล้วแสดงค่าตัวเลข หากเป็นตัวอื่นให้แสดง Invalid","อักขระ 1 ตัว","ค่าตัวเลขหรือ Invalid","I","1",[
    ("PUBLIC","I","1"),("PUBLIC","L","50"),("PUBLIC","m","Invalid"),("PUBLIC","V","5"),("PUBLIC","X","10"),("HIDDEN","C","100"),("HIDDEN","D","500"),("HIDDEN","M","1000"),("HIDDEN","i","Invalid"),("HIDDEN","A","Invalid")]),
   (20,"เลขในดวงใจ (SecretNumber)","รับจำนวน N และจำนวนเต็มบวก N ค่า เลขในดวงใจ = (จำนวนเลขคู่ × 6) + (จำนวนเลขคี่ × 5)","2 บรรทัด: N และตัวเลข N ค่า","เลขในดวงใจ","6\n50 51 32 33 41 37","32",[
    ("PUBLIC","6\n50 51 32 33 41 37","32"),("PUBLIC","5\n54 82 44 13 56","29"),("PUBLIC","10\n57 79 86 90 48 72 25 19 32 59","55"),("PUBLIC","2\n1 2","11"),("PUBLIC","4\n2 4 6 8","24"),("HIDDEN","3\n1 3 5","15"),("HIDDEN","7\n0 2 4 6 8 10 12","42"),("HIDDEN","6\n1 2 3 4 5 6","33"),("HIDDEN","8\n10 11 12 13 14 15 16 17","44"),("HIDDEN","10\n0 1 0 1 0 1 0 1 0 1","55")]),
   (21,"ซุปเปอร์ดิจิต (SuperDigit)","รับตัวเลข n ที่มีไม่เกิน 100 หลักและจำนวนซ้ำ k แล้วหาซุปเปอร์ดิจิตของ n ที่ถูกนำมาต่อกัน k ครั้ง","จำนวนเต็ม 2 ค่า: n และ k","ซุปเปอร์ดิจิตเป็นเลขหลักเดียว","148 3","3",[
    ("PUBLIC","148 3","3"),("PUBLIC","9875 4","8"),("PUBLIC","123 3","9"),("PUBLIC","5 100000","5"),("PUBLIC","99 2","9"),("HIDDEN","1 1","1"),("HIDDEN","10 10","1"),("HIDDEN","999 1","9"),("HIDDEN","12345 2","3"),("HIDDEN","987654321 2","9")]),
   (22,"สร้างค่าสามเหลี่ยมสูง N ชั้น (numberTriangle)","รับ N แล้วพิมพ์สามเหลี่ยม N บรรทัด บรรทัดที่ i มี i ค่า โดยค่าเริ่มต้นแต่ละบรรทัดวน 1,2,3,4,0 และค่าถัดไปลดลงทีละ 1 โดยหลัง 0 วนกลับเป็น 4","จำนวนเต็ม N โดย 1 ≤ N ≤ 30","แสดงสามเหลี่ยม N บรรทัด คั่นค่าด้วยช่องว่าง","4","1\n2 1\n3 2 1\n4 3 2 1",[
    ("PUBLIC","2","1\n2 1"),("PUBLIC","4","1\n2 1\n3 2 1\n4 3 2 1"),("PUBLIC","8","1\n2 1\n3 2 1\n4 3 2 1\n0 4 3 2 1\n1 0 4 3 2 1\n2 1 0 4 3 2 1\n3 2 1 0 4 3 2 1"),("PUBLIC","1","1"),("PUBLIC","5","1\n2 1\n3 2 1\n4 3 2 1\n0 4 3 2 1"),("HIDDEN","3","1\n2 1\n3 2 1"),("HIDDEN","6","1\n2 1\n3 2 1\n4 3 2 1\n0 4 3 2 1\n1 0 4 3 2 1"),("HIDDEN","7","1\n2 1\n3 2 1\n4 3 2 1\n0 4 3 2 1\n1 0 4 3 2 1\n2 1 0 4 3 2 1"),("HIDDEN","9","1\n2 1\n3 2 1\n4 3 2 1\n0 4 3 2 1\n1 0 4 3 2 1\n2 1 0 4 3 2 1\n3 2 1 0 4 3 2 1\n4 3 2 1 0 4 3 2 1"),("HIDDEN","10","1\n2 1\n3 2 1\n4 3 2 1\n0 4 3 2 1\n1 0 4 3 2 1\n2 1 0 4 3 2 1\n3 2 1 0 4 3 2 1\n4 3 2 1 0 4 3 2 1\n0 4 3 2 1 0 4 3 2 1")]),
   (23,"พร้อมบวก (ToSum)","รับจำนวนเต็ม 2 จำนวนแล้วแสดงผลบวกของทั้งสองจำนวน","จำนวนเต็ม 2 ค่า","ผลบวกเป็นจำนวนเต็ม","55 17","72",[
    ("PUBLIC","55 17","72"),("PUBLIC","5 -7","-2"),("PUBLIC","0 0","0"),("PUBLIC","999999999 1","1000000000"),("PUBLIC","-10 20","10"),("HIDDEN","123 456","579"),("HIDDEN","-999999999 999999999","0"),("HIDDEN","100000000 200000000","300000000"),("HIDDEN","7 -3","4"),("HIDDEN","-123 -456","-579")]),
   (24,"ชนิดสามเหลี่ยม (TriTypes)","รับความยาวด้านสามด้าน ตรวจว่าเป็นสามเหลี่ยมหรือไม่ และถ้าเป็นให้จำแนกเป็น 1=ด้านเท่า, 2=หน้าจั่ว, 3=ด้านไม่เท่า ถ้าไม่ใช่ตอบ 0","จำนวนเต็ม 3 ค่า","0, 1, 2 หรือ 3","9 4 2","0",[
    ("PUBLIC","9 4 2","0"),("PUBLIC","9 4 9","2"),("PUBLIC","3 4 2","3"),("PUBLIC","5 5 5","1"),("PUBLIC","3 3 5","2"),("HIDDEN","1 2 3","0"),("HIDDEN","2 2 3","2"),("HIDDEN","6 8 10","3"),("HIDDEN","10 10 1","2"),("HIDDEN","0 1 1","0")])
  ]
  for qid,title,body,inp,out,sin,sout,cases in extra:
   if not c.execute("SELECT 1 FROM q WHERE id=?",(qid,)).fetchone():
    c.execute("INSERT INTO q(id,title,body,input,output,sample_in,sample_out,score) VALUES(?,?,?,?,?,?,?,10)",(qid,title,body,inp,out,sin,sout))
   if c.execute("SELECT COUNT(*) FROM tc WHERE qid=?",(qid,)).fetchone()[0] != len(cases):
    c.execute("DELETE FROM tc WHERE qid=?",(qid,))
    c.executemany("INSERT INTO tc(qid,kind,input,expected,weight) VALUES(?,?,?,?,1)",[(qid,k,i,e) for k,i,e in cases])
 c.execute("DELETE FROM sub WHERE qid BETWEEN 1 AND 10")
 c.execute("DELETE FROM tc WHERE qid BETWEEN 1 AND 10")
 c.execute("DELETE FROM q WHERE id BETWEEN 1 AND 10")
 ensure_test_data(c)
 c.commit()

def db():
 global DB_READY
 DB.parent.mkdir(exist_ok=True)
 c=sqlite3.connect(DB,timeout=30)
 c.row_factory=sqlite3.Row
 c.execute("PRAGMA busy_timeout=30000")
 if not DB_READY:
  with DB_INIT_LOCK:
   if not DB_READY:
    _init_db(c)
    DB_READY=True
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
  if self.path=="/admin" or self.path=="/admin/":
   if not ADMIN_WEB.exists(): return send(self,{"error":"admin page not found"},404)
   b=ADMIN_WEB.read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b); return
  u=self.user(); c=db()
  if self.path=="/api/me":
   if not u:return send(self,{"user":None})
   active=c.execute("SELECT participant_name FROM exam WHERE user_id=? AND status='ACTIVE' ORDER BY id DESC LIMIT 1",(u["id"],)).fetchone()
   user=dict(u)
   if active and active["participant_name"]: user["display_name"]=active["participant_name"]
   return send(self,{"user":user})
  if self.path=="/api/exam/state":
   return send(self,self.exam_payload(self.current_exam(c,u) if u else None))
  if self.path.startswith("/api/summary/"):
   if not u:return send(self,{"error":"login"},401)
   eid=int(self.path.rsplit("/",1)[1]); ex=c.execute("SELECT * FROM exam WHERE id=? AND user_id=?",(eid,u["id"])).fetchone()
   if not ex:return send(self,{"error":"exam not found"},404)
   qs=c.execute("SELECT id,title,score FROM q WHERE id>=11 ORDER BY id").fetchall()
   rows=c.execute("SELECT s.qid,s.score,s.passed,s.total,s.status FROM sub s WHERE s.user_id=? AND s.exam_id=? AND s.id=(SELECT MAX(s2.id) FROM sub s2 WHERE s2.user_id=s.user_id AND s2.exam_id=s.exam_id AND s2.qid=s.qid)",(u["id"],eid)).fetchall()
   by={r["qid"]:dict(r) for r in rows}
   items=[]; total=0; max_total=0; solved=0
   for q in qs:
    x=by.get(q["id"]); val=float(x["score"]) if x else 0
    total+=val; max_total+=float(q["score"] or 10)
    if x: solved+=1
    items.append({"qid":q["id"],"title":q["title"],"max_score":q["score"],"score":val,"passed":x["passed"] if x else 0,"test_total":x["total"] if x else 10,"status":x["status"] if x else "NOT_SUBMITTED"})
   return send(self,{"exam":dict(ex),"participant_name":ex["participant_name"],"total_score":round(total,2),"max_score":round(max_total,2),"solved":solved,"questions":items})
  if not u: return send(self,{"error":"login"},401)
  if self.path=="/api/questions":
   return send(self,[dict(x) for x in c.execute("SELECT id,title,body,input,output,sample_in,sample_out,score FROM q WHERE id>=11 ORDER BY id")])
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
   rows=c.execute("SELECT sub.id,sub.qid,q.title,sub.status,sub.score,sub.passed,sub.total,sub.created,sub.exam_id,exam.mode,exam.duration_minutes,exam.participant_name FROM sub JOIN q ON q.id=sub.qid LEFT JOIN exam ON exam.id=sub.exam_id WHERE sub.user_id=? ORDER BY sub.id DESC LIMIT 200",(u["id"],)).fetchall()
   return send(self,[dict(r) for r in rows])
  if self.path=="/api/admin/exams" and u["role"]=="admin":
   rows=c.execute("""
    SELECT e.id,e.participant_name,e.mode,e.duration_minutes,e.started_at,e.expires_at,e.finished_at,e.status,e.created,
           COALESCE(SUM(s.score),0) AS total_score,
           COALESCE(MAX(q_tot.max_score),0) AS ignored,
           COUNT(DISTINCT s.qid) AS solved
    FROM exam e
    LEFT JOIN sub s ON s.exam_id=e.id
    LEFT JOIN (
      SELECT id, score AS max_score FROM q
    ) q_tot ON q_tot.id=s.qid
    GROUP BY e.id
    ORDER BY e.id DESC
    LIMIT 500
   """).fetchall()
   out=[]
   for r in rows:
    item=dict(r)
    max_score=c.execute("SELECT COALESCE(SUM(score),0) FROM q").fetchone()[0] or 0
    item["max_score"]=float(max_score)
    item.pop("ignored",None)
    out.append(item)
   return send(self,out)
  if self.path=="/api/admin/solutions" and u["role"]=="admin":
   rows=c.execute("SELECT id,title FROM q WHERE id>=11 ORDER BY id").fetchall()
   out=[]
   for no,row in enumerate(rows,1):
    out.append({"number":no,"qid":row["id"],"title":row["title"],"solution":SOLUTIONS.get(row["id"],"")})
   return send(self,out)
  if self.path.startswith("/api/admin/exams/") and u["role"]=="admin":
   try:eid=int(self.path.rsplit("/",1)[1])
   except Exception:return send(self,{"error":"invalid exam id"},400)
   ex=c.execute("SELECT * FROM exam WHERE id=?",(eid,)).fetchone()
   if not ex:return send(self,{"error":"exam not found"},404)
   rows=c.execute("""
    SELECT s.*,q.title,q.score AS max_score
    FROM sub s JOIN q ON q.id=s.qid
    WHERE s.exam_id=?
    ORDER BY s.id ASC
   """,(eid,)).fetchall()
   subs=[]
   for r in rows:
    item=dict(r)
    try:item["details"]=json.loads(item.get("details") or "[]")
    except Exception:item["details"]=[]
    subs.append(item)
   total=sum(float(x["score"] or 0) for x in subs)
   max_total=sum(float(x["max_score"] or 0) for x in subs) if subs else sum(float(q["score"] or 0) for q in c.execute("SELECT score FROM q").fetchall())
   return send(self,{"exam":dict(ex),"total_score":round(total,2),"max_score":round(max_total,2),"submissions":subs})
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
   u=self.user(); s=self.headers.get("Cookie",""); cc=cookies.SimpleCookie(s); t=cc.get("sid"); SESS.pop(t.value,None) if t else None
   if u:
    c.execute("UPDATE exam SET status='ABANDONED',finished_at=? WHERE user_id=? AND status='ACTIVE'",(int(time.time()),u["id"])); c.commit()
   b=json.dumps({"ok":1}).encode(); self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.send_header("Set-Cookie","sid=; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; SameSite=Lax; Path=/"); self.end_headers(); self.wfile.write(b); return
  if p=="/api/admin/login":
   api_key=str(x.get("api_key","")).strip()
   expected_key=os.getenv("RENDER_API_KEY","")
   if not expected_key:
    return send(self,{"error":"ยังไม่ได้ตั้ง RENDER_API_KEY ใน Render Environment"},503)
   if not api_key or not hmac.compare_digest(api_key,expected_key):
    return send(self,{"error":"API Key ไม่ถูกต้อง"},401)
   u=c.execute("SELECT * FROM users WHERE username='admin' AND role='admin'").fetchone()
   if not u:return send(self,{"error":"ไม่พบบัญชี Admin"},500)
   token=self.make_token(u["username"])
   return send(self,{"user":dict(u),"token":token})
  if p=="/api/guest/start":
   name=" ".join(str(x.get("name","")).strip().split())
   mode=str(x.get("mode","practice"))
   duration=int(x.get("duration_minutes",0) or 0)
   if not name:return send(self,{"error":"กรุณากรอกชื่อ"},400)
   if len(name)>80:return send(self,{"error":"ชื่อยาวเกิน 80 ตัวอักษร"},400)
   if mode not in ("practice","timed"):return send(self,{"error":"โหมดไม่ถูกต้อง"},400)
   if mode=="timed" and duration not in (60,90):return send(self,{"error":"เลือกเวลา 60 หรือ 90 นาที"},400)
   guest_username="guest_"+secrets.token_hex(12)
   cur=c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",(guest_username,"","guest"))
   guest_id=cur.lastrowid
   now=int(time.time())
   expires=now+duration*60 if mode=="timed" else 0
   cur=c.execute("INSERT INTO exam(user_id,participant_name,mode,duration_minutes,started_at,expires_at,status) VALUES(?,?,?,?,?,?,?)",(guest_id,name,mode,duration if mode=="timed" else None,now,expires,"ACTIVE"))
   eid=cur.lastrowid
   c.commit()
   token=self.make_token(guest_username)
   SESS[token]={"id":guest_id,"username":guest_username,"password":"","role":"guest","display_name":name}
   row=c.execute("SELECT * FROM exam WHERE id=?",(eid,)).fetchone()
   b=json.dumps({"user":{"id":guest_id,"username":name,"role":"guest","display_name":name},"token":token,"exam":dict(row)},ensure_ascii=False).encode()
   self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.send_header("Set-Cookie",f"sid={token}; HttpOnly; SameSite=Lax; Path=/"); self.end_headers(); self.wfile.write(b); return
  u=self.user()
  if not u:return send(self,{"error":"login"},401)
  if p=="/api/exam/start":
   mode=str(x.get("mode","practice"))
   duration=int(x.get("duration_minutes",60) or 60)
   if mode not in ("practice","timed"): return send(self,{"error":"invalid mode"},400)
   if mode=="timed" and duration not in (60,90): return send(self,{"error":"เลือกเวลา 60 หรือ 90 นาที"},400)
   now=int(time.time())
   active_name=c.execute("SELECT participant_name FROM exam WHERE user_id=? AND status='ACTIVE' ORDER BY id DESC LIMIT 1",(u["id"],)).fetchone()
   pname=active_name["participant_name"] if active_name and active_name["participant_name"] else u.get("display_name") or u.get("username")
   c.execute("UPDATE exam SET status='ABANDONED',finished_at=? WHERE user_id=? AND status='ACTIVE'",(now,u["id"]))
   expires=now+duration*60 if mode=="timed" else 0
   c.execute("INSERT INTO exam(user_id,participant_name,mode,duration_minutes,started_at,expires_at,status) VALUES(?,?,?,?,?,?,?)",(u["id"],pname,mode,duration if mode=="timed" else None,now,expires,"ACTIVE"))
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

