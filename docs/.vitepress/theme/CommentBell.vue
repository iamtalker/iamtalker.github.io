<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import site from '../../../site.json'

// A bell in the nav bar that lists the newest comments. The list is a small
// JSON file kept up to date by .github/workflows/comments.yml on the
// "comments-data" branch - the site itself is not rebuilt for a comment.
//
// site.json "commentBell":
//   "owner" (default)  shown only in browsers that opened any page once with ?admin=1
//   "all"              shown to every visitor
//   "off"              never shown
const G = site.giscus || {}
const REPO = (G.repo || '').trim().replace(/^https?:\/\/github\.com\//, '').replace(/\.git$/, '').replace(/\/$/, '')
const MODE = site.commentBell || 'owner'

const show = ref(false)
const open = ref(false)
const items = ref([])
const seen = ref(0)

const store = {
  get: (k) => { try { return localStorage.getItem(k) } catch { return null } },
  set: (k, v) => { try { localStorage.setItem(k, v) } catch {} },
}

// notifications the visitor cleared: remembered in this browser only (the comments
// themselves stay on GitHub; delete them there)
const hidden = ref([])
const visible = computed(() => items.value.filter((c) => !hidden.value.includes(c.url)))
const unread = computed(() => visible.value.filter((c) => Date.parse(c.createdAt) > seen.value))

function saveHidden() {
  hidden.value = hidden.value.slice(-300)   // enough; comments older than the 20 listed drop out anyway
  store.set('cb-hidden', JSON.stringify(hidden.value))
}

function dismiss(c) {
  if (!hidden.value.includes(c.url)) hidden.value.push(c.url)
  saveHidden()
}

function clearAll() {
  markAllRead()
  for (const c of visible.value) hidden.value.push(c.url)
  saveHidden()
}

function ago(iso) {
  const m = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000))
  if (m < 1) return '방금'
  if (m < 60) return `${m}분 전`
  if (m < 1440) return `${Math.round(m / 60)}시간 전`
  return `${Math.round(m / 1440)}일 전`
}

// giscus names each discussion after the page path (URL-encoded in older lists)
const pageName = (c) => { try { return decodeURIComponent(c.page) } catch { return String(c.page) } }
const pageLink = (c) => '/' + pageName(c).replace(/^\/+/, '') + '#giscus-comments'  // land on the comment box, not the top

function onPick() {
  open.value = false
  // same page: the address changes without a page change, so tell the comment box to jump
  setTimeout(() => window.dispatchEvent(new Event('hashchange')), 60)
}

function markAllRead() {
  if (!items.value.length) return
  seen.value = Math.max(...items.value.map((c) => Date.parse(c.createdAt)))
  store.set('cb-seen', String(seen.value))
}

// the list is read when the page opens, then again every minute while the tab
// is visible and whenever the tab comes back to the front - so a comment that
// arrives while the page is open shows up without a reload
async function load() {
  try {
    // the time value keeps GitHub's CDN from serving an old copy for long.
    // ?cb-src=/some.json (a path on this site only) swaps in another list, for testing.
    const own = new URLSearchParams(location.search).get('cb-src')
    let res
    if (own && own.startsWith('/') && !own.startsWith('//')) {
      res = await fetch(own, { cache: 'no-store' })
    } else {
      // GitHub's API serves the file with a 60 s cache (raw.githubusercontent.com holds
      // on to an old copy for ~5 min, whatever is appended to the address), and an
      // unchanged file comes back as a cheap 304 that does not count against the rate limit
      res = await fetch(`https://api.github.com/repos/${REPO}/contents/recent-comments.json?ref=comments-data`,
        { headers: { Accept: 'application/vnd.github.raw+json' }, cache: 'no-cache' }).catch(() => null)
      if (!res || !res.ok) {   // rate-limited or blocked: fall back to the raw file
        res = await fetch(`https://raw.githubusercontent.com/${REPO}/comments-data/recent-comments.json?t=${Math.floor(Date.now() / 20000)}`,
          { cache: 'no-store' })
      }
    }
    if (res.ok) items.value = (await res.json()).comments || []
  } catch {}
}

let timer = null
const onVisible = () => { if (document.visibilityState === 'visible') load() }

onMounted(() => {
  if (!REPO || MODE === 'off') return
  if (new URLSearchParams(location.search).get('admin') === '1') store.set('cb-admin', '1')
  if (MODE === 'owner' && store.get('cb-admin') !== '1') return
  show.value = true
  seen.value = Number(store.get('cb-seen') || 0)
  try { hidden.value = JSON.parse(store.get('cb-hidden') || '[]') } catch { hidden.value = [] }
  load()
  timer = setInterval(onVisible, 60000)
  document.addEventListener('visibilitychange', onVisible)
})

onUnmounted(() => {
  clearInterval(timer)
  document.removeEventListener('visibilitychange', onVisible)
})
</script>

<template>
  <div v-if="show" class="cbell">
    <button class="cbell-btn" type="button" :title="unread.length ? `새 댓글 ${unread.length}개` : '최근 댓글'" @click="open = !open">
      🔔<span v-if="unread.length" class="cbell-badge">{{ unread.length }}</span>
    </button>
    <div v-if="open" class="cbell-pop">
      <div class="cbell-head">
        <strong>최근 댓글</strong>
        <span>
          <button type="button" class="cbell-link" @click="markAllRead">모두 읽음</button>
          <button type="button" class="cbell-link" title="이 브라우저의 알림 목록만 비웁니다. GitHub의 댓글은 그대로입니다." @click="clearAll">모두 지우기</button>
        </span>
      </div>
      <p v-if="!visible.length" class="cbell-empty">{{ items.length ? '표시할 알림이 없습니다.' : '아직 댓글이 없습니다.' }}</p>
      <ul v-else>
        <li v-for="c in visible" :key="c.url" :class="{ fresh: Date.parse(c.createdAt) > seen }">
          <a :href="pageLink(c)" @click="onPick">
            <span class="cbell-meta">{{ c.author }} · {{ ago(c.createdAt) }}</span>
            <span class="cbell-text">{{ c.text }}</span>
            <span class="cbell-page">{{ pageName(c) }}</span>
          </a>
          <span class="cbell-side">
            <a class="cbell-gh" :href="c.url" target="_blank" rel="noopener" title="GitHub에서 답글 달기">↗</a>
            <button type="button" class="cbell-x" title="이 알림 지우기" @click.stop="dismiss(c)">✕</button>
          </span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style>
.cbell { position: relative; margin-left: 8px; }
.cbell-btn { position: relative; padding: 4px 8px; font-size: 18px; line-height: 1; cursor: pointer; }
.cbell-badge {
  position: absolute; top: -2px; right: -2px; min-width: 16px; padding: 0 4px;
  border-radius: 8px; background: var(--vp-c-danger-1, #e5484d); color: #fff;
  font-size: 11px; line-height: 16px; text-align: center;
}
.cbell-pop {
  position: absolute; right: 0; top: 36px; z-index: 50; width: 340px; max-height: 70vh; overflow-y: auto; overflow-x: hidden;
  white-space: normal; text-align: left; /* the nav bar sets nowrap */
  background: var(--vp-c-bg); border: 1px solid var(--vp-c-divider); border-radius: 8px;
  box-shadow: var(--vp-shadow-3); padding: 8px 0;
}
.cbell-head { display: flex; justify-content: space-between; align-items: center; padding: 4px 14px 8px; }
.cbell-link { color: var(--vp-c-brand-1); font-size: 13px; cursor: pointer; }
.cbell-link + .cbell-link { margin-left: 10px; }
.cbell-side { flex: none; display: flex; flex-direction: column; align-items: center; padding: 4px 6px 0 0; }
.cbell-x { padding: 2px 8px; font-size: 12px; color: var(--vp-c-text-3); cursor: pointer; }
.cbell-x:hover { color: var(--vp-c-danger-1, #e5484d); }
.cbell-empty { padding: 8px 14px; color: var(--vp-c-text-2); font-size: 14px; }
.cbell-pop ul { list-style: none; margin: 0; padding: 0; }
.cbell-pop li { display: flex; align-items: flex-start; border-top: 1px solid var(--vp-c-divider); }
.cbell-pop li.fresh { background: var(--vp-c-brand-soft); }
.cbell-pop li > a:first-child { flex: 1; min-width: 0; display: block; padding: 8px 14px; text-decoration: none; color: var(--vp-c-text-1); }
.cbell-meta { display: block; font-size: 12px; color: var(--vp-c-text-2); }
.cbell-text { display: block; font-size: 14px; line-height: 1.4; margin: 2px 0; overflow-wrap: anywhere; }
.cbell-page { display: block; font-size: 12px; color: var(--vp-c-brand-1); }
.cbell-gh { flex: none; padding: 8px 10px; color: var(--vp-c-text-2); text-decoration: none; }
@media (max-width: 767px) { .cbell-pop { position: fixed; left: 8px; right: 8px; top: 56px; width: auto; } }
</style>
