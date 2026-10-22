<script setup>
import { computed, ref } from 'vue'
import PageHeading from '../components/PageHeading.vue'
import UiButton from '../components/UiButton.vue'
import { news } from '../data/demo'

const props = defineProps({ profile: Object })
const category = ref('Для меня')
const categories = [
  'Для меня',
  'Все',
  'Торговля',
  'Производство',
  'Строительство',
  'Финансы',
]
const filtered = computed(() =>
  news.filter(
    (article) =>
      category.value === 'Все' ||
      (category.value === 'Для меня'
        ? [props.profile.category, 'Финансы'].includes(article.category)
        : article.category === category.value),
  ),
)
</script>

<template>
  <PageHeading
    title="Новости для бизнеса"
    :description="`Персональная подборка для ${profile.company} · демоданные`"
  />
  <div class="flex wrap mb start">
    <UiButton
      v-for="item in categories"
      :key="item"
      :alt="category !== item"
      :aria-pressed="category === item"
      @click="category = item"
      >{{ item }}</UiButton
    >
  </div>
  <TransitionGroup name="feed" tag="div" class="grid2 news-grid" appear>
    <div
      v-for="(article, index) in filtered"
      :key="article.id"
      class="card news-card"
      :class="`news-tone-${index % 3}`"
    >
      <div class="news-art" aria-hidden="true">
        <span>{{ article.category === 'Финансы' ? '₽' : '↗' }}</span>
      </div>
      <span class="news-tag">{{ article.category }}</span>
      <h3>{{ article.title }}</h3>
      <p class="small muted">
        Рекомендации для развития бизнеса. Демонстрационный материал.
      </p>
    </div>
  </TransitionGroup>
</template>
