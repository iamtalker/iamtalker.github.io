import DefaultTheme from 'vitepress/theme'
import { h } from 'vue'
import { useData } from 'vitepress'
import Giscus from './Giscus.vue'

// Only show comments on an actual essay page, not on a domain/book/library
// index (those set `giscus: false` in frontmatter - see build_site.py's
// write_domain_index() and build_book_index.py/build_library.py, which use
// `layout: home` and so never hit the doc-after slot at all anyway, but
// domain index pages use the plain doc layout, hence the explicit flag).
const GiscusSlot = {
  setup() {
    const { frontmatter } = useData()
    return () => (frontmatter.value.giscus === false ? null : h(Giscus))
  },
}

export default {
  extends: DefaultTheme,
  Layout() {
    return h(DefaultTheme.Layout, null, {
      'doc-after': () => h(GiscusSlot),
    })
  },
}
