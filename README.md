# iamtalker.github.io

DokuWiki(`iamtalker_docs.txt` + `wordblock/*.txt`)에서 만든 개인 철학 전집을
[VitePress](https://vitepress.dev)로 렌더링해 GitHub Pages에 올리는 사이트.

## 구조

- `docs/` — VitePress 소스. `tools/build_site.py`가 매번 통째로 다시 생성함
  (도메인별 폴더 + 글 하나당 `.md` 파일 + `sidebar.json`).
- `docs/.vitepress/config.mjs` — `sidebar.json`을 읽어 nav/sidebar를 만듦.
- `.github/workflows/deploy.yml` — `main`에 push되면 자동 빌드 후 Pages 배포.

## 내용 갱신하기

DokuWiki 쪽(`iamtalker_docs.txt` 또는 `wordblock/*.txt`)을 고친 뒤:

```bash
python3 tools/build_site.py docs
python3 - <<'PY'   # 홈페이지(도메인 카드) 재생성 — build_site.py가 안 건드림
import json
sidebar = json.load(open('sidebar.json', encoding='utf-8'))
home = """---
layout: home
hero:
  name: "iamtalker"
  text: "존재에서 세계까지"
  tagline: 개인 철학 전집 — 내면에서 외면으로
features:
%s
---
""" % "\n".join('  - title: %s\n    link: /%s/' % (d['text'], d['text']) for d in sidebar)
open('docs/index.md', 'w', encoding='utf-8', newline='\n').write(home)
PY
git add -A && git commit -m "content update" && git push
```

1분 안에 `https://iamtalker.github.io`에 반영됨(GitHub Actions가 자동 빌드+배포).

`tools/build_site.py`는 실행 컴퓨터에 pandoc(`C:\Users\misti\AppData\Local\Pandoc\pandoc.exe`)이
설치돼 있어야 하고, DokuWiki 데이터 경로가 `C:\MyData\DokuWikiStick\dokuwiki\data\pages`에
있다고 가정함(스크립트 상단 상수로 바꿀 수 있음).
