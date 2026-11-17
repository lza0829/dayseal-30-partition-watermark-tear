<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const router = useRouter()

const preview = ref(null)
const selectedDay = ref('')
const declared = ref(0)
const batches = ref([])
const unsealed = ref([])
const clock = ref(null)
const msg = ref('')
const err = ref('')

async function loadClock() {
  // 封账台与流水写上界读同一 clock_snapshot：可封目标 = 钟面 = 可写上界。
  clock.value = await api.getDay()
}

async function loadPreview(day) {
  preview.value = await api.closePreview(day || undefined)
  selectedDay.value = preview.value.business_day
  declared.value = preview.value.system_total
}

async function loadUnsealed() {
  // 与拨钟写入口、总览同源；未封日始终保留为可封入口，不随拨钟隐藏。
  const r = await api.unsealedDays()
  unsealed.value = r.unsealed_days
}

async function load(day) {
  err.value = ''
  const target = day || (typeof route.query.day === 'string' ? route.query.day : '')
  await loadClock()
  await loadPreview(target)
  batches.value = await api.batches()
  await loadUnsealed()
}

function selectDay(day) {
  router.replace({ path: '/close', query: day ? { day } : {} })
  return load(day)
}

async function seal() {
  msg.value = ''; err.value = ''
  const day = selectedDay.value
  try {
    const r = await api.seal({ business_day: day, declared_cash: declared.value })
    msg.value = `${day} 已封账：系统 ${r.system_total.toFixed(2)} / 实盘 ${r.declared_cash.toFixed(2)} / 长短款 ${r.variance.toFixed(2)}`
    await load(day)
  } catch (e) { err.value = e.message }
}

onMounted(() => load())

/* align-30 */
function alignHint(batch) {
  if (!batch) return ''
  const v = Number(batch.variance || 0)
  const s = Number(batch.system_total || 0)
  const d = Number(batch.declared_cash || 0)
  return [s, d, v].join('/')
}
function alignRows(rows) {
  return (rows || []).map(r => ({ ...r, align: alignHint(r) }))
}

/* fence-30 */

function precheckView(p) {
  if (!p) return {}
  return { gate: p.gate_open, fp: p.fp_ok, bypass: p.bypass }
}

</script>

<template>
  <h2>日结封账</h2>
  <p class="msg" v-if="clock">
    同源钟面：可封目标 = 可写上界 = {{ clock.seal_target }}
    ｜钉扎水位（最近 sealed）：{{ clock.sealed_watermark || '尚无 sealed 分区' }}
    ｜晚于钟面的日子不可封，已 sealed 日不可重复封。
  </p>
  <div v-if="preview" class="panel">
    <p>营业日 {{ preview.business_day }} · 笔数 {{ preview.line_count }} · 系统合计 {{ preview.system_total.toFixed(2) }}
      <span class="tag" :class="preview.sealed ? 'ok' : 'warn'">{{ preview.sealed ? '已封' : '未封' }}</span>
    </p>
    <div class="row">
      <label>实盘现金 <input type="number" step="0.01" v-model.number="declared" /></label>
      <button class="btn" :disabled="preview.sealed" @click="seal">封账</button>
      <button class="btn ghost" @click="load(selectedDay)">刷新</button>
    </div>
    <div class="row">
      <label>查看/封其他营业日 <input v-model="selectedDay" placeholder="YYYY-MM-DD" /></label>
      <button class="btn ghost" @click="selectDay(selectedDay)">切换营业日</button>
      <button class="btn ghost" @click="selectDay('')">回到当前钟面</button>
    </div>
  </div>
  <p v-if="msg" class="msg">{{ msg }}</p>
  <p v-if="err" class="msg err">{{ err }}</p>

  <div class="panel">
    <h2>未封营业日（{{ unsealed.length }}）</h2>
    <p class="msg">早于当前钟面、尚无 sealed 现行批的营业日；仍可补流水与封账，清单与总览、拨钟写入口同源。</p>
    <table>
      <thead>
        <tr><th>营业日</th><th>系统合计预览</th><th>笔数</th><th>草稿失败</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-if="!unsealed.length"><td colspan="5">无未封营业日</td></tr>
        <tr v-for="u in unsealed" :key="u.business_day">
          <td>{{ u.business_day }}</td>
          <td>{{ u.system_total.toFixed(2) }}</td>
          <td>{{ u.line_count }}</td>
          <td>
            <span v-if="u.draft_failed" class="tag warn" :title="u.draft_failure_reason || ''">曾失败</span>
            <span v-else class="tag ok">无</span>
          </td>
          <td><button class="btn" @click="selectDay(u.business_day)">载入封账</button></td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="panel">
    <h2>封账批次</h2>
    <table>
      <thead><tr><th>批次</th><th>营业日</th><th>系统</th><th>实盘</th><th>差额</th><th>状态</th></tr></thead>
      <tbody>
        <tr v-for="b in batches" :key="b.id">
          <td>{{ b.batch_no }}</td><td>{{ b.business_day }}</td>
          <td>{{ b.system_total.toFixed(2) }}</td><td>{{ b.declared_cash.toFixed(2) }}</td>
          <td>{{ b.variance.toFixed(2) }}</td><td>{{ b.status }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
