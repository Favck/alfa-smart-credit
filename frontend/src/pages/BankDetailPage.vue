<script setup>
import { ref, watch } from 'vue'
import PageHeading from '../components/PageHeading.vue'
import UiButton from '../components/UiButton.vue'
import AppIcon from '../components/AppIcon.vue'
import { money, products } from '../data/demo'
const props = defineProps({
  application: Object,
  history: Array,
  busy: Boolean,
})
defineEmits(['back', 'decision'])
const reason = ref('')
const verdict = ref('approve')
watch(
  () => props.application?.id,
  () => {
    reason.value = ''
  },
)
const date = (value) => new Date(value).toLocaleString('ru-RU')
</script>
<template>
  <button class="link mb" @click="$emit('back')">← Все заявки</button>
  <section v-if="!application" class="card empty-state">
    <AppIcon name="queue" />
    <h2>Нет выбранной заявки</h2>
    <p class="muted">Откройте обращение из очереди.</p>
  </section>
  <template v-else
    ><PageHeading
      :title="`Анализ заявки ${application.number}`"
      :description="application.company"
    />
    <div class="flex wrap mb">
      <span
        class="pill"
        :class="{ success: application.status === 'APPROVED' }"
        >{{ application.status_label }}</span
      ><span class="muted small"
        >{{ products.find((p) => p.id === application.productId)?.name }} ·
        {{ application.months }} мес.</span
      >
    </div>
    <div class="grid3 mb">
      <section class="card">
        <span class="muted small">Запрошенная сумма</span>
        <div class="stat">{{ money(application.amount) }}</div>
      </section>
      <section class="card">
        <span class="muted small">Скоринг · шкала 300–850</span>
        <div class="stat">{{ application.score ?? '—' }}</div>
      </section>
      <section class="card">
        <span class="muted small">Вероятность дефолта PD</span>
        <div class="stat">
          {{
            application.scoring?.pd != null
              ? (application.scoring.pd * 100).toFixed(2) + '%'
              : '—'
          }}
        </div>
      </section>
    </div>
    <div
      v-if="application.scoring_unavailable"
      class="app-feedback error-feedback mb"
      role="status"
    >
      Автоматический скоринг недоступен. Заявка сохранена для ручного
      рассмотрения; показатели модели отсутствуют.
    </div>
    <div class="grid2">
      <div class="stack">
        <section class="card">
          <div class="section-title">
            <h2>Что влияет на оценку</h2>
            <AppIcon name="detail" />
          </div>
          <p v-if="!application.scoring" class="muted">
            Результат модели отсутствует.
          </p>
          <div
            v-for="(factor, index) in application.scoring?.reasons || []"
            :key="index"
            class="risk-factor"
          >
            <div class="flex">
              <span>{{ factor.text }}</span
              ><b :class="factor.impact >= 0 ? 'positive' : 'red'"
                >{{ factor.impact > 0 ? '+' : '' }}{{ factor.impact }}</b
              >
            </div>
            <div class="risk-track">
              <span
                :class="{ negative: factor.impact < 0 }"
                :style="{
                  width: `${Math.min(100, Math.abs(factor.impact))}%`,
                }"
              ></span>
            </div>
          </div>
          <div v-if="application.scoring?.stop_factors.length" class="note">
            <b>Стоп-факторы ML</b>
            <ul>
              <li
                v-for="factor in application.scoring.stop_factors"
                :key="factor"
              >
                {{ factor }}
              </li>
            </ul>
          </div>
          <div v-if="application.scoring" class="line">
            <span class="muted">Рейтинг</span
            ><b> {{ application.scoring.grade || 'Не рассчитан' }}</b>
            <p class="small muted">
              Посильная сумма модели:
              {{
                application.scoring.max_affordable_amount != null
                  ? money(application.scoring.max_affordable_amount)
                  : 'Нет оценки'
              }}
            </p>
            <p class="small muted">
              Версия, заявленная ML: {{ application.scoring.model_version }}
            </p>
          </div>
          <p class="small muted mt">
            <span v-if="application.scoring?.stop_factors.length"
              >При стоп-факторе балл не рассчитывается, а PD возвращается
              моделью как служебное значение.
            </span>
            Модель использует ставку 22% для оценки риска. Её рекомендация не
            заменяет решение кредитной логики Django.
          </p>
        </section>
        <section class="card">
          <h3>Компания и сведения проверок</h3>
          <div class="line flex">
            <span class="muted">ИНН</span
            ><b>{{ application.companyData?.inn }}</b>
          </div>
          <div class="line flex">
            <span class="muted">Выручка / мес.</span
            ><b>{{ money(application.revenue) }}</b>
          </div>
          <div class="line flex">
            <span class="muted">Текущие платежи / мес.</span
            ><b>{{ money(application.payments) }}</b>
          </div>
          <template v-if="application.enrichment"
            ><div class="line flex">
              <span class="muted">Стаж бизнеса</span
              ><b>{{ application.enrichment.company_age_months }} мес.</b>
            </div>
            <div class="line flex">
              <span class="muted">Активные кредиты</span
              ><b>{{ application.enrichment.bki_active_loans }}</b>
            </div>
            <div class="line flex">
              <span class="muted">Максимальная просрочка</span
              ><b>{{ application.enrichment.bki_max_overdue_days }} дн.</b>
            </div>
            <p class="muted small mt">
              {{ application.enrichment.source }}
            </p></template
          >
        </section>
      </div>
      <div class="stack">
        <form
          class="card"
          @submit.prevent="$emit('decision', { verdict, reason })"
        >
          <h3>Решение по заявке</h3>
          <p class="muted small">
            Ручное решение доступно только для заявок на рассмотрении
            сотрудника. Оно сохранится в БД и истории клиента.
          </p>
          <label class="label" for="bank-reason">Обоснование решения</label
          ><textarea
            id="bank-reason"
            v-model="reason"
            class="field"
            required
            maxlength="2000"
            rows="4"
            :disabled="application.status !== 'REVIEW'"
            placeholder="Объясните причину решения клиенту"
          ></textarea>
          <div class="stack mt">
            <UiButton
              type="submit"
              :disabled="busy || application.status !== 'REVIEW'"
              @click="verdict = 'approve'"
              >Одобрить</UiButton
            ><UiButton
              type="submit"
              alt
              :disabled="busy || application.status !== 'REVIEW'"
              @click="verdict = 'reject'"
              >Отказать</UiButton
            >
          </div>
          <p v-if="application.status !== 'REVIEW'" class="note">
            {{ application.client_scoring?.explanation }}
          </p>
          <p class="muted small mt">
            Встречное предложение и запрос документов будут подключены на
            следующем этапе.
          </p>
        </form>
        <section class="card">
          <h3>История рассмотрения</h3>
          <ol class="event-list">
            <li v-for="event in history" :key="event.id">
              <span class="event-dot"></span>
              <div>
                <b>{{ event.message }}</b>
                <p class="muted small">
                  {{ date(event.created_at) }} · {{ event.actor_role }}
                </p>
              </div>
            </li>
          </ol>
        </section>
      </div>
    </div></template
  >
</template>
