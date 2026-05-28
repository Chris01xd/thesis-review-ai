import axios from 'axios'

// En desarrollo: '' → el proxy de Vite reenvía /api → localhost:8000
// En producción: VITE_API_URL → https://tu-backend.onrender.com
const BASE = import.meta.env.VITE_API_URL ?? ''

const client = axios.create({
  baseURL: BASE,
  timeout: 300000, // 5 min — análisis IA puede tardar en servidores lentos
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('tr_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('tr_token')
      localStorage.removeItem('tr_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export default client
