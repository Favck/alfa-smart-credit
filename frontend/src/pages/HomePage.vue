<script setup>
import UiButton from '../components/UiButton.vue'
import FinanceArt from '../components/FinanceArt.vue'
import AppIcon from '../components/AppIcon.vue'
import AnimatedNumber from '../components/AnimatedNumber.vue'
import { money } from '../data/demo'

defineProps({
  profile: Object,
  application: Object,
  product: Object,
  stage: { type: Number, default: 2 },
})
defineEmits(['navigate'])
const today = new Intl.DateTimeFormat('ru-RU', {
  dateStyle: 'long',
  timeZone: 'Europe/Moscow',
}).format(new Date())
</script>

<template>
  <div class="home-greeting flex wrap">
    <div>
      <h1 class="heading">Здравствуйте, {{ profile.name }}</h1>
    </div>
    <span class="date-label">{{ today }}</span>
  </div>
  <section class="banner">
    <div class="banner-copy">
      <h2>Ваши планы.<br /><span>Наши возможности.</span></h2>
      <p>
        Финансируем развитие вашего бизнеса —<br class="desktop-break" />
        от оборотных средств до масштабных проектов.
      </p>
      <div class="hero-actions">
        <UiButton @click="$emit('navigate', 'products')"
          >Подобрать финансирование <span aria-hidden="true">↗</span></UiButton
        >
      </div>
    </div>
    <FinanceArt />
  </section>
  <div class="grid3 overview-grid">
    <div class="card overview-card">
      <span class="overview-icon"><AppIcon name="applications" /></span>
      <div>
        <div class="small muted">Активные заявки</div>
        <div class="stat">
          <AnimatedNumber :value="1" />
        </div>
      </div>
    </div>
    <div class="card overview-card">
      <span class="overview-icon"><span aria-hidden="true">₽</span></span>
      <div>
        <div class="small muted">Запрошено</div>
        <div class="stat">
          <AnimatedNumber :value="application.amount" currency />
        </div>
      </div>
    </div>
    <div class="card overview-card">
      <span class="overview-icon"><AppIcon name="profile" /></span>
      <div class="overview-company">
        <div class="small muted">Профиль компании</div>
        <div class="stat">
          <AnimatedNumber :value="100" /><span class="stat-unit">%</span>
        </div>
      </div>
    </div>
  </div>
  <div class="grid2 home-details">
    <section>
      <div class="card application-preview">
        <div class="flex">
          <span class="eyebrow">ЗАЯВКА APP-1042</span
          ><span class="pill"
            ><span></span>
            {{ stage === 4 ? 'Одобрена' : 'На рассмотрении' }}</span
          >
        </div>
        <h3>{{ product.name }}</h3>
        <div class="preview-amount">
          {{ money(application.amount) }}
          <span>на {{ application.months }} мес.</span>
        </div>
        <div class="preview-stepper">
          <div
            v-for="(label, index) in [
              'Заявка создана',
              'Проверка',
              'Оценка рисков',
              'Решение',
              'Подписание',
            ]"
            :key="label"
            class="preview-step"
            :class="{ complete: index < stage, current: index === stage }"
          >
            <span class="preview-step-dot"></span><span>{{ label }}</span>
          </div>
        </div>
        <div class="flex preview-footer">
          <span class="muted small">Оцениваем возможности бизнеса</span
          ><button
            class="round-arrow"
            aria-label="Открыть заявку"
            @click="$emit('navigate', 'applications')"
          >
            ↗
          </button>
        </div>
      </div>
    </section>
    <section>
      <button class="card editorial-card" @click="$emit('navigate', 'news')">
        <span class="news-tag">ПОЛЕЗНО ДЛЯ БИЗНЕСА</span>
        <h3>Идеи для роста</h3>
        <p>
          Практические материалы,<br />разборы и истории предпринимателей<br />в
          нашем журнале.
        </p>
        <span class="editorial-bottom"
          >Читать подборку <span aria-hidden="true">↗</span></span
        >
      </button>
    </section>
  </div>
</template>
