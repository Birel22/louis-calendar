# Source unique des horaires : génère le bloc TIMETABLES de la page + les fichiers .ics
import json, re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
UTC = ZoneInfo("UTC")

# libellés et durées indicatives (minutes)
# catégorie : fp = essais libres, q = qualifs/Hyperpole, r = course, x = autre (warm-up…)
CAT = {"fp1":"fp","fp2":"fp","fp3":"fp","q1gt":"q","q2gt":"q","q1h":"q","q2h":"q","hp":"q","r1":"r","r2":"r","start":"r","wu":"x"}
SESS = {
 "fp1":({"en":"Free Practice 1","fr":"Essais libres 1"},90), "fp2":({"en":"Free Practice 2","fr":"Essais libres 2"},90),
 "q1gt":({"en":"Qualifying 1 – GT3","fr":"Qualifs 1 – GT3"},15), "q2gt":({"en":"Qualifying 2 – GT3","fr":"Qualifs 2 – GT3"},15),
 "q1h":({"en":"Qualifying 1 – Hypercar & LMP2","fr":"Qualifs 1 – Hypercar & LMP2"},15), "q2h":({"en":"Qualifying 2 – Hypercar & LMP2","fr":"Qualifs 2 – Hypercar & LMP2"},15),
 "r1":({"en":"Race 1","fr":"Course 1"},240), "r2":({"en":"Race 2","fr":"Course 2"},240),
 "wu":({"en":"Warm-up","fr":"Warm-up"},15), "start":({"en":"Race start","fr":"Départ de la course"},1440),
}
EV = {
 "jerez": {"title":"ALMS Jerez","tz":"Europe/Madrid","loc":"Circuito de Jerez – Ángel Nieto, Jerez de la Frontera, Spain",
   "src":"https://www.asianlemansseries.com/en/race/4-hours-of-jerez-by-alms-2027",
   "s":[("2027-01-15","10:10","fp1"),("2027-01-15","13:30","fp2"),("2027-01-15","16:05","q1gt"),("2027-01-15","16:25","q2gt"),("2027-01-15","16:50","q1h"),("2027-01-15","17:10","q2h"),("2027-01-16","13:45","r1"),("2027-01-17","13:45","r2")]},
 "portimao-alms": {"title":"ALMS Portimão","tz":"Europe/Lisbon","loc":"Autódromo Internacional do Algarve, Portimão, Portugal",
   "src":"https://www.asianlemansseries.com/en/race/4-hours-of-portimao-by-alms-2027",
   "s":[("2027-02-19","10:10","fp1"),("2027-02-19","13:30","fp2"),("2027-02-19","16:05","q1gt"),("2027-02-19","16:25","q2gt"),("2027-02-19","16:50","q1h"),("2027-02-19","17:10","q2h"),("2027-02-20","13:15","r1"),("2027-02-21","13:15","r2")]},
 "lemans": {"title":"24h Le Mans","tz":"Europe/Paris","loc":"Circuit de la Sarthe, Le Mans, France",
   "src":"https://www.24h-lemans.com/en/program",
   "s":[("2027-06-12","12:00","wu"),("2027-06-12","16:00","start")]},
}
def utc(date,time,tz):
    return datetime.fromisoformat(f"{date}T{time}").replace(tzinfo=ZoneInfo(tz)).astimezone(UTC)
def fmt(dt): return dt.strftime("%Y%m%dT%H%M%SZ")
def esc(t): return t.replace("\\","\\\\").replace(",","\\,").replace(";","\\;")
def vevent(eid,i,ev,sess):
    date,time,key = sess; lab,mins = SESS[key]; st = utc(date,time,ev["tz"])
    name = f'{ev["title"]} – {lab["en"]}'
    return "\r\n".join(["BEGIN:VEVENT",f"UID:{eid}-{i}-2027@louisdeletraz-calendar",f"DTSTAMP:{fmt(datetime.now(UTC))}",
      f"DTSTART:{fmt(st)}",f"DTEND:{fmt(st+timedelta(minutes=mins))}",f"SUMMARY:{esc(name)}",f"LOCATION:{esc(ev['loc'])}",
      f"DESCRIPTION:{esc('Louis Delétraz · '+ev['title']+' · '+ev['src'])}",
      "BEGIN:VALARM","ACTION:DISPLAY",f"DESCRIPTION:{esc(name)}","TRIGGER:-PT15M","END:VALARM","END:VEVENT"])
def cal(events):
    return "\r\n".join(["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Louis Deletraz//Calendar 2027//EN","CALSCALE:GREGORIAN","METHOD:PUBLISH",*events,"END:VCALENDAR"])+"\r\n"
import os
import shutil
shutil.rmtree("/home/claude/louis-calendar/ics", ignore_errors=True)
os.makedirs("/home/claude/louis-calendar/ics", exist_ok=True)
js = {}
for eid,ev in EV.items():
    vs=[vevent(eid,i,ev,s) for i,s in enumerate(ev["s"])]
    # un fichier par combinaison de sessions (bit k = session k) -> "ajouter la sélection"
    for mask in range(1, 1 << len(vs)):
        open(f"/home/claude/louis-calendar/ics/{eid}-m{mask}.ics","w",newline="").write(cal([v for k,v in enumerate(vs) if mask >> k & 1]))
    js[eid]={"src":ev["src"],"tz":ev["tz"],"missing":[c for c in ("fp","q","r") if c not in {CAT[k] for _,_,k in ev["s"]}],
             "title":ev["title"],"loc":ev["loc"],
             "sessions":[{"date":d,"time":t,"label":SESS[k][0],"min":SESS[k][1],"utc":utc(d,t,ev["tz"]).strftime("%Y-%m-%dT%H:%M:%SZ")} for d,t,k in ev["s"]]}
html_src = open("/home/claude/calendrier-2027.html").read()
weekends = []
for m in re.finditer(r'\{s:"(\d{4}-\d\d-\d\d)",e:"(\d{4}-\d\d-\d\d)",series:"(\w+)",id:"([^"]+)",name:(\{en:"([^"]+)"[^}]*\}|"([^"]+)")', html_src):
    sd, ed, ser, eid2 = m.group(1), m.group(2), m.group(3), m.group(4)
    raw = m.group(5)
    nm = raw.strip('"') if raw.startswith('"') else raw.split('en:"',1)[1].split('"',1)[0]
    weekends.append((sd, ed, ser, eid2, nm))
from datetime import date
def weekend_events():
    out=[]
    for sd, ed, ser, eid2, nm in weekends:
        e_excl = (date.fromisoformat(ed) + timedelta(days=1)).strftime("%Y%m%d")
        out.append("\r\n".join(["BEGIN:VEVENT", f"UID:weekend-{eid2}-2027@louisdeletraz-calendar", f"DTSTAMP:{fmt(datetime.now(UTC))}",
            f"DTSTART;VALUE=DATE:{sd.replace('-','')}", f"DTEND;VALUE=DATE:{e_excl}", f"SUMMARY:{esc(ser.upper() if ser!='lm' else 'Le Mans')} – {esc(nm)} (Louis Delétraz)",
            "TRANSP:TRANSPARENT", "END:VEVENT"]))
    return out
for fname, cats, calname in [("louis-2027.ics", {"fp","q","r","x"}, "Louis Delétraz 2027"),
                             ("louis-2027-quali-race.ics", {"q","r"}, "Louis Delétraz 2027 – Qualifs & races"),
                             ("louis-2027-races.ics", {"r"}, "Louis Delétraz 2027 – Races")]:
    sub = weekend_events()
    for eid, ev in EV.items():
        for i, ss in enumerate(ev["s"]):
            if CAT[ss[2]] in cats: sub.append(vevent(eid, i, ev, ss))
    subcal = cal(sub).replace("METHOD:PUBLISH", f"METHOD:PUBLISH\r\nX-WR-CALNAME:{calname}\r\nX-PUBLISHED-TTL:PT12H\r\nREFRESH-INTERVAL;VALUE=DURATION:PT12H")
    open(f"/home/claude/louis-calendar/{fname}", "w", newline="").write(subcal)
print("weekends", len(weekends))
block = "// TT-START (généré par gen_tt.py)\nconst TIMETABLES = " + json.dumps(js, ensure_ascii=False, indent=1) + ";\n// TT-END"
p="/home/claude/calendrier-2027.html"; s=open(p).read()
if "// TT-START" in s:
    s=re.sub(r"// TT-START.*?// TT-END", lambda m: block, s, flags=re.S)
else:
    s,n=re.subn(r"const S = \{.*?\n\};\nconst TIMETABLES = \{.*?\n\};", lambda m: block, s, flags=re.S); assert n==1
open(p,"w").write(s); print("ok", sorted(js))
