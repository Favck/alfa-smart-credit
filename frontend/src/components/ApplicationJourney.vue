<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import UiButton from './UiButton.vue'
import AppIcon from './AppIcon.vue'
import { documentBlob } from '../api'
import { money } from '../data/demo'
const props = defineProps({
  application: Object,
  documents: { type: Array, default: () => [] },
  busy: Boolean,
  bank: Boolean,
})
const emit = defineEmits([
  'accept',
  'decline',
  'sign',
  'reply',
  'upload',
  'error',
])
const consent = ref(false)
const comment = ref('')
const revenue = ref(0)
const payments = ref(0)
const selected = ref([])
const preview = ref('')
const previewing = ref(false)
const info = computed(() => props.application?.info_request)
const offer = computed(() => props.application?.current_offer)
const contract = computed(() =>
  props.documents.find((d) => d.kind === 'contract'),
)
const attachments = computed(() =>
  props.documents.filter((d) => d.kind !== 'contract'),
)
let sequence = 0
function clearPreview() {
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = ''
}
watch(
  () => [props.application?.id, props.application?.updated_at],
  () => {
    sequence++
    consent.value = false
    clearPreview()
    comment.value = ''
    revenue.value = props.application?.revenue || 0
    payments.value = props.application?.payments || 0
    selected.value = []
  },
  { immediate: true },
)
onBeforeUnmount(() => {
  sequence++
  clearPreview()
})
async function download(document, show = false) {
  const current = sequence
  previewing.value = true
  try {
    const blob = await documentBlob(props.application.id, document.id)
    if (current !== sequence) return
    const url = URL.createObjectURL(blob)
    if (show) {
      clearPreview()
      preview.value = url
    } else {
      const link = window.document.createElement('a')
      link.href = url
      link.download = document.filename
      link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    }
  } catch (e) {
    emit('error', e.message)
  } finally {
    previewing.value = false
  }
}
function upload(event) {
  const files = [...event.target.files]
  event.target.value = ''
  if (files.some((f) => f.size > 10 * 1024 * 1024))
    return emit('error', 'Файл не должен превышать 10 МиБ.')
  emit('upload', files)
}
function reply() {
  const values = { message: comment.value, document_ids: selected.value }
  if (info.value.requested_fields.includes('monthly_revenue'))
    values.monthly_revenue = Number(revenue.value)
  if (info.value.requested_fields.includes('current_monthly_payments'))
    values.current_monthly_payments = Number(payments.value)
  emit('reply', { id: info.value.id, values })
}
</script>
<template>
  <div class="journey-stack">
    <section
      v-if="application.disbursement"
      class="journey-card issued-card"
      aria-label="Результат выдачи"
    >
      <span class="issued-icon"><AppIcon name="check" /></span>
      <h3>Финансирование выдано · демо</h3>
      <div class="stat">{{ money(application.disbursement.amount) }}</div>
      <p>
        Договор подписан. Зачисление на счёт
        {{ application.disbursement.account }} смоделировано.
      </p>
      <p class="small muted">
        Номер операции: {{ application.disbursement.reference }}<br />{{
          new Date(application.disbursement.created_at).toLocaleString('ru-RU')
        }}
      </p>
      <strong class="small"
        >Реальные деньги не переводились. Юридических обязательств нет.</strong
      >
    </section>

    <section v-if="offer" class="journey-card offer-card">
      <span class="eyebrow">{{
        offer.kind === 'counter'
          ? 'ВСТРЕЧНОЕ ПРЕДЛОЖЕНИЕ БАНКА'
          : 'УСЛОВИЯ ФИНАНСИРОВАНИЯ'
      }}</span>
      <h3>
        {{
          offer.kind === 'counter'
            ? 'Банк предлагает другие условия'
            : 'Ваше предложение готово'
        }}
      </h3>
      <div class="offer-terms">
        <div>
          <span>Сумма</span><strong>{{ money(offer.amount) }}</strong
          ><small v-if="offer.amount !== application.amount"
            >Запрошено {{ money(application.amount) }}</small
          >
        </div>
        <div>
          <span>Срок</span><strong>{{ offer.term_months }} мес.</strong
          ><small v-if="offer.term_months !== application.months"
            >Запрошено {{ application.months }} мес.</small
          >
        </div>
        <div>
          <span>Ставка · демо</span
          ><strong>{{ offer.annual_rate_percent }}%</strong>
        </div>
        <div>
          <span>Платёж в месяц</span
          ><strong>{{
            offer.monthly_payment != null
              ? money(offer.monthly_payment)
              : 'По использованию лимита'
          }}</strong>
        </div>
      </div>
      <p class="muted small">{{ offer.explanation }}</p>
      <p class="small muted">
        Условия демонстрационные. Это не предложение реального банка.
      </p>
      <div
        v-if="
          !bank && ['APPROVED', 'COUNTER_OFFER'].includes(application.status)
        "
        class="flex wrap mt"
      >
        <UiButton :disabled="busy" @click="$emit('accept', offer.id)"
          >Принять условия</UiButton
        ><UiButton alt :disabled="busy" @click="$emit('decline', offer.id)"
          >Отказаться</UiButton
        >
      </div>
      <span v-else class="pill">{{
        offer.status === 'accepted'
          ? 'Условия приняты'
          : 'Ожидается решение клиента'
      }}</span>
    </section>

    <form
      v-if="info && !bank"
      class="journey-card info-form"
      @submit.prevent="reply"
    >
      <span class="eyebrow">ЗАПРОС СОТРУДНИКА БАНКА</span>
      <h3>Нужны дополнительные сведения</h3>
      <p>{{ info.message }}</p>
      <label
        v-if="info.requested_fields.includes('monthly_revenue')"
        class="label"
        >Уточнённая выручка / мес.<input
          v-model="revenue"
          class="field"
          type="number"
          min="0"
          max="1000000000000"
          required /></label
      ><label
        v-if="info.requested_fields.includes('current_monthly_payments')"
        class="label"
        >Текущие кредитные платежи / мес.<input
          v-model="payments"
          class="field"
          type="number"
          min="0"
          max="1000000000000"
          required
      /></label>
      <p v-if="info.document_required" class="small">
        Банк запросил документ. Загрузите файл ниже и отметьте его для
        отправки.
      </p>
      <div
        v-for="document in attachments"
        :key="document.id"
        class="document-choice"
      >
        <label
          ><input v-model="selected" type="checkbox" :value="document.id" />{{
            document.filename
          }}</label
        >
      </div>
      <label class="label"
        >Комментарий<textarea
          v-model="comment"
          class="field"
          maxlength="2000"
          rows="3"
          placeholder="Пояснение для сотрудника банка"
        ></textarea></label
      ><UiButton class="mt" type="submit" :disabled="busy"
        >Отправить ответ банку</UiButton
      >
    </form>

    <section class="journey-card">
      <div class="section-title">
        <h3>Документы заявки</h3>
        <AppIcon name="applications" />
      </div>
      <p v-if="!documents.length" class="muted small">Документов пока нет.</p>
      <div
        v-for="document in documents"
        :key="document.id"
        class="document-row"
      >
        <AppIcon name="applications" />
        <div>
          <b>{{ document.filename }}</b
          ><span
            >{{ Math.ceil(document.size_bytes / 1024) }} КБ ·
            {{
              document.signed_at
                ? 'Демо-подписан'
                : document.kind === 'contract'
                  ? 'Демо-договор'
                  : 'Файл клиента'
            }}</span
          >
        </div>
        <button
          class="link"
          :disabled="previewing"
          @click="download(document)"
        >
          Скачать</button
        ><button
          v-if="document.kind === 'contract'"
          class="link"
          :disabled="previewing"
          @click="download(document, true)"
        >
          Просмотр
        </button>
      </div>
      <label
        v-if="!bank && ['DRAFT', 'NEED_INFO'].includes(application.status)"
        class="file-upload mt"
        ><AppIcon name="apply" /><span
          >Загрузить PDF или XLSX<small
            >До 10 МиБ, не более 6 файлов. Без автоматического
            распознавания.</small
          ></span
        ><input
          aria-label="Загрузить документы заявки"
          type="file"
          accept=".pdf,.xlsx"
          multiple
          :disabled="busy"
          @change="upload" /></label
      ><iframe
        v-if="preview"
        class="contract-preview"
        :src="preview"
        title="Просмотр демонстрационного договора"
      ></iframe>
      <form
        v-if="!bank && application.status === 'SIGNING' && contract"
        class="signature-form"
        @submit.prevent="$emit('sign', { document_id: contract.id, consent })"
      >
        <h3>Подписание договора</h3>
        <p class="muted small">
          Откройте и прочитайте договор. Подписание и последующая выдача
          полностью смоделированы.
        </p>
        <label class="consent-label"
          ><input v-model="consent" type="checkbox" required />Я ознакомился с
          условиями и понимаю, что это демонстрация без юридической силы и
          реального перевода денег.</label
        ><UiButton class="mt" type="submit" :disabled="busy || !consent"
          >Подписать и завершить демосценарий</UiButton
        >
      </form>
    </section>
  </div>
</template>
