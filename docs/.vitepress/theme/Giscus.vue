<script setup>
import { nextTick, onMounted, onUnmounted, watch, ref } from 'vue'
import { useRoute } from 'vitepress'
import { useData } from 'vitepress'
import site from '../../../site.json'

const route = useRoute()
const { isDark } = useData()
const el = ref(null)

// Arrived through a #giscus-comments link (the comment bell): the comment box is
// still empty at that moment, so the page is too short to bring its top to the top
// of the screen. While that hash is active it gets room, and we scroll to it
// ourselves once the room is there (VitePress scrolls before it exists).
// (VitePress's route object has no hash, hence location.hash.)
const jumped = ref(false)
function syncJump() {
  jumped.value = location.hash === '#giscus-comments'
  if (jumped.value) nextTick(() => el.value && el.value.scrollIntoView({ block: 'start' }))
}

// comments are configured in site.json ("giscus"), written by the settings
// window. Left blank, no comment box is shown at all.
const G = site.giscus || {}
// giscus wants "owner/name"; tolerate a pasted clone URL ("https://github.com/owner/name.git")
const REPO = (G.repo || '').trim().replace(/^https?:\/\/github\.com\//, '').replace(/\.git$/, '').replace(/\/$/, '')
const REPO_ID = G.repoId
const CATEGORY = G.category || 'Announcements'
const CATEGORY_ID = G.categoryId
const enabled = !!(REPO && REPO_ID && CATEGORY_ID)

// the page path without the leading slash, decoded: "book name/post name"
function pageTerm() {
  const p = location.pathname.replace(/^\/+/, '')
  try { return decodeURIComponent(p) } catch { return p }
}

function loadGiscus() {
  if (!enabled || !el.value) return
  el.value.innerHTML = ''
  const script = document.createElement('script')
  script.src = 'https://giscus.app/client.js'
  script.async = true
  script.crossOrigin = 'anonymous'
  script.setAttribute('data-repo', REPO)
  script.setAttribute('data-repo-id', REPO_ID)
  script.setAttribute('data-category', CATEGORY)
  script.setAttribute('data-category-id', CATEGORY_ID)
  // One discussion per page, named after the page path. "pathname" would use the
  // browser's percent-encoded path (%EB%8B%A8...), which makes GitHub's discussion
  // titles unreadable for non-ASCII page names; "specific" lets us name it ourselves.
  script.setAttribute('data-mapping', 'specific')
  script.setAttribute('data-term', pageTerm())
  script.setAttribute('data-strict', '0')
  script.setAttribute('data-reactions-enabled', '1')
  script.setAttribute('data-emit-metadata', '0')
  script.setAttribute('data-input-position', 'bottom')
  script.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  script.setAttribute('data-lang', 'ko')
  el.value.appendChild(script)
}

function sendThemeToGiscus() {
  const iframe = document.querySelector('iframe.giscus-frame')
  if (!iframe) return
  iframe.contentWindow.postMessage(
    { giscus: { setConfig: { theme: isDark.value ? 'dark' : 'light' } } },
    'https://giscus.app'
  )
}

onMounted(() => {
  loadGiscus()
  syncJump()
  window.addEventListener('hashchange', syncJump)
})
onUnmounted(() => window.removeEventListener('hashchange', syncJump))
// giscus maps one discussion per page path, so a client-side route change
// (VitePress is an SPA) needs a fresh embed, not just a re-render.
watch(() => route.path, () => {
  loadGiscus()
  nextTick(syncJump)
})
watch(isDark, sendThemeToGiscus)
</script>

<template>
  <div v-if="enabled" id="giscus-comments" class="giscus-wrap" :class="{ jumped }" ref="el"></div>
</template>

<style>
.giscus-wrap.jumped { min-height: calc(100vh - 100px); }
.giscus-wrap {
  scroll-margin-top: 72px; /* the sticky nav bar must not cover the top when jumped to (#giscus-comments) */
  margin-top: 48px;
  padding-top: 32px;
  border-top: 1px solid var(--vp-c-divider);
}
</style>
