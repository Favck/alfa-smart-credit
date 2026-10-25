<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { api } from '../api'
import AppIcon from './AppIcon.vue'
import UiButton from './UiButton.vue'
const emit = defineEmits(['select'])
const query = ref('')
const result = ref(null)
const loading = ref(false)
const error = ref('')
const examples = [
  {
    title: 'Закрыть кассовый разрыв',
    text: 'Нечем платить зарплату завтра, клиент задерживает расчет',
  },
  {
    title: 'Закупить товар',
    text: 'Закупаем партию обуви на осенне-зимний сезон',
  },
  {
    title: 'Открыть новую точку',
    text: 'Открываем новую точку пекарни с ремонтом помещения',
  },
]
let sequence = 0
let controller
watch(query, () => {
  sequence++
  controller?.abort()
  result.value = null
  error.value = ''
  loading.value = false
})
onBeforeUnmount(() => {
  sequence++
  controller?.abort()
})
async function consult() {
  if (loading.value || query.value.trim().length < 5) return
  const current = ++sequence
  controller = new AbortController()
  loading.value = true
  result.value = null
  error.value = ''
  try {
    const answer = await api('consultations/', {
      method: 'POST',
      data: { user_query: query.value.trim() },
      signal: controller.signal,
    })
    if (current === sequence) result.value = answer
  } catch (e) {
    if (current === sequence && e.name !== 'AbortError')
      error.value = e.message
  } finally {
    if (current === sequence) loading.value = false
  }
}
</script>
<template>
  <section class="card consultant-panel mb" aria-labelledby="consultant-title">
    <div class="consultant-heading">
      <span class="consultant-icon"><AppIcon name="idea" /></span>
      <div>
        <span class="eyebrow">AI-КОНСУЛЬТАНТ</span>
        <h2 id="consultant-title">Расскажите о задаче бизнеса</h2>
        <p class="muted">
          Подберём продукт и срок финансирования под ваши планы
        </p>
      </div>
    </div>
    <form @submit.prevent="consult">
      <label class="label" for="consultant-query">На что нужны деньги?</label>
      <textarea
        id="consultant-query"
        v-model="query"
        class="field consultant-query"
        rows="3"
        minlength="5"
        maxlength="1000"
        required
        placeholder="Например, хочу открыть вторую пекарню и сделать ремонт"
      ></textarea>
      <div class="consultant-input-footer">
        <div class="consultant-examples">
          <button
            v-for="example in examples"
            :key="example.title"
            type="button"
            @click="query = example.text"
          >
            {{ example.title }}
          </button>
        </div>
        <span class="muted small">{{ query.length }} / 1000</span>
      </div>
      <UiButton
        class="mt"
        type="submit"
        :disabled="loading || query.trim().length < 5"
        ><AppIcon name="idea" />{{
          loading ? 'Подбираем решение…' : 'Подобрать продукт'
        }}</UiButton
      >
    </form>
    <p v-if="error" class="note" role="alert">{{ error }}</p>
    <div v-if="loading" class="consultant-progress" role="status">
      Анализируем задачу и подбираем срок финансирования…
    </div>
    <article v-if="result" class="consultant-result" aria-live="polite">
      <div class="consultant-result-header">
        <div>
          <span class="eyebrow">{{
            result.is_fallback ? 'БАЗОВЫЙ ВАРИАНТ' : 'ПОДХОДЯЩИЙ ПРОДУКТ'
          }}</span>
          <h3>{{ result.title }}</h3>
        </div>
        <span class="pill">{{ result.suggested_term_months }} мес.</span>
      </div>
      <p>{{ result.explanation }}</p>
      <UiButton @click="emit('select', { result, query: query.trim() })"
        >Перейти к заявке<AppIcon name="arrow"
      /></UiButton>
    </article>
  </section>
</template>
