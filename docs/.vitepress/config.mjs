import { defineConfig } from 'vitepress'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const sidebarDomains = JSON.parse(
  readFileSync(resolve(__dirname, '../../sidebar.json'), 'utf-8')
)

// VitePress wants one sidebar config per top-level path prefix; since every
// domain is its own top-level folder, map each domain's own items under its
// own path key so the sidebar changes as you navigate between domains.
const sidebar = {}
for (const domain of sidebarDomains) {
  sidebar[`/${domain.text}/`] = [domain]
}

export default defineConfig({
  title: 'iamtalker',
  description: '존재에서 세계까지 — 개인 철학 전집',
  lang: 'ko-KR',
  base: '/',
  cleanUrls: true,
  themeConfig: {
    nav: sidebarDomains.map((d) => ({ text: d.text, link: `/${d.text}/` })),
    sidebar,
    search: { provider: 'local' },
    outline: { label: '이 글의 목차' },
    docFooter: { prev: '이전 글', next: '다음 글' },
    returnToTopLabel: '맨 위로',
  },
})
