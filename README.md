# githubio_book

DokuWiki 문서 또는 마크다운 폴더를 [VitePress](https://vitepress.dev) 정적 사이트로 변환해
GitHub Pages에 올리는 도구. 사이트 구조는 **서재 → 책 → 대분류 → 소주제 → 글** 4단계이고,
책이 몇 권이든 자동으로 늘어난다.

## 처음 쓰기

1. GitHub에서 `<아이디>.github.io` 이름으로 빈 저장소를 만들고, 저장소 Settings → Pages 의
   Source 를 **GitHub Actions** 로 설정한다.
2. **`settings.bat`** 더블클릭 → 설정 창에서 입력 (텍스트 파일을 직접 고칠 필요 없음).
   "GitHub 업로드"의 **저장소 주소**에 1번에서 만든 저장소 주소를 넣고 "연결 확인"을 눌러 본다.
   git 저장소 초기화와 remote 연결은 업로드할 때 자동으로 된다.
3. **`update.bat`** 더블클릭 → 변환 + commit + push. 1분 안에 사이트에 반영된다.
   (`config.json`이 없으면 설정 창이 먼저 열린다. 처음 push 때 git 이 브라우저로 GitHub 로그인을 물어본다.
   비밀번호/토큰은 이 도구가 저장하지 않는다.)

## 입력 소스 (설정 창에서 선택, 둘 다 켜면 함께 빌드)

| 소스 | 폴더 규칙 |
|---|---|
| **도쿠위키 → 마크다운** | 설정의 **책 폴더**(도쿠위키 `pages` 안의 폴더) 안의 `.txt` 하나 = 책 하나. `pages` 루트는 경로에서 자동으로 찾는다. 파일 안에서 `======` 대분류 / `=====` 소주제 / `====` 글 + `{{page>ns:id}}` 참조. pandoc 필요. |
| **마크다운 → 마크다운** | 마크다운 폴더 안의 **하위 폴더 하나 = 책 하나**. 그 안의 폴더 = 장, 그 안의 폴더 = 소주제, `.md` = 글. 폴더 밖의 `.md`는 한 페이지짜리 책. |

마크다운 소스 세부:
- 이름 앞의 `01 `, `02_` 는 순서에만 쓰이고 제목에서는 빠진다.
- 노트 맨 위 `title:` (YAML frontmatter)가 있으면 그것을 글 제목으로 쓴다.
- 이미지 `![](img/a.png)` 와 Obsidian식 `![[a.png]]` 는 자동으로 사이트에 복사된다.
- 점(`.`)이나 밑줄(`_`)로 시작하는 파일/폴더는 무시한다.
- 4단계보다 깊은 폴더는 "폴더 - 글" 제목으로 펼쳐진다.

책을 지우려면 소스 파일/폴더만 지우면 된다 (다음 빌드에서 산출물도 정리됨).

## 설정 파일 (설정 창이 만들어 준다)

- `config.json` — 이 컴퓨터 전용(경로, pandoc, 자동 push 여부). **git에 올라가지 않는다.**
- `site.json` — 사이트 제목/소개/언어/댓글(giscus). 저장소에 함께 올라가고 GitHub Actions 빌드도 읽는다.

## 구조

- `tools/config.py` — 설정 읽기/쓰기, `tools/settings_gui.py` — 설정 창.
- `tools/build_books.py` — 핵심 변환기. `tools/markdown_source.py` — 마크다운 폴더를 변환기 입력으로 바꾸는 어댑터.
- `tools/build_library.py` — 서재 첫 페이지(`docs/index.md`) 생성.
- `docs/.vitepress/config.mjs` — `site.json`/`books.json`/`sidebar.json`으로 nav·사이드바 구성.
- `.github/workflows/deploy.yml` — `main`에 push되면 빌드 후 Pages 배포.

## 의존성

- Python 3 (tkinter 포함, 윈도우 기본 설치본이면 됨).
- pandoc — **도쿠위키 소스를 쓸 때만** 필요 (`winget install pandoc`).
- 로컬 미리보기(선택): `npm install` 후 `npx vitepress dev docs`.
