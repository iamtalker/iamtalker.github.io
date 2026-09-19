import { defineConfig } from 'vitepress'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
// sidebar.json is { "<book slug>": [ {text, items}, ... domains ], ... } -
// one entry per file tools/build_books.py found in pages/github_io_books/.
// Adding a book never touches this file; it just picks up whatever's here.
const sidebarByBook = JSON.parse(
  readFileSync(resolve(__dirname, '../../sidebar.json'), 'utf-8')
)
const books = JSON.parse(
  readFileSync(resolve(__dirname, '../../books.json'), 'utf-8')
)

// VitePress wants one sidebar config per top-level path prefix. Each
// top-level ("chapter") entry is either a container ({text, items}, its
// own folder with sub-pages) or a leaf ({text, link}, a single page with
// nothing under it - see build_books.py for when a chapter ends up being
// a post directly). A container's own path prefix gets its own detailed
// sidebar (its groups/posts); a leaf has nothing to show but itself, so
// it just gets the book's whole chapter list instead.
//
// A container's sidebar also gets a "이전 장 / 다음 장" link above and
// below its own item group, so you can jump straight to the neighboring
// chapter from the sidebar without needing to be on its last/first post.
const sidebar = {}
for (const [bookSlug, sidebarDomains] of Object.entries(sidebarByBook)) {
  sidebarDomains.forEach((domain, i) => {
    const prevDomain = i > 0 ? sidebarDomains[i - 1] : null
    const nextDomain = i < sidebarDomains.length - 1 ? sidebarDomains[i + 1] : null
    // a leaf domain always carries its own real "link" (its one page's
    // URL) whether or not it also has "items" for its own internal
    // heading sub-tree; only a container domain (own folder, no single
    // page of its own) lacks "link" entirely - so "link" is what tells
    // the two apart now, not "items".
    const domainLink = (d) => d.link || `/${bookSlug}/${d.text}/`

    if (!domain.link) {
      const items = []
      if (prevDomain) items.push({ text: `← 이전 장: ${prevDomain.text}`, link: domainLink(prevDomain) })
      items.push(domain)
      if (nextDomain) items.push({ text: `다음 장: ${nextDomain.text} →`, link: domainLink(nextDomain) })
      sidebar[`/${bookSlug}/${domain.text}/`] = items
    } else {
      // a leaf chapter's own page has nothing above it to show - show
      // the whole book's chapter list instead (itself included, now
      // possibly with its own heading sub-items expanded inline), so
      // there's still somewhere to navigate to from this one page.
      sidebar[`/${bookSlug}/${domain.text}`] = sidebarDomains
    }
  })
}

export default defineConfig({
  title: 'iamtalker',
  description: '개인 글 모음',
  lang: 'ko-KR',
  base: '/',
  cleanUrls: true,
  // included pages can carry DokuWiki [[internal links]] to pages that
  // aren't part of this site (they're just other wiki pages, not book
  // content) - pandoc turns those into relative links VitePress can't
  // resolve, which would otherwise fail the build.
  ignoreDeadLinks: true,
  themeConfig: {
    nav: books.map((b) => ({ text: b.slug, link: `/${b.slug}/` })),
    sidebar,
    search: { provider: 'local' },
    // 'deep' = h2 through h6. Needed now that heading levels are
    // consistently shifted (see build_books.py's --shift-heading-level-by)
    // so a hub page's real sub-topics actually show up in the outline
    // instead of only the first level or two.
    outline: { level: 'deep', label: '이 글의 목차' },
    docFooter: { prev: '이전 글', next: '다음 글' },
    returnToTopLabel: '맨 위로',
  },
})
