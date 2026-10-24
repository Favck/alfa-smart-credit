<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import PageHeading from '../components/PageHeading.vue'
import UiButton from '../components/UiButton.vue'
import AppIcon from '../components/AppIcon.vue'
defineProps({ profile: Object })
const categories = {
  '': 'Для меня',
  trade: 'Торговля',
  production: 'Производство',
  construction: 'Строительство',
  finance: 'Финансы',
}
const category = ref('')
const articles = ref([])
const selected = ref(null)
const loading = ref(false)
const error = ref('')
let sequence = 0
async function load(value = '') {
  category.value = value
  selected.value = null
  error.value = ''
  loading.value = true
  const current = ++sequence
  try {
    const data = await api('news/' + (value ? `?category=${value}` : ''))
    if (sequence === current) articles.value = data
  } catch (e) {
    if (sequence === current) error.value = e.message
  } finally {
    if (sequence === current) loading.value = false
  }
}
async function open(id) {
  error.value = ''
  loading.value = true
  try {
    selected.value = await api(`news/${id}/`)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(() => load())
</script>
<template>
  <PageHeading
    title="Полезное для вашего бизнеса"
    :description="`Подборка для ${profile.company} · демонстрационные материалы`"
  />
  <p v-if="error" class="app-feedback error-feedback" role="alert">
    {{ error }}
  </p>
  <p v-if="loading" role="status">Загружаем материалы…</p>
  <article v-if="selected" class="card full-article">
    <button class="link mb" @click="selected = null">← Все материалы</button>
    <div class="news-tag">{{ categories[selected.category] }}</div>
    <h2>{{ selected.title }}</h2>
    <p class="muted">{{ selected.summary }}</p>
    <p v-for="(paragraph, index) in selected.body.split('\n\n')" :key="index">
      {{ paragraph }}
    </p>
    <p class="note small">
      Материал подготовлен для демонстрации продукта на хакатоне.
    </p>
  </article>
  <template v-else>
    <div class="flex wrap mb start news-filters">
      <UiButton
        v-for="(title, value) in categories"
        :key="value"
        :alt="category !== value"
        :aria-pressed="category === value"
        :disabled="loading"
        @click="load(value)"
        >{{ title }}</UiButton
      >
    </div>
    <div class="grid2 news-grid">
      <button
        v-for="(article, index) in articles"
        :key="article.id"
        class="card news-card"
        :class="`news-tone-${index % 3}`"
        @click="open(article.id)"
      >
        <div class="news-art" aria-hidden="true">
          <img
            v-if="article.category === 'production'"
            src="/images/bakery-story.png"
            alt=""
            loading="lazy"
          /><AppIcon
            v-else
            :name="article.category === 'finance' ? 'coins' : 'idea'"
          />
        </div>
        <span class="news-tag">{{ categories[article.category] }}</span>
        <h3>{{ article.title }}</h3>
        <p class="small muted">{{ article.summary }}</p>
        <div class="news-card-footer">
          <span>Читать материал →</span><AppIcon name="news" />
        </div>
      </button>
    </div>
  </template>
</template>
