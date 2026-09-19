import { defineConfig } from 'vitepress'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const BOOK_SLUG = '자유로의 초대'
const sidebarDomains = JSON.parse(
  readFileSync(resolve(__dirname, '../../sidebar.json'), 'utf-8')
)
const books = JSON.parse(
  readFileSync(resolve(__dirname, '../../books.json'), 'utf-8')
)

// VitePress wants one sidebar config per top-level path prefix; since every
// domain is its own folder under the book's path, map each domain's own
// items under its own path key so the sidebar changes as you navigate
// between domains. Only 자유로의 초대 has content right now - a future
// book's build script would add its own entries here the same way.
//
// Each domain's sidebar also gets a "이전 장 / 다음 장" link above and
// below its own item group, so you can jump straight to the neighboring
// chapter from the sidebar without needing to be on its last/first post.
const sidebar = {}
sidebarDomains.forEach((domain, i) => {
  const items = []
  if (i > 0) {
    const prevDomain = sidebarDomains[i - 1]
    items.push({ text: `← 이전 장: ${prevDomain.text}`, link: `/${BOOK_SLUG}/${prevDomain.text}/` })
  }
  items.push(domain)
  if (i < sidebarDomains.length - 1) {
    const nextDomain = sidebarDomains[i + 1]
    items.push({ text: `다음 장: ${nextDomain.text} →`, link: `/${BOOK_SLUG}/${nextDomain.text}/` })
  }
  sidebar[`/${BOOK_SLUG}/${domain.text}/`] = items
})

export default defineConfig({
  title: 'iamtalker',
  description: '개인 글 모음',
  lang: 'ko-KR',
  base: '/',
  cleanUrls: true,
  themeConfig: {
    nav: books.map((b) => ({ text: b.slug, link: `/${b.slug}/` })),
    sidebar,
    search: { provider: 'local' },
    outline: { label: '이 글의 목차' },
    docFooter: { prev: '이전 글', next: '다음 글' },
    returnToTopLabel: '맨 위로',
  },
})
