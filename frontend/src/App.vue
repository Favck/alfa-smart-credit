<script setup>
import { computed, reactive, ref, watch } from 'vue'
import {
  createCases,
  createDraft,
  pages,
  products,
  profiles,
} from './data/demo'
import HomePage from './pages/HomePage.vue'
import ProductsPage from './pages/ProductsPage.vue'
import ApplyPage from './pages/ApplyPage.vue'
import ApplicationsPage from './pages/ApplicationsPage.vue'
import NewsPage from './pages/NewsPage.vue'
import ProfilePage from './pages/ProfilePage.vue'
import BankQueuePage from './pages/BankQueuePage.vue'
import BankDetailPage from './pages/BankDetailPage.vue'
import AppIcon from './components/AppIcon.vue'

const dark = ref(false)
const profileId = ref('')
const view = ref('home')
const cases = reactive(createCases())
const chosenId = ref(cases[0].id)
const clients = reactive(
  Object.fromEntries(
    profiles
      .filter((profile) => profile.role === 'client')
      .map((profile) => {
        const draft = createDraft(profile)
        return [profile.id, { draft, application: { ...draft }, stage: 2 }]
      }),
  ),
)
const profile = computed(() =>
  profiles.find((item) => item.id === profileId.value),
)
const client = computed(() => clients[profileId.value])
const applicationProduct = computed(() =>
  products.find((item) => item.id === client.value?.application.productId),
)
const selectedCase = computed(() =>
  cases.find((item) => item.id === chosenId.value),
)
const tabs = computed(() =>
  profile.value?.role === 'bank'
    ? ['queue', 'detail']
    : ['home', 'products', 'apply', 'applications', 'news', 'profile'],
)

watch([view, profileId], () => window.scrollTo({ top: 0 }), {
  flush: 'post',
})

function selectProfile(id) {
  profileId.value = id
  view.value =
    profiles.find((item) => item.id === id)?.role === 'bank' ? 'queue' : 'home'
}

function selectProduct(id) {
  const selected = products.find((item) => item.id === id)
  const draft = client.value.draft
  draft.productId = id
  draft.amount = Math.max(
    selected.minAmount,
    Math.min(selected.maxAmount, draft.amount),
  )
  draft.months = Math.max(
    selected.minTerm,
    Math.min(selected.maxTerm, draft.months),
  )
  view.value = 'apply'
}

function submitApplication() {
  client.value.application = { ...client.value.draft }
  client.value.stage = 0
  view.value = 'applications'
}

function openCase(id) {
  chosenId.value = id
  view.value = 'detail'
}
</script>

<template>
  <div class="app-shell" :class="{ dark }">
    <header class="top">
      <button
        class="brand"
        aria-label="Альфа.Поток — главная"
        @click="view = profile?.role === 'bank' ? 'queue' : 'home'"
      >
        <span class="brand-name"><span>Альфа.</span>Поток</span>
        <span class="demo-badge">Демо</span>
      </button>
      <nav v-if="profile" id="desktop" aria-label="Основная навигация">
        <button
          v-for="tab in tabs"
          :key="tab"
          class="nav"
          :class="{ active: view === tab }"
          :aria-current="view === tab ? 'page' : undefined"
          @click="view = tab"
        >
          {{ pages[tab].title }}
        </button>
      </nav>
      <div class="actions">
        <label v-if="profile" class="company-select">
          <AppIcon name="profile" />
          <select
            aria-label="Демо-профиль"
            :value="profileId"
            @change="selectProfile($event.target.value)"
          >
            <option v-for="item in profiles" :key="item.id" :value="item.id">
              {{ item.role === 'bank' ? 'Сотрудник банка' : item.company }}
            </option>
          </select>
        </label>
        <button
          v-if="profile"
          class="user-control"
          :disabled="profile.role === 'bank'"
          @click="view = 'profile'"
        >
          <AppIcon name="user" /><span
            >{{ profile.name
            }}<span class="user-surname">
              {{
                profile.role === 'bank'
                  ? profile.fullName.split(' ').slice(1).join(' ')
                  : profile.fullName.split(' ')[0]
              }}</span
            ></span
          >
        </button>
        <button
          class="icon-button theme-button"
          aria-label="Сменить тему"
          :aria-pressed="dark"
          @click="dark = !dark"
        >
          <AppIcon :name="dark ? 'sun' : 'moon'" />
        </button>
        <button
          v-if="profile"
          class="icon-button logout-button"
          aria-label="Выйти"
          title="Выйти"
          @click="profileId = ''"
        >
          <AppIcon name="logout" />
        </button>
        <span v-else class="header-secure"
          ><AppIcon name="lock" />Кабинет предпринимателя</span
        >
      </div>
    </header>
    <Transition name="session" mode="out-in" appear>
      <main v-if="!profile" v-reveal key="profiles" class="profile-picker">
        <section class="welcome-copy">
          <span class="eyebrow">ВАШ БИЗНЕС — НАШИ ВОЗМОЖНОСТИ</span>
          <h1>Большие планы.<br />Понятный путь.</h1>
          <p class="welcome-description">
            Финансирование для тех, кто создаёт.<br />От первой заявки до новых
            возможностей —<br />в одном кабинете.
          </p>
          <div class="welcome-benefits">
            <span><AppIcon name="check" />Всё онлайн</span
            ><span><AppIcon name="check" />Понятные этапы</span
            ><span><AppIcon name="check" />Для вашего бизнеса</span>
          </div>
          <div class="welcome-photo">
            <div class="glass-message">
              Ваше дело.<br /><strong>Новые возможности.</strong
              ><span>Поддерживаем бизнес<br />на каждом этапе роста</span>
            </div>
          </div>
        </section>
        <section class="entry-panel">
          <div class="entry-heading">
            <span class="eyebrow">НАЧНЁМ ЗНАКОМСТВО</span>
            <h2>Добро пожаловать</h2>
            <p class="muted">
              Выберите готовый профиль и посмотрите,<br
                class="desktop-break"
              />
              как работает Альфа.Поток.
            </p>
          </div>
          <div class="profile-list">
            <button
              v-for="(item, index) in profiles"
              :key="item.id"
              class="profile-card"
              :class="`profile-${item.id}`"
              :style="{ '--profile-delay': `${index * 75 + 160}ms` }"
              @click="selectProfile(item.id)"
            >
              <span class="profile-avatar"
                ><AppIcon :name="item.role === 'bank' ? 'detail' : 'profile'"
              /></span>
              <span class="profile-info"
                ><span class="profile-type">{{ item.description }}</span>
                <strong>{{
                  item.role === 'bank' ? 'Сотрудник банка' : item.company
                }}</strong>
                <span class="profile-person">{{ item.fullName }}</span></span
              >
              <span class="profile-arrow" aria-hidden="true">↗</span>
            </button>
          </div>
          <p class="entry-note">
            <span aria-hidden="true">ⓘ</span> Регистрация не нужна. Все данные
            вымышлены.
          </p>
        </section>
      </main>
      <div v-else key="workspace" class="layout">
        <aside id="mobile" aria-label="Мобильная навигация">
          <button
            v-for="tab in tabs"
            :key="tab"
            class="nav"
            :class="{ active: view === tab }"
            :title="pages[tab].title"
            :aria-label="pages[tab].title"
            :aria-current="view === tab ? 'page' : undefined"
            @click="view = tab"
          >
            <AppIcon :name="tab" /><span>{{ pages[tab].title }}</span>
          </button>
        </aside>
        <main id="page">
          <div class="demo-notice">
            <span class="demo-dot"></span> Демо-кабинет
            <span class="notice-divider">/</span> {{ profile.company
            }}<span class="notice-local"
              >Данные сохраняются до обновления страницы</span
            >
          </div>
          <Transition name="page" mode="out-in" appear>
            <div :key="`${profileId}:${view}`" v-reveal class="page-view">
              <HomePage
                v-if="view === 'home'"
                :profile="profile"
                :application="client.application"
                :product="applicationProduct"
                :stage="client.stage"
                @navigate="view = $event"
              />
              <ProductsPage
                v-else-if="view === 'products'"
                @select="selectProduct"
              />
              <ApplyPage
                v-else-if="view === 'apply'"
                v-model="client.draft"
                :profile="profile"
                @submit="submitApplication"
              />
              <ApplicationsPage
                v-else-if="view === 'applications'"
                :application="client.application"
                :product="applicationProduct"
                :stage="client.stage"
                :profile="profile"
                @stage="client.stage = $event"
              />
              <NewsPage v-else-if="view === 'news'" :profile="profile" />
              <ProfilePage v-else-if="view === 'profile'" :profile="profile" />
              <BankQueuePage
                v-else-if="view === 'queue'"
                :cases="cases"
                @open="openCase"
              />
              <BankDetailPage
                v-else-if="view === 'detail'"
                :application="selectedCase"
                @back="view = 'queue'"
                @decision="selectedCase.decision = $event"
              />
            </div>
          </Transition>
        </main>
      </div>
    </Transition>
    <footer class="site-footer">
      <span>© 2026 Альфа.Поток</span
      ><span>Создано для бизнеса. Разработано для хакатона.</span
      ><span>Демонстрационный прототип</span>
    </footer>
  </div>
</template>
