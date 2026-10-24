<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { api, draftPayload } from '../api'
import PageHeading from '../components/PageHeading.vue'
import UiButton from '../components/UiButton.vue'
import AnimatedNumber from '../components/AnimatedNumber.vue'
import { money, products } from '../data/demo'

const props = defineProps({
  modelValue: Object,
  profile: Object,
  busy: Boolean,
})
const emit = defineEmits(['update:modelValue', 'submit', 'changed', 'save'])
const product = computed(() =>
  products.find((item) => item.id === props.modelValue.productId),
)
const terms = computed(() =>
  [1, 3, 6, 12, 18, 24, 36, 48, 60].filter(
    (term) => term >= product.value.minTerm && term <= product.value.maxTerm,
  ),
)
const payment = computed(() => {
  if (product.value.id === 'overdraft') return null
  const rate = product.value.rate / 100 / 12
  return (
    (props.modelValue.amount * rate) /
    (1 - (1 + rate) ** -props.modelValue.months)
  )
})

function update(field, value) {
  const next = { ...props.modelValue, [field]: value }
  if (field === 'productId') {
    const selected = products.find((item) => item.id === value)
    next.amount = Math.max(
      selected.minAmount,
      Math.min(selected.maxAmount, next.amount),
    )
    next.months = Math.max(
      selected.minTerm,
      Math.min(selected.maxTerm, next.months),
    )
  }
  emit('changed')
  emit('update:modelValue', next)
}
const preview = ref(null)
const previewLoading = ref(false)
const previewError = ref('')
let timer
let sequence = 0
watch(
  () => [
    props.modelValue.productId,
    props.modelValue.amount,
    props.modelValue.months,
    props.modelValue.revenue,
    props.modelValue.payments,
  ],
  () => {
    const value = { ...props.modelValue }
    clearTimeout(timer)
    const current = ++sequence
    preview.value = null
    previewError.value = ''
    previewLoading.value = true
    timer = setTimeout(async () => {
      try {
        const result = await api('scoring/pre-predict/', {
          method: 'POST',
          data: draftPayload(value),
        })
        if (current === sequence) preview.value = result
      } catch (error) {
        if (current === sequence) previewError.value = error.message
      } finally {
        if (current === sequence) previewLoading.value = false
      }
    }, 600)
  },
  { deep: true, immediate: true },
)
onBeforeUnmount(() => {
  clearTimeout(timer)
  sequence++
})
</script>

<template>
  <PageHeading
    title="Расскажите о ваших планах"
    description="Выберите параметры финансирования — данные вашей компании уже заполнены."
  />
  <ol class="form-phases" aria-label="Этапы оформления">
    <li class="done"><span>✓</span>Компания</li>
    <li class="current" aria-current="step"><span>2</span>Параметры</li>
    <li><span>3</span>Проверка</li>
  </ol>
  <form class="grid2 application-form" @submit.prevent="$emit('submit')">
    <div class="stack">
      <div class="card company-summary">
        <div class="flex">
          <b>Ваша компания</b
          ><span class="company-verified">✓ Данные заполнены</span>
        </div>
        <div class="company-strip">
          <span class="company-strip-icon" aria-hidden="true">А</span>
          <div>
            <strong>{{ profile.company }}</strong>
            <p class="muted">ИНН {{ profile.inn }}</p>
          </div>
        </div>
      </div>
      <div class="card">
        <b>Параметры финансирования</b
        ><label class="label" for="product">Продукт</label>
        <select
          id="product"
          class="field"
          :value="modelValue.productId"
          @change="update('productId', $event.target.value)"
        >
          <option v-for="item in products" :key="item.id" :value="item.id">
            {{ item.name }}
          </option>
        </select>
        <label class="label" for="amount"
          >Сумма: <b>{{ money(modelValue.amount) }}</b></label
        >
        <input
          id="amount"
          type="range"
          :min="product.minAmount"
          :max="product.maxAmount"
          step="50000"
          :value="modelValue.amount"
          @input="update('amount', Number($event.target.value))"
        />
        <label class="label" for="months">Срок</label>
        <select
          id="months"
          class="field"
          :value="modelValue.months"
          @change="update('months', Number($event.target.value))"
        >
          <option v-for="term in terms" :key="term" :value="term">
            {{ term }} месяцев
          </option>
        </select>
        <label class="label" for="purpose">Цель</label>
        <input
          id="purpose"
          class="field"
          maxlength="1000"
          :value="modelValue.purpose"
          @input="update('purpose', $event.target.value)"
        />
      </div>
      <div class="card">
        <b>Финансовые показатели</b>
        <div class="grid2 mt">
          <div>
            <label class="label" for="revenue">Выручка / мес.</label
            ><input
              id="revenue"
              class="field"
              type="number"
              min="0"
              required
              :value="modelValue.revenue"
              @input="update('revenue', Number($event.target.value))"
            />
          </div>
          <div>
            <label class="label" for="payments">Текущие платежи</label
            ><input
              id="payments"
              class="field"
              type="number"
              min="0"
              required
              :value="modelValue.payments"
              @input="update('payments', Number($event.target.value))"
            />
          </div>
        </div>
      </div>
    </div>
    <div>
      <div class="card payment-summary">
        <img
          class="payment-decoration"
          src="/images/product-overdraft.png"
          width="1024"
          height="1024"
          alt=""
        />
        <div class="small muted">Предварительный платёж</div>
        <template v-if="payment !== null"
          ><div class="stat">
            <AnimatedNumber :value="payment" currency :duration="300" />
          </div>
          <div class="small muted">В месяц · примерный расчёт</div></template
        >
        <p v-else class="small muted">
          Платёж по овердрафту зависит от использования лимита. Условия расчёта
          уточняются.
        </p>
        <div class="line flex mt">
          <span>Сумма</span><b>{{ money(modelValue.amount) }}</b>
        </div>
        <div class="line flex">
          <span>Срок</span><b>{{ modelValue.months }} мес.</b>
        </div>
        <div class="line flex">
          <span>Расчётная ставка (демо)</span><b>{{ product.rate }}%</b>
        </div>
        <p class="small muted">
          Окончательные условия определяются после проверки заявки.
        </p>
        <section class="ml-preview note" aria-live="polite">
          <b>Предварительная оценка ML</b>
          <p v-if="previewLoading">Выполняется расчёт…</p>
          <p v-else-if="previewError">{{ previewError }}</p>
          <template v-else-if="preview"
            ><div class="ml-probability">
              {{ preview.approval_probability_percent
              }}<span>% · оценка 100 − PD</span>
            </div>
            <p>{{ preview.hint_message }}</p>
            <p v-if="preview.recommended_max_amount">
              Ориентир по сумме: {{ money(preview.recommended_max_amount) }}
            </p>
            <p v-if="preview.recommended_min_term_months">
              Рекомендуемый срок:
              {{ preview.recommended_min_term_months }} мес.
            </p>
            <p class="small">{{ preview.method_note }}</p></template
          >
        </section>
        <div class="stack">
          <UiButton type="submit" :disabled="busy">Отправить заявку →</UiButton
          ><UiButton alt :disabled="busy" @click="$emit('save')"
            >Сохранить черновик</UiButton
          >
        </div>
        <p class="small muted mt">
          Документы PDF или XLSX можно приложить к сохранённому черновику в
          разделе «Мои заявки».
        </p>
      </div>
    </div>
  </form>
</template>
