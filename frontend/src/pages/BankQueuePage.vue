<script setup>
import PageHeading from '../components/PageHeading.vue'
import AppIcon from '../components/AppIcon.vue'
import { money } from '../data/demo'

defineProps({ cases: Array })
defineEmits(['open'])
</script>

<template>
  <PageHeading
    title="Кредитный конвейер"
    description="Очередь заявок малого и микробизнеса · демоданные"
  />
  <div class="grid3 mb">
    <div class="card bank-metric">
      <span class="overview-icon"><AppIcon name="applications" /></span>
      <div>
        <div class="small muted">Всего заявок</div>
        <div class="stat">{{ cases.length }}</div>
      </div>
    </div>
    <div class="card bank-metric">
      <span class="overview-icon accent"><AppIcon name="clock" /></span>
      <div>
        <div class="small muted">Без деморешения</div>
        <div class="stat">
          {{ cases.filter((item) => !item.decision).length }}
        </div>
      </div>
    </div>
    <div class="card bank-metric">
      <span class="overview-icon"><AppIcon name="detail" /></span>
      <div>
        <div class="small muted">Требуют внимания</div>
        <div class="stat">
          {{
            cases.filter((item) => item.score < 620 && !item.decision).length
          }}
        </div>
      </div>
    </div>
  </div>
  <div class="card">
    <b>Очередь заявок</b>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Компания</th>
            <th>Сумма</th>
            <th>Скоринг</th>
            <th>Решение</th>
            <th>Действие</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in cases" :key="item.id">
            <td>
              <b>{{ item.company }}</b>
              <div class="muted">{{ item.id }}</div>
            </td>
            <td>{{ money(item.amount) }}</td>
            <td>
              <b>{{ item.score }}</b>
              <div>
                <span
                  class="pill"
                  :class="item.score >= 620 ? 'success' : 'pending'"
                  >{{ item.risk }} риск</span
                >
              </div>
            </td>
            <td>
              <span class="pill" :class="{ success: item.decision }">{{
                item.decision || 'Ожидает решения'
              }}</span>
            </td>
            <td>
              <button
                class="link"
                :aria-label="`Открыть заявку ${item.id}`"
                @click="$emit('open', item.id)"
              >
                Открыть →
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
