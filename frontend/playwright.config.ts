import{defineConfig,devices}from'@playwright/test'
export default defineConfig({testDir:'./e2e',workers:1,use:{baseURL:'http://127.0.0.1:5173'},projects:[{name:'desktop',use:{...devices['Desktop Chrome']}},{name:'mobile',use:{...devices['Pixel 7']}}]})
