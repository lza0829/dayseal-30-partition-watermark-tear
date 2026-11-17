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

// 四数同源（水位力）：钟面、钉扎水位、可写上界、可封目标均由后端
// watermark.clock_snapshot 一次派生，前端只展示、不自行推算。
function wmText(d) {
  return d.sealed_watermark || '尚无 sealed 分区'
}
</script>

<template>
  <section class="hero">
    <h1>日封台</h1>
    <p>把当日收银流水钉进营业日封账：系统合计与实盘对齐，封账后流水不可再改。</p>
  </section>
  <p v-if="err" class="msg err">{{ err }}</p>
  <div class="stats" v-if="dash">
    <div class="stat"><div class="label">营业日（钟面）</div><div class="value">{{ dash.business_day }}</div></div>
    <div class="stat"><div class="label">钉扎水位（最近 sealed）</div><div class="value">{{ wmText(dash) }}</div></div>
    <div class="stat"><div class="label">流水可写上界</div><div class="value">{{ dash.writable_upper_bound }}</div></div>
    <div class="stat"><div class="label">封账可封目标</div><div class="value">{{ dash.seal_target }}</div></div>
    <div class="stat"><div class="label">今日流水笔数</div><div class="value">{{ dash.line_count_today }}</div></div>
    <div class="stat"><div class="label">系统合计</div><div class="value">{{ dash.system_total_today.toFixed(2) }}</div></div>
    <div class="stat"><div class="label">封账状态</div><div class="value">{{ dash.sealed_today ? '已封' : '未封' }}</div></div>
  </div>
  <p class="msg" v-if="dash">
    同源约束：钟面 = 可写上界 = 可封目标 = {{ dash.business_day }}；
    钉扎水位仅由真实封账推进（{{ wmText(dash) }}），回拨钟面不会伪造水位。
  </p>

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
