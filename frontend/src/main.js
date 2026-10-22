import { createApp } from 'vue'
import App from './App.vue'
import './styles.css'
import { reveal } from './motion'

createApp(App).directive('reveal', reveal).mount('#app')
