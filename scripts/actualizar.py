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
TUTORIALS=[{"id":"blender-nodos-2026","herramienta":"Blender","titulo":"Crear paisajes paramétricos con Geometry Nodes","creador":"Ryan King Art","fecha":"2026-05-14","idioma":"en","nivel":"Intermedio","duracion":"30 min aprox.","objetivo":"Construye un terreno procedural con controles ajustables y variaciones del patrón.","reto":"Genera tres relieves diferentes y adapta uno como textura conceptual para un empaque.","url":"https://www.youtube.com/watch?v=5avrqTMYOCs","video_id":"5avrqTMYOCs","tipo":"video"},{"id":"fusion-bloque-2026","herramienta":"Fusion","titulo":"Modelar un bloque 3D con extrusión, vaciado y redondeos","creador":"Product Design Online","fecha":"2026-03-10","idioma":"en","nivel":"Inicial","duracion":"20 min aprox.","objetivo":"Utiliza bocetos, extrusión, patrón rectangular, Shell y Fillet.","reto":"Diseña una caja modular de 60 × 40 × 25 mm y crea una segunda versión cambiando parámetros.","url":"https://www.youtube.com/watch?v=4G2E_DqQteM","video_id":"4G2E_DqQteM","tipo":"video"},{"id":"rhino-fachada-2026","herramienta":"Rhino / Grasshopper","titulo":"Construir una superficie con patrón paramétrico","creador":"Architutors","fecha":"2026-05-19","idioma":"en","nivel":"Intermedio","duracion":"15 min aprox.","objetivo":"Crea patrones paramétricos usando curvas atractoras y controla sus parámetros.","reto":"Convierte el patrón en un panel de ventilación de 20 × 20 cm, con dos grados de apertura.","url":"https://www.youtube.com/watch?v=RrQcN98w3j8","video_id":"RrQcN98w3j8","tipo":"video"},{"id":"affinity-raw-2025","herramienta":"Affinity Photo","titulo":"Revelar una fotografía RAW con ajustes y máscaras","creador":"Practical Affinity","fecha":"2025-01-13","idioma":"en","nivel":"Intermedio","duracion":"Tutorial puntual","objetivo":"Mejora luz y color con superposiciones, máscaras y herramientas de revelado.","reto":"Edita una fotografía de un prototipo con dos zonas de exposición y compara el antes y después.","url":"https://www.youtube.com/watch?v=zmgLvaBsLcc","video_id":"zmgLvaBsLcc","tipo":"video"},{"id":"affinity-logo-2025","herramienta":"Affinity Designer","titulo":"Crear un logotipo-emblema con vectores y texto","creador":"Design Made Simple","fecha":"2025-02-21","idioma":"en","nivel":"Inicial","duracion":"17 min","objetivo":"Combina figuras vectoriales y texto para desarrollar un emblema.","reto":"Diseña un emblema para una colección de objetos con dos colores y prepara una versión monocroma.","url":"https://www.youtube.com/watch?v=B69bLxIODcg","tipo":"video","video_id":"B69bLxIODcg"}]

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
def traducir(texto, idioma="en"):
    """Traduce títulos y sinopsis públicos mediante MyMemory (gratis, con cuota).
    Nunca inventa traducciones: devuelve None cuando no puede traducir.
    """
    texto=(texto or "").strip()
    if not texto:return None
    if idioma=="es":return texto
    if idioma not in ("en","fr","de","it","pt"):return None
    # La API admite un máximo de 500 bytes por petición.
    while len(texto.encode("utf-8"))>480:
        texto=texto[:max(1,len(texto)-20)].rsplit(" ",1)[0]
    try:
        endpoint="https://api.mymemory.translated.net/get?"+urllib.parse.urlencode({"q":texto,"langpair":idioma+"|es"})
        respuesta=json.loads(request(endpoint,timeout=14))
        translated=html.unescape((respuesta.get("responseData") or {}).get("translatedText","")).strip()
        if int(respuesta.get("responseStatus",0))!=200 or not translated:return None
        if "MYMEMORY WARNING" in translated.upper() or "QUOTA" in translated.upper():return None
        if translated.casefold()==texto.casefold():return None
        return translated
    except Exception as exc:
        print("Traducción temporalmente no disponible:",type(exc).__name__)
        return None

def image(title):
    # No se utiliza una fotografía genérica solo por compartir palabras clave.
    # Las fotografías reales deben aprobarse para la noticia concreta, con licencia y autor.
    return {"tipo":"Ilustración conceptual original de FORMA","semilla":hashlib.sha256(title.encode()).hexdigest()[:12]}

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
            if n.get("imagen_licenciada",{}).get("verificada_para_articulo") is True and n["imagen_licenciada"].get("correspondencia_url")==n["url"]:cache[n["url"]]=n["imagen_licenciada"]
    bytopic={}
    anteriores={n.get("url"):n for e in old.get("ediciones",[]) for n in e.get("noticias",[])}
    for item in chosen:
        # Los feeds de esta selección son medios publicados en inglés.
        item["idioma_original"]="en"
        item["titulo_original"]=item["titulo"]
        item["resumen_original"]=item["resumen"]
        anterior=anteriores.get(item["url"],{})
        item["titulo_es"]=anterior.get("titulo_es") or traducir(item["titulo"],"en")
        # Una sinopsis traducida solo se muestra si también existe título en español.
        item["resumen_es"]=(anterior.get("resumen_es") or traducir(item["resumen"],"en")) if item["titulo_es"] else None
        item["traduccion"]=anterior.get("traduccion","automática")
        topic=next((t for t in ("furniture","chair","textile","plastic","ceramic","robot","lighting","wood","3d printing","fashion") if t in item["titulo"].lower()),"industrial design")
        if item["url"] in cache:img=cache[item["url"]]
        elif topic in bytopic:img=bytopic[topic]
        else:img=image(item["titulo"]);bytopic[topic]=img
        item["imagen_licenciada"]=img
    monday=(now.date()-dt.timedelta(days=now.weekday())).isoformat()
    week=now.isocalendar().week
    ed={"id":monday,"publicada":now.date().isoformat(),"titulo":"Diseño, materia y futuro","noticias":chosen,"papers":[PAPERS[(week+i)%len(PAPERS)] for i in range(3)],"tutoriales":[TUTORIALS[(week+i)%len(TUTORIALS)] for i in range(len(TUTORIALS))],"tipo":"Selección automática de fuentes RSS; sin validación editorial humana"}
    editions=[ed]+[x for x in old.get("ediciones",[]) if x.get("id")!=monday]
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps({"ultima_actualizacion":now.isoformat(),"ediciones":editions[:52]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Edición",monday,len(chosen),"noticias")
if __name__=="__main__":main()
