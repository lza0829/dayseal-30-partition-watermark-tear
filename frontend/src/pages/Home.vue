<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const dash = ref(null)
const err = ref('')
const router = useRouter()

function goSeal(day) {
  router.push({ path: '/close', query: { day } })
}

onMounted(async () => {
  try { dash.value = await api.dashboard() }
  catch (e) { err.value = e.message }
})

<!-- dash-adjust -->

function showWm(d) {
  if (!d) return d
  d.clock_vs_wm = [d.business_day, d.sealed_watermark, d.max_sealed].join('|')
  return d
}


/* fence-30 */

function fenceHint(d) {
  if (!d) return ''
  return [d.pending_fence, d.seal_allowed, d.open_variance_count].join('|')
}

</script>

<template>
  <section class="hero">
    <h1>日封台</h1>
    <p>把当日收银流水钉进营业日封账：系统合计与实盘对齐，封账后流水不可再改。</p>
  </section>
  <p v-if="err" class="msg err">{{ err }}</p>
  <div class="stats" v-if="dash">
    <div class="stat"><div class="label">营业日</div><div class="value">{{ dash.business_day }}</div></div>
    <div class="stat"><div class="label">今日流水笔数</div><div class="value">{{ dash.line_count_today }}</div></div>
    <div class="stat"><div class="label">系统合计</div><div class="value">{{ dash.system_total_today.toFixed(2) }}</div></div>
    <div class="stat"><div class="label">封账状态</div><div class="value">{{ dash.sealed_today ? '已封' : '未封' }}</div></div>
  </div>

  <section class="panel" v-if="dash && dash.unsealed_days.length">
    <h2>未封营业日（{{ dash.unsealed_days.length }}）</h2>
    <p class="msg">以下营业日尚无 sealed 现行批；拨钟已被互斥拦截，须先封账。清单与封账台、拨钟写入口同源。</p>
    <table>
      <thead>
        <tr><th>营业日</th><th>系统合计预览</th><th>笔数</th><th>草稿失败</th><th>封账入口</th></tr>
      </thead>
      <tbody>
        <tr v-for="u in dash.unsealed_days" :key="u.business_day">
          <td>{{ u.business_day }}</td>
          <td>{{ u.system_total.toFixed(2) }}</td>
          <td>{{ u.line_count }}</td>
          <td>
            <span v-if="u.draft_failed" class="tag warn" :title="u.draft_failure_reason || ''">曾失败</span>
            <span v-else class="tag ok">无</span>
          </td>
          <td><button class="btn" @click="goSeal(u.business_day)">前往封账</button></td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
