import json
import shutil
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None  # 允許超大圖

SRC = Path("/Volumes/X9 Pro/作品")
OUT = Path("/Users/linmengru/Downloads/meng-agent/portfolio")
EXTS = {'.jpg', '.jpeg', '.png', '.heic', '.JPG', '.JPEG', '.PNG'}
MAX_PHOTOS = 8   # 每個專案最多顯示幾張
MAX_SIDE  = 1500 # 壓縮後最長邊（px）

# 自動掃描這些分類資料夾，有新專案就自動加入作品集
SCAN_CATEGORIES = ["人像寫真", "活動紀錄", "空間攝影", "婚禮紀錄", "運動攝影"]

# 各分類的最大顯示張數（人像已挑過，全放；其他分類抽樣）
MAX_PHOTOS_BY_CAT = {
    "人像寫真": 999,
    "活動紀錄": 12,
    "空間攝影": 15,
    "婚禮紀錄": 15,
    "運動攝影": 12,
}

# 暫時不要顯示的資料夾（例如：照片還沒修完）
SKIP = []

# ══════════════════════════════════════════════════════
# 作品集設定
# 格式：(硬碟資料夾路徑,  作品集分類,   作品集顯示名稱,  封面關鍵字)
#
# 硬碟資料夾路徑 = 相對於 /Volumes/X9 Pro/作品/
# 封面關鍵字     = 檔名中包含這個字的第一張當封面
#                  留空 "" = 自動用第一張
# ══════════════════════════════════════════════════════
PORTFOLIO = [

    # ── 人像寫真 ──────────────────────────────────────
    ("人像寫真/260427羽甄山棚/羽甄/第一套/修完",   "人像寫真", "韓系寫真",   "20260427-11 拷貝"),
    ("人像寫真/260427羽甄山棚/羽甄/第三套/修完",   "人像寫真", "清甜寫真",   "3-8"),
    ("人像寫真/260510adora藏書閣/調色/修完的",       "人像寫真", "白天鵝",     ""),
    ("人像寫真/260511謝藏書閣/Wynni/精修作品", "人像寫真", "模特卡",     "IMG_9813"),
    ("人像寫真/260427羽甄山棚/羽甄/第二套/修完",   "人像寫真", "韓系寫真 2", "2-3"),
    ("人像寫真/260316風格寫真",                    "人像寫真", "風格寫真",    ""),
    ("人像寫真/Yona/精修（po文圖）",                "人像寫真", "藍調寫真",    "IMG_7082"),
    ("人像寫真/b_b_b1014",      "人像寫真", "底片感街拍",  "IMG_5469"),
    ("人像寫真/潔妮",            "人像寫真", "主題創作",    "0124_0024"),
    ("人像寫真/禹臻",            "人像寫真", "海風寫真",    "IMG_5446"),
    ("人像寫真/范飯",            "人像寫真", "青春校園",    "IMG_8108"),

    # ── 活動紀錄 ──────────────────────────────────────
    ("活動紀錄/20250601國三畢業典禮",       "活動紀錄", "國三畢業典禮",     "A7S01360"),
    ("活動紀錄/20250615木子診所開幕",       "活動紀錄", "木子診所開幕",     "A7S04000"),
    ("活動紀錄/260425台大異國文化節",       "活動紀錄", "台大異國文化節",   "_DSC3748"),
    ("活動紀錄/逗點十週年",                 "活動紀錄", "逗點十週年",       "241223_184"),
    ("活動紀錄/郵輪派對stepcwaveparty",    "活動紀錄", "郵輪派對",         "A7S00821"),

    # ── 空間攝影 ──────────────────────────────────────
    ("空間攝影/成品",   "空間攝影", "空間攝影",   "1 jpg"),

    # ── 婚禮紀錄 ──────────────────────────────────────
    # ("婚禮紀錄/XXX",  "婚禮紀錄", "XXX",        ""),

    # ── 運動攝影 ──────────────────────────────────────
    # ("運動攝影/XXX",  "運動攝影", "XXX",        ""),

]


# ── 以下不需要修改 ────────────────────────────────────

def is_photo(p: Path) -> bool:
    return p.suffix in EXTS and not p.name.startswith('._')

def all_photos(folder: Path):
    return sorted([f for f in folder.rglob('*') if f.is_file() and is_photo(f)])

def pick_photos(photos, cover_key, max_photos=MAX_PHOTOS):
    if not photos:
        return []
    # 封面
    if cover_key:
        match = next((p for p in photos if cover_key in p.name), None)
        if match:
            rest = [p for p in photos if p != match]
        else:
            match, rest = photos[0], photos[1:]
    else:
        match, rest = photos[0], photos[1:]
    # 最多 max_photos 張，其餘平均抽樣；若 max_photos 極大則全部保留
    if max_photos <= 1:
        return [match]
    slots = max_photos - 1
    remaining = rest[:slots] if len(rest) <= slots else \
                [rest[int(i * len(rest) / slots)] for i in range(slots)]
    return [match] + remaining

def compress(src: Path, dst: Path) -> Path:
    dst = dst.with_suffix('.jpg')
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return dst
    try:
        img = Image.open(src).convert("RGB")
        w, h = img.size
        if max(w, h) > MAX_SIDE:
            s = MAX_SIDE / max(w, h)
            img = img.resize((int(w * s), int(h * s)), Image.LANCZOS)
        img.save(dst, "JPEG", quality=85, optimize=True)
    except Exception as e:
        print(f"  ⚠️  {src.name}: {e}")
        shutil.copy2(src, dst)
    return dst

# ── 建立資料 ─────────────────────────────────────────
categories = {}

for (folder_path, cat_name, display_name, cover_key) in PORTFOLIO:
    src_dir = SRC / folder_path
    if not src_dir.exists():
        print(f"⚠️  找不到資料夾：{src_dir}，已跳過")
        continue

    photos = all_photos(src_dir)
    if not photos:
        print(f"⚠️  {folder_path} 沒有照片，已跳過")
        continue

    max_ph = MAX_PHOTOS_BY_CAT.get(cat_name, MAX_PHOTOS)
    selected = pick_photos(photos, cover_key, max_photos=max_ph)

    # slug = 用資料夾路徑產生，確保唯一
    slug = folder_path.replace('/', '__').replace(' ', '_')
    cat_slug = cat_name.replace(' ', '_')

    copied = []
    for p in selected:
        dst = OUT / "images" / slug / p.stem
        out_path = compress(p, dst)
        copied.append(f"images/{slug}/{p.stem}.jpg")

    if not categories.get(cat_slug):
        categories[cat_slug] = {'name': cat_name, 'slug': cat_slug, 'projects': []}

    categories[cat_slug]['projects'].append({
        'name': display_name,
        'slug': slug,
        'cover': copied[0],
        'photos': copied,
    })
    print(f"  [{cat_name}] {display_name}  ({len(copied)} 張)")

# ── 自動偵測硬碟中尚未在 PORTFOLIO 設定的新專案 ──────────
covered = set()
for (folder_path, _, _, _) in PORTFOLIO:
    parts = folder_path.split('/')
    if len(parts) >= 2:
        covered.add(f"{parts[0]}/{parts[1]}")

for cat_name in SCAN_CATEGORIES:
    cat_dir = SRC / cat_name
    if not cat_dir.exists():
        continue
    cat_slug = cat_name.replace(' ', '_')

    for proj_dir in sorted(cat_dir.iterdir()):
        if not proj_dir.is_dir() or proj_dir.name.startswith('.'):
            continue
        rel = f"{cat_name}/{proj_dir.name}"
        if rel in covered or rel in SKIP:
            continue

        photos = all_photos(proj_dir)
        if not photos:
            continue

        slug = rel.replace('/', '__').replace(' ', '_')
        max_ph = MAX_PHOTOS_BY_CAT.get(cat_name, MAX_PHOTOS)
        selected = pick_photos(photos, "", max_photos=max_ph)
        copied = []
        for p in selected:
            dst = OUT / "images" / slug / p.stem
            compress(p, dst)
            copied.append(f"images/{slug}/{p.stem}.jpg")

        if copied:
            if cat_slug not in categories:
                categories[cat_slug] = {'name': cat_name, 'slug': cat_slug, 'projects': []}
            categories[cat_slug]['projects'].append({
                'name': proj_dir.name,
                'slug': slug,
                'cover': copied[0],
                'photos': copied,
            })
            print(f"  🆕 [{cat_name}] {proj_dir.name}  ({len(copied)} 張) ← 自動新增")

data = list(categories.values())
for cat in data:
    cat['cover'] = cat['projects'][0]['cover']

# ── 產生 HTML ─────────────────────────────────────────
data_json = json.dumps(data, ensure_ascii=False, indent=2)

html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>作品集｜MENGRULENS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400&family=Noto+Serif+TC:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: "Noto Serif TC", serif; background: #1a1a1a; color: #ccc; }}

/* ── nav bar ── */
.topbar {{
  position: sticky; top: 0; z-index: 200;
  background: #111; border-bottom: 1px solid #222;
  padding: 0 24px;
  height: 56px;
  display: flex; align-items: center; justify-content: space-between;
}}
.topbar-brand {{
  font-family: "Cormorant Garamond", serif;
  font-size: 18px; letter-spacing: 7px; font-weight: 300; color: #fff;
  text-decoration: none;
}}
.breadcrumb {{
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; letter-spacing: 2px;
}}
.breadcrumb a {{
  color: #a0845c; text-decoration: none; cursor: pointer;
  transition: color .2s;
}}
.breadcrumb a:hover {{ color: #fff; }}
.breadcrumb .sep {{ color: #333; }}
.breadcrumb .cur {{ color: #666; }}

/* ── page header ── */
.pg-header {{
  padding: 48px 24px 32px;
  text-align: center;
}}
.pg-title {{
  font-family: "Cormorant Garamond", serif;
  font-size: 28px; letter-spacing: 6px; font-weight: 300; color: #fff;
  margin-bottom: 8px;
}}
.pg-sub {{
  font-size: 12px; letter-spacing: 4px; color: #a0845c;
}}
.pg-divider {{
  display: flex; align-items: center; gap: 10px; justify-content: center;
  margin: 16px 0 0;
}}
.pg-divider span {{ height: 1px; width: 40px; background: #2a2a2a; display: block; }}
.pg-divider em {{ color: #a0845c; font-style: normal; font-size: 11px; }}

/* ── category grid ── */
.cat-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 3px;
  padding: 0 0 60px;
}}
.cat-card {{
  cursor: pointer;
  position: relative;
  overflow: hidden;
  aspect-ratio: 4/3;
}}
.cat-card img {{
  width: 100%; height: 100%;
  object-fit: cover; object-position: center 30%;
  display: block;
  transition: transform .5s ease;
}}
.cat-card:hover img {{ transform: scale(1.06); }}
.cat-card-overlay {{
  position: absolute; inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,.75) 0%, rgba(0,0,0,.1) 55%, transparent 100%);
  transition: background .3s;
}}
.cat-card:hover .cat-card-overlay {{
  background: linear-gradient(to top, rgba(0,0,0,.85) 0%, rgba(0,0,0,.2) 55%, transparent 100%);
}}
.cat-card-info {{
  position: absolute; bottom: 0; left: 0; right: 0;
  padding: 20px 18px 16px;
}}
.cat-card-name {{
  font-family: "Cormorant Garamond", serif;
  font-size: 20px; letter-spacing: 4px; color: #fff; font-weight: 300;
  margin-bottom: 4px;
}}
.cat-card-count {{
  font-size: 11px; letter-spacing: 3px; color: #a0845c;
}}

/* ── project grid (masonry) ── */
.proj-wrap {{ padding: 0 20px 60px; }}
.proj-grid {{ columns: 2; column-gap: 3px; }}
.proj-card {{
  break-inside: avoid; margin-bottom: 3px;
  cursor: pointer; position: relative; overflow: hidden;
}}
.proj-card img {{ width: 100%; display: block; transition: transform .45s ease; }}
.proj-card:hover img {{ transform: scale(1.04); }}
.proj-card-overlay {{
  position: absolute; inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,.7) 0%, transparent 55%);
  opacity: 0; transition: opacity .3s;
}}
.proj-card:hover .proj-card-overlay {{ opacity: 1; }}
.proj-card-label {{
  position: absolute; bottom: 0; left: 0; right: 0;
  padding: 16px 14px 12px;
  font-family: "Cormorant Garamond", serif;
  font-size: 16px; letter-spacing: 3px; color: #fff;
  opacity: 0; transform: translateY(6px); transition: all .3s;
}}
.proj-card:hover .proj-card-label {{ opacity: 1; transform: translateY(0); }}

/* ── photo view ── */
.photo-hero {{
  position: relative;
}}
.photo-hero img {{
  width: 100%; max-height: 88vh;
  object-fit: contain; background: #111; display: block;
}}
.photo-info {{
  padding: 24px 24px 20px;
  display: flex; align-items: baseline; gap: 16px;
}}
.photo-info-title {{
  font-family: "Cormorant Garamond", serif;
  font-size: 22px; letter-spacing: 5px; color: #fff; font-weight: 300;
}}
.photo-info-count {{
  font-size: 11px; letter-spacing: 3px; color: #555;
}}
.photo-grid {{
  columns: 2; column-gap: 3px;
  padding: 0 0 60px;
}}
.photo-grid img {{
  width: 100%; display: block; margin-bottom: 3px;
  cursor: pointer; break-inside: avoid;
  transition: transform .35s ease, filter .3s;
  filter: brightness(1);
}}
.photo-grid img:hover {{
  transform: scale(1.02);
  filter: brightness(1.08);
}}

/* ── lightbox ── */
.lb {{
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,.96);
  z-index: 999; align-items: center; justify-content: center;
}}
.lb.open {{ display: flex; }}
.lb img {{
  max-width: 92vw; max-height: 92vh; object-fit: contain;
  transition: opacity .2s;
}}
.lb-close {{
  position: absolute; top: 20px; right: 24px;
  color: #666; font-size: 22px; cursor: pointer; letter-spacing: 2px;
  transition: color .2s;
}}
.lb-close:hover {{ color: #fff; }}
.lb-prev, .lb-next {{
  position: absolute; top: 50%; transform: translateY(-50%);
  color: #444; font-size: 40px; cursor: pointer; padding: 24px;
  user-select: none; transition: color .2s;
}}
.lb-prev:hover, .lb-next:hover {{ color: #a0845c; }}
.lb-prev {{ left: 0; }} .lb-next {{ right: 0; }}
.lb-counter {{
  position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
  font-size: 11px; letter-spacing: 3px; color: #444;
}}

@media (max-width: 600px) {{
  .cat-grid {{ grid-template-columns: 1fr 1fr; }}
  .proj-wrap {{ padding: 0 0 60px; }}
  .photo-info {{ padding: 16px 16px 12px; }}
}}
</style>
</head>
<body>

<div class="topbar">
  <a class="topbar-brand" href="../index.html">MENGRULENS</a>
  <div class="breadcrumb" id="nav"></div>
</div>

<div id="app"></div>

<div class="lb" id="lb">
  <span class="lb-close" onclick="closeLb()">✕ CLOSE</span>
  <span class="lb-prev" onclick="lbMove(-1)">&#8249;</span>
  <img id="lb-img" src="">
  <span class="lb-next" onclick="lbMove(1)">&#8250;</span>
  <div class="lb-counter" id="lb-counter"></div>
</div>

<script>
const DATA = {data_json};
let lbPhotos = [], lbIdx = 0;

function render() {{
  const raw = decodeURIComponent(location.hash.slice(1)) || '/';
  const parts = raw.split('/').filter(Boolean);
  const nav = document.getElementById('nav');
  const app = document.getElementById('app');

  if (parts.length === 0) {{
    nav.innerHTML = `<span class="cur">作品集</span>`;
    app.innerHTML = `
      <div class="pg-header">
        <div class="pg-title">作品集</div>
        <div class="pg-sub">PORTFOLIO</div>
        <div class="pg-divider"><span></span><em>✦</em><span></span></div>
      </div>
      <div class="cat-grid">
        ${{DATA.map(c=>`
          <div class="cat-card" data-go="${{c.slug}}">
            <img src="${{enc(c.cover)}}" loading="lazy">
            <div class="cat-card-overlay"></div>
            <div class="cat-card-info">
              <div class="cat-card-name">${{c.name}}</div>
              <div class="cat-card-count">${{c.projects.length}} 個專案</div>
            </div>
          </div>`).join('')}}
      </div>`;
  }} else if (parts.length === 1) {{
    const cat = DATA.find(c=>c.slug===parts[0]); if(!cat) return go('');
    nav.innerHTML = `<a data-go="">作品集</a><span class="sep">/</span><span class="cur">${{cat.name}}</span>`;
    app.innerHTML = `
      <div class="pg-header">
        <div class="pg-title">${{cat.name}}</div>
        <div class="pg-divider"><span></span><em>✦</em><span></span></div>
      </div>
      <div class="proj-wrap">
        <div class="proj-grid">
          ${{cat.projects.map(p=>`
            <div class="proj-card" data-go="${{cat.slug}}/${{p.slug}}">
              <img src="${{enc(p.cover)}}" loading="lazy">
              <div class="proj-card-overlay"></div>
              <div class="proj-card-label">${{p.name}}</div>
            </div>`).join('')}}
        </div>
      </div>`;
  }} else if (parts.length === 2) {{
    const cat = DATA.find(c=>c.slug===parts[0]); if(!cat) return go('');
    const proj = cat.projects.find(p=>p.slug===parts[1]); if(!proj) return go(parts[0]);
    lbPhotos = proj.photos;
    nav.innerHTML = `<a data-go="">作品集</a><span class="sep">/</span><a data-go="${{cat.slug}}">${{cat.name}}</a><span class="sep">/</span><span class="cur">${{proj.name}}</span>`;
    app.innerHTML = `
      <div class="photo-hero"><img src="${{enc(proj.photos[0])}}" data-lb="0"></div>
      <div class="photo-info">
        <div class="photo-info-title">${{proj.name}}</div>
        <div class="photo-info-count">${{proj.photos.length}} 張</div>
      </div>
      <div class="photo-grid">
        ${{proj.photos.slice(1).map((p,i)=>`<img src="${{enc(p)}}" loading="lazy" data-lb="${{i+1}}">`).join('')}}
      </div>`;
  }}
  window.scrollTo(0,0);
}}

function enc(p){{ return p.split('/').map(s=>encodeURIComponent(s)).join('/'); }}
function go(path){{ history.pushState(null,'','#/'+path); render(); }}
function openLb(i){{
  lbIdx=i;
  const img=document.getElementById('lb-img');
  img.style.opacity=0;
  img.src=enc(lbPhotos[i]);
  img.onload=()=>{{ img.style.opacity=1; }};
  document.getElementById('lb-counter').textContent=(i+1)+' / '+lbPhotos.length;
  document.getElementById('lb').classList.add('open');
}}
function closeLb(){{ document.getElementById('lb').classList.remove('open'); }}
function lbMove(d){{
  lbIdx=(lbIdx+d+lbPhotos.length)%lbPhotos.length;
  const img=document.getElementById('lb-img');
  img.style.opacity=0;
  img.src=enc(lbPhotos[lbIdx]);
  img.onload=()=>{{ img.style.opacity=1; }};
  document.getElementById('lb-counter').textContent=(lbIdx+1)+' / '+lbPhotos.length;
}}

document.addEventListener('click', e=>{{
  const el=e.target.closest('[data-go]'); if(el){{ e.preventDefault(); go(el.dataset.go); }}
  const lb=e.target.closest('[data-lb]'); if(lb) openLb(parseInt(lb.dataset.lb));
}});
document.getElementById('lb').addEventListener('click', e=>{{ if(e.target===e.currentTarget) closeLb(); }});
document.addEventListener('keydown', e=>{{
  if(e.key==='Escape') closeLb();
  if(e.key==='ArrowLeft') lbMove(-1);
  if(e.key==='ArrowRight') lbMove(1);
}});
window.addEventListener('popstate', render);
render();
</script>
</body>
</html>"""

(OUT / "index.html").write_text(html, encoding='utf-8')
print(f"\n✅ 完成！開啟：{OUT / 'index.html'}")
