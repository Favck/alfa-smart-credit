<script setup>
import PageHeading from '../components/PageHeading.vue'
import UiButton from '../components/UiButton.vue'
import { money, products } from '../data/demo'

defineEmits(['select'])
</script>

<template>
  <PageHeading
    title="Деньги для следующего шага"
    description="Развивайте бизнес с подходящим финансированием. Понятные условия, удобное оформление — всё в одном кабинете."
  />
  <div class="card mb product-guide">
    <div class="product-guide-title">
      <h3>На что нужны деньги?</h3>
      <p class="small muted">Выберите цель — покажем подходящие решения</p>
    </div>
    <div class="flex wrap start">
      <UiButton
        v-for="product in products"
        :key="product.id"
        alt
        @click="$emit('select', product.id)"
        >{{ product.purpose }}</UiButton
      >
    </div>
  </div>
  <div class="grid3 product-grid">
    <div
      v-for="(product, index) in products"
      :key="product.id"
      class="card stack product-card"
      :class="`product-tone-${index}`"
    >
      <h2>{{ product.name }}</h2>
      <p class="small muted">{{ product.description }}</p>
      <div class="product-specs">
        <div class="small muted">Сумма</div>
        <b>{{
          product.id === 'overdraft'
            ? 'до ' + money(product.maxAmount)
            : 'от ' + money(product.minAmount)
        }}</b>
        <div class="small muted">Срок</div>
        <b>до {{ product.maxTerm }} мес.</b>
        <div class="small muted">Ставка от (демо)</div>
        <b class="product-rate">от {{ product.rate }}<span>%</span></b>
      </div>
      <img
        class="product-art"
        :src="`/images/${['product-growth', 'product-equipment', 'product-overdraft'][index]}.png`"
        alt=""
        loading="lazy"
        width="1024"
        height="1024"
      />
      <UiButton @click="$emit('select', product.id)">Выбрать →</UiButton>
    </div>
  </div>
  <p class="product-legal small muted">Условия и ставки демонстрационные.</p>
</template>
