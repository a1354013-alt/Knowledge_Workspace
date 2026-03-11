import { createApp } from 'vue'
import App from './App.vue'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import 'primevue/resources/themes/lara-light-blue/theme.css'
import 'primevue/resources/primevue.css'
import 'primeicons/primeicons.css'

const app = createApp(App)

// 使用 PrimeVue
app.use(PrimeVue)

// 註冊 ToastService
app.use(ToastService)

// 掛載應用
app.mount('#app')
