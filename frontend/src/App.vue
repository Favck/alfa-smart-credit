<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { createDraft, pages, products, profiles } from './data/demo'
import {
  api,
  setToken,
  hasToken,
  draftPayload,
  normalizeApplication,
} from './api'
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
const applications = ref([])
const cases = ref([])
const chosenId = ref('')
const history = ref([])
const documents = ref([])
const editingId = ref('')
const busy = ref(false)
const error = ref('')
let generation = 0
let submissionKey = ''
const drafts = reactive(
  Object.fromEntries(
    profiles
      .filter((p) => p.role === 'client')
      .map((p) => [p.id, createDraft(p)]),
  ),
)
const profile = computed(() => profiles.find((p) => p.id === profileId.value))
const draft = computed(() => drafts[profileId.value])
const selectedApplication = computed(
  () =>
    applications.value.find((a) => a.id === chosenId.value) ||
    applications.value[0] ||
    null,
)
const latest = computed(() => applications.value[0] || null)
const selectedCase = computed(
  () =>
    cases.value.find((a) => a.id === chosenId.value) || cases.value[0] || null,
)
const applicationProduct = computed(() =>
  products.find((p) => p.id === latest.value?.productId),
)
const tabs = computed(() =>
  profile.value?.role === 'bank'
    ? ['queue', 'detail']
    : ['home', 'products', 'apply', 'applications', 'news', 'profile'],
)
watch(view, () => window.scrollTo({ top: 0 }), { flush: 'post' })

async function run(action) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    return await action()
  } catch (e) {
    error.value = e.message
    if (e.status === 401) {
      setToken('')
      profileId.value = ''
    }
  } finally {
    busy.value = false
  }
}
async function refreshData() {
  const current = generation
  const bank = profile.value?.role === 'bank'
  const path = bank ? 'bank/applications/' : 'applications/'
  const all = []
  let page = 1
  while (true) {
    const result = await api(`${path}?page_size=100&page=${page}`)
    if (current !== generation) return
    all.push(...result.results.map(normalizeApplication))
    if (!result.next) break
    page++
  }
  if (bank) cases.value = all
  else applications.value = all
  if (!all.some((a) => a.id === chosenId.value))
    chosenId.value = all[0]?.id || ''
  if (chosenId.value && all.some((a) => a.id === chosenId.value))
    await loadHistory(chosenId.value, bank)
}
async function loadHistory(id, bank = profile.value?.role === 'bank') {
  const current = generation
  const prefix = `${bank ? 'bank/' : ''}applications/${id}/`
  const [events, files] = await Promise.all([
    api(prefix + 'history/'),
    api(prefix + 'documents/'),
  ])
  if (current === generation && chosenId.value === id) {
    history.value = events
    documents.value = files
  }
}
async function establish(id) {
  profileId.value = id
  applications.value = []
  cases.value = []
  history.value = []
  documents.value = []
  editingId.value = ''
  chosenId.value = ''
  view.value = profile.value.role === 'bank' ? 'queue' : 'home'
  if (profile.value.role === 'client') {
    const company = await api('company/')
    // The server owns company/financial defaults; the local profile supplies presentation labels.
    Object.assign(profile.value, {
      company: company.name,
      inn: company.inn,
      ogrn: company.ogrn,
      industry: company.industry,
      revenue: company.monthly_revenue,
      payments: company.current_monthly_payments,
    })
    drafts[id] = createDraft(profile.value)
  }
  await refreshData()
}
function selectProfile(id) {
  if (busy.value) return
  run(async () => {
    generation++
    const result = await api('auth/demo-login/', {
      method: 'POST',
      data: { profile_id: id },
    })
    setToken(result.token)
    submissionKey = ''
    await establish(result.user.profile_id)
  })
}
function logout() {
  run(async () => {
    await api('auth/logout/', { method: 'POST' })
    generation++
    setToken('')
    profileId.value = ''
    applications.value = []
    cases.value = []
  })
}
function navigate(tab) {
  if (tab === 'apply') {
    newApplication()
    return
  }
  view.value = tab
  if (['home', 'applications', 'queue', 'detail'].includes(tab))
    run(refreshData)
}
function newApplication() {
  editingId.value = ''
  submissionKey = ''
  view.value = 'apply'
}
function editDraft(id) {
  const app = applications.value.find((a) => a.id === id)
  if (!app || app.status !== 'DRAFT') return
  drafts[profileId.value] = {
    productId: app.productId,
    amount: app.amount,
    months: app.months,
    purpose: app.purpose,
    revenue: app.revenue,
    payments: app.payments,
  }
  editingId.value = id
  view.value = 'apply'
}
function selectProduct(id) {
  editingId.value = ''
  const product = products.find((p) => p.id === id)
  Object.assign(draft.value, {
    productId: id,
    amount: Math.max(
      product.minAmount,
      Math.min(product.maxAmount, draft.value.amount),
    ),
    months: Math.max(
      product.minTerm,
      Math.min(product.maxTerm, draft.value.months),
    ),
  })
  submissionKey = ''
  view.value = 'apply'
}
function applyConsultation({ result, query }) {
  selectProduct(result.product)
  const product = products.find((item) => item.id === result.product)
  draft.value.months = Math.max(
    product.minTerm,
    Math.min(product.maxTerm, result.suggested_term_months),
  )
  draft.value.purpose = query
}
function submitApplication(send = true) {
  run(async () => {
    submissionKey ||= crypto.randomUUID()
    const saved = await api(
      editingId.value ? `applications/${editingId.value}/` : 'applications/',
      {
        method: editingId.value ? 'PATCH' : 'POST',
        data: draftPayload(draft.value),
        key: submissionKey,
      },
    )
    chosenId.value = saved.id
    editingId.value = saved.id
    if (send) {
      await api(`applications/${saved.id}/submit/`, { method: 'POST' })
      editingId.value = ''
    }
    submissionKey = ''
    await refreshData()
    view.value = 'applications'
  })
}
function submitDraft(id) {
  run(async () => {
    await api(`applications/${id}/submit/`, { method: 'POST' })
    chosenId.value = id
    await refreshData()
  })
}
function cancelApplication(id) {
  if (!confirm('Отменить эту заявку?')) return
  run(async () => {
    await api(`applications/${id}/cancel/`, { method: 'POST', data: {} })
    await refreshData()
  })
}
function openApplication(id) {
  chosenId.value = id
  view.value = 'applications'
  run(() => loadHistory(id))
}
function openCase(id) {
  chosenId.value = id
  view.value = 'detail'
  run(() => loadHistory(id, true))
}
function decide(values) {
  run(async () => {
    await api(`bank/applications/${selectedCase.value.id}/decisions/`, {
      method: 'POST',
      data: values,
    })
    await refreshData()
  })
}
function journey(action, values) {
  run(async () => {
    const app = selectedApplication.value
    const path = `applications/${app.id}/`
    if (action === 'upload') {
      for (const file of values) {
        const form = new FormData()
        form.append('file', file)
        await api(path + 'documents/', { method: 'POST', data: form })
      }
    } else {
      const route =
        action === 'reply'
          ? `info-requests/${values.id}/respond/`
          : action === 'sign'
            ? 'sign/'
            : `offers/${values}/${action}/`
      await api(path + route, {
        method: 'POST',
        data:
          action === 'reply' ? values.values : action === 'sign' ? values : {},
      })
    }
    await refreshData()
  })
}
onMounted(() => {
  if (hasToken())
    run(async () => {
      const user = await api('auth/me/')
      await establish(user.profile_id)
    })
})
</script>

<template>
  <div class="app-shell" :class="{ dark }">
    <header class="top">
      <button
        class="brand"
        aria-label="Альфа.Поток — главная"
        @click="navigate(profile?.role === 'bank' ? 'queue' : 'home')"
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
          @click="navigate(tab)"
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
            :disabled="busy"
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
          @click="logout"
        >
          <AppIcon name="logout" />
        </button>
        <span v-else class="header-secure"
          ><AppIcon name="lock" />Кабинет предпринимателя</span
        >
      </div>
    </header>
    <div v-if="error" class="app-feedback error-feedback" role="alert">
      {{ error }}<button class="link" @click="error = ''">Закрыть</button>
    </div>
    <div v-if="busy" class="app-feedback" role="status">
      Выполняется запрос…
    </div>
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
              :disabled="busy"
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
            @click="navigate(tab)"
          >
            <AppIcon :name="tab" /><span>{{ pages[tab].title }}</span>
          </button>
        </aside>
        <main id="page">
          <div class="demo-notice">
            <span class="demo-dot"></span> Демо-кабинет
            <span class="notice-divider">/</span> {{ profile.company
            }}<span class="notice-local"
              >Заявки и решения сохраняются в базе данных</span
            >
          </div>
          <Transition name="page" mode="out-in" appear>
            <div :key="`${profileId}:${view}`" v-reveal class="page-view">
              <HomePage
                v-if="view === 'home'"
                :profile="profile"
                :application="latest"
                :applications="applications"
                :product="applicationProduct"
                @navigate="navigate"
              />
              <ProductsPage
                v-else-if="view === 'products'"
                @select="selectProduct"
                @consultation="applyConsultation"
              />
              <ApplyPage
                v-else-if="view === 'apply'"
                v-model="drafts[profileId]"
                :profile="profile"
                :busy="busy"
                @submit="submitApplication(true)"
                @save="submitApplication(false)"
                @changed="submissionKey = ''"
              />
              <ApplicationsPage
                v-else-if="view === 'applications'"
                :applications="applications"
                :application="selectedApplication"
                :history="history"
                :documents="documents"
                :busy="busy"
                @open="openApplication"
                @refresh="run(refreshData)"
                @create="newApplication"
                @edit="editDraft"
                @accept="journey('accept', $event)"
                @decline="journey('decline', $event)"
                @sign="journey('sign', $event)"
                @reply="journey('reply', $event)"
                @upload="journey('upload', $event)"
                @error="error = $event"
                @submit="submitDraft"
                @cancel="cancelApplication"
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
                :history="history"
                :documents="documents"
                :busy="busy"
                @back="view = 'queue'"
                @decision="decide"
                @error="error = $event"
              />
            </div>
          </Transition>
        </main>
      </div>
    </Transition>
    <footer class="site-footer">
      <span>© 2026 Альфа.Поток</span
      ><span>Создано для бизнеса. Разработано для хакатона.</span
      ><span>ITigers · Кредитный кабинет</span>
    </footer>
  </div>
</template>
