<script setup>
import { computed } from 'vue'
import UiButton from '../components/UiButton.vue'
import AppIcon from '../components/AppIcon.vue'
import AnimatedNumber from '../components/AnimatedNumber.vue'
import { money, steps } from '../data/demo'

const props = defineProps({
  profile: Object,
  application: Object,
  product: Object,
  applications: { type: Array, default: () => [] },
})
defineEmits(['navigate'])
const approved = computed(() => props.application?.status === 'APPROVED')
const status = computed(() => props.application?.status_label || 'Нет заявок')
const stage = computed(
  () =>
    ({
      DRAFT: 0,
      SUBMITTED: 0,
      CHECK: 1,
      ENRICH: 1,
      SCORING: 2,
      REVIEW: 3,
      APPROVED: 3,
      REJECTED: 3,
      CANCELLED: 0,
    })[props.application?.status] ?? 0,
)
const message = computed(
  () =>
    ({
      APPROVED: 'Заявка одобрена',
      REJECTED: 'По заявке принято решение',
      CANCELLED: 'Заявка отменена',
      DRAFT: 'Продолжите оформление',
      REVIEW: 'Рассмотрение сотрудником',
    })[props.application?.status] || 'Ваши планы уже в работе',
)
const activeCount = computed(
  () =>
    props.applications.filter(
      (a) => !['DRAFT', 'REJECTED', 'CANCELLED'].includes(a.status),
    ).length,
)
const totalAmount = computed(() =>
  props.applications.reduce((total, a) => total + a.amount, 0),
)
</script>

<template>
  <section class="dashboard-hero">
    <div class="dashboard-hero-copy">
      <span class="eyebrow">ВАШ БИЗНЕС — НАШИ ВОЗМОЖНОСТИ</span>
      <h1>Здравствуйте, {{ profile.name }}!</h1>
      <p>
        Альфа.Поток помогает вашему бизнесу расти.<br />Подберите подходящее
        финансирование или создайте новую заявку в несколько кликов.
      </p>
      <div class="hero-actions">
        <UiButton @click="$emit('navigate', 'products')"
          >Подобрать финансирование <AppIcon name="arrow" /></UiButton
        ><UiButton alt @click="$emit('navigate', 'apply')"
          ><AppIcon name="apply" />Создать заявку</UiButton
        >
      </div>
    </div>
    <div class="hero-photo" aria-hidden="true"></div>
    <div class="glass-message">
      <strong>Развиваем<br />российский бизнес<br />вместе</strong><i></i
      ><span>Больше возможностей<br />для тех, кто создаёт<br />будущее</span>
    </div>
  </section>

  <div class="grid3 overview-grid">
    <button
      class="card overview-card"
      @click="$emit('navigate', 'applications')"
    >
      <span class="overview-icon accent"><AppIcon name="applications" /></span
      ><span class="metric-copy"
        ><span class="metric-label">Активные заявки</span
        ><strong><AnimatedNumber :value="activeCount" /></strong
        ><span class="muted small">Следите за каждым этапом</span></span
      ><AppIcon name="chevron" />
    </button>
    <button
      class="card overview-card"
      @click="$emit('navigate', 'applications')"
    >
      <span class="overview-icon"><AppIcon name="coins" /></span
      ><span class="metric-copy"
        ><span class="metric-label">Сумма заявок</span
        ><strong><AnimatedNumber :value="totalAmount" currency /></strong
        ><span class="muted small">Общая запрашиваемая сумма</span></span
      ><AppIcon name="chevron" />
    </button>
    <button class="card overview-card" @click="$emit('navigate', 'profile')">
      <span class="completion-ring">100<span>%</span></span
      ><span class="metric-copy"
        ><span class="metric-label">Профиль компании</span
        ><b>Всё готово к новым планам</b
        ><span class="muted small"
          >Реквизиты автоматически<br />подставляются в заявку</span
        ></span
      ><AppIcon name="chevron" />
    </button>
  </div>

  <section class="card dashboard-section">
    <div class="section-title">
      <h2>Последняя заявка</h2>
      <button class="link" @click="$emit('navigate', 'applications')">
        Все заявки <AppIcon name="arrow" />
      </button>
    </div>
    <div v-if="application" class="latest-application">
      <div class="application-details">
        <div class="application-title-row">
          <span class="overview-icon accent"><AppIcon name="coins" /></span>
          <div>
            <h3>Заявка {{ application.number }}</h3>
            <span class="muted">{{ product.name }}</span>
          </div>
          <span class="pill" :class="approved ? 'success' : 'pending'"
            ><AppIcon :name="approved ? 'check' : 'clock'" />{{ status }}</span
          >
        </div>
        <div class="application-numbers">
          <div>
            <span>Сумма</span><strong>{{ money(application.amount) }}</strong>
          </div>
          <div>
            <span>Срок</span><strong>{{ application.months }} мес.</strong>
          </div>
          <div>
            <span>Ежемесячная выручка</span
            ><strong>{{ money(application.revenue) }}</strong>
          </div>
        </div>
        <ol class="horizontal-timeline" aria-label="Путь заявки">
          <li
            v-for="(step, index) in steps.slice(0, 4)"
            :key="step.title"
            :class="{ done: index < stage, current: index === stage }"
            :aria-current="index === stage ? 'step' : undefined"
          >
            <span class="timeline-dot"
              ><AppIcon v-if="index < stage" name="check" /><span
                v-else
              ></span></span
            ><b>{{ step.title }}</b
            ><small>{{
              index < stage
                ? 'Завершено'
                : index === stage
                  ? 'Текущий этап'
                  : 'Ожидает'
            }}</small>
          </li>
        </ol>
      </div>
      <div class="application-next" :class="{ 'is-approved': approved }">
        <div class="next-heading">
          <span class="status-medallion"
            ><AppIcon :name="approved ? 'check' : 'clock'"
          /></span>
          <div>
            <h3>{{ message }}</h3>
            <p>
              {{
                application.client_scoring?.explanation ||
                application.status_label
              }}
            </p>
          </div>
        </div>
        <UiButton @click="$emit('navigate', 'applications')"
          >{{ 'Открыть заявку' }}<AppIcon name="arrow"
        /></UiButton>
        <div class="document-note">
          <AppIcon name="applications" /><span
            >Результат и история сохранены. Договоры и подписание появятся на
            следующем этапе проекта.</span
          >
        </div>
      </div>
    </div>
    <div v-if="!application" class="empty-state">
      <AppIcon name="applications" />
      <h3>Здесь начнётся история ваших планов</h3>
      <p class="muted">
        Создайте первую заявку — её статус и результат появятся в кабинете.
      </p>
      <UiButton @click="$emit('navigate', 'apply')">Создать заявку</UiButton>
    </div>
  </section>

  <section class="card dashboard-section useful-section">
    <div class="section-title">
      <h2>Полезное для вашего бизнеса</h2>
      <button class="link" @click="$emit('navigate', 'news')">
        Все материалы <AppIcon name="arrow" />
      </button>
    </div>
    <div class="useful-grid">
      <button class="useful-card" @click="$emit('navigate', 'news')">
        <img
          src="/images/bakery-story.png"
          alt="Свежая выпечка в пекарне"
        /><span
          ><span class="news-tag">Статья</span
          ><strong>Как превратить планы в рост бизнеса</strong
          ><span class="muted">Идеи и решения для вашей отрасли.</span></span
        ><AppIcon name="chevron" />
      </button>
      <button class="useful-card" @click="$emit('navigate', 'news')">
        <span class="useful-illustration"><AppIcon name="idea" /></span
        ><span
          ><span class="news-tag rose">Совет</span
          ><strong>Как управлять денежным потоком</strong
          ><span class="muted"
            >Практические рекомендации для предпринимателей.</span
          ></span
        ><AppIcon name="chevron" />
      </button>
      <button class="useful-card" @click="$emit('navigate', 'products')">
        <img src="/images/product-growth.png" alt="" /><span
          ><span class="news-tag rose">Рекомендуем</span
          ><strong>Оборотный кредит для постоянного роста</strong
          ><span class="muted"
            >Финансирование для вашего следующего шага.</span
          ></span
        ><AppIcon name="chevron" />
      </button>
    </div>
  </section>
</template>
