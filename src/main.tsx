import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './styles/global.css';
// 引入 authStore 以确保 http 层的鉴权配置在启动时完成注入
import '@/stores/authStore';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
