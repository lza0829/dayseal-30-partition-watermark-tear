<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const stations = [
  { to: '/', no: '01', label: '总览', hint: '今日钉扎' },
  { to: '/lines', no: '02', label: '流水', hint: '收银入账' },
  { to: '/close', no: '03', label: '封账', hint: '日结锁定' },
  { to: '/variance', no: '04', label: '长短款', hint: '差额处置' },
]

function active(to) {
  if (to === '/') return route.path === '/'
  return route.path.startsWith(to)
}

const current = computed(() => {
  if (route.path.startsWith('/settings')) return { no: '·', label: '设置', hint: '营业日' }
  return stations.find((s) => active(s.to)) || stations[0]
})
</script>

<template>
  <div class="shell">
    <aside class="rail" aria-label="日封台导航">
      <router-link class="mark" to="/" aria-label="Dayseal 日封台">
        <span class="mark-en">Dayseal</span>
        <span class="mark-cn">日封台</span>
      </router-link>

      <nav class="stations">
        <router-link
          v-for="s in stations"
          :key="s.to"
          :to="s.to"
          class="station"
          :class="{ on: active(s.to) }"
        >
          <span class="no">{{ s.no }}</span>
          <span class="lab">
            <strong>{{ s.label }}</strong>
            <small>{{ s.hint }}</small>
          </span>
        </router-link>
      </nav>

      <router-link to="/settings" class="rail-foot" :class="{ on: route.path.startsWith('/settings') }">
        设置 · 营业日
      </router-link>
    </aside>

    <div class="stage">
      <div class="stage-strip" aria-hidden="true">
        <span>{{ current.no }}</span>
        <span class="strip-label">{{ current.label }}</span>
        <span class="strip-hint">{{ current.hint }}</span>
      </div>
      <main class="main">
        <router-view />
      </main>
    </div>
  </div>
</template>
