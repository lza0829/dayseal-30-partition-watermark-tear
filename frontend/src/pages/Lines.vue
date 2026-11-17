<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const rows = ref([])
const tills = ref([])
const day = ref('')
const clockDay = ref('')
const form = ref({ till_code: 'TILL-A', amount: 10, pay_method: '现金', note: '' })
const msg = ref('')
const err = ref('')

async function load() {
  err.value = ''
  const d = await api.getDay()
  clockDay.value = d.business_day
  if (!day.value) day.value = clockDay.value
  tills.value = await api.tills()
  rows.value = await api.lines(day.value)
}

async function add() {
  msg.value = ''; err.value = ''
  try {
    await api.createLine({ ...form.value, business_day: day.value })
    msg.value = `已登记流水（营业日 ${day.value}）`
    await load()
  } catch (e) { err.value = e.message }
}

onMounted(load)
</script>

<template>
  <h2>收银流水</h2>
  <div class="row">
    <label>营业日（未封日可补流水，已封日禁写）
      <input v-model="day" placeholder="YYYY-MM-DD" />
    </label>
    <button class="btn ghost" @click="day = clockDay; load()">回到当前钟面 {{ clockDay }}</button>
  </div>
  <div class="row">
    <label>收银机
      <select v-model="form.till_code">
        <option v-for="t in tills" :key="t.till_code" :value="t.till_code">{{ t.title }}</option>
      </select>
    </label>
    <label>金额 <input type="number" step="0.01" v-model.number="form.amount" /></label>
    <label>支付方式
      <select v-model="form.pay_method">
        <option>现金</option><option>微信</option><option>支付宝</option>
      </select>
    </label>
    <button class="btn" @click="add">登记</button>
  </div>
  <p v-if="msg" class="msg">{{ msg }}</p>
  <p v-if="err" class="msg err">{{ err }}</p>
  <div class="panel">
    <table>
      <thead><tr><th>单号</th><th>机</th><th>时刻</th><th>金额</th><th>方式</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td>{{ r.line_no }}</td><td>{{ r.till_code }}</td><td>{{ r.occurred_at }}</td>
          <td>{{ r.amount.toFixed(2) }}</td><td>{{ r.pay_method }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
