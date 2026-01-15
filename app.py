import streamlit as st
import feedparser
import requests
from datetime import datetime, timedelta, timezone
from dateutil import parser as dtparser
import re

st.set_page_config(page_title="Mapa biblických zdrojov (beta)", layout="wide")
st.image("logo.png", width=240)
st.markdown("### Mapa biblických zdrojov na Slovensku – betaverzia")
st.caption("Agregátor zdrojov o Svätom Písme (weby, médiá, nástroje) + adresár.")
st.divider()
st.markdown("""
<style>
/* Celková typografia a rozostupy */
.block-container {
  padding-top: 1.2rem;
  padding-bottom: 2rem;
  max-width: 1200px;
}

/* Karty */
.card {
  border: 1px solid rgba(49,51,63,0.15);
  border-radius: 16px;
  padding: 14px 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 8px rgba(0,0,0,0.05);
}

/* Menší text */
.muted {
  opacity: 0.75;
  font-size: 0.92rem;
}

/* Štítky (badge) */
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid rgba(49,51,63,0.18);
  margin-right: 6px;
  font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)



# ---- Konfigurácia zdrojov (dopĺňaj ďalšie RSS/Atom feedy) ----
SOURCES = [
    # Katolíci / správy (často obsahuje aj biblické témy; v beta to filtruješ ručne/keywordmi)
    {
        "name": "TK KBS – Domáce spravodajstvo",
        "home": "https://www.tkkbs.sk/",
        "feed": "https://www.tkkbs.sk/rss/domov",
        "denom": "Katolíci",
        "focus": "Správy / články",
        "format": "Text",
    },
    {
        "name": "TK KBS – Zahraničné spravodajstvo",
        "home": "https://www.tkkbs.sk/",
        "feed": "https://www.tkkbs.sk/rss/zahranicie",
        "denom": "Katolíci",
        "focus": "Správy / články",
        "format": "Text",
    },

    # Protestanti (príklad: lutheran.sk – RSS novinky a kázne)
    {
        "name": "lutheran.sk – Novinky",
        "home": "https://www.lutheran.sk/",
        "feed": "http://www.lutheran.sk/index.php/sk/novinky?format=feed&type=atom",
        "denom": "Protestanti",
        "focus": "Správy / články",
        "format": "Text",
    },
    {
        "name": "lutheran.sk – Kázne",
        "home": "https://www.lutheran.sk/",
        "feed": "http://www.lutheran.sk/index.php/sk/kazne?format=feed&type=atom",
        "denom": "Protestanti",
        "focus": "Kázne / výklad",
        "format": "Text",
    },
]
# ---- Adresár zdrojov (aj bez RSS) ----
DIRECTORY = [
    # Katolíci – liturgia a texty
    {"name": "DoKostola.sk", "url": "https://www.dokostola.sk/", "denom": "Katolíci", "focus": "Liturgia / čítania", "type": "Web", "format": "Text"},
    {"name": "breviar.sk", "url": "https://breviar.sk/", "denom": "Katolíci", "focus": "Liturgia / čítania", "type": "Web", "format": "Text"},
    {"name": "Liturgický kalendár (KBS)", "url": "https://lc.kbs.sk/", "denom": "Katolíci", "focus": "Liturgia / čítania", "type": "Web", "format": "Text"},
    {"name": "Liturgia hodín (KBS)", "url": "https://lh.kbs.sk/", "denom": "Katolíci", "focus": "Liturgia / čítania", "type": "Web", "format": "Text"},
    {"name": "Sväté písmo online (svatepismo.sk)", "url": "https://svatepismo.sk/", "denom": "Katolíci", "focus": "Biblia online", "type": "Web", "format": "Text"},
    {"name": "AudioSvätéPísmo.sk", "url": "https://www.audiosvatepismo.sk/", "denom": "Katolíci", "focus": "Audio Biblia", "type": "Web", "format": "Audio"},

    # Katolíci – organizácie a médiá
    {"name": "Katolícke biblické dielo (KBD)", "url": "https://kbd.sk/", "denom": "Katolíci", "focus": "Apoštolát / komentáre", "type": "Web", "format": "Text"},
    {"name": "KBS.sk", "url": "https://www.kbs.sk/", "denom": "Katolíci", "focus": "Inštitucionálne", "type": "Web", "format": "Text"},
    {"name": "TV LUX – web", "url": "https://www.tvlux.sk/", "denom": "Katolíci", "focus": "Médiá", "type": "Web", "format": "Video"},
    {"name": "TV LUX – Biblia (podcast)", "url": "https://www.tvlux.sk/podcast/biblia", "denom": "Katolíci", "focus": "Audio/Video Biblia", "type": "Podcast", "format": "Audio"},
    {"name": "TV LUX – Biblia (YouTube playlist)", "url": "https://www.youtube.com/playlist?list=PLIzsQMptV5HbUp25MYNbml7oi3oFwF5ax", "denom": "Katolíci", "focus": "Audio/Video Biblia", "type": "YouTube", "format": "Video"},

    # Ekumenické – Biblia online
    {"name": "Biblia.sk (SBS)", "url": "https://biblia.sk/", "denom": "Ekumenické", "focus": "Biblia online", "type": "Web", "format": "Text"},
    {"name": "Slovenská biblická spoločnosť", "url": "https://www.bible.sk/", "denom": "Ekumenické", "focus": "Organizácia", "type": "Web", "format": "Text"},
    {"name": "MojaBiblia.sk", "url": "https://www.mojabiblia.sk/", "denom": "Ekumenické", "focus": "Štúdium / nástroje", "type": "Web", "format": "Text"},

    # Protestanti (ECAV a širšie)
    {"name": "ECAV.sk – komunitné štúdium Biblie", "url": "https://www.ecav.sk/komnunitne-studium-biblie", "denom": "Protestanti", "focus": "Štúdium Biblie", "type": "Web", "format": "Text"},
    {"name": "ZD ECAV – online štúdium Biblie", "url": "https://www.zdecav.sk/online-studium-biblie/", "denom": "Protestanti", "focus": "Štúdium Biblie", "type": "Web", "format": "Text"},
    {"name": "lutheran.sk", "url": "https://www.lutheran.sk/", "denom": "Protestanti", "focus": "Inštitucionálne / kázne", "type": "Web", "format": "Text"},

    # Pravoslávni
    {"name": "Pravoslávna cirkev na Slovensku (orthodox.sk)", "url": "https://orthodox.sk/", "denom": "Pravoslávni", "focus": "Inštitucionálne", "type": "Web", "format": "Text"},
    {"name": "pravoslavie.sk", "url": "https://pravoslavie.sk/", "denom": "Pravoslávni", "focus": "Články / duchovno", "type": "Web", "format": "Text"},

    # Adventisti
    {"name": "Sobotná škola (CASD) – štúdium Biblie", "url": "https://sobotnaskola.casd.sk/studium-biblie/", "denom": "Adventisti", "focus": "Štúdium Biblie", "type": "Web", "format": "Text"},

    # Jehovovi svedkovia
    {"name": "JW.org – Biblia (slovenčina)", "url": "https://www.jw.org/sk/kniznica/biblia/", "denom": "Jehovovi svedkovia", "focus": "Biblia online", "type": "Web", "format": "Text"},

    # Komerčné (predaj Biblie a biblickej literatúry)
    {"name": "Kumran.sk – Biblia (eshop)", "url": "https://www.kumran.sk/45-biblia", "denom": "Komerčné", "focus": "Predaj Biblie", "type": "Eshop", "format": "Text"},
    {"name": "Zachej.sk – Biblia (eshop)", "url": "https://www.zachej.sk/kategoria/14/biblia/", "denom": "Komerčné", "focus": "Predaj Biblie", "type": "Eshop", "format": "Text"},
    {"name": "SSV eobchod – Biblia/Sväté Písmo", "url": "https://eobchod.ssv.sk/eshop/biblia-svate-pismo/p-16.xhtml", "denom": "Komerčné", "focus": "Predaj Biblie", "type": "Eshop", "format": "Text"},
]


# ---- Helpery ----
def safe_get(url: str, timeout=12) -> bytes | None:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "BibleMapBeta/0.1"})
        if r.status_code >= 400:
            return None
        return r.content
    except Exception:
        return None

def parse_dt(entry) -> datetime | None:
    # feedparser dáva published_parsed/updated_parsed, niekedy len textové published
    for key in ("published_parsed", "updated_parsed"):
        if key in entry and entry[key]:
            try:
                return datetime(*entry[key][:6], tzinfo=timezone.utc)
            except Exception:
                pass
    for key in ("published", "updated"):
        if key in entry and entry[key]:
            try:
                dt = dtparser.parse(entry[key])
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
    return None
def pick_image_from_entry(entry):
    # media_thumbnail (časté pri RSS)
    try:
        mt = entry.get("media_thumbnail")
        if mt and isinstance(mt, list) and mt[0].get("url"):
            return mt[0]["url"]
    except Exception:
        pass

    # media_content
    try:
        mc = entry.get("media_content")
        if mc and isinstance(mc, list) and mc[0].get("url"):
            return mc[0]["url"]
    except Exception:
        pass

    # enclosures (image/jpeg a pod.)
    try:
        enc = entry.get("enclosures")
        if enc and isinstance(enc, list):
            for e in enc:
                href = e.get("href")
                etype = (e.get("type") or "").lower()
                if href and ("image" in etype or href.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))):
                    return href
    except Exception:
        pass

    return None
      # Niekedy je obrázok priamo v HTML summary (napr. <img src="...">)
    try:
        html = entry.get("summary") or entry.get("description") or ""
        if "<img" in html and "src=" in html:
            # jednoduché vytiahnutie prvého src="
            part = html.split("src=", 1)[1]
            quote = part[0]
            if quote in ['"', "'"]:
                url = part[1:].split(quote, 1)[0]
                if url.startswith("http"):
                    return url
    except Exception:
        pass



@st.cache_data(ttl=300)
def load_items(sources):
    items = []
    for s in sources:
        raw = safe_get(s["feed"])
        if not raw:
            continue
        fp = feedparser.parse(raw)
        for e in fp.entries[:50]:
            dt = parse_dt(e) or datetime.now(timezone.utc)
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            summary = (e.get("summary") or e.get("description") or "").strip()
            img = pick_image_from_entry(e)

            items.append({
                "source": s["name"],
                "home": s["home"],
                "denom": s["denom"],
                "focus": s["focus"],
                "format": s["format"],
                "title": title,
                "link": link,
                "summary": summary,
                "dt": dt,
                "image": img,
            })
    items.sort(key=lambda x: x["dt"], reverse=True)
    return items
  @st.cache_data(ttl=3600)
def get_og_image(url: str) -> str | None:
    raw = safe_get(url, timeout=10)
    if not raw:
        return None
    try:
        html = raw.decode("utf-8", errors="ignore")
    except Exception:
        return None

    # og:image
    m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m:
        return m.group(1)

    # twitter:image
    m = re.search(r'name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m:
        return m.group(1)

    return None

# ---- UI ----
st.title("Mapa biblických zdrojov na Slovensku – betaverzia")
st.caption("Agregácia cez RSS/Atom. Sociálne siete zatiaľ ako linky (bez API).")

colA, colB = st.columns([1, 2], gap="large")

with colA:
    denoms = sorted(set(s["denom"] for s in SOURCES))
    focuses = sorted(set(s["focus"] for s in SOURCES))
    formats = sorted(set(s["format"] for s in SOURCES))

    denom_sel = st.multiselect("Denominácia", denoms, default=denoms)
    focus_sel = st.multiselect("Zameranie", focuses, default=focuses)
    format_sel = st.multiselect("Formát", formats, default=formats)

    kw = st.text_input("Kľúčové slovo (napr. Biblia, evanjelium, čítania, Žalm)", value="")
    days = st.slider("Rozsah (dni dozadu)", 1, 30, 7)

    st.divider()
    st.subheader("Aktivita (posledných N dní)")
    st.write("Rýchly pohľad: kto publikoval v zvolenom okne.")
    st.caption("V ďalšej iterácii sa to zmení na ‘blindspoty’ podľa tém/perikop.")

with colB:
    tab_feed, tab_dir = st.tabs(["Feed", "Adresár"])

    # ---------------- FEED ----------------
    with tab_feed:
        items = load_items(SOURCES)

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        filtered = []
        for it in items:
            if it["denom"] not in denom_sel:
                continue
            if it["focus"] not in focus_sel:
                continue
            if it["format"] not in format_sel:
                continue
            if it["dt"] < cutoff:
                continue
            if kw.strip():
                blob = f"{it['title']} {it['summary']}".lower()
                if kw.lower().strip() not in blob:
                    continue
            filtered.append(it)

        # Aktivita podľa zdroja
        activity = {}
        for it in filtered:
            activity[it["source"]] = activity.get(it["source"], 0) + 1

        st.subheader("Feed")
        st.write(f"Nájdené položky: **{len(filtered)}**")

        st.markdown("**Aktívne zdroje:**")
        if activity:
            for src, cnt in sorted(activity.items(), key=lambda x: x[1], reverse=True):
                st.write(f"- {src}: {cnt}")
        else:
            st.info("Žiadne položky v zvolenom okne/filtri.")

        st.divider()

        for it in filtered[:80]:
            dt_local = it["dt"].astimezone()
            title = (it.get("title") or "(bez názvu)").replace("\n", " ")
            link = it.get("link") or "#"
            summary = (it.get("summary") or "").replace("\n", " ")
            denom = it.get("denom", "—")
            focus = it.get("focus", "—")
            source = it.get("source", "—")

        for it in filtered[:80]:
            dt_local = it["dt"].astimezone()
            img = it.get("image")
          if not img and it.get("link"):
    img = get_og_image(it["link"])
            title = (it.get("title") or "(bez názvu)").replace("\n", " ")
            link = it.get("link") or "#"
            summary = (it.get("summary") or "").replace("\n", " ")
            denom = it.get("denom", "—")
            focus = it.get("focus", "—")
            source = it.get("source", "—")

            c_img, c_txt = st.columns([1, 3], gap="medium")

            with c_img:
                if img:
                    try:
                        st.image(img, use_container_width=True)
                    except Exception:
                        pass

            with c_txt:
                st.markdown(f"""
<div class="card">
  <div>
    <span class="badge">{denom}</span>
    <span class="badge">{focus}</span>
    <span class="badge">{source}</span>
  </div>
  <h4 style="margin:10px 0 6px 0;">
    <a href="{link}" target="_blank" style="text-decoration:none;">
      {title}
    </a>
  </h4>
  <div class="muted">{dt_local:%Y-%m-%d %H:%M}</div>
  <div style="margin-top:8px;">{summary[:300]}{"…" if len(summary) > 300 else ""}</div>
</div>
""", unsafe_allow_html=True)



    # ---------------- ADRESÁR ----------------
    with tab_dir:
        st.subheader("Adresár zdrojov")
        st.caption("Zoznam dôležitých slovenských webov/kanálov o Svätom písme (aj bez RSS).")

        # Filtre pre adresár
        d_denoms = sorted(set(x["denom"] for x in DIRECTORY))
        d_focus = sorted(set(x["focus"] for x in DIRECTORY))
        d_types = sorted(set(x["type"] for x in DIRECTORY))
        d_formats = sorted(set(x["format"] for x in DIRECTORY))

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            d_denom_sel = st.multiselect("Denominácia", d_denoms, default=d_denoms)
        with c2:
            d_focus_sel = st.multiselect("Zameranie", d_focus, default=d_focus)
        with c3:
            d_type_sel = st.multiselect("Typ", d_types, default=d_types)
        with c4:
            d_format_sel = st.multiselect("Formát", d_formats, default=d_formats)

        d_q = st.text_input("Hľadať v adresári (názov / URL)", value="")

                # --- Výber triedenia a rozsahu ---
        c_sort1, c_sort2 = st.columns([2, 1])
        with c_sort1:
            sort_mode = st.selectbox("Triediť podľa", ["Priority (TOP)", "Abecedne", "Denominácia → názov"])
        with c_sort2:
            top_n = st.number_input("Limit (0 = bez limitu)", min_value=0, max_value=500, value=0, step=10)

        # --- Filtrovanie ---
        rows = []
        for x in DIRECTORY:
            if x.get("denom") not in d_denom_sel:
                continue
            if x.get("focus") not in d_focus_sel:
                continue
            if x.get("type") not in d_type_sel:
                continue
            if x.get("format") not in d_format_sel:
                continue
            if d_q.strip():
                blob = f"{x.get('name','')} {x.get('url','')} {x.get('tags','')} {x.get('notes','')}".lower()
                if d_q.lower().strip() not in blob:
                    continue
            rows.append(x)

        # --- Triedenie ---
        def prio(x):
            v = x.get("priority")
            try:
                return int(v)
            except Exception:
                return 9999

        if sort_mode == "Priority (TOP)":
            rows.sort(key=lambda x: (prio(x), x.get("name","").lower()))
        elif sort_mode == "Abecedne":
            rows.sort(key=lambda x: x.get("name","").lower())
        else:
            rows.sort(key=lambda x: (x.get("denom",""), x.get("name","").lower()))

        if top_n and top_n > 0:
            rows = rows[:top_n]

        st.write(f"Položiek v adresári: **{len(rows)}**")
        st.divider()

        # --- Tabuľka (rýchly prehľad) ---
        table_rows = []
        for x in rows:
            table_rows.append({
                "Názov": x.get("name","—"),
                "Denominácia": x.get("denom","—"),
                "Zameranie": x.get("focus","—"),
                "Typ": x.get("type","—"),
                "Formát": x.get("format","—"),
                "Oficiálnosť": x.get("official","—"),
                "Priority": x.get("priority","—"),
                "URL": x.get("url","—"),
            })
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

        st.divider()

        # --- Karty (detail) ---
        for x in rows:
            st.markdown(f"### [{x.get('name','(bez názvu)')}]({x.get('url','#')})")
            line = f"**{x.get('denom','—')}** | {x.get('focus','—')} | {x.get('type','—')} | {x.get('format','—')}"
            if x.get("official"):
                line += f" | {x.get('official')}"
            if x.get("priority") is not None:
                line += f" | priority: {x.get('priority')}"
            st.write(line)

            if x.get("tags"):
                st.caption(f"Značky: {x.get('tags')}")
            if x.get("notes"):
                st.write(x.get("notes"))

            st.caption(x.get("url"))
            st.divider()


