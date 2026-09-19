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

// VitePress wants one sidebar config per top-level path prefix. Every
// top-level ("chapter") entry - container ({text, items}, its own
// folder with sub-pages) or leaf ({text, link}, a single page, maybe
// with its own heading sub-tree) alike - gets the SAME focused sidebar:
// itself plus "이전 장 / 다음 장" links to its neighbors, not the whole
// book's flat chapter list. (Leaves used to get the whole list, back
// when a leaf had nothing of its own to show; now that a leaf can carry
// its own heading sub-tree, that list stopped being just a static
// index - VitePress keeps its sidebar item components alive across
// client-side navigation, so their "expanded" state persists with
// them, and since every leaf route pointed at the exact same list of
// domain objects, expanding one leaf's tree left it stuck open on
// every OTHER leaf's page too, compounding the more pages you visited.
// A focused per-domain list, matching what containers already did,
// sidesteps this entirely - and makes every chapter behave the same
// way, container or leaf.)
const sidebarEntries = []
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

    const items = []
    if (prevDomain) items.push({ text: `← 이전 장: ${prevDomain.text}`, link: domainLink(prevDomain) })
    items.push(domain)
    if (nextDomain) items.push({ text: `다음 장: ${nextDomain.text} →`, link: domainLink(nextDomain) })
    const key = domain.link ? `/${bookSlug}/${domain.text}` : `/${bookSlug}/${domain.text}/`
    sidebarEntries.push([key, items])
  })
}
// VitePress resolves a route's sidebar by finding the first registered
// key (among those tied for the most "/"-separated segments) that the
// route STARTS WITH - a plain string prefix check with no path-segment
// boundary awareness. Two sibling leaves whose names happen to share a
// prefix (e.g. "여성혐오" and "여성혐오_주장과_그에_대한_반론" both live
// directly under the book, so both keys have the same segment count)
// tie, and ties fall back to insertion order - so "여성혐오"'s key,
// inserted first, was silently swallowing "여성혐오_주장과..."'s route
// too, showing the wrong domain's sidebar entirely. Inserting longer
// keys first guarantees a more specific key is always found before a
// shorter one that happens to be its textual prefix.
const sidebar = {}
for (const [key, items] of sidebarEntries.sort((a, b) => b[0].length - a[0].length)) {
  sidebar[key] = items
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
    // the left sidebar now shows each page's own heading tree too (see
    // build_heading_sidebar in build_books.py), which made this in-page
    // outline pure duplication - removed rather than kept redundant.
    outline: false,
    docFooter: { prev: '이전 글', next: '다음 글' },
    returnToTopLabel: '맨 위로',
  },
})
