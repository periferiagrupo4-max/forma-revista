#!/usr/bin/env python3
"""FORMA: selección semanal de artículos RSS con enlaces originales e imágenes con licencia."""
import datetime as dt,email.utils,html,json,pathlib,re,urllib.parse,urllib.request,xml.etree.ElementTree as ET,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
DEST=ROOT/"data"/"ediciones.json"
FEEDS=[("designboom","https://www.designboom.com/feed/"),("Dezeen","https://www.dezeen.com/design/feed/"),("Core77","https://feeds.feedburner.com/core77/blog"),("Yanko Design","https://www.yankodesign.com/feed/"),("Design Milk","https://design-milk.com/feed/")]
KEYWORDS=("industrial","product","material","recycl","circular","furniture","manufactur","3d print","robot","sustainab","plastic","textile","prototype","biomaterial","craft","ceramic")
PAPERS=[
{"categoria":"UX","titulo":"Why You Only Need to Test with 5 Users","url":"https://www.nngroup.com/articles/why-you-only-need-to-test-with-5-users/"},
{"categoria":"Sostenibilidad","titulo":"A New Textiles Economy","url":"https://www.ellenmacarthurfoundation.org/a-new-textiles-economy"},
{"categoria":"Moda","titulo":"A New Textiles Economy","url":"https://www.ellenmacarthurfoundation.org/a-new-textiles-economy"},
{"categoria":"Industrial","titulo":"Design for the Real World — Victor Papanek","url":"https://www.worldcat.org/search?q=Design+for+the+Real+World+Victor+Papanek"}]
TUTORIALS=[{"herramienta":"Blender","titulo":"Tutoriales de modelado Blender","url":"https://www.blender.org/support/tutorials/"},{"herramienta":"Fusion","titulo":"Aprender CAD paramétrico","url":"https://www.autodesk.com/learn/ondemand"},{"herramienta":"Rhino","titulo":"Introducción a Rhino","url":"https://www.rhino3d.com/learn/"},{"herramienta":"Affinity","titulo":"Aprender Affinity","url":"https://affinity.serif.com/en-us/learn/"}]
NS={"a":"http://www.w3.org/2005/Atom","dc":"http://purl.org/dc/elements/1.1/"}
def request(url,timeout=15):
    req=urllib.request.Request(url,headers={"User-Agent":"FORMA-DesignRadar/1.0 (weekly educational curation)","Accept":"application/xml,application/json,*/*"})
    with urllib.request.urlopen(req,timeout=timeout) as res:return res.read(3000000)
def val(item,*paths):
    for p in paths:
        e=item.find(p,NS)
        if e is not None and e.text:return html.unescape(re.sub(r"<[^>]+>"," ",e.text)).strip()
    return ""
def getdate(value):
    if not value:return None
    try:return email.utils.parsedate_to_datetime(value).astimezone(dt.timezone.utc)
    except Exception:
        try:return dt.datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(dt.timezone.utc)
        except Exception:return None
def entries(name,url):
    try:
        root=ET.fromstring(request(url));out=[]
        for it in root.findall(".//item")+root.findall(".//a:entry",NS):
            title=val(it,"title","a:title")
            link=val(it,"link")
            if not link:
                a=it.find("a:link",NS)
                link=a.get("href","") if a is not None else ""
            pub=getdate(val(it,"pubDate","a:published","a:updated","dc:date"))
            if not title or not link.startswith("https://") or pub is None:continue
            if any(bad in title.lower() for bad in ("sponsored:", "advertorial", "weekly roundup", "among nine new products", "partner content", "paid partnership")):continue
            desc=val(it,"description","a:summary")
            score=sum(2 if x in title.lower() else 1 if x in desc.lower() else 0 for x in KEYWORDS)
            out.append({"titulo":title[:180],"medio":name,"url":link,"fecha":pub.date().isoformat(),"resumen":desc[:230],"_date":pub,"_score":score})
        print(name,len(out))
        return out
    except Exception as ex:
        print("Aviso: fuente no disponible",name,ex);return []
def image(title):
    # Se permite solo fotografía ilustrativa con licencia abierta comprobada; no se reutiliza la foto RSS.
    term=next((t for t in ("furniture","chair","textile","plastic","ceramic","robot","lighting","wood","3d printing","fashion") if t in title.lower()),"industrial design")
    api="https://commons.wikimedia.org/w/api.php"
    params={"action":"query","format":"json","generator":"search","gsrsearch":"filetype:bitmap "+term,"gsrnamespace":6,"gsrlimit":8,"prop":"imageinfo","iiprop":"url|extmetadata|size","iiurlwidth":900}
    try:
        data=json.loads(request(api+"?"+urllib.parse.urlencode(params),10))
        for page in data.get("query",{}).get("pages",{}).values():
            info=(page.get("imageinfo") or [{}])[0];meta=info.get("extmetadata",{})
            def m(key):return html.unescape(re.sub("<[^>]+>"," ",meta.get(key,{}).get("value",""))).strip()
            license=m("LicenseShortName");licurl=m("LicenseUrl")
            if license not in ("CC0","Public domain","CC BY 4.0","CC BY 3.0","CC BY 2.0","CC BY 2.5"):continue
            url=info.get("thumburl") or info.get("url","");pageurl=info.get("descriptionurl","")
            if not url.startswith("https://") or not pageurl.startswith("https://commons.wikimedia.org/"):continue
            if not licurl.startswith("https://") and license!="Public domain":continue
            if info.get("width",0)<650 or info.get("height",0)<350:continue
            return {"url":url,"autor":m("Artist")[:150] or "Autor en Wikimedia Commons","licencia":license,"licencia_url":licurl or pageurl,"pagina":pageurl,"tipo":"Imagen ilustrativa de Wikimedia Commons; no corresponde necesariamente al proyecto"}
    except Exception as ex:print("Aviso: imagen no disponible",ex)
    return {"tipo":"Ilustración editorial original de FORMA","semilla":hashlib.sha256(title.encode()).hexdigest()[:12]}
def main():
    now=dt.datetime.now(dt.timezone.utc)
    try:old=json.loads(DEST.read_text(encoding="utf-8"))
    except Exception:old={"ediciones":[]}
    pool=sum((entries(n,u) for n,u in FEEDS),[])
    pool=[x for x in pool if -86400 <= (now-x["_date"]).total_seconds() <= 12*86400]
    pool.sort(key=lambda x:(x["_score"],x["_date"]),reverse=True)
    chosen=[];seen=set();counts={}
    for item in pool:
        key=item["url"].split("?")[0].rstrip("/")
        if key in seen or counts.get(item["medio"],0)>=3:continue
        seen.add(key);counts[item["medio"]]=counts.get(item["medio"],0)+1
        chosen.append({k:v for k,v in item.items() if not k.startswith("_")})
        if len(chosen)>=8:break
    if len(chosen)<4:print("Sin suficientes artículos recientes: se conserva edición previa.");return
    cache={}
    for oldedition in old.get("ediciones",[]):
        for n in oldedition.get("noticias",[]):
            if n.get("imagen_licenciada"):cache[n["url"]]=n["imagen_licenciada"]
    bytopic={}
    for item in chosen:
        topic=next((t for t in ("furniture","chair","textile","plastic","ceramic","robot","lighting","wood","3d printing","fashion") if t in item["titulo"].lower()),"industrial design")
        if item["url"] in cache:img=cache[item["url"]]
        elif topic in bytopic:img=bytopic[topic]
        else:img=image(item["titulo"]);bytopic[topic]=img
        item["imagen_licenciada"]=img
    monday=(now.date()-dt.timedelta(days=now.weekday())).isoformat()
    week=now.isocalendar().week
    ed={"id":monday,"publicada":now.date().isoformat(),"titulo":"Diseño, materia y futuro","noticias":chosen,"papers":[PAPERS[(week+i)%len(PAPERS)] for i in range(3)],"tutoriales":[TUTORIALS[(week+i)%len(TUTORIALS)] for i in range(3)],"tipo":"Selección automática de fuentes RSS; sin validación editorial humana"}
    editions=[ed]+[x for x in old.get("ediciones",[]) if x.get("id")!=monday]
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps({"ultima_actualizacion":now.isoformat(),"ediciones":editions[:52]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Edición",monday,len(chosen),"noticias")
if __name__=="__main__":main()
