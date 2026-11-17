<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const day = ref('')
const currentDay = ref('')
const msg = ref('')
const err = ref('')
const blocked = ref([])
const router = useRouter()

onMounted(async () => {
  const d = await api.getDay()
  day.value = d.business_day
  currentDay.value = d.business_day
})

async function save() {
  msg.value = ''; err.value = ''; blocked.value = []
  try {
    const r = await api.setDay(day.value)
    msg.value = `拨钟成功：${currentDay.value} → ${r.business_day}`
    currentDay.value = r.business_day
  } catch (e) {
    err.value = e.message
    // 有未封则拒拨：钟面不变，回执列出未封日，须先封账后才能再拨。
    if (e.status === 409 && e.data && e.data.detail && Array.isArray(e.data.detail.unsealed_days)) {
      blocked.value = e.data.detail.unsealed_days
      if (e.data.detail.business_day) currentDay.value = e.data.detail.business_day
    }
  }
}

function goSeal(d) {
  router.push({ path: '/close', query: { day: d } })
}
</script>

<template>
  <h2>设置 · 营业日拨钟</h2>
  <p class="msg">当前钟面营业日：{{ currentDay }}</p>
  <div class="row">
    <label>目标营业日 <input v-model="day" placeholder="YYYY-MM-DD" /></label>
    <button class="btn" @click="save">拨钟</button>
  </div>
  <p class="msg">互斥规则：向前拨钟时，若存在更早的未封账营业日，拨钟将被拒绝且钟面不变；须先在封账台收口。</p>
  <p v-if="msg" class="msg">{{ msg }}</p>
  <p v-if="err" class="msg err">{{ err }}</p>

  <div class="panel" v-if="blocked.length">
    <h2>拦截回执：未封营业日（{{ blocked.length }}）</h2>
    <table>
      <thead>
        <tr><th>营业日</th><th>系统合计预览</th><th>笔数</th><th>草稿失败</th><th>封账入口</th></tr>
      </thead>
      <tbody>
        <tr v-for="u in blocked" :key="u.business_day">
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
  </div>
</template>
