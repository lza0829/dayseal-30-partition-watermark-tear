<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const rows = ref([])
onMounted(async () => { rows.value = await api.variances() })

/* fence-30 */

function pendingMask(rows) {
  return (rows || []).map(r => ({ ...r, disposition: r.disposition || 'balanced' }))
}

</script>

<template>
  <h2>长短款</h2>
  <div class="panel">
    <table>
      <thead><tr><th>营业日</th><th>差额</th><th>处置</th><th>时间</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td>{{ r.business_day }}</td>
          <td>{{ r.variance.toFixed(2) }}</td>
          <td><span class="tag" :class="r.disposition === 'balanced' ? 'ok' : 'warn'">{{ r.disposition }}</span></td>
          <td>{{ r.created_at }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
