import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { useEffect } from 'react';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useAuthStore } from '@/store/auth';
import { routes } from '@/routes';

// 创建路由实例
const router = createBrowserRouter(routes);

/**
 * 应用根组件
 * 配置 Ant Design 中文语言、主题色
 * 启动时检查认证状态
 */
function App() {
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 8,
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif",
        },
        components: {
          Layout: {
            bodyBg: '#f5f6f8',
            headerBg: '#ffffff',
            siderBg: '#ffffff',
          },
          Menu: {
            itemBg: 'transparent',
            itemSelectedBg: 'rgba(22, 119, 255, 0.08)',
            itemSelectedColor: '#1677ff',
            itemHoverBg: 'rgba(22, 119, 255, 0.04)',
            itemBorderRadius: 8,
          },
          Card: {
            borderRadius: 8,
          },
          Table: {
            headerBg: '#fafafa',
            borderRadius: 8,
          },
          Button: {
            borderRadius: 6,
          },
          Input: {
            borderRadius: 6,
          },
          Select: {
            borderRadius: 6,
          },
          Tag: {
            borderRadius: 4,
          },
        },
      }}
    >
      <RouterProvider router={router} />
    </ConfigProvider>
  );
}

export default App;