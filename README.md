# iamtalker.github.io

DokuWiki 문서를 [VitePress](https://vitepress.dev) 정적 사이트로 변환해
GitHub Pages에 올리는 개인 글 모음 사이트.

사이트 구조는 **서재(library) → 책(book) → 대분류 → 소주제 → 글** 4단계.
루트(`/`)는 여러 책을 나열하는 서재 페이지이고, 책이 몇 권이든 자동으로 늘어난다.

## 책 추가/삭제하기 (직접 할 때)

1. `C:\MyData\DokuWikiStick\dokuwiki\data\pages\github_io_books\`에 도쿠위키
   문법(`====== 대분류 ======` / `===== 소주제 =====` / `==== 글제목 ====` +
   `{{page>wordblock:ID}}` 같은 참조)으로 쓴 `.txt` 파일 하나 = 책 하나.
   파일명이 책 제목이 된다(언더스코어는 공백으로 치환).
   - 책을 지우려면 그 `.txt` 파일만 지우면 됨 — 다음 빌드 때 산출물도 자동 정리됨.
2. `update.bat` 더블클릭. 끝.
   `build_books.py`가 폴더를 스캔해서 책마다 사이트를 새로 생성하고
   `books.json`/`sidebar.json`도 알아서 다시 쓴다. 새 스크립트도, 수동 등록도 불필요.

## 구조

- `tools/build_books.py` — 핵심 스크립트. `pages/github_io_books/*.txt`를
  전부 스캔해서 각 글을 pandoc(dokuwiki → gfm)으로 변환, `docs/<책>/...`에
  써넣고 `books.json`/`sidebar.json`을 생성한다.
  - 대분류/소주제/글제목 중 **어느 레벨이든** 자식 헤더 없이 참조나 본문이
    바로 오면 그 자체가 "리프(글)"가 됨 — 3단을 다 채울 필요 없음.
  - `{{page>...}}` 참조는 아무 도쿠위키 네임스페이스나 지원(`#anchor` 포함),
    중첩된 참조(허브 페이지가 또 다른 페이지를 참조)도 재귀적으로 풀어내고
    헤더 레벨을 그 위치에 맞게 재번호매김(도쿠위키 include 플러그인과 동일하게
    동작). 각 leaf 페이지의 실제 헤더 구조가 왼쪽 사이드바에도 (같은 페이지
    안 앵커로) 트리로 뜬다.
  - 이미지: 로컬 도쿠위키 미디어(`{{ns:file.jpg}}`)는 `data/media/`에서
    찾아 `docs/public/`에 같은 경로로 복사, 외부 URL(`{{https://...}}`)은
    그대로 통과, `<markdown>...</markdown>` 플러그인 블록도 내용을 보존해
    그대로 삽입.
- `tools/build_library.py` — `books.json`을 읽어 **서재 루트**(`docs/index.md`)를
  재생성. 책 추가/삭제해도 이 파일은 안 건드려도 됨.
- `docs/.vitepress/config.mjs` — `sidebar.json`/`books.json`으로 모든 책의
  nav/sidebar를 구성. 새 책이 추가돼도 이 파일 자체는 안 건드려도 됨.
- `.github/workflows/deploy.yml` — `main`에 push되면 GitHub Actions가
  빌드 후 Pages에 배포(1분 이내 반영).
- `update.bat` — `build_books.py` → `build_library.py` → `git add -A` →
  `git commit` → `git push`를 한 번에 실행하는 원클릭 스크립트.

## 의존성

- **pandoc**: `C:\Users\misti\AppData\Local\Pandoc\pandoc.exe`
  (winget으로 설치, `build_books.py` 상단 `PANDOC` 상수에 절대경로로 고정).
- 도쿠위키 데이터 경로 `C:\MyData\DokuWikiStick\dokuwiki\data\pages`가
  `build_books.py` 상단 `PAGES_DIR` 상수로 고정돼 있음.
- 로컬 미리보기(선택): `npm install` 후 `npx vitepress dev docs` 또는
  `npx vitepress build docs` + `npx vitepress preview docs`.
  `update.bat` 자체는 Node 없이도 동작(배포는 GitHub Actions가 서버에서 빌드).
