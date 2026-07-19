/**
 * 应用入口文件
 * 成员1：公共基础 & 成员3：管理后台
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import dayjs from 'dayjs';

import App from './App';
import './styles/index.css';
import 'dayjs/locale/zh-cn';

// 设置 dayjs 中文
dayjs.locale('zh-cn');

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);