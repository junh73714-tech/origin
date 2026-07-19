import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { RouterProvider } from 'react-router-dom';
import { router } from './routes';
import { appTheme } from './theme';

export function App() {
  return (
    <ConfigProvider locale={zhCN} theme={appTheme}>
      <RouterProvider router={router} />
    </ConfigProvider>
  );
}
