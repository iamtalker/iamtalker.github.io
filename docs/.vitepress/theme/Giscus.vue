<script setup>
import { onMounted, onUnmounted, watch, ref } from 'vue'
import { useRoute } from 'vitepress'
import { useData } from 'vitepress'
import site from '../../../site.json'

const route = useRoute()
const { isDark } = useData()
const el = ref(null)

// comments are configured in site.json ("giscus"), written by the settings
// window. Left blank, no comment box is shown at all.
const G = site.giscus || {}
const REPO = G.repo
const REPO_ID = G.repoId
const CATEGORY = G.category || 'Announcements'
const CATEGORY_ID = G.categoryId
const enabled = !!(REPO && REPO_ID && CATEGORY_ID)

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
  script.setAttribute('data-mapping', 'pathname')
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

onMounted(loadGiscus)
// giscus maps one discussion per page path, so a client-side route change
// (VitePress is an SPA) needs a fresh embed, not just a re-render.
watch(() => route.path, loadGiscus)
watch(isDark, sendThemeToGiscus)
</script>

<template>
  <div v-if="enabled" class="giscus-wrap" ref="el"></div>
</template>

<style>
.giscus-wrap {
  margin-top: 48px;
  padding-top: 32px;
  border-top: 1px solid var(--vp-c-divider);
}
</style>
