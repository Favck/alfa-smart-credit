<script setup>
import PageHeading from '../components/PageHeading.vue'
import UiButton from '../components/UiButton.vue'
import AppIcon from '../components/AppIcon.vue'
import { money, products } from '../data/demo'
defineEmits(['select'])
</script>
<template>
  <PageHeading
    title="Финансирование для ваших планов"
    description="Подберите решение под задачу бизнеса. Всё остальное — поможем пройти шаг за шагом."
  />
  <section class="card product-guide">
    <div>
      <span class="eyebrow">НАЧНЁМ С ВАШЕЙ ЗАДАЧИ</span>
      <h2>На что нужны деньги?</h2>
      <p class="muted">У каждого плана есть подходящее решение</p>
    </div>
    <div class="flex wrap start">
      <UiButton
        v-for="product in products"
        :key="product.id"
        alt
        @click="$emit('select', product.id)"
        >{{ product.purpose }}<AppIcon name="arrow"
      /></UiButton>
    </div>
  </section>
  <div class="grid3 product-grid">
    <article
      v-for="(product, index) in products"
      :key="product.id"
      class="card product-card"
    >
      <span class="news-tag rose">{{
        ['На каждый день', 'В развитие бизнеса', 'Когда нужно вовремя'][index]
      }}</span>
      <h2>{{ product.name }}</h2>
      <p class="muted">{{ product.description }}</p>
      <img
        class="product-art"
        :src="`/images/${['product-growth', 'product-equipment', 'product-overdraft'][index]}.png`"
        alt=""
        loading="lazy"
        width="1024"
        height="1024"
      />
      <div class="product-specs">
        <div>
          <span>Сумма финансирования</span
          ><b
            >{{ money(product.minAmount) }} – {{ money(product.maxAmount) }}</b
          >
        </div>
        <div>
          <span>Срок</span
          ><b>{{ product.minTerm }}–{{ product.maxTerm }} месяцев</b>
        </div>
        <div class="rate-row">
          <span>Ставка от · демо</span
          ><b class="product-rate"
            >{{ product.rate }}<small>% годовых</small></b
          >
        </div>
      </div>
      <UiButton @click="$emit('select', product.id)"
        >Оформить заявку<AppIcon name="arrow"
      /></UiButton>
    </article>
  </div>
  <p class="product-legal muted small">
    <AppIcon name="lock" />Условия и ставки демонстрационные. Окончательные
    условия определяются после рассмотрения заявки.
  </p>
</template>
