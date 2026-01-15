import streamlit as st
import feedparser
import requests
from datetime import datetime, timedelta, timezone
from dateutil import parser as dtparser

st.set_page_config(page_title="Mapa biblických zdrojov (beta)", layout="wide")

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
            })
    items.sort(key=lambda x: x["dt"], reverse=True)
    return items

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

    # Zobraz aktivitu
    st.markdown("**Aktívne zdroje:**")
    if activity:
        for src, cnt in sorted(activity.items(), key=lambda x: x[1], reverse=True):
            st.write(f"- {src}: {cnt}")
    else:
        st.info("Žiadne položky v zvolenom okne/filtri.")

    st.divider()

    # Zobraz položky
    for it in filtered[:80]:
        dt_local = it["dt"].astimezone()  # lokálny čas prostredia
        st.markdown(f"### [{it['title']}]({it['link']})")
        st.write(f"{dt_local:%Y-%m-%d %H:%M} | **{it['denom']}** | {it['focus']} | {it['source']}")
        if it["summary"]:
            st.write(it["summary"][:350] + ("…" if len(it["summary"]) > 350 else ""))
        st.caption(it["home"])
        st.divider()

st.sidebar.header("Zdroje v betaverzii")
for s in SOURCES:
    st.sidebar.write(f"- {s['denom']} | {s['focus']} | {s['name']}")
