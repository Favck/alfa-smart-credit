<script setup>
import { computed, ref } from 'vue'
import PageHeading from '../components/PageHeading.vue'
import UiButton from '../components/UiButton.vue'
import AppIcon from '../components/AppIcon.vue'
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
  <div class="flex wrap mb start news-filters">
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
        <img
          v-if="article.category === 'Производство'"
          src="/images/bakery-story.png"
          alt=""
          loading="lazy"
        />
        <AppIcon
          v-else
          :name="
            article.category === 'Финансы'
              ? 'coins'
              : article.category === 'Торговля'
                ? 'idea'
                : 'profile'
          "
        />
      </div>
      <span class="news-tag">{{ article.category }}</span>
      <h3>{{ article.title }}</h3>
      <p class="small muted">
        Рекомендации для развития бизнеса. Демонстрационный материал.
      </p>
      <div class="news-card-footer">
        <span>Альфа.Поток · Для предпринимателей</span><AppIcon name="news" />
      </div>
    </div>
  </TransitionGroup>
</template>
